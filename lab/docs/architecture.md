# Architecture — RAG Pipeline (Day 08 Lab)

> Template: Điền vào các mục này khi hoàn thành từng sprint.
> Deliverable của Documentation Owner.

## 1. Tổng quan kiến trúc

```
[Raw Docs — 5 tài liệu nội bộ (.txt)]
    ↓
[index.py: Preprocess → Chunk → Embed → Store]
    ↓
[ChromaDB Vector Store — 29 chunks, cosine similarity]
    ↓
[rag_answer.py: Query → Retrieve (dense/hybrid) → (Rerank) → Generate]
    ↓
[Grounded Answer + Citation [1][2][3]]
```

**Mô tả ngắn gọn:**
> Hệ thống RAG (Retrieval-Augmented Generation) hỗ trợ nhân viên nội bộ tra cứu chính sách công ty — bao gồm SLA hỗ trợ IT, chính sách hoàn tiền CS, kiểm soát truy cập IT Security, FAQ helpdesk và chính sách nhân sự HR. Người dùng đặt câu hỏi bằng tiếng Việt tự nhiên, hệ thống tìm kiếm trong 5 tài liệu nội bộ và trả lời có trích dẫn nguồn, từ chối trả lời khi không đủ dữ liệu. Giải quyết bài toán nhân viên phải tìm kiếm thủ công qua nhiều tài liệu PDF/Markdown rải rác.

---

## 2. Indexing Pipeline (Sprint 1)

### Tài liệu được index
| File | Nguồn | Department | Số chunk |
|------|-------|-----------|---------|
| `policy_refund_v4.txt` | policy/refund-v4.pdf | CS | 6 |
| `sla_p1_2026.txt` | support/sla-p1-2026.pdf | IT | 5 |
| `access_control_sop.txt` | it/access-control-sop.md | IT Security | 7 |
| `it_helpdesk_faq.txt` | support/helpdesk-faq.md | IT | 6 |
| `hr_leave_policy.txt` | hr/leave-policy-2026.pdf | HR | 5 |
| **Tổng** | — | — | **29** |

### Quyết định chunking
| Tham số | Giá trị | Lý do |
|---------|---------|-------|
| Chunk size | 400 tokens (~1600 ký tự) | Đủ lớn để giữ ngữ cảnh một điều khoản, đủ nhỏ để tránh "lost in the middle" khi đưa vào prompt |
| Overlap | 80 tokens (~320 ký tự) | Đảm bảo thông tin nằm ở ranh giới giữa hai chunk không bị mất |
| Chunking strategy | Heading-based (`=== Section ===`) trước, sau đó split theo kích thước nếu section > 1600 ký tự | Ưu tiên ranh giới tự nhiên của tài liệu thay vì cắt cứng theo số ký tự |
| Metadata fields | `source`, `section`, `department`, `effective_date`, `access` | Phục vụ filter theo phòng ban, kiểm tra freshness, và citation chính xác trong câu trả lời |

### Embedding model
- **Model**: OpenAI `text-embedding-3-small`
- **Vector store**: ChromaDB (PersistentClient, lưu tại `lab/chroma_db/`)
- **Similarity metric**: Cosine
- **Collection name**: `rag_lab`

### Lưu ý indexing đã phát hiện (Sprint 4)
> **Bug đã biết**: `preprocess_document()` drop các dòng "Ghi chú / Note" nằm giữa phần header metadata (`Source:`, `Department:`, ...) và heading đầu tiên (`=== Section 1 ===`). Cụ thể: dòng `"Ghi chú: Tài liệu này trước đây có tên Approval Matrix for System Access"` trong `access_control_sop.txt` bị mất → làm giảm completeness của q07. **Fix**: mở rộng điều kiện parse để include các dòng text thuần trong vùng header trước `===`.

---

## 3. Retrieval Pipeline (Sprint 2 + 3)

### Baseline (Sprint 2)
| Tham số | Giá trị |
|---------|---------|
| Strategy | Dense (embedding similarity via ChromaDB) |
| Top-k search | 10 |
| Top-k select | 3 |
| Rerank | Không |
| Query transform | Không |

### Variant (Sprint 3)
| Tham số | Giá trị | Thay đổi so với baseline |
|---------|---------|------------------------|
| Strategy | Hybrid (Dense 0.6 + BM25 0.4, Reciprocal Rank Fusion) | Dense → Hybrid |
| Top-k search | 10 | Không đổi |
| Top-k select | 3 | Không đổi |
| Rerank | LLM-as-reranker (gpt-4o-mini chấm relevance 1-10) | Không → Có |
| Query transform | Không | Không đổi |

**Lý do chọn variant này:**
> Chọn hybrid vì corpus chứa cả ngôn ngữ tự nhiên (chính sách, quy trình) lẫn tên kỹ thuật và alias (mã lỗi ERR-403, nhãn SLA "P1", tên cũ "Approval Matrix"). Dense embedding có thể bỏ lỡ exact keyword khi query dùng tên cũ/alias. BM25 trong hybrid bổ sung khả năng exact match.
>
> Thêm LLM reranker để loại bỏ noise khi hybrid retrieval mang về nhiều candidate hơn. Tuy nhiên qua đánh giá Sprint 4, reranker phản tác dụng trên out-of-scope queries → xem Sprint 4 kết quả.

