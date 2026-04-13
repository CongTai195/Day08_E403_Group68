# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 2026-04-13  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = "gpt-4o-mini"
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.3 /5 |
| Answer Relevance | 4.7 /5 |
| Context Recall | 5.0 /5 |
| Completeness | 4.1 /5 |

**Per-question chi tiết:**
| ID | Category | F | R | Rc | C | Ghi chú |
|----|----------|---|---|----|---|---------|
| q01 | SLA | 5 | 5 | 5 | 5 | Hoàn hảo |
| q02 | Refund | 5 | 5 | 5 | 5 | Hoàn hảo |
| q03 | Access Control | 5 | 5 | 5 | 5 | Hoàn hảo |
| q04 | Refund | 4 | 5 | 5 | 3 | Model thêm ngoại lệ không hoàn toàn đúng |
| q05 | IT Helpdesk | 5 | 5 | 5 | 5 | Hoàn hảo |
| q06 | SLA | 4 | 5 | 5 | 5 | Nhỏ: answer lặp lại bước từ nhiều section |
| q07 | Access Control | 5 | 5 | 5 | 2 | Dense tìm đúng doc nhưng không biết alias "Approval Matrix" (bị drop ở preprocess) |
| q08 | HR Policy | 5 | 5 | 5 | 4 | Thiếu điều kiện "Team Lead phê duyệt" |
| q09 | Insufficient | 4 | 5 | N/A | 5 | Model hallucinated ERR-403-AUTH explanation thay vì abstain |
| q10 | Refund | 1 | 2 | 5 | 2 | Model nói "không có thông tin" nhưng rồi tự kết luận — không grounded |

**Câu hỏi yếu nhất (điểm thấp):**
> - **q10** (VIP refund — Faithfulness=1, Relevance=2, Completeness=2): Context recall = 5 (đúng doc), nhưng model tự thêm kết luận "quy trình không khác" dù không có bằng chứng → Faithfulness=1. Đây là "lost in abstain" — model không hoàn toàn từ chối mà lại suy diễn.
> - **q07** (Approval Matrix alias — Completeness=2): Dense retrieval tìm đúng document (recall=5), nhưng note "Tài liệu này trước đây có tên Approval Matrix" bị drop trong bước preprocess (nằm giữa header metadata và `=== Section 1 ===`, ngoài cả hai vùng parse). Model không biết alias nên completeness thấp.
> - **q04** (Digital product refund — Completeness=3): Model trả lời "không được hoàn tiền, trừ khi có lỗi nhà sản xuất" — thêm điều kiện ngoại lệ không có trong câu hỏi gốc, làm lẫn lộn với Điều 2.

**Giả thuyết nguyên nhân (Error Tree):**
- [x] Indexing: Chunking cắt metadata alias — "Ghi chú: Tài liệu này trước đây có tên Approval Matrix" bị drop trong `preprocess_document()` vì nằm ngoài cả header và section
- [ ] Indexing: Metadata thiếu effective_date — **Không xảy ra**, tất cả chunks đủ metadata
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias — **Bán phần**: dense vẫn tìm được doc (recall=5) nhưng alias text đã mất từ indexing
- [ ] Retrieval: Top-k quá ít → thiếu evidence — **Không xảy ra**, top_k=10 đủ với corpus 29 chunks
- [x] Generation: Prompt không đủ grounding — q10: model tự suy diễn khi không có đủ context (thiếu negative example trong prompt)
- [ ] Generation: Context quá dài → lost in the middle — **Không xảy ra**, corpus nhỏ, context gọn

---

## Variant 1 (Sprint 3)

**Ngày:** 2026-04-13  
**Biến thay đổi:** `retrieval_mode = "hybrid"` + `use_rerank = True` (đổi 2 biến cùng lúc — xem nhận xét)  
**Lý do chọn biến này:**
> Chọn hybrid vì q07 (Approval Matrix alias) và q09 (ERR-403-AUTH — keyword không xuất hiện trong corpus) là dạng query mà dense embedding có thể bỏ lỡ do thiếu semantic overlap. BM25 trong hybrid mạnh hơn ở exact keyword. Thêm rerank để loại bỏ noise khi hybrid mang về nhiều candidate hơn.
>
> *Lưu ý vi phạm A/B rule*: Thay đổi đồng thời hybrid + rerank nên không tách biệt được contribution. Nếu có thêm thời gian, cần chạy Variant 1a (hybrid only) và Variant 1b (dense + rerank) riêng.

