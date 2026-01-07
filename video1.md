# Video 01 – Kafka Single Node (KRaft Mode)

## Mục tiêu video

Minh họa việc triển khai **Kafka single node** sử dụng **KRaft mode (không Zookeeper)** và thực hiện gửi/nhận message cơ bản.

Video chứng minh:

* Kafka đã được cài đặt và khởi chạy thành công
* Có thể tạo topic
* Producer gửi message
* Consumer nhận message

---

## Bố cục video đề xuất (5–7 phút)

### 1. Giới thiệu nhanh (10–15s)

**Lời nói:**

> “Đây là video minh họa bài thực hành 01 – triển khai Kafka single node sử dụng KRaft mode.”

---

### 2. Kiểm tra môi trường (20–30s)

**Mục tiêu:** chứng minh môi trường đã sẵn sàng

```bash
java -version
```

**Narration gợi ý:**

> “Kafka được triển khai trên Ubuntu với Java 17 theo yêu cầu của bài thực hành.”

---

### 3. Khởi tạo Kafka storage (KRaft) (30–40s)

```bash
cd /home/bigdata/kafka/standalone/kafka
./bin/kafka-storage.sh random-uuid
```

(Sao chép CLUSTER_ID)

```bash
./bin/kafka-storage.sh format -t <CLUSTER_ID> -c config/kraft/server.properties
```

**Narration:**

> “Kafka sử dụng KRaft mode, do đó cần khởi tạo metadata storage trước khi khởi chạy broker.”

---

### 4. Khởi chạy Kafka server (30s)

```bash
./bin/kafka-server-start.sh config/kraft/server.properties
```

**Narration:**

> “Kafka broker được khởi chạy trên cổng 9092.”

---

### 5. Tạo topic (20s)

(Mở terminal mới)

```bash
./bin/kafka-topics.sh \
--create \
--topic test-topic \
--bootstrap-server localhost:9092 \
--partitions 1 \
--replication-factor 1
```

---

### 6. Gửi message – Producer (30s)

```bash
./bin/kafka-console-producer.sh \
--topic test-topic \
--bootstrap-server localhost:9092
```

Gõ vài message mẫu:

```
hello kafka
single node test
```

---

### 7. Nhận message – Consumer (30s)

```bash
./bin/kafka-console-consumer.sh \
--topic test-topic \
--from-beginning \
--bootstrap-server localhost:9092
```

**Narration:**

> “Consumer nhận đầy đủ message đã được gửi, chứng minh Kafka single node hoạt động đúng.”

---

## Checklist trước khi nộp (Video 01 – Kafka Single Node)

Checklist này **phải được thể hiện đầy đủ trong video**, không chỉ thực hiện ngầm:

1. Có phần mở đầu video, nêu rõ: *Lab 1 – Kafka – Single Node (KRaft Mode)*
2. Hiển thị rõ terminal và thư mục làm việc Kafka (`standalone/kafka`)
3. Chạy và hiển thị kết quả `java -version` (Java 17)
4. Thực hiện `kafka-storage.sh random-uuid` và hiển thị CLUSTER_ID
5. Thực hiện `kafka-storage.sh format` thành công (không lỗi)
6. Khởi chạy Kafka server và log cho thấy broker start thành công
7. Tạo topic thành công (`kafka-topics.sh --create`)
8. Producer gửi được message (gõ message trực tiếp trên terminal)
9. Consumer nhận đúng các message đã gửi
10. Có câu kết luận ngắn ở cuối video xác nhận Kafka single node hoạt động đúng

---

## Kết luận (10s)

> “Video đã minh họa việc triển khai Kafka single node và thực hiện gửi/nhận message cơ bản.”