---

## 4. Generation (Sprint 2)

### Grounded Prompt Template
```
Answer only from the retrieved context below.
If the context is insufficient to answer the question, say you do not know
and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

Question: {query}

Context:
[1] {source} | {section} | score={score}
{chunk_text}

[2] {source} | {section} | score={score}
{chunk_text}

[3] ...

Answer:
```

### LLM Configuration
| Tham số | Giá trị |
|---------|---------|
| Model | `gpt-4o-mini` |
| Temperature | 0 (để output ổn định, tái lập được khi eval) |
| Max tokens | 512 |
| Provider | OpenAI API |

### Điểm mạnh / hạn chế của prompt hiện tại
| | Chi tiết |
|---|---------|
| ✅ Tốt | Citation `[1][2]` nhất quán, answer ngắn và bám context với in-scope queries |
| ⚠️ Yếu | Khi context thiếu, model đôi khi suy diễn thay vì abstain hoàn toàn (q10 VIP refund: Faithfulness=1) |
| ⚠️ Yếu | Chưa có instruction ép model chỉ dẫn người dùng đến nguồn khác khi không đủ dữ liệu |

---

## 5. Evaluation Results (Sprint 4)

### Scorecard tổng hợp
| Metric | Baseline (Dense) | Variant (Hybrid+Rerank) | Winner |
|--------|:---:|:---:|:---:|
| Faithfulness | **4.3/5** | 4.1/5 | Baseline |
| Answer Relevance | **4.7/5** | 4.2/5 | Baseline |
| Context Recall | **5.0/5** | 5.0/5 | Tie |
| Completeness | **4.1/5** | 3.4/5 | Baseline |

### Per-question breakdown
| ID | Category | Baseline F/R/Rc/C | Variant F/R/Rc/C | Winner |
|----|----------|--------------------|------------------|--------|
| q01 | SLA | 5/5/5/5 | 5/5/5/5 | Tie |
| q02 | Refund | 5/5/5/5 | 5/5/5/5 | Tie |
| q03 | Access Control | 5/5/5/5 | 5/5/5/5 | Tie |
| q04 | Refund | 4/5/5/3 | 4/5/5/3 | Tie |
| q05 | IT Helpdesk | 5/5/5/5 | 5/5/5/5 | Tie |
| q06 | SLA | 4/5/5/**5** | 5/5/5/**2** | Baseline |
| q07 | Access Control | 5/5/5/**2** | 5/5/5/**3** | Variant |
| q08 | HR Policy | 5/5/5/4 | 5/5/5/4 | Tie |
| q09 | Insufficient | **4/5/–/5** | 1/1/–/1 | Baseline |
| q10 | Insufficient | 1/2/5/2 | 1/1/5/1 | Baseline |

**Kết luận Sprint 4**: Baseline dense thắng overall. Corpus nhỏ (29 chunks) → Dense recall đã đạt 5.0/5, không cần hybrid. Reranker gây hại trên out-of-scope queries.

---

## 6. Failure Mode Checklist

> Dùng khi debug — kiểm tra lần lượt: index → retrieval → generation

| Failure Mode | Triệu chứng | Cách kiểm tra | Đã gặp? |
|-------------|-------------|---------------|---------|
| Index lỗi | Retrieve về docs cũ / sai version | `inspect_metadata_coverage()` trong index.py | Không |
| Chunking tệ — alias bị drop | Completeness thấp dù Recall cao | Đọc `list_chunks()`, kiểm tra text trước `=== Section 1 ===` | **Có** — q07 |
| Retrieval lỗi | Không tìm được expected source | `score_context_recall()` trong eval.py | Không |
| Generation hallucination | Faithfulness thấp dù context đúng | `score_faithfulness()` trong eval.py | **Có** — q09 baseline, q10 |
| Reranker over-abstain | Model nói "Tôi không biết" với out-of-scope query | So sánh answer baseline vs variant cho câu abstain | **Có** — q09/q10 variant |
| Token overload | Context quá dài → lost in the middle | Kiểm tra độ dài `context_block` | Không (corpus nhỏ) |

---

## 7. Diagram

```mermaid
graph LR
    A[User Query\ntiếng Việt] --> B[Query Embedding\ntext-embedding-3-small]
    B --> C[ChromaDB\nVector Search]
    C --> D[Top-10 Candidates]

    A --> E[BM25 Tokenize]
    E --> F[BM25 Keyword Search]
    F --> D2[Top-10 Sparse]

    D & D2 --> G[RRF Fusion\n0.6 dense + 0.4 sparse]
    G --> H{use_rerank?}

    H -->|Yes - Variant| I[LLM Reranker\ngpt-4o-mini]
    H -->|No - Baseline| J[Top-3 Select]
    I --> J

    J --> K[Build Context Block\nsource + section + score]
    K --> L[Grounded Prompt\nevidence-only + citation]
    L --> M[LLM\ngpt-4o-mini, T=0]
    M --> N[Answer + Citation\n[1][2][3]]

    style G fill:#f9f,stroke:#333
    style I fill:#faa,stroke:#333
    style N fill:#afa,stroke:#333
```
