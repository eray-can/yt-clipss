import requests
import json

# API endpoint
API_URL = "http://localhost:5000/api/create-clips"

# Test verisi
test_data = {
    "video_id": "KDV_-rXGy7A",
    "clips": [
        {
            "start": 0.32,
            "end": 41.56,
            "duration": 41.24,
            "text": "Oh. την έρθει να παραλάβει το διπλωμά",
            "caption": "Taşacak Bu Deniz 1.Bölüm: Diplomasını teslim alma anı."
        },
        {
            "start": 126.36,
            "end": 179.8,
            "duration": 53.44,
            "text": "yine Gregor. Elene yalızlıktan ölmez ama ameliyat etmezsek bu hasta ölür.",
            "caption": "Taşacak Bu Deniz 1.Bölüm: Melina'nın zorlu doktorluk kararı."
        },
        {
            "start": 179.8,
            "end": 210.45,
            "duration": 30.65,
            "text": "gregor Gregori. >> Bizler Konstantinopoli'nin evlatlarıyız.",
            "caption": "Taşacak Bu Deniz 1.Bölüm: İstanbullu Rumların Araf'ı."
        }
    ]
}

def test_create_clips():
    """API'yi test et"""
    print("🚀 API'ye istek gönderiliyor...")
    print(f"Video ID: {test_data['video_id']}")
    print(f"Kesit sayısı: {len(test_data['clips'])}\n")
    
    response = requests.post(API_URL, json=test_data)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Başarılı!\n")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        print("\n📹 Oluşturulan kesitler:")
        for clip in result.get('clips', []):
            print(f"\n- {clip['caption']}")
            print(f"  URL: {clip['url']}")
            print(f"  Süre: {clip['start']}s - {clip['end']}s")
    else:
        print(f"❌ Hata: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_create_clips()
