# BÁO CÁO NHÓM — Lab Day 08: Full RAG Pipeline

**Nhóm:** 68
**Ngày nộp:** 2026-04-13  
**Thành viên:** Tài, Sơn, Quang, Tín, Ngọc

---

## 1. Tóm tắt dự án

### Mục tiêu
Xây dựng hệ thống RAG (Retrieval-Augmented Generation) cho trợ lý nội bộ CS + IT Helpdesk, trả lời câu hỏi về:
- Chính sách hoàn tiền (7 ngày, ngoại lệ digital products)
- SLA ticket P1 (15 phút response, 4 giờ resolution)
- Quy trình cấp quyền (Level 1/2/3 với approvers khác nhau)

### Kết quả đạt được
| Sprint | Nội dung | Status |
|--------|----------|--------|
| 1 | Build Index (29 chunks, 5 docs) | ✅ Hoàn thành |
| 2 | Baseline RAG (Dense + Grounded Prompt) | ✅ Hoàn thành |
| 3 | 3 Variants (Hybrid, Rerank, Query Transform) | ✅ Hoàn thành |
| 4 | Evaluation + A/B Comparison | ✅ Hoàn thành |

---

## 2. Phân công công việc (4 Sprints → 5 người)

> **Lưu ý**: Sprint 3 được chia cho 2 người (Sơn + Tín) vì có nhiều components nhất.

| Thành viên | Vai trò | Sprint | Đóng góp cụ thể |
|------------|---------|--------|-----------------|
| **Tài** | Tech Lead | 1, 2 | `get_embedding()`, `build_index()`, `retrieve_dense()`, `call_llm()`, baseline pipeline |
| **Sơn** | Retrieval Owner | 1, 3a | Chunking strategy, `retrieve_sparse()`, `retrieve_hybrid()`, `rerank_with_llm()` |
| **Tín** | Query Transform | 3b | `transform_query()`, `rag_answer_with_query_transform()`, expansion/HyDE |
| **Quang** | Eval Owner | 4 | LLM-as-Judge functions, scorecard runner, A/B comparison, metrics analysis |
| **Ngọc** | Documentation | All | `architecture.md`, `tuning-log.md`, báo cáo nhóm, GitHub coordination |

### Chi tiết chia Sprint 3:
- **Sprint 3a (Sơn)**: Retrieval variants - Hybrid search (Dense + BM25), RRF fusion, LLM-based reranking
- **Sprint 3b (Tín)**: Query transformation - Expansion, Decomposition, HyDE strategies

---

## 3. Kiến trúc hệ thống

```
[5 Policy Docs]
    ↓
[Preprocess: Extract metadata]
    ↓  
[Chunk: Section-based, 400 tokens]
    ↓
[Embed: OpenAI text-embedding-3-small]
    ↓
[ChromaDB: 29 chunks with metadata]
    ↓
[Query] → [Transform: Optional] → [Retrieve: Dense/Hybrid] → [Rerank: Optional] → [LLM: GPT-4o-mini] → [Answer + Citation]
    ↓
[Evaluate: LLM-as-Judge, 4 metrics]
```

---

## 4. Kết quả Evaluation

### Baseline vs Variant
| Metric | Baseline (Dense) | Variant (Hybrid+Rerank) | Delta |
|--------|-----------------|------------------------|-------|
| Faithfulness | 4.40 | 4.10 | -0.30 ❌ |
| Relevance | 4.70 | 4.20 | -0.50 ❌ |
| Context Recall | 5.00 | 5.00 | 0.00 |
| Completeness | 4.10 | 3.10 | -1.00 ❌ |
| **Average** | **4.55** | **4.10** | **-0.45** |

### Kết luận
> **Baseline Dense tốt hơn Variant Hybrid+Rerank!**
>
> Root cause: LLM-based Rerank không chính xác bằng Dense search thuần hoặc Cross-encoder.
>
> Bài học: "More complex ≠ Better" - phải đo lường thực tế.

---

## 5. Bài học rút ra

### Kỹ thuật
1. **Chunking theo section heading** tốt hơn cắt cứng theo token count
2. **Grounded prompting** cần 4 yếu tố: evidence-only, abstain, citation, temperature=0
3. **LLM-based Rerank** cần evaluation riêng - không nên giả định nó tốt

### Process
1. **A/B Rule**: Chỉ đổi 1 biến/lần - nhóm vi phạm và không rõ lỗi do Hybrid hay Rerank
2. **LLM-as-Judge có bias**: Cần calibrate với few-shot examples
3. **Document negative results**: Kết quả "Variant kém hơn" vẫn có giá trị học tập

---

## 6. Hướng phát triển tiếp theo

| Ưu tiên | Việc cần làm | Lý do |
|---------|-------------|-------|
| 1 | Fix Cross-Encoder (thay LLM rerank) | LLM rerank là root cause của regression |
| 2 | A/B test đúng cách: Hybrid riêng, Rerank riêng | Xác định biến nào tác động |
| 3 | Calibrate LLM-as-Judge với few-shot | Giảm bias trong abstention cases |
| 4 | Thử semantic chunking | Cải thiện q06 (Escalation bị chọn sai) |

---

## 7. Deliverables

| File | Mô tả | Owner |
|------|-------|-------|
| `index.py` | Indexing pipeline | Tài |
| `rag_answer.py` | Retrieval + Generation | Sơn, Tín |
| `eval.py` | Evaluation + Scorecard | Quang |
| `docs/architecture.md` | Kiến trúc hệ thống | Ngọc |
| `docs/tuning-log.md` | A/B experiments log | Ngọc |
| `results/scorecard_baseline.md` | Kết quả baseline | Quang |
| `results/scorecard_variant.md` | Kết quả variant | Quang |
| `reports/individual/*.md` | Báo cáo cá nhân 5 người | Tất cả |
| `reports/group_report.md` | Báo cáo nhóm | Ngọc |

---

## 8. Phân công Push GitHub

| Thứ tự | Người | Files |
|--------|-------|-------|
| 1 | **Tài** | `index.py`, `.env.example`, `requirements.txt`, `reports/individual/tai.md` |
| 2 | **Sơn** | `rag_answer.py` (phần retrieval), `reports/individual/son.md` |
| 3 | **Tín** | `rag_answer.py` (phần query transform), `reports/individual/tin.md` |
| 4 | **Quang** | `eval.py`, `results/`, `reports/individual/quang.md` |
| 5 | **Ngọc** | `docs/`, `reports/group_report.md`, `reports/individual/ngoc.md` |

**Lưu ý**: Sơn và Tín cùng edit `rag_answer.py` → Sơn push trước (retrieval functions), Tín pull rồi add query transform functions.

---

*Document: `reports/group_report.md`*
*Last updated: 2026-04-13*