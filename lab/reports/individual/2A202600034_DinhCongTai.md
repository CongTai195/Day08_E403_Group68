# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Đinh Công Tài  
**MSSV:** 2A202600034  
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Với vai trò Tech Lead, tôi chịu trách nhiệm chính trong Sprint 1 và Sprint 2, đảm bảo pipeline hoạt động end-to-end. Cụ thể:

- **Sprint 1**: Implement `get_embedding()` sử dụng OpenAI text-embedding-3-small model và hoàn thiện `build_index()` để lưu 29 chunks từ 5 tài liệu vào ChromaDB.
- **Sprint 2**: Implement `retrieve_dense()` để query vector store và `call_llm()` để gọi GPT-4o-mini sinh câu trả lời có citation.
- Tôi cũng phối hợp với Sơn (Retrieval Owner) để đảm bảo chunking strategy phù hợp và kết nối với Quang (Eval Owner) để test các edge cases.

Công việc của tôi tạo nền tảng cho cả nhóm - không có index và baseline thì không thể chạy variant hay evaluation.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Tôi hiểu rõ hơn về **Grounded Prompting** - cách ép LLM chỉ trả lời từ context đã retrieve thay vì dùng internal knowledge.

Trước lab, tôi nghĩ chỉ cần nói "trả lời từ context" là đủ. Nhưng qua việc implement `build_grounded_prompt()`, tôi nhận ra prompt cần 4 yếu tố:
1. **Evidence-only rule**: "Answer only from retrieved context"
2. **Abstain instruction**: "Say you don't know if insufficient"  
3. **Citation format**: "[1], [2]..." để dễ verify
4. **Temperature=0**: Để output ổn định cho evaluation

Khi test với câu "ERR-403-AUTH là lỗi gì?", baseline trả lời "không có thông tin chi tiết" thay vì bịa - đúng như kỳ vọng của grounded prompting.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều ngạc nhiên nhất là **Baseline Dense tốt hơn Variant Hybrid+Rerank** trong A/B comparison!

Ban đầu tôi kỳ vọng Hybrid + Rerank sẽ cải thiện vì:
- Hybrid kết hợp cả semantic (Dense) và exact match (BM25)
- Rerank lọc ra chunks relevant nhất

Nhưng kết quả:
- Baseline: Faithfulness 4.40, Completeness 4.10
- Variant: Faithfulness 4.10, Completeness 3.10

Lỗi nằm ở **LLM-based Rerank** - khi yêu cầu LLM chấm điểm relevance, nó có thể chọn chunks kém hơn Dense search thuần. Câu q06 (Escalation P1) variant chỉ đạt completeness 1/5 vs baseline 5/5.

Bài học: "More complex ≠ Better" - phải đo lường thực tế.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q01 - "SLA xử lý ticket P1 là bao lâu?"

**Phân tích:**

Đây là câu hỏi "easy" category và cả Baseline lẫn Variant đều trả lời đúng:

| Config | Faithfulness | Relevance | Recall | Completeness |
|--------|-------------|-----------|--------|--------------|
| Baseline | 5 | 5 | 5 | 5 |
| Variant | 5 | 5 | 5 | 3 |

**Baseline** trả lời: "SLA ticket P1 là 4 giờ khắc phục, 15 phút phản hồi ban đầu [1]" - đầy đủ cả 2 thông tin.

**Variant** trả lời: "SLA ticket P1 là 4 giờ [1]" - đúng nhưng thiếu chi tiết "15 phút phản hồi ban đầu".

**Vấn đề**: Không nằm ở Retrieval (recall = 5/5 cả hai) mà ở **Rerank + Generation**. Rerank có thể đã đẩy chunk chứa "15 phút first response" xuống thấp hơn, khiến LLM chỉ thấy thông tin "4 giờ resolution".

**Kết luận**: Với câu hỏi đơn giản, Dense baseline đủ tốt. Rerank chỉ cần thiết khi Dense trả về nhiều noise.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Thay LLM-based Rerank bằng Cross-Encoder**: Kết quả eval cho thấy LLM rerank không hiệu quả (completeness giảm 1.0 điểm). Cross-encoder như `ms-marco-MiniLM` sẽ chấm điểm chính xác hơn mà không cần gọi LLM.

2. **Thử Query Expansion riêng lẻ**: Trong Sprint 3, tôi thấy Query Expansion tạo ra các phiên bản hay ("Tài liệu phê duyệt quyền truy cập", "Ma trận phê duyệt"). Sẽ thử A/B test riêng Query Expansion vs Baseline.

---

*File: `reports/individual/tai.md`*
