import requests
import json

# Test data
data = {
    "video_id": "Z3TMbaX_X0k",
    "clips": [
        {
            "start": 0.0,
            "end": 10.0
        }
    ]
}

print("📤 İstek gönderiliyor...")
print(json.dumps(data, indent=2))

try:
    response = requests.post(
        "http://localhost:5000/api/create-clips",
        json=data,
        timeout=600  # 10 dakika timeout
    )
    
    print(f"\n📥 Response Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    
except requests.exceptions.Timeout:
    print("❌ TIMEOUT!")
except Exception as e:
    print(f"❌ Hata: {e}")
