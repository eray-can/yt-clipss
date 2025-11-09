import requests
import json
import time

# Test data - 20 clip
data = {
    "video_id": "Z3TMbaX_X0k",
    "clips": [
        {"start": i * 10, "end": i * 10 + 10}
        for i in range(20)
    ]
}

print(f"📤 İstek gönderiliyor... ({len(data['clips'])} clip)")

try:
    start_time = time.time()
    
    response = requests.post(
        "http://localhost:5000/api/create-clips",
        json=data,
        timeout=600  # 10 dakika timeout
    )
    
    elapsed = time.time() - start_time
    
    print(f"\n📥 Response Status: {response.status_code}")
    print(f"⏱️  Süre: {elapsed:.2f} saniye")
    print(f"📊 Clip başına: {elapsed / len(data['clips']):.2f} saniye")
    print(json.dumps(response.json(), indent=2))
    
except requests.exceptions.Timeout:
    print("❌ TIMEOUT!")
except Exception as e:
    print(f"❌ Hata: {e}")
