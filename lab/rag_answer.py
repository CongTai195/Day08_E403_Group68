"""
rag_answer.py — Sprint 2 + Sprint 3: Retrieval & Grounded Answer
================================================================
Sprint 2 (60 phút): Baseline RAG
  - Dense retrieval từ ChromaDB
  - Grounded answer function với prompt ép citation
  - Trả lời được ít nhất 3 câu hỏi mẫu, output có source

Sprint 3 (60 phút): Tuning tối thiểu
  - Thêm hybrid retrieval (dense + sparse/BM25)
  - Hoặc thêm rerank (cross-encoder)
  - Hoặc thử query transformation (expansion, decomposition, HyDE)
  - Tạo bảng so sánh baseline vs variant

Definition of Done Sprint 2:
  ✓ rag_answer("SLA ticket P1?") trả về câu trả lời có citation
  ✓ rag_answer("Câu hỏi không có trong docs") trả về "Không đủ dữ liệu"

Definition of Done Sprint 3:
  ✓ Có ít nhất 1 variant (hybrid / rerank / query transform) chạy được
  ✓ Giải thích được tại sao chọn biến đó để tune
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Dense retrieval: tìm kiếm theo embedding similarity trong ChromaDB.
    """
    import chromadb
    from index import get_embedding, CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")

    query_embedding = get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for i in range(len(results["documents"][0])):
        chunks.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score": 1 - results["distances"][0][i],  # distance → similarity
        })
    return chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).
    Mạnh ở: exact term, mã lỗi, tên riêng (ví dụ: "ERR-403", "P1", "refund")
    """
    import chromadb
    from rank_bm25 import BM25Okapi
    from index import CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    
    all_data = collection.get(include=["documents", "metadatas"])
    documents = all_data["documents"]
    metadatas = all_data["metadatas"]
    
    tokenized_corpus = [doc.lower().split() for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)
    
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    
    chunks = []
    for idx in top_indices:
        chunks.append({
            "text": documents[idx],
            "metadata": metadatas[idx],
            "score": float(scores[idx]),
        })
    return chunks


# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: kết hợp dense và sparse bằng Reciprocal Rank Fusion (RRF).
    RRF_score(doc) = dense_weight * (1 / (60 + dense_rank)) + sparse_weight * (1 / (60 + sparse_rank))
    """
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)
    
    def get_chunk_key(chunk):
        return chunk["metadata"].get("source", "") + "|" + chunk.get("text", "")[:100]
    
    dense_ranks = {get_chunk_key(c): i for i, c in enumerate(dense_results)}
    sparse_ranks = {get_chunk_key(c): i for i, c in enumerate(sparse_results)}
    
    all_chunks = {}
    for chunk in dense_results + sparse_results:
        key = get_chunk_key(chunk)
        if key not in all_chunks:
            all_chunks[key] = chunk
    
    rrf_scores = {}
    for key, chunk in all_chunks.items():
        dense_rank = dense_ranks.get(key, top_k + 100)
        sparse_rank = sparse_ranks.get(key, top_k + 100)
        rrf_score = dense_weight * (1 / (60 + dense_rank)) + sparse_weight * (1 / (60 + sparse_rank))
        rrf_scores[key] = rrf_score
        chunk["score"] = rrf_score
    
    sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
    return [all_chunks[k] for k in sorted_keys[:top_k]]


# =============================================================================
# RERANK (Sprint 3 alternative)
# Cross-encoder để chấm lại relevance sau search rộng
# =============================================================================

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Rerank các candidate chunks bằng LLM.
    Yêu cầu LLM chấm điểm relevance từ 1-10 cho mỗi chunk.
    """
    import json
    
    chunks_text = ""
    for i, chunk in enumerate(candidates):
        chunks_text += f"[{i}] {chunk['text'][:300]}...\n\n"
    
    prompt = f"""Given this question: "{query}"

Rate the relevance of each document chunk below from 1-10 (10 = most relevant).
Output ONLY a JSON array of scores in order, like: [8, 5, 9, 3, ...]

Chunks:
{chunks_text}

Scores (JSON array only):"""

    try:
        response = call_llm(prompt)
        scores = json.loads(response.strip())
        
        for i, chunk in enumerate(candidates):
            if i < len(scores):
                chunk["rerank_score"] = float(scores[i])
            else:
                chunk["rerank_score"] = 0.0
        
        ranked = sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
        return ranked[:top_k]
    except:
        return candidates[:top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.
    Strategies:
      - "expansion": Thêm từ đồng nghĩa, alias
      - "decomposition": Tách query phức tạp thành sub-queries
      - "hyde": Sinh hypothetical document
    """
    import json
    
    if strategy == "expansion":
        prompt = f"""Given this query in Vietnamese: "{query}"
Generate 2 alternative phrasings or related terms that might help find relevant documents.
Output as JSON array of strings only, no explanation.
Example: ["alternative 1", "alternative 2"]"""
    elif strategy == "decomposition":
        prompt = f"""Break down this query into 2 simpler sub-queries: "{query}"
Output as JSON array of strings only.
Example: ["sub-query 1", "sub-query 2"]"""
    elif strategy == "hyde":
        prompt = f"""Write a short paragraph (2-3 sentences) that would be a good answer to: "{query}"
This will be used to search for similar documents. Write in Vietnamese.
Output the paragraph only, no explanation."""
        response = call_llm(prompt)
        return [response.strip()]
    else:
        return [query]
    
    try:
        response = call_llm(prompt)
        alternatives = json.loads(response)
        return [query] + alternatives
    except:
        return [query]


