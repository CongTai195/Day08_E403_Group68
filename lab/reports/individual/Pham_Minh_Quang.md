# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phạm Minh Quang 2A202600263  
**Vai trò trong nhóm:** Eval Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Với vai trò Eval Owner, tôi chịu trách nhiệm về test questions, expected evidence và scorecard trong Sprint 3 và Sprint 4:

- **Sprint 3**: Hỗ trợ test các variants với query mẫu, verify output có citation không, kiểm tra abstain behavior với câu hỏi không có trong docs.
- **Sprint 4**: Implement LLM-as-Judge cho 4 scoring functions:
  - `score_faithfulness()` - answer có grounded không?
  - `score_answer_relevance()` - có trả lời đúng câu hỏi không?
  - `score_completeness()` - có đủ thông tin so với expected answer không?
  - `score_context_recall()` - retriever có mang về đúng source không?

Tôi chạy scorecard cho cả Baseline và Variant, tạo A/B comparison report với delta metrics.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Tôi hiểu rõ hơn về **LLM-as-Judge** - cách dùng LLM để tự động chấm điểm RAG output.

Ưu điểm:
- Nhanh: Chấm 10 câu trong ~3 phút thay vì 30 phút manual
- Nhất quán: Không bị bias theo mood như người chấm

Nhược điểm quan sát được:
- LLM có xu hướng chấm cao (optimistic bias) - cần prompt kỹ
- Với câu ambiguous như q09 (ERR-403-AUTH), Baseline được 5/5 faithfulness dù trả lời inference, còn Variant được 1/5 vì nói "không biết"

Bài học: LLM-as-Judge cần calibration - có thể thêm few-shot examples trong prompt để LLM chấm consistent hơn.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Ngạc nhiên nhất là **câu q09 (ERR-403-AUTH) có kết quả trái ngược giữa Baseline và Variant**:

| Config | Faithfulness | Relevance | Completeness |
|--------|-------------|-----------|--------------|
| Baseline | 4 | 5 | 5 |
| Variant | 1 | 1 | 1 |

Câu hỏi này không có trong docs (category: "Insufficient Context"). Expected behavior là abstain.

- **Baseline**: Trả lời inference "ERR-403-AUTH là lỗi liên quan đến quyền truy cập..." - LLM chấm cao vì câu trả lời nghe hợp lý
- **Variant**: Trả lời "Tôi không biết" - LLM chấm thấp vì không cung cấp thông tin

Đây là **limitation của LLM-as-Judge**: Nó reward câu trả lời "có vẻ tốt" thay vì reward abstain đúng cách.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q06 - "Escalation trong sự cố P1 diễn ra như thế nào?"

**Phân tích:**

Đây là câu có sự khác biệt lớn nhất giữa Baseline và Variant:

| Config | Faithfulness | Relevance | Recall | Completeness |
|--------|-------------|-----------|--------|--------------|
| Baseline | 5 | 5 | 5 | **5** |
| Variant | 5 | 5 | 5 | **1** |

**Baseline** trả lời đầy đủ: "Nếu không có phản hồi trong 10 phút, ticket tự động escalate lên Senior Engineer."

**Variant** trả lời lạc đề: "On-call IT Admin có thể cấp quyền tạm thời (tối đa 24 giờ)..." - đây là thông tin về Access Control, không phải SLA escalation!

**Root cause**: Rerank (LLM-based) chọn sai chunk. Khi yêu cầu LLM chấm điểm relevance, nó có thể bị confused bởi keyword "escalation" xuất hiện trong cả SLA docs và Access Control docs.

**Kết luận**: LLM-based rerank không đủ chính xác cho domain-specific queries.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Calibrate LLM-as-Judge với few-shot examples**: Thêm 2-3 examples trong prompt cho mỗi metric, đặc biệt với abstain cases để LLM không penalize câu "Tôi không biết".

2. **Human evaluation sampling**: Chấm manual 3-5 câu rồi so sánh với LLM scores để detect bias. Kết quả q09 cho thấy LLM có thể reward wrong behavior.

---

*File: `reports/individual/quang.md`*
