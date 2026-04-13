# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trương Gia Ngọc  
**Vai trò trong nhóm:** Documentation Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Với vai trò Documentation Owner, tôi chịu trách nhiệm về tài liệu và báo cáo trong Sprint 4:

- Hoàn thiện **`docs/architecture.md`**: Mô tả kiến trúc pipeline từ index đến generation, document các quyết định thiết kế (chunk size, embedding model, retrieval strategy).

- Hoàn thiện **`docs/tuning-log.md`**: Ghi lại kết quả Baseline vs Variant với delta metrics, phân tích câu hỏi yếu nhất và root cause.

- Tổng hợp **báo cáo nhóm**: Tập hợp đóng góp từ 5 thành viên, tóm tắt kết quả và bài học.

- Tạo **README hướng dẫn GitHub**: Phân công file cho từng người push, đảm bảo không conflict.

Tôi làm việc chặt với Quang để document kết quả eval và với cả nhóm để thu thập insights.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Tôi hiểu rõ hơn về **tầm quan trọng của A/B Rule: Chỉ đổi MỘT biến mỗi lần**.

Trước lab, tôi nghĩ càng nhiều cải tiến càng tốt. Nhưng kết quả:
- Variant (Hybrid + Rerank) kém hơn Baseline!
- Không biết lỗi do Hybrid hay do Rerank

Nếu làm lại, sẽ test:
1. Baseline Dense vs Hybrid (giữ rerank=False)
2. Baseline Dense vs Dense+Rerank (giữ retrieval_mode="dense")

Rồi mới kết luận biến nào có tác động tích cực/tiêu cực.

Bài học để document: "Mỗi experiment chỉ thay đổi 1 config. Ghép nhiều thay đổi = không biết thủ phạm."

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất là **document kết quả trái ngược kỳ vọng**.

Nhóm kỳ vọng Variant sẽ tốt hơn Baseline. Khi kết quả ngược lại:
- Faithfulness: 4.40 → 4.10 (-0.30)
- Completeness: 4.10 → 3.10 (-1.00)

Tôi phải document một cách trung thực thay vì "spin" kết quả. Bài học lấy từ đây:
- "Không phải complexity nào cũng tốt"
- "LLM-based rerank cần evaluation riêng"
- "A/B testing quan trọng hơn giả định"

Đây là insight quan trọng hơn nhiều so với "Variant tốt hơn 10%" - cho thấy nhóm hiểu process.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q02 - "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?"

**Phân tích:**

Đây là câu "easy" mà cả hai configs đều trả lời hoàn hảo:

| Config | Faithfulness | Relevance | Recall | Completeness |
|--------|-------------|-----------|--------|--------------|
| Baseline | 5 | 5 | 5 | 5 |
| Variant | 5 | 5 | 5 | 5 |

**Tại sao thành công?**

1. **Indexing tốt**: Chunk chứa "Điều 2: Điều kiện được hoàn tiền" giữ nguyên cả section, không cắt giữa điều khoản.

2. **Retrieval chính xác**: Query "hoàn tiền trong bao nhiêu ngày" match cao với chunk chứa "trong vòng 7 ngày làm việc".

3. **Grounded prompt hiệu quả**: LLM trích đúng số liệu "7 ngày" và cite [1].

**Tại sao document câu này?**

Để chứng minh pipeline hoạt động đúng với happy path. Không phải mọi câu đều thất bại - câu đơn giản với exact match trong docs sẽ luôn được trả lời tốt.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Tạo Decision Tree cho configuration**: Dựa trên kết quả eval, tạo sơ đồ "Khi nào dùng Hybrid?", "Khi nào dùng Rerank?" dựa trên đặc điểm query.

2. **Viết Run Book**: Hướng dẫn troubleshooting cho production - "Nếu recall thấp, check chunking. Nếu faithfulness thấp, check prompt."