**Config thay đổi:**
```
retrieval_mode = "hybrid"   # dense (0.6 weight) + BM25 (0.4 weight), RRF fusion
use_rerank = True           # LLM reranker chấm lại top-10, chọn top-3
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.3/5 | 4.1/5 | -0.2 |
| Answer Relevance | 4.7/5 | 4.2/5 | -0.5 |
| Context Recall | 5.0/5 | 5.0/5 | 0.0 |
| Completeness | 4.1/5 | 3.4/5 | -0.7 |

**Per-question so sánh:**
| Câu | Baseline F/R/Rc/C | Variant F/R/Rc/C | Better? | Lý do |
|-----|-------------------|------------------|---------|-------|
| q01 | 5/5/5/5 | 5/5/5/5 | Tie | — |
| q02 | 5/5/5/5 | 5/5/5/5 | Tie | — |
| q03 | 5/5/5/5 | 5/5/5/5 | Tie | — |
| q04 | 4/5/5/3 | 4/5/5/3 | Tie | — |
| q05 | 5/5/5/5 | 5/5/5/5 | Tie | — |
| q06 | 4/5/5/5 | 5/5/5/2 | **Baseline** | Hybrid mang thêm access-control chunks làm lẫn P1 escalation với emergency access |
| q07 | 5/5/5/2 | 5/5/5/3 | **Variant** | BM25 keyword "Approval Matrix" cải thiện completeness 2→3 |
| q08 | 5/5/5/4 | 5/5/5/4 | Tie | — |
| q09 | 4/5/N/5 | 1/1/N/1 | **Baseline** | Reranker loại bỏ mọi chunk (không có ERR-403-AUTH trong corpus) → model over-abstain "Tôi không biết", judge phạt nặng |
| q10 | 1/2/5/2 | 1/1/5/1 | **Baseline** | Tương tự q09 — reranker dẫn đến over-abstain |

**Nhận xét:**
> - **Cải thiện**: q07 (Approval Matrix alias) completeness tăng 2→3. BM25 đã giúp tìm kiếm keyword "Approval Matrix" hiệu quả hơn. Tuy nhiên completeness vẫn chưa đạt 5 vì alias note bị mất trong preprocess (vấn đề indexing, không phải retrieval).
>
> - **Tệ hơn đáng kể**: q09 và q10. Reranker LLM khi không tìm thấy chunk liên quan (ERR-403-AUTH không tồn tại trong corpus) → chấm điểm tất cả chunks 0 → top-3 là noise → model nói "Tôi không biết" ngắn gọn. Đây là trường hợp reranker phản tác dụng với out-of-scope queries.
>
> - **Tệ hơn nhẹ**: q06 (P1 escalation). Hybrid BM25 từ "escalation" match với access-control-sop.md (cũng có "escalation" keyword) → context bị pha trộn → model nhầm P1 SLA escalation với emergency access escalation.

**Kết luận:**
> Variant 1 (hybrid + rerank) **không tốt hơn baseline** trên corpus này.
>
> Bằng chứng: Tổng điểm giảm ở 3/4 metrics (Faithfulness -0.2, Relevance -0.5, Completeness -0.7). Chỉ Context Recall không đổi.
>
> **Nguyên nhân chính**:
> 1. Reranker gây hại cho out-of-scope queries (q09, q10) — khi không có chunk nào liên quan, reranker hạ hết điểm, model over-abstain.
> 2. Corpus nhỏ (29 chunks) — dense retrieval đã đủ tốt, recall=5.0 cả baseline lẫn variant. Hybrid không có thêm lợi ích đáng kể.
> 3. BM25 cross-section noise (q06) — "escalation" keyword xuất hiện ở nhiều doc khác nhau.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** Sửa `preprocess_document()` để giữ lại dòng "Ghi chú" / alias notes trước `=== Section 1 ===`  
**Config:**
```
# Thay đổi ở index.py, không phải retrieval config
# Giả thuyết: fixing indexing bug → q07 completeness tăng lên 4-5
# Biến thay đổi: chunking/indexing strategy
retrieval_mode = "dense"   # giữ nguyên baseline
use_rerank = False          # giữ nguyên baseline
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.3 | 4.1 | (chưa chạy) | Baseline |
| Answer Relevance | 4.7 | 4.2 | (chưa chạy) | Baseline |
| Context Recall | 5.0 | 5.0 | (chưa chạy) | Tie |
| Completeness | 4.1 | 3.4 | (chưa chạy) | Baseline |

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > **Generation grounding failure**: Model không abstain đúng cách khi context thiếu (q10 tự suy diễn, q09 trong baseline hallucinate). Prompt hiện tại chưa đủ mạnh ở rule "abstain completely" — model vẫn cố trả lời thay vì từ chối rõ ràng và chỉ dẫn người dùng đến nguồn khác.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > **`use_rerank`** — Reranker LLM tác động mạnh nhất (cả tốt lẫn xấu). Với in-scope queries (q01-q08) hiệu quả tương đương, nhưng với out-of-scope queries (q09, q10) reranker loại bỏ mọi candidate khiến model over-abstain. Trên corpus nhỏ (29 chunks), rerank không đem lại lợi ích đủ lớn để bù rủi ro này.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > **Sửa indexing bug cho alias notes** (Variant 2): Cập nhật `preprocess_document()` để include dòng "Ghi chú/Note" nằm giữa header metadata và section đầu tiên. Dự kiến sẽ giúp q07 completeness từ 2 lên 4-5 mà không cần thay đổi retrieval. Đây là "free win" vì chỉ sửa logic index, không tốn thêm API call.
