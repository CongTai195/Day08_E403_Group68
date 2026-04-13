# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Trọng Tín
**Vai trò trong nhóm:** Query Transform Specialist  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi chịu trách nhiệm về **Query Transformation** trong Sprint 3:

- Implement `transform_query()` với 3 strategies:
  - **Expansion**: Dùng LLM sinh 2 phiên bản query khác ("Approval Matrix" → "Tài liệu phê duyệt quyền", "Ma trận phê duyệt")
  - **Decomposition**: Tách query phức tạp thành sub-queries
  - **HyDE**: Sinh hypothetical document để search

- Implement `rag_answer_with_query_transform()` - pipeline RAG với query expansion trước khi retrieve.

- Hỗ trợ Sơn test `compare_all_variants()` để test 4 variants cùng lúc.

Công việc của tôi giúp tăng recall cho queries dùng alias hoặc tên cũ - như "Approval Matrix" khi docs đã đổi tên thành "Access Control SOP".

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Tôi hiểu rõ hơn về **Query Expansion** và khi nào nó hiệu quả.

Trước lab, tôi nghĩ expansion luôn tốt vì "nhiều query hơn = nhiều kết quả hơn". Nhưng thực tế:

**Khi expansion tốt**:
- Query dùng alias/tên cũ: "Approval Matrix" → "Access Control SOP"
- Query ngắn, mơ hồ: "hoàn tiền" → "chính sách hoàn tiền", "refund policy"

**Khi expansion không cần thiết**:
- Query đã cụ thể: "SLA xử lý ticket P1 là bao lâu?" - Dense search đủ tìm đúng
- Query chứa exact term trong docs: "Level 3", "7 ngày làm việc"

Bài học: Expansion là **fallback strategy**, không phải default. Chỉ dùng khi Dense baseline thất bại.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất là **parse JSON output từ LLM** cho query expansion.

Prompt của tôi:
```
Generate 2 alternative phrasings...
Output as JSON array of strings only.
```

Nhưng LLM thường trả về:
```
Here are the alternatives:
["alternative 1", "alternative 2"]
```

Phải strip text trước JSON và bọc try-except để fallback về query gốc khi parse fail.

Điều ngạc nhiên: Expansion sinh ra các phiên bản rất hay! Với "Approval Matrix để cấp quyền", LLM tạo:
- "Tài liệu phê duyệt quyền truy cập"
- "Ma trận phê duyệt quyền hạn"

Cả hai đều chứa keywords xuất hiện trong `access_control_sop.txt`.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q10 - "Nếu cần hoàn tiền khẩn cấp cho khách hàng VIP, quy trình có khác không?"

**Phân tích:**

Đây là câu "hard" category vì hỏi về case **không có trong docs** (chính sách không đề cập VIP).

| Config | Faithfulness | Relevance | Recall | Completeness |
|--------|-------------|-----------|--------|--------------|
| Baseline | 1 | 2 | 5 | 2 |
| Variant | 1 | 1 | 5 | 2 |

**Tại sao Recall = 5/5?** Cả hai đều retrieve đúng `policy/refund-v4.pdf` - source expected.

**Tại sao Faithfulness = 1?** Câu trả lời là "Không có thông tin..." - LLM-as-Judge chấm thấp vì answer không cung cấp giá trị, dù đó là abstain đúng cách!

**Vấn đề**: LLM-as-Judge không được train để reward correct abstention. Expected answer là "Tài liệu không đề cập quy trình VIP, tất cả theo quy trình tiêu chuẩn" - cần thêm context trong abstain.

**Bài học**: Prompt cần hướng dẫn abstain có thông tin: "Nếu không đủ data, nói rõ docs hiện có không đề cập VIP".

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **A/B test Query Expansion riêng**: Kết quả hiện tại lẫn lộn cùng Hybrid+Rerank. Sẽ test: Baseline Dense vs Dense+Expansion để thấy expansion đóng góp bao nhiêu.

2. **Implement HyDE cho queries mơ hồ**: Với câu như "quy trình khi cần thay đổi quyền nhanh", sinh hypothetical document sẽ giúp match tốt hơn với "Escalation" section trong SLA.

---

*File: `reports/individual/tin.md`*