# =============================================================================
# GENERATION — GROUNDED ANSWER FUNCTION
# =============================================================================

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Đóng gói danh sách chunks thành context block để đưa vào prompt.

    Format: structured snippets với source, section, score (từ slide).
    Mỗi chunk có số thứ tự [1], [2], ... để model dễ trích dẫn.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")

        # TODO: Tùy chỉnh format nếu muốn (thêm effective_date, department, ...)
        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        if score > 0:
            header += f" | score={score:.2f}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Xây dựng grounded prompt theo 4 quy tắc từ slide:
    1. Evidence-only: Chỉ trả lời từ retrieved context
    2. Abstain: Thiếu context thì nói không đủ dữ liệu
    3. Citation: Gắn source/section khi có thể
    4. Short, clear, stable: Output ngắn, rõ, nhất quán

    TODO Sprint 2:
    Đây là prompt baseline. Trong Sprint 3, bạn có thể:
    - Thêm hướng dẫn về format output (JSON, bullet points)
    - Thêm ngôn ngữ phản hồi (tiếng Việt vs tiếng Anh)
    - Điều chỉnh tone phù hợp với use case (CS helpdesk, IT support)
    """
    prompt = f"""Answer only from the retrieved context below.
If the context is insufficient to answer the question, say you do not know and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM để sinh câu trả lời.
    Sử dụng OpenAI với temperature=0 để output ổn định.
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512,
    )
    return response.choices[0].message.content


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng cross-encoder rerank không
        verbose: In thêm thông tin debug

    Returns:
        Dict với:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "config": cấu hình pipeline đã dùng

    TODO Sprint 2 — Implement pipeline cơ bản:
    1. Chọn retrieval function dựa theo retrieval_mode
    2. Gọi rerank() nếu use_rerank=True
    3. Truncate về top_k_select chunks
    4. Build context block và grounded prompt
    5. Gọi call_llm() để sinh câu trả lời
    6. Trả về kết quả kèm metadata

    TODO Sprint 3 — Thử các variant:
    - Variant A: đổi retrieval_mode="hybrid"
    - Variant B: bật use_rerank=True
    - Variant C: thêm query transformation trước khi retrieve
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
    }

    # --- Bước 1: Retrieve ---
    if retrieval_mode == "dense":
        candidates = retrieve_dense(query, top_k=top_k_search)
    elif retrieval_mode == "sparse":
        candidates = retrieve_sparse(query, top_k=top_k_search)
    elif retrieval_mode == "hybrid":
        candidates = retrieve_hybrid(query, top_k=top_k_search)
    else:
        raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)

    # --- Bước 5: Extract sources ---
    sources = list({
        c["metadata"].get("source", "unknown")
        for c in candidates
    })

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
    }


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies với cùng một query.

    TODO Sprint 3:
    Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "hybrid"]  # Thêm "sparse" sau khi implement

    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        try:
            result = rag_answer(query, retrieval_mode=strategy, verbose=False)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError as e:
            print(f"Chưa implement: {e}")
        except Exception as e:
            print(f"Lỗi: {e}")


def rag_answer_with_query_transform(
    query: str,
    strategy: str = "expansion",
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
) -> Dict[str, Any]:
    """
    RAG với query transformation: mở rộng query trước khi retrieve.
    """
    queries = transform_query(query, strategy=strategy)
    
    all_candidates = []
    seen_texts = set()
    
    for q in queries:
        if retrieval_mode == "dense":
            candidates = retrieve_dense(q, top_k=top_k_search)
        elif retrieval_mode == "hybrid":
            candidates = retrieve_hybrid(q, top_k=top_k_search)
        else:
            candidates = retrieve_dense(q, top_k=top_k_search)
        
        for c in candidates:
            text_key = c["text"][:100]
            if text_key not in seen_texts:
                seen_texts.add(text_key)
                all_candidates.append(c)
    
    all_candidates = sorted(all_candidates, key=lambda x: x.get("score", 0), reverse=True)[:top_k_select]
    
    context_block = build_context_block(all_candidates)
    prompt = build_grounded_prompt(query, context_block)
    answer = call_llm(prompt)
    
    sources = list({c["metadata"].get("source", "unknown") for c in all_candidates})
    
    return {
        "query": query,
        "expanded_queries": queries,
        "answer": answer,
        "sources": sources,
        "chunks_used": all_candidates,
    }


def compare_all_variants(query: str) -> None:
    """So sánh tất cả variants với cùng một query."""
    print(f"\n{'='*70}")
    print(f"QUERY: {query}")
    print('='*70)
    
    variants = [
        ("Baseline (Dense)", lambda q: rag_answer(q, retrieval_mode="dense")),
        ("Hybrid (Dense+BM25)", lambda q: rag_answer(q, retrieval_mode="hybrid")),
        ("Dense + Rerank", lambda q: rag_answer(q, retrieval_mode="dense", use_rerank=True)),
        ("Query Expansion", lambda q: rag_answer_with_query_transform(q, strategy="expansion")),
    ]
    
    for name, func in variants:
        print(f"\n--- {name} ---")
        try:
            result = func(query)
            print(f"Answer: {result['answer'][:200]}...")
            print(f"Sources: {result['sources']}")
            if "expanded_queries" in result:
                print(f"Expanded: {result['expanded_queries']}")
        except Exception as e:
            print(f"Error: {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",
    ]

    print("\n--- Sprint 2: Test Baseline (Dense) ---")
    for query in test_queries[:2]:
        print(f"\nQuery: {query}")
        try:
            result = rag_answer(query, retrieval_mode="dense", verbose=False)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except Exception as e:
            print(f"Error: {e}")

    print("\n--- Sprint 3: So sánh tất cả variants ---")
    compare_all_variants("Approval Matrix để cấp quyền là tài liệu nào?")

    print("\n\nSprint 3 hoàn thành!")
