# Video 02 – Kafka Multi Nodes (Docker Compose)

## Mục tiêu video

Minh họa việc triển khai **Kafka cluster nhiều node** bằng **Docker Compose**, bao gồm:

* Khởi chạy cluster Kafka
* Kiểm tra các container broker
* Truy cập Kafka UI
* Gửi và nhận message trong môi trường multi nodes

---

## Bố cục video đề xuất (6–8 phút)

### 1. Giới thiệu nhanh (10–15s)

**Lời nói:**

> “Đây là video minh họa bài thực hành 01 – triển khai Kafka cluster nhiều node bằng Docker Compose.”

---

### 2. Kiểm tra Docker & Docker Compose (20s)

```bash
docker --version
docker compose version
```

**Narration:**

> “Docker và Docker Compose đã được cài đặt sẵn trên VM.”

---

### 3. Khởi chạy Kafka cluster (30–40s)

```bash
cd /home/bigdata/kafka/cluster/bigdata-learning/l1/kafka
docker compose up -d
```

Kiểm tra container:

```bash
docker ps
```

**Narration:**

> “Kafka cluster gồm nhiều broker và Kafka UI đã được khởi chạy.”

---

### 4. Truy cập Kafka UI (20–30s)

Mở trình duyệt:

```
http://<VM_PUBLIC_IP>:8080
```

**Narration:**

> “Kafka UI cho phép quan sát broker, topic và message trong cluster.”

---

### 5. Tạo topic trong cluster (20s)

```bash
docker exec -it kafka1 kafka-topics \
--create \
--topic test-topic \
--bootstrap-server kafka1:9092 \
--partitions 1 \
--replication-factor 1
```

---

### 6. Producer gửi message (30s)

```bash
docker exec -it kafka1 kafka-console-producer \
--topic test-topic \
--bootstrap-server kafka1:9092
```

Gõ message mẫu:

```
hello cluster
multi node kafka
```

---

### 7. Consumer nhận message (30s)

```bash
docker exec -it kafka1 kafka-console-consumer \
--topic test-topic \
--from-beginning \
--bootstrap-server kafka1:9092
```

**Narration:**

> “Consumer nhận được các message trong môi trường Kafka nhiều node.”

---

## Checklist trước khi nộp

* [ ] docker compose up -d thành công
* [ ] docker ps thấy nhiều broker
* [ ] Kafka UI truy cập được
* [ ] Producer gửi message
* [ ] Consumer nhận message

---

## Kết luận (10s)

> “Video đã minh họa việc triển khai và vận hành Kafka cluster nhiều node bằng Docker Compose.”
