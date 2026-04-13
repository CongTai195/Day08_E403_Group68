# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Đào Văn Sơn  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 2026-04-13  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Với vai trò Retrieval Owner, tôi chịu trách nhiệm chính về chunking, metadata và retrieval strategy trong Sprint 1 và Sprint 3:

- **Sprint 1**: Thiết kế chunking strategy - quyết định chunk theo section heading "=== ... ===" thay vì cắt cứng theo số ký tự. Đảm bảo metadata (source, section, department, effective_date) được gắn đầy đủ cho mỗi chunk.
- **Sprint 3**: Implement 3 variants retrieval:
  - `retrieve_sparse()` với BM25 cho exact keyword match
  - `retrieve_hybrid()` với Reciprocal Rank Fusion (RRF)
  - `rerank()` với LLM-based scoring

Tôi phối hợp với Tài để test chunking quality qua `list_chunks()` và với Quang để đánh giá Context Recall của từng variant.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Tôi hiểu rõ hơn về **Hybrid Retrieval với RRF (Reciprocal Rank Fusion)**.

RRF là cách kết hợp Dense và Sparse search thông minh:
```
RRF_score(doc) = 0.6 * (1/(60 + dense_rank)) + 0.4 * (1/(60 + sparse_rank))
```

- Số 60 là hằng số RRF tiêu chuẩn, giúp tránh phụ thuộc quá nhiều vào rank cao nhất
- Dense weight 0.6 vì semantic matching quan trọng hơn
- Sparse weight 0.4 để bắt exact keywords như "P1", "Level 3"

Trước lab, tôi nghĩ đơn giản là cộng score lại. Nhưng RRF dùng **rank** thay vì score, tránh vấn đề scale khác nhau giữa cosine similarity và BM25 score.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất là **Cross-encoder không chạy được** do xung đột Keras 3 vs TensorFlow.

Ban đầu tôi implement:
```python
from sentence_transformers import CrossEncoder
model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
```

Nhưng gặp lỗi: "Keras 3 not yet supported in Transformers". Dù đã cài `tf-keras`, vẫn không fix được.

**Giải pháp**: Chuyển sang LLM-based rerank - yêu cầu GPT chấm điểm relevance từ 1-10 cho mỗi chunk. Tuy nhiên, kết quả A/B cho thấy LLM rerank kém hơn không rerank - LLM có xu hướng chấm điểm không chính xác bằng cross-encoder được train riêng cho task này.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** q07 - "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**

Đây là câu hỏi "hard" category vì query dùng **alias** ("Approval Matrix") trong khi docs dùng tên mới ("Access Control SOP").

| Config | Faithfulness | Relevance | Recall | Completeness |
|--------|-------------|-----------|--------|--------------|
| Baseline | 5 | 5 | 5 | 2 |
| Variant | 5 | 5 | 5 | 2 |

**Điều thú vị**: Cả Dense lẫn Hybrid đều đạt Context Recall = 5/5 - tức là đều tìm được đúng source `it/access-control-sop.md`.

**Vấn đề**: Completeness thấp (2/5) không phải lỗi retrieval mà lỗi **generation**. Expected answer là: "Tài liệu 'Approval Matrix' hiện có tên mới là 'Access Control SOP'". Nhưng LLM không nhận ra cần giải thích sự thay đổi tên.

**Bài học**: Với alias queries, vấn đề có thể nằm ở generation prompt - cần thêm instruction "Nếu query dùng tên cũ/alias, hãy giải thích tên hiện tại".

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

1. **Fix Cross-Encoder**: Thử downgrade TensorFlow hoặc dùng PyTorch-only environment để cross-encoder chạy được. Eval cho thấy LLM rerank không hiệu quả.

2. **Semantic Chunking**: Thay vì chunk theo heading, thử semantic chunking - nhóm các câu có nghĩa liên quan. Câu q06 (Escalation P1) có thể bị chunk cắt giữa quy trình escalation.

---


