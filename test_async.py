import requests
import json
import time

# Test data
data = {
    "video_id": "Z3TMbaX_X0k",
    "clips": [
        {"start": i * 10, "end": i * 10 + 10}
        for i in range(5)  # 5 clip test
    ]
}

print(f"📤 İstek gönderiliyor... ({len(data['clips'])} clip)")

# 1. Job başlat
response = requests.post(
    "http://localhost:5000/api/create-clips",
    json=data,
    timeout=10
)

print(f"\n✅ Job başlatıldı!")
print(json.dumps(response.json(), indent=2))

job_id = response.json()['job_id']
print(f"\n🔍 Job ID: {job_id}")
print(f"📋 Clip dosya isimleri:")
for filename in response.json()['clip_filenames']:
    print(f"  - {filename}")

# 2. Job durumunu kontrol et
print(f"\n⏳ Job durumu kontrol ediliyor...")
while True:
    check_response = requests.get(f"http://localhost:5000/api/check-job/{job_id}")
    job_status = check_response.json()
    
    status = job_status['status']
    processed = job_status['processed']
    total = job_status['total']
    
    print(f"📊 Durum: {status} | İşlenen: {processed}/{total}")
    
    if status == 'finished':
        print(f"\n✅ Job tamamlandı!")
        print(json.dumps(job_status, indent=2))
        break
    elif status == 'failed':
        print(f"\n❌ Job başarısız!")
        print(json.dumps(job_status, indent=2))
        break
    
    time.sleep(2)  # 2 saniye bekle
