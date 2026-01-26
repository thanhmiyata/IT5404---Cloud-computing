import requests
import json
import time
import uuid
import random

API_URL = "http://localhost:8080/v1/exams/exam-2/submissions"
API_KEY = "change-me"

def submit_test(user_id):
    payload = {
        "userId": user_id,
        "answers": [
            {"questionId": "q1", "choice": random.choice(["A", "B", "C", "D"])},
            {"questionId": "q2", "choice": random.choice(["A", "B", "C", "D"])}
        ]
    }
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }
    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload, headers=headers)
        end_time = time.time()
        
        if response.status_code == 202:
            data = response.json()
            print(f"✅ [SUCCESS] User: {user_id} | SubID: {data['submissionId']} | Time: {round((end_time-start_time)*1000)}ms")
        else:
            print(f"❌ [FAILED] User: {user_id} | Status: {response.status_code} | Error: {response.text}")
    except Exception as e:
        print(f"⚠️ [ERROR] {e}")

if __name__ == "__main__":
    count = 30  # Số lượng bài nộp giả lập
    print(f"🚀 Bắt đầu nộp {count} bài thi hàng loạt...")
    
    for i in range(count):
        user_id = f"student_{random.randint(1000, 9999)}"
        submit_test(user_id)
        time.sleep(0.5)  # Nghỉ nửa giây giữa mỗi lần nộp để tạo hiệu ứng live feed mượt mà
        
    print("\n✨ Hoàn thành nộp bài hàng loạt!")
