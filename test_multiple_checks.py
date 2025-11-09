import requests
import json
import time

# Test data
data = {
    "video_id": "Z3TMbaX_X0k",
    "clips": [
        {"start": 0, "end": 5}
    ]
}

print(f"📤 İstek gönderiliyor...")

# 1. Job başlat
response = requests.post(
    "http://localhost:5000/api/create-clips",
    json=data,
    timeout=10
)

job_id = response.json()['job_id']
print(f"✅ Job başlatıldı: {job_id}")

# 2. Job tamamlanana kadar bekle
while True:
    check_response = requests.get(f"http://localhost:5000/api/check-job/{job_id}")
    job_status = check_response.json()
    
    status = job_status['status']
    print(f"📊 Durum: {status}")
    
    if status == 'finished':
        print(f"\n✅ Job tamamlandı!")
        break
    elif status == 'failed':
        print(f"\n❌ Job başarısız!")
        break
    
    time.sleep(2)

# 3. Aynı job'u 5 kere daha kontrol et
print(f"\n🔄 Aynı job'u 5 kere daha kontrol ediyorum...")
for i in range(5):
    time.sleep(1)
    check_response = requests.get(f"http://localhost:5000/api/check-job/{job_id}")
    
    if check_response.status_code == 200:
        print(f"  {i+1}. kontrol: ✅ Job bulundu (status: {check_response.json()['status']})")
    else:
        print(f"  {i+1}. kontrol: ❌ Job bulunamadı!")
        print(f"  Response: {check_response.json()}")

print(f"\n✅ Test tamamlandı!")
