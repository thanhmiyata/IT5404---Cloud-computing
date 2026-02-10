# CÂU HỎI ÔN TẬP: HỆ THỐNG CHẤM ĐIỂM THI TRÊN CLOUD (EXAM SCORING CLOUD)
**Chủ đề:** Cloud Computing, Microservices, Auto-scaling & Elasticity

---

### Phần 1: Kiến trúc & Khả năng Co giãn (Auto-scaling)

#### Câu 1: Tại sao em lại chọn mô hình Pub/Sub trung gian thay vì API gọi trực tiếp sang Worker? Điều này ảnh hưởng thế nào đến khả năng Auto-scaling của hệ thống?
*   **Trả lời:** Việc sử dụng Pub/Sub giúp **Decouple (tách rời)** dịch vụ nhận bài (API) và dịch vụ xử lý (Worker). 
    *   **Về phía API:** Có thể trả về mã `202 Accepted` cực nhanh (low latency) giúp hệ thống không bị nghẽn kết nối khi hàng nghìn sinh viên nộp bài cùng lúc.
    *   **Về phía Worker:** Cloud Run sẽ không bị quá tải bởi các request HTTP dồn dập. Thay vào đó, nó co giãn dựa trên **Backlog (lượng tin nhắn tồn đọng)** trong Pub/Sub. Khi số lượng tin nhắn tăng, GCP sẽ tự động tạo thêm các instance Worker (theo cấu hình `max-instances`) để giải quyết hàng đợi.

#### Câu 2: Giải thích các tham số cấu hình sau trong lệnh deploy Cloud Run và tác động của chúng đến Scaling:
*   `--concurrency=80` (cho api) vs `--concurrency=5` (cho worker)
*   `--max-instances=200` vs `--max-instances=300`
*   **Trả lời:** 
    *   `--concurrency`: Số lượng request tối đa mà một `instance` xử lý đồng thời. 
        *   **API** đặt mức cao (80) vì nó chỉ làm việc nhẹ (ghi DB và đẩy Pub/Sub), giúp tiết kiệm chi phí và scale nhanh.
        *   **Worker** đặt mức thấp (5) vì việc xử lý chấm điểm tốn CPU hơn. Nếu đặt quá cao, CPU của instance sẽ bị nghẽn, làm tăng latency.
    *   `--max-instances`: Ngưỡng chặn trên để tránh chi phí vượt kiểm soát (Cloud Sprawl). Worker được ưu tiên scale mạnh hơn (300) để xử lý dứt điểm backlog nhanh nhất có thể.

---

### Phần 2: Lưu trữ & Dữ liệu (Storage & Database)

#### Câu 3: Trong kịch bản Auto-scale mạnh, thành phần nào thường trở thành "điểm nghẽn" (bottleneck) về lưu trữ? Em đã xử lý vấn đề đó như thế nào trong code?
*   **Trả lời:** Điểm nghẽn thường là **Số lượng kết nối đến Database (Cloud SQL Connections)**. 
*   **Cách xử lý:** Sử dụng **Connection Pooling** trong code (`psycopg2.pool`). Em giới hạn mỗi instance chỉ mở một số lượng connection nhất định và thu hồi ngay khi dùng xong (`put_conn`). Điều này ngăn việc Worker scale-out quá nhanh làm "sập" Database do tràn kết nối.

#### Câu 4: Cloud SQL có khả năng tự động co giãn về dung lượng lưu trữ (Storage Auto-scaling) không? Làm sao để cấu hình nó?
*   **Trả lời:** Có. Cloud SQL hỗ trợ tính năng tự động tăng kích thước ổ đĩa khi sắp hết dung lượng. Cấu hình bằng tham số `--enable-storage-auto-increase` trong lệnh `gcloud sql instances create` hoặc bật trong Console.

---

### Phần 3: Mã nguồn & Cài đặt (Config & Implementation)

#### Câu 5: Tính chất "Idempotency" (Tính lũy đẳng) là gì và tại sao nó cực kỳ quan trọng đối với Worker? Cho ví dụ trong code.
*   **Trả lời:** Idempotency đảm bảo rằng nếu một bài thi bị gửi đến Worker nhiều lần (do Pub/Sub retry hoặc lỗi mạng), kết quả cuối cùng trong DB vẫn duy nhất và chính xác.
*   **Minh chứng trong code:** Trước khi chấm điểm, Worker thực hiện `SELECT ... FOR UPDATE` để kiểm tra trạng thái. Nếu trạng thái đã là `SCORED`, Worker sẽ bỏ qua và trả về thành công ngay lập tức thay vì tính toán lại.

#### Câu 6: Giải thích cơ chế tiêm cấu hình (Configuration Injection) cho Frontend Dashboard.
*   **Trả lời:** Dự án sử dụng script `generate_config.sh` để đọc biến môi trường `PUBLIC_IP` từ file hệ thống và ghi đè vào file `config.js`. Điều này giúp tách biệt mã nguồn Frontend khỏi thông tin hạ tầng thực tế, cho phép deploy linh hoạt trên các VM hoặc môi trường Cloud khác nhau mà không cần sửa code.

---

### Phần 4: Demo & Kiểm thử (Testing)

#### Câu 7: Làm sao em chứng minh được hệ thống đang Auto-scaling thực tế khi bảo vệ?
*   **Trả lời:** Em sẽ sử dụng script `scripts/demo_spike.py` để đẩy hàng nghìn submissions trong thời gian ngắn. Sau đó:
    1.  Mở **Cloud Run Metrics** để xem biểu đồ `Instance Count` tăng trưởng theo thời gian thực.
    2.  Theo dõi biểu đồ **Backlog** trên Dashboard để thấy Pub/Sub hấp thụ spike như thế nào.
    3.  Chứng minh hệ thống không bị lỗi (Error rate ~ 0%) nhờ khả năng co giãn linh hoạt.
