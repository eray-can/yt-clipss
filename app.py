from flask import Flask, request, jsonify, send_from_directory, url_for
import subprocess
import os
import time
import requests
from pathlib import Path
from urllib.parse import quote
import threading
import uuid
from datetime import datetime
import json
import urllib3

# SSL uyarılarını bastır
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Kesitlerin kaydedileceği klasör
CLIPS_FOLDER = "clips"
Path(CLIPS_FOLDER).mkdir(exist_ok=True)

# Job durumlarını sakla (file-based, worker'lar arası paylaşım için)
JOBS_FOLDER = "jobs"
Path(JOBS_FOLDER).mkdir(exist_ok=True)

def get_job(job_id):
    """Job'u dosyadan oku"""
    job_file = os.path.join(JOBS_FOLDER, f"{job_id}.json")
    if os.path.exists(job_file):
        with open(job_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def save_job(job_id, job_data):
    """Job'u dosyaya kaydet"""
    job_file = os.path.join(JOBS_FOLDER, f"{job_id}.json")
    with open(job_file, 'w', encoding='utf-8') as f:
        json.dump(job_data, f, ensure_ascii=False, indent=2)

def delete_job(job_id):
    """Job dosyasını sil"""
    job_file = os.path.join(JOBS_FOLDER, f"{job_id}.json")
    if os.path.exists(job_file):
        os.remove(job_file)

def generate_clip_filename(video_id, start, end):
    """Dosya adı oluştur: videoID-start-end_reels.mp4"""
    return f"{video_id}-{start}-{end}_reels.mp4"

def get_audio_from_turboscribe(video_id):
    """TurboScribe.ai'den sadece ses linkini al"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # TurboScribe.ai API endpoint'i
        api_url = "https://turboscribe.ai/_htmx/NCN20gAEkZMBzQPXkQc"
        
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Cookie': 'webp=1797256741161; avif=1797256741161; snowflake=95gnirLz7bCR2kB0Dt8ngg%3D%3D; lev=1; screen-width=3440; screen-height=1440; device-pixel-ratio=1; time-zone=Europe%2FIstanbul; js=1; device-token=oAyZHBNdLqTjpZ4yCou3N2af; _gcl_au=1.1.2035078395.1762696717; _ga=GA1.1.566270759.1762696717; _fbp=fb.1.1762696716933.482611337420647145; FPID=FPID2.2.i3BDLW5hKAoCqGaYAFQnmjZCu1qBRg7uEXUZ53RihzQ%3D.1762696717; FPAU=1.1.2035078395.1762696717; i18n-activated-languages=en%2Ctr; window-height=1271; _rdt_uuid=1762696716620.f2dd5fd5-a7ba-4d4a-923d-d2a45f2a3a31; session-secret=b3bec4b0de969c6607d9a1f4b32e589b6103; FPLC=kXlkQ8Zh%2F2uQ%2FQR4b8m7KpaBmRcX0aL97C83aFCmUNU1QoeuX6VmBUQ%2BWkRBZYLbuNF3yOLXVrF7tn4PryfnfeYUi2w7YuDcxaWt7EyHWMeY0bDG17NKoh%2FoNqQR0w%3D%3D; window-width=1260; _uetsid=a336f2b0ca3e11f09aae2f6bb5649835; _uetvid=2ffba9b0bd7411f099f6e713043f5551; _ga_LCTR22QQ87=GS2.1.s1764103082$o3$g1$t1764103139$j3$l0$h1585645753; fingerprint=1RA5lIj7xu4-8DJ5SVzGP-99bj_hs9u5TiTrWK2moT2BeXqoAASRnQOTCM4AnZA9znlAAACTCM4AcCQKzkzgAACTCM4Acmd8zhPAAACTCM4AjySCzlnAAACTCM4DG3AZzmIAAACTCM4CcSjFzmUgAACTCM4DMjx-zi6AAACTCM4Ah2lVzj0AAACTCM4DKVrgzkLAAACTCM4AaV_wzkTgAACTCM4Dctn-zk8AAACTCM4DxMZpzg6gAAA',
            'Origin': 'https://turboscribe.ai',
            'Pragma': 'no-cache',
            'Referer': 'https://turboscribe.ai/downloader/youtube/mp4',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'X-Turbolinks-Loaded': '',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'x-lev-xhr': ''
        }
        
        # POST data
        post_data = {
            "url": video_url
        }
        
        print(f"🔄 TurboScribe.ai API'ye istek atılıyor...")
        response = requests.post(api_url, headers=headers, json=post_data, timeout=30, verify=False)
        
        if response.status_code != 200:
            return None, f"API hatası: {response.status_code}"
        
        # HTML yanıtını parse et
        html_content = response.text
        
        # Başlığı çıkar
        import re
        title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html_content)
        title = title_match.group(1) if title_match else 'Unknown'
        
        # Audio URL'ini çıkar - farklı itag'leri dene
        audio_url = None
        
        # Önce itag=140 (m4a 128kbps) dene
        audio_url_match = re.search(r'href="([^"]*videoplayback[^"]*itag=140[^"]*)"', html_content)
        if audio_url_match:
            audio_url = audio_url_match.group(1).replace('&amp;', '&')
            print(f"✅ Audio bulundu: itag=140 (m4a 128kbps)")
        else:
            # itag=139 (m4a 48kbps) dene
            audio_url_match = re.search(r'href="([^"]*videoplayback[^"]*itag=139[^"]*)"', html_content)
            if audio_url_match:
                audio_url = audio_url_match.group(1).replace('&amp;', '&')
                print(f"✅ Audio bulundu: itag=139 (m4a 48kbps)")
            else:
                # itag=251 (webm opus) dene
                audio_url_match = re.search(r'href="([^"]*videoplayback[^"]*itag=251[^"]*)"', html_content)
                if audio_url_match:
                    audio_url = audio_url_match.group(1).replace('&amp;', '&')
                    print(f"✅ Audio bulundu: itag=251 (webm opus)")
        
        if not audio_url:
            # Alternatif arama - herhangi bir audio URL'i bul
            print(f"🔍 Alternatif audio arama yapılıyor...")
            
            # Genel audio URL arama
            general_audio_matches = re.findall(r'href="([^"]*googlevideo\.com[^"]*mime=audio[^"]*)"', html_content)
            if general_audio_matches:
                audio_url = general_audio_matches[0].replace('&amp;', '&')
                print(f"✅ Genel audio URL bulundu")
            else:
                # Son çare: herhangi bir videoplayback URL'i
                all_matches = re.findall(r'href="([^"]*videoplayback[^"]*)"', html_content)
                audio_candidates = [url for url in all_matches if 'mime=audio' in url or any(tag in url for tag in ['itag=140', 'itag=139', 'itag=251'])]
                
                if audio_candidates:
                    audio_url = audio_candidates[0].replace('&amp;', '&')
                    print(f"✅ Audio candidate bulundu")
                else:
                    # Debug için HTML'in bir kısmını logla
                    html_preview = html_content[:1000] if len(html_content) > 1000 else html_content
                    print(f"🔍 HTML preview: {html_preview}")
                    return None, f"Hiçbir audio URL bulunamadı. HTML uzunluğu: {len(html_content)}"
        
        print(f"✅ Audio linki alındı (TurboScribe.ai)")
        return {
            'audio_url': audio_url,
            'title': title
        }, None
        
    except Exception as e:
        return None, f"Hata: {str(e)}"

def get_video_from_postsyncer(video_id):
    """PostSyncer.com API'den video linkini al"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        api_url = "https://postsyncer.com/api/social-media-downloader"
        
        headers = {
            'accept': '*/*',
            'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'cookie': 'XSRF-TOKEN=eyJpdiI6Ijlhc0RxR3kybkpDcDB5d3MraTh3YVE9PSIsInZhbHVlIjoiQXRqNlVwd00zWXFnbndYOHJuRUdSQzkyWXVzU2RENlNIdmdtUVlXMjNYMy8xZk5MWlNsVGdOMUt6eVc3WmtrcFYwYmFVZ2UrQjhvUmtPRDE5ZlNreXRvTDlMWlBnNkpMZnRuYUtRYWl1Wjlmd3kyalJvemwwWlM3SC91MGhHMUgiLCJtYWMiOiI3MzY3MmRjNzMwMzA5ZTdmOGY0NWIxNmY2ZjljOTU0YzhmZTE2NTQ4ZTBlMDUyODBiOGNhZTQwOWNlYjliN2VhIiwidGFnIjoiIn0%3D; postsyncer_session_v2=eyJpdiI6IlBScjNveWNNZENSMkxlOVpSSWQzb2c9PSIsInZhbHVlIjoiZU1DcE5Rd1hKZVBSbkMzWVV5T3k5ZWJYeitCalgzR1NKcWE1cnRINnJvcmFBdGVSdGx0dXg0V1g4YXY3Y2JweHZJM2ZJejJuUHppbFBvSXBQRE9tWjZMSjhVRGhDd0hnQ2c2d3ZaTEVad1pUb2FncVE0RkZzakJ5L0RqTmlIanciLCJtYWMiOiI5ZDVjMzkzNTE2YTY1MzU5M2VkNGNkYTJmYWUyNWZlMTM4ZWYzODgwODkzNzk5ZTRjNjZjMDBmY2JlMWM4MzUwIiwidGFnIjoiIn0%3D',
            'origin': 'https://postsyncer.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://postsyncer.com/tools/youtube-video-downloader',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'x-csrf-token': 'TEKzaBQgwZlh9fciF7MnaF6G4VFUJfCr2gNM5Gph'
        }
        
        payload = {
            "url": video_url,
            "platform": "youtube"
        }
        
        print(f"🔄 PostSyncer.com API'ye istek atılıyor...")
        response = requests.post(api_url, headers=headers, json=payload, timeout=30, verify=False)
        
        if response.status_code != 200:
            return None, f"API hatası: {response.status_code}"
        
        data = response.json()
        
        if data.get('error'):
            return None, f"API yanıt hatası: {data}"
        
        title = data.get('title', 'Unknown')
        videos = data.get('medias', {}).get('videos', [])
        audios = data.get('medias', {}).get('audio', [])
        
        # En iyi video kalitesini bul (720p veya 1080p MP4)
        video_url = None
        best_quality = 0
        
        for video in videos:
            if video.get('extension') == 'mp4' and not video.get('has_no_audio', True):
                height = video.get('height', 0)
                # 720p veya 1080p tercih et
                if height in [720, 1080] and height > best_quality:
                    video_url = video.get('url')
                    best_quality = height
        
        # Eğer 720p/1080p bulunamazsa, en yüksek kaliteyi al
        if not video_url:
            for video in videos:
                if video.get('extension') == 'mp4':
                    height = video.get('height', 0)
                    if height > best_quality:
                        video_url = video.get('url')
                        best_quality = height
        
        if not video_url:
            available_qualities = [f"{v.get('height')}p {v.get('extension')}" for v in videos]
            return None, f"Uygun video bulunamadı. Mevcut: {', '.join(available_qualities)}"
        
        print(f"✅ Video: {best_quality}p MP4")
        return {
            'video_url': video_url,
            'title': title,
            'resolution': f'{best_quality}p'
        }, None
        
    except Exception as e:
        return None, f"Hata: {str(e)}"

def get_video_urls_from_savenow(video_id):
    """SaveNow.to API'den video URL'ini al (tek URL - video+audio birlikte)"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # 1. İlk istek - download job başlat
        api_url = f"https://p.savenow.to/ajax/download.php?copyright=0&format=720&url={quote(video_url)}"
        
        headers = {
            'accept': '*/*',
            'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'origin': 'https://downloaderto.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://downloaderto.com/',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'Cookie': 'loader_session=jca8PUEZIft5WtClNmqEG98lw5nF2Op85vG6SLPg'
        }
        
        print(f"🔄 SaveNow.to API'ye istek atılıyor...")
        response = requests.get(api_url, headers=headers, timeout=30, verify=False)
        
        if response.status_code != 200:
            return None, f"API hatası: {response.status_code}"
        
        data = response.json()
        
        if not data.get('success'):
            return None, f"API yanıt hatası: {data}"
        
        # Progress URL'ini al
        progress_url = data.get('progress_url')
        title = data.get('title', 'Unknown')
        
        if not progress_url:
            return None, "Progress URL bulunamadı"
        
        print(f"✅ Job başlatıldı: {data.get('id')}")
        print(f"📊 Progress URL: {progress_url}")
        
        # 2. Progress polling - download tamamlanana kadar bekle
        max_attempts = 60  # 60 * 5 = 5 dakika max
        for attempt in range(max_attempts):
            try:
                print(f"📊 Progress kontrol ediliyor... ({attempt + 1}/{max_attempts})")
                
                progress_response = requests.get(progress_url, headers=headers, timeout=15, verify=False)
                
                if progress_response.status_code != 200:
                    print(f"⚠️ Progress API hatası: {progress_response.status_code}")
                    time.sleep(5)
                    continue
                
                progress_data = progress_response.json()
                
                success = progress_data.get('success', 0)
                progress = progress_data.get('progress', 0)
                text = progress_data.get('text', 'Unknown')
                
                print(f"📊 Progress: {progress}% - {text}")
                
                if success == 1:  # Tamamlandı
                    download_url = progress_data.get('download_url')
                    
                    if not download_url:
                        # Alternative URLs'i dene
                        alt_urls = progress_data.get('alternative_download_urls', [])
                        if alt_urls:
                            download_url = alt_urls[0].get('url')
                            print(f"🔄 Alternative URL kullanılıyor: {download_url}")
                    
                    if not download_url:
                        return None, "Download URL bulunamadı"
                    
                    print(f"✅ Download hazır: {download_url}")
                    
                    return {
                        'video_url': download_url,
                        'audio_url': download_url,  # Aynı URL (video+audio birlikte)
                        'title': title,
                        'resolution': '720p'
                    }, None
                
                elif success == 0:  # Devam ediyor
                    if progress >= 1000:  # Bazen success=0 ama progress=1000 oluyor
                        download_url = progress_data.get('download_url')
                        if download_url:
                            print(f"✅ Download hazır (progress=1000): {download_url}")
                            return {
                                'video_url': download_url,
                                'audio_url': download_url,
                                'title': title,
                                'resolution': '720p'
                            }, None
                    
                    # Bekle ve tekrar dene
                    time.sleep(5)
                    continue
                
                else:  # Hata
                    error_msg = progress_data.get('message', 'Bilinmeyen hata')
                    return None, f"Progress hatası: {error_msg}"
                
            except Exception as progress_error:
                print(f"⚠️ Progress kontrol hatası: {str(progress_error)}")
                time.sleep(5)
                continue
        
        return None, "Download timeout - 5 dakika içinde tamamlanamadı"
        
    except Exception as e:
        return None, f"Hata: {str(e)}"

def get_video_urls(video_id):
    """Video URL'lerini al (SaveNow.to'dan tek URL - video+audio birlikte)"""
    try:
        # SaveNow.to'dan tek URL al (video+audio birlikte)
        result, error = get_video_urls_from_savenow(video_id)
        if error:
            print(f"❌ SaveNow.to hatası: {error}")
            return {"success": False, "error": error}
        
        return {
            "success": True,
            "video_url": result['video_url'],
            "audio_url": result['audio_url'],  # Aynı URL
            "title": result['title'],
            "resolution": result['resolution']
        }
            
    except Exception as e:
        error_msg = f"Hata: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

def cut_clip_from_url(video_url, audio_url, video_id, start, end, title, resolution):
    """Kesit oluştur - ARM64 için curl, diğerleri için direkt URL"""
    output_path = None
    temp_video = None
    temp_audio = None
    
    try:
        output_file = generate_clip_filename(video_id, start, end)
        output_path = os.path.join(CLIPS_FOLDER, output_file)
        
        # Eğer dosya zaten varsa, tekrar kesme
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > 0:
                print(f"✅ Kesit zaten mevcut: {output_file} ({file_size} bytes)")
                return {
                    "success": True,
                    "filename": output_file,
                    "video_info": {
                        "title": title,
                        "resolution": resolution,
                        "file_size": file_size,
                        "file_size_mb": round(file_size / (1024 * 1024), 2)
                    }
                }
            else:
                print(f"⚠️ Boş dosya bulundu, siliniyor: {output_file}")
                os.remove(output_path)
        
        print(f"✂️ Kesit oluşturuluyor: {start}s - {end}s (video: {video_id})")
        duration = end - start
        
        # Platform kontrolü - ARM64 veya Windows için indirme modu
        import platform
        is_arm64 = platform.machine() in ['aarch64', 'arm64']
        is_windows = platform.system() == 'Windows'
        use_download_mode = is_arm64 or is_windows  # Her iki durumda da indir
        
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        
        if use_download_mode:
            if is_windows:
                print(f"🔧 Windows tespit edildi - indirme modu aktif")
            else:
                print(f"🔧 ARM64 tespit edildi - indirme modu aktif")
            
            # Geçici dosya isimleri
            if is_windows:
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_video = os.path.join(temp_dir, f"{video_id}_v_{start}_{end}.mp4")
                temp_audio = os.path.join(temp_dir, f"{video_id}_a_{start}_{end}.m4a")
            else:
                temp_video = f"/tmp/{video_id}_v_{start}_{end}.mp4"
                temp_audio = f"/tmp/{video_id}_a_{start}_{end}.m4a"
            
            # 1. Video indir (Python requests ile)
            print(f"📥 Video indiriliyor...")
            
            try:
                # Vidfly.ai için özel headers
                headers = {
                    'User-Agent': user_agent,
                    'Accept': '*/*',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'video',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'cross-site',
                    'Range': 'bytes=0-',
                    'Referer': 'https://vidfly.ai/'
                }
                
                response = requests.get(video_url, headers=headers, stream=True, verify=False, timeout=180)
                response.raise_for_status()
                
                with open(temp_video, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                print(f"✅ Video indirildi: {os.path.getsize(temp_video)} bytes")
                
            except Exception as e:
                error_msg = f"Video indirme hatası: {str(e)[:200]}"
                print(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Video dosya boyutu kontrol
            if not os.path.exists(temp_video) or os.path.getsize(temp_video) < 1000:
                return {"success": False, "error": "Video dosyası indirilemedi veya çok küçük"}
            
            # 2. Audio indir (Python requests ile)
            print(f"📥 Audio indiriliyor...")
            
            try:
                # Audio için Vidfly.ai headers
                headers = {
                    'User-Agent': user_agent,
                    'Accept': '*/*',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'audio',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'cross-site',
                    'Range': 'bytes=0-',
                    'Referer': 'https://vidfly.ai/'
                }
                
                response = requests.get(audio_url, headers=headers, stream=True, verify=False, timeout=180)
                response.raise_for_status()
                
                with open(temp_audio, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                print(f"✅ Audio indirildi: {os.path.getsize(temp_audio)} bytes")
                
            except Exception as e:
                error_msg = f"Audio indirme hatası: {str(e)[:200]}"
                print(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            # Audio dosya boyutu kontrol
            if not os.path.exists(temp_audio) or os.path.getsize(temp_audio) < 1000:
                return {"success": False, "error": "Audio dosyası indirilemedi veya çok küçük"}
            
            print(f"✅ Video: {os.path.getsize(temp_video)} bytes, Audio: {os.path.getsize(temp_audio)} bytes")
            
            # 3. Local dosyalardan Instagram Reels formatında kes (letterbox)
            cmd = [
                "ffmpeg",
                "-ss", str(start),
                "-i", temp_video,
                "-ss", str(start),
                "-i", temp_audio,
                "-t", str(duration),
                "-map", "0:v", "-map", "1:a",
                # Instagram Reels letterbox formatı (üst/alt siyah bar)
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                "-avoid_negative_ts", "make_zero",
                "-movflags", "+faststart", "-y", output_path
            ]
        else:
            print(f"🔧 Standart platform - direkt URL modu")
            # Diğer platformlar için direkt URL (Instagram Reels letterbox)
            cmd = [
                "ffmpeg",
                "-user_agent", user_agent,
                "-referer", "https://downloaderto.com/",
                "-ss", str(start),
                "-i", video_url,
                "-user_agent", user_agent,
                "-referer", "https://downloaderto.com/",
                "-ss", str(start),
                "-i", audio_url,
                "-t", str(duration),
                "-map", "0:v", "-map", "1:a",
                # Instagram Reels letterbox formatı (üst/alt siyah bar)
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                "-avoid_negative_ts", "make_zero",
                "-movflags", "+faststart", "-y", output_path
            ]
        
        # FFmpeg'i çalıştır
        print(f"🔄 FFmpeg başlatılıyor...")
        print(f"🔧 FFmpeg komutu: {' '.join(cmd[:10])}...")  # İlk 10 parametreyi göster
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')
        
        # Geçici dosyaları temizle (indirme modu)
        if use_download_mode:
            try:
                if temp_video and os.path.exists(temp_video):
                    os.remove(temp_video)
                    print(f"🗑️ Geçici video dosyası silindi")
                if temp_audio and os.path.exists(temp_audio):
                    os.remove(temp_audio)
                    print(f"🗑️ Geçici audio dosyası silindi")
            except Exception as cleanup_error:
                print(f"⚠️ Geçici dosya temizleme hatası: {cleanup_error}")
        
        # FFmpeg stderr'ini her zaman logla (hata olsa da olmasa da)
        if result.stderr:
            stderr_preview = result.stderr[:2000] if len(result.stderr) > 2000 else result.stderr
            print(f"📋 FFmpeg log: {stderr_preview}")
        
        # FFmpeg stdout'u da logla
        if result.stdout:
            stdout_preview = result.stdout[:1000] if len(result.stdout) > 1000 else result.stdout
            print(f"📋 FFmpeg stdout: {stdout_preview}")
        
        if result.returncode != 0:
            # Daha detaylı hata analizi
            error_details = result.stderr if result.stderr else "Bilinmeyen FFmpeg hatası"
            
            # Daha detaylı hata analizi
            if "Invalid data found when processing input" in error_details:
                error_msg = f"FFmpeg hatası: Video/audio stream'e erişilemiyor. URL'ler geçersiz olabilir. Detay: {error_details[:300]}"
            elif "Connection refused" in error_details or "HTTP error" in error_details:
                error_msg = f"FFmpeg hatası: URL'lere bağlanılamıyor. Network sorunu olabilir. Detay: {error_details[:300]}"
            elif "No such file or directory" in error_details:
                error_msg = f"FFmpeg hatası: Input dosyası bulunamıyor. Detay: {error_details[:300]}"
            elif "SSL" in error_details or "certificate" in error_details:
                error_msg = f"FFmpeg hatası: SSL sertifika sorunu. Detay: {error_details[:300]}"
            elif "403" in error_details or "Forbidden" in error_details:
                error_msg = f"FFmpeg hatası: URL'lere erişim reddedildi (403). Detay: {error_details[:300]}"
            elif "404" in error_details or "Not Found" in error_details:
                error_msg = f"FFmpeg hatası: URL bulunamadı (404). Detay: {error_details[:300]}"
            elif "timeout" in error_details.lower() or "timed out" in error_details.lower():
                error_msg = f"FFmpeg hatası: Bağlantı zaman aşımı. Detay: {error_details[:300]}"
            else:
                # Tam hata mesajını göster
                error_msg = f"FFmpeg hatası (code {result.returncode}): {error_details[:800]}"
            
            print(f"❌ {error_msg}")
            print(f"🔍 Kullanılan video URL: {video_url[:100]}...")
            print(f"🔍 Kullanılan audio URL: {audio_url[:100]}...")
            
            # Hatalı dosyayı temizle
            if output_path and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            return {"success": False, "error": error_msg}
        
        # Dosya oluşturuldu mu ve boyutu 0'dan büyük mü kontrol et
        if not os.path.exists(output_path):
            error_msg = "Dosya oluşturulamıyor"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            error_msg = "Dosya boş oluşturuldu (0 byte)"
            print(f"❌ {error_msg}")
            try:
                os.remove(output_path)  # Boş dosyayı sil
            except:
                pass
            return {"success": False, "error": error_msg}
        
        print(f"✅ Kesit oluşturuldu: {output_file} ({file_size} bytes, {round(file_size / (1024 * 1024), 2)} MB)")
        return {
            "success": True,
            "filename": output_file,
            "video_info": {
                "title": title,
                "resolution": resolution,
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2)
            }
        }
    
    except subprocess.TimeoutExpired:
        error_msg = f"İşlem timeout (>5 dakika): {start}s - {end}s"
        print(f"❌ {error_msg}")
        # Timeout durumunda dosyaları temizle
        try:
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
            if temp_video and os.path.exists(temp_video):
                os.remove(temp_video)
            if temp_audio and os.path.exists(temp_audio):
                os.remove(temp_audio)
        except:
            pass
        return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"Hata: {str(e)}"
        print(f"❌ {error_msg}")
        # Hata durumunda dosyaları temizle
        try:
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
            if temp_video and os.path.exists(temp_video):
                os.remove(temp_video)
            if temp_audio and os.path.exists(temp_audio):
                os.remove(temp_audio)
        except:
            pass
        return {"success": False, "error": error_msg}

def cut_clip_from_local_file(temp_file, video_id, start, end, title, resolution):
    """Local dosyadan kesit oluştur (Instagram Reels formatında 9:16)"""
    output_path = None
    
    try:
        output_file = generate_clip_filename(video_id, start, end)
        output_path = os.path.join(CLIPS_FOLDER, output_file)
        
        # Eğer dosya zaten varsa, tekrar kesme
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            if file_size > 0:
                print(f"✅ Kesit zaten mevcut: {output_file}")
                return {
                    "success": True,
                    "filename": output_file,
                    "video_info": {
                        "title": title,
                        "resolution": "1080x1920 (9:16)",
                        "file_size": file_size,
                        "file_size_mb": round(file_size / (1024 * 1024), 2)
                    }
                }
            else:
                os.remove(output_path)
        
        duration = end - start
        
        # Instagram Reels formatında kes (9:16 letterbox - üst/alt siyah bar)
        cmd = [
            "ffmpeg",
            "-ss", str(start),
            "-i", temp_file,
            "-t", str(duration),
            # Video filtreleri - Letterbox format (tüm içerik görünsün)
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264",  # H.264 codec (Instagram uyumlu)
            "-preset", "fast",  # Encoding hızı
            "-crf", "23",       # Kalite (18-28 arası, 23 iyi)
            "-c:a", "aac",      # AAC audio codec
            "-b:a", "128k",     # Audio bitrate
            "-ar", "44100",     # Audio sample rate
            "-avoid_negative_ts", "make_zero",
            "-movflags", "+faststart", 
            "-y", output_path
        ]
        
        print(f"🔧 FFmpeg komutu: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')
        
        # FFmpeg stderr'ini logla
        if result.stderr:
            stderr_preview = result.stderr[:2000] if len(result.stderr) > 2000 else result.stderr
            print(f"📋 FFmpeg log: {stderr_preview}")
        
        # Dosya varlığını kontrol et
        print(f"🔍 Input dosyası var mı: {os.path.exists(temp_file)} ({temp_file})")
        
        if result.returncode != 0:
            error_details = result.stderr if result.stderr else "Bilinmeyen FFmpeg hatası"
            error_msg = f"FFmpeg hatası (code {result.returncode}): {error_details[:500]}"
            print(f"❌ {error_msg}")
            
            if output_path and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            return {"success": False, "error": error_msg}
        
        # Dosya kontrolü
        if not os.path.exists(output_path):
            return {"success": False, "error": "Dosya oluşturulamadı"}
        
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            try:
                os.remove(output_path)
            except:
                pass
            return {"success": False, "error": "Dosya boş oluşturuldu"}
        
        print(f"✅ Instagram Reels kesiti oluşturuldu: {output_file} ({round(file_size / (1024 * 1024), 2)} MB)")
        return {
            "success": True,
            "filename": output_file,
            "video_info": {
                "title": title,
                "resolution": "1080x1920 (9:16)",
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2)
            }
        }
    
    except subprocess.TimeoutExpired:
        error_msg = f"FFmpeg timeout: {start}s - {end}s"
        print(f"❌ {error_msg}")
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"Hata: {str(e)}"
        print(f"❌ {error_msg}")
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        return {"success": False, "error": error_msg}

def cleanup_job(job_id):
    """Job'u 10 dakika sonra sil"""
    time.sleep(600)  # 10 dakika bekle
    job = get_job(job_id)
    if job:
        print(f"🗑️ Job siliniyor: {job_id}")
        delete_job(job_id)

def process_clips_async(job_id, video_id, clips, video_url, audio_url, title, resolution):
    """Clipleri async olarak işle - TEK İNDİRME MANTIGI"""
    job = None
    temp_file = None
    
    try:
        results = []
        errors = []
        
        # Job'u processing olarak işaretle
        job = get_job(job_id)
        if not job:
            print(f"❌ Job bulunamadı: {job_id}")
            return
        
        job['status'] = 'processing'
        job['total'] = len(clips)
        job['processed'] = 0
        save_job(job_id, job)
        
        print(f"🔄 Processing started for job {job_id} with {len(clips)} clips")
        
        # Platform kontrolü
        import platform
        is_arm64 = platform.machine() in ['aarch64', 'arm64']
        is_windows = platform.system() == 'Windows'
        use_download_mode = is_arm64 or is_windows
        
        # User-Agent rotation (bot detection önlemi)
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0"
        ]
        import random
        user_agent = random.choice(user_agents)
        print(f"🔄 Kullanılan User-Agent: {user_agent[:50]}...")
        
        if use_download_mode:
            if is_windows:
                print(f"🔧 Windows tespit edildi - tek indirme modu")
            else:
                print(f"🔧 ARM64 tespit edildi - tek indirme modu")
            
            # Geçici dosya ismi (JOB için tek dosya - video+audio birlikte)
            if is_windows:
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, f"{video_id}_full.mp4")
            else:
                temp_file = f"/tmp/{video_id}_full.mp4"
            
            # 1. TEK SEFERLIK DOSYA İNDİR (video+audio birlikte)
            print(f"📥 Tam dosya indiriliyor... (video+audio birlikte)")
            try:
                # SaveNow.to için headers
                headers = {
                    'User-Agent': user_agent,
                    'Accept': '*/*',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'video',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'cross-site',
                    'Referer': 'https://downloaderto.com/',
                    'Origin': 'https://downloaderto.com'
                }
                
                # Güçlü retry mekanizması
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        print(f"📥 Dosya indirme denemesi {attempt + 1}/{max_retries}")
                        
                        # Her denemede farklı delay
                        if attempt > 0:
                            delay = attempt * 2  # 2, 4, 6, 8 saniye
                            print(f"⏳ {delay} saniye bekleniyor...")
                            time.sleep(delay)
                        
                        # Session kullan (cookie persistence)
                        session = requests.Session()
                        session.headers.update(headers)
                        
                        # video_url ve audio_url aynı (SaveNow.to'dan)
                        response = session.get(video_url, stream=True, verify=False, timeout=300)
                        response.raise_for_status()
                        break  # Başarılı ise döngüden çık
                        
                    except requests.exceptions.HTTPError as http_err:
                        if response.status_code == 403:
                            print(f"❌ 403 Forbidden - Deneme {attempt + 1}")
                            if attempt < max_retries - 1:
                                continue
                        raise http_err
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"❌ Hata: {str(e)[:100]} - Tekrar deneniyor...")
                            continue
                        raise e
                
                with open(temp_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                print(f"✅ Tam dosya indirildi: {os.path.getsize(temp_file)} bytes")
                
            except Exception as e:
                error_msg = f"Dosya indirme hatası: {str(e)[:200]}"
                print(f"❌ {error_msg}")
                # Tüm job'u failed yap
                job = get_job(job_id)
                if job:
                    job['status'] = 'failed'
                    job['error'] = error_msg
                    job['completed_at'] = datetime.now().isoformat()
                    save_job(job_id, job)
                return
            
            print(f"🎬 Tüm clipler tek dosyadan kesilecek!")
        
        # 3. TÜM CLİPLERİ KES
        for idx, clip in enumerate(clips):
            try:
                start = clip.get('start')
                end = clip.get('end')
                
                if start is None or end is None:
                    errors.append({
                        'index': idx,
                        'error': 'start ve end değerleri gerekli',
                        'clip': clip
                    })
                    continue
                
                print(f"✂️ Clip {idx+1}/{len(clips)}: {start}s - {end}s")
                
                # Local dosyadan veya URL'den kes
                if use_download_mode:
                    result = cut_clip_from_local_file(temp_file, video_id, start, end, title, resolution)
                else:
                    result = cut_clip_from_url(video_url, audio_url, video_id, start, end, title, resolution)
                
                if result.get('success'):
                    filename = result['filename']
                    video_info = result.get('video_info', {})
                    
                    results.append({
                        'start': start,
                        'end': end,
                        'filename': filename,
                        'video_title': video_info.get('title'),
                        'resolution': video_info.get('resolution'),
                        'file_size_mb': video_info.get('file_size_mb')
                    })
                    print(f"✅ Clip {idx+1} tamamlandı")
                else:
                    error_msg = result.get('error', 'Bilinmeyen hata')
                    errors.append({
                        'index': idx,
                        'error': error_msg,
                        'clip': {'start': start, 'end': end}
                    })
                    print(f"❌ Clip {idx+1} başarısız: {error_msg}")
                
            except Exception as clip_error:
                error_msg = f"Clip processing exception: {str(clip_error)}"
                print(f"❌ {error_msg}")
                errors.append({
                    'index': idx,
                    'error': error_msg,
                    'clip': clip
                })
            finally:
                # Her durumda processed sayısını artır ve kaydet
                job = get_job(job_id)
                if job:
                    job['processed'] += 1
                    save_job(job_id, job)
        
        # Geçici dosyayı temizle
        if use_download_mode:
            try:
                if temp_file and os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"🗑️ Geçici dosya silindi")
            except Exception as cleanup_error:
                print(f"⚠️ Geçici dosya temizleme hatası: {cleanup_error}")
        
        # Job'u finished olarak işaretle
        job = get_job(job_id)
        if job:
            job['status'] = 'finished'
            job['results'] = results
            job['errors'] = errors
            job['completed_at'] = datetime.now().isoformat()
            save_job(job_id, job)
            print(f"✅ Job {job_id} tamamlandı: {len(results)} başarılı, {len(errors)} hata")
        
        # 10 dakika sonra job'u sil
        cleanup_thread = threading.Thread(target=cleanup_job, args=(job_id,))
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
    except Exception as e:
        # Kritik hata - job'u failed olarak işaretle
        error_msg = f"Critical error in process_clips_async: {str(e)}"
        print(f"❌ {error_msg}")
        try:
            job = get_job(job_id)
            if job:
                job['status'] = 'failed'
                job['error'] = error_msg
                job['completed_at'] = datetime.now().isoformat()
                save_job(job_id, job)
        except Exception as save_error:
            print(f"❌ Failed to save error state: {str(save_error)}")

@app.route('/api/create-clips', methods=['POST'])
def create_clips():
    """
    Kesitler oluştur (async) ve job ID döndür
    
    Request body:
    {
        "video_id": "KDV_-rXGy7A",
        "clips": [
            {
                "start": 0.32,
                "end": 41.56
            }
        ]
    }
    """
    try:
        data = request.json
        video_id = data.get('video_id')
        clips = data.get('clips', [])
        
        if not video_id or not clips:
            return jsonify({
                'success': False,
                'error': 'video_id ve clips gerekli'
            }), 400
        
        # Video URL'lerini al (sadece 1 kere API'ye istek)
        url_result = get_video_urls(video_id)
        
        if not url_result.get('success'):
            return jsonify({
                'success': False,
                'error': url_result.get('error', 'Video URL alınamadı')
            }), 500
        
        video_url = url_result['video_url']
        audio_url = url_result['audio_url']
        title = url_result.get('title', 'Unknown')
        resolution = url_result.get('resolution', '720p')
        
        # Job ID oluştur
        job_id = str(uuid.uuid4())
        
        # Job'u kaydet (file-based)
        job_data = {
            'job_id': job_id,
            'video_id': video_id,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'total': len(clips),
            'processed': 0,
            'clip_filenames': [generate_clip_filename(video_id, c.get('start'), c.get('end')) for c in clips if c.get('start') is not None and c.get('end') is not None]
        }
        save_job(job_id, job_data)
        
        # Async olarak işle
        thread = threading.Thread(
            target=process_clips_async,
            args=(job_id, video_id, clips, video_url, audio_url, title, resolution)
        )
        thread.daemon = True
        thread.start()
        
        # Hemen job ID döndür
        return jsonify({
            'success': True,
            'job_id': job_id,
            'video_id': video_id,
            'status': 'pending',
            'total_clips': len(clips),
            'message': 'Job başlatıldı. /api/check-job/<job_id> ile durumu kontrol edin.',
            'clip_filenames': job_data['clip_filenames']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/check-job/<job_id>', methods=['GET'])
def check_job(job_id):
    """Job durumunu kontrol et"""
    job = get_job(job_id)
    
    if not job:
        return jsonify({
            'success': False,
            'error': 'Job bulunamadı'
        }), 404
    
    response = {
        'success': True,
        'job_id': job_id,
        'video_id': job['video_id'],
        'status': job['status'],
        'created_at': job['created_at'],
        'total': job['total'],
        'processed': job['processed'],
        'clip_filenames': job.get('clip_filenames', [])
    }
    
    if job['status'] == 'finished':
        response['completed_at'] = job.get('completed_at')
        # URL'leri düzgün oluştur
        clips_with_urls = []
        for clip in job.get('results', []):
            clip_copy = clip.copy()
            clip_copy['url'] = url_for('serve_clip', filename=clip['filename'], _external=True)
            clips_with_urls.append(clip_copy)
        response['clips'] = clips_with_urls
        response['errors'] = job.get('errors')
        response['error_count'] = len(job.get('errors', []))
    elif job['status'] == 'failed':
        response['error'] = job.get('error')
    
    return jsonify(response)

@app.route('/clips/<filename>')
def serve_clip(filename):
    """Kesit dosyasını sun"""
    return send_from_directory(CLIPS_FOLDER, filename)

@app.route('/api/clips', methods=['GET'])
def list_clips():
    """Mevcut kesitleri listele"""
    clips = []
    for filename in os.listdir(CLIPS_FOLDER):
        if filename.endswith('.mp4'):
            file_path = os.path.join(CLIPS_FOLDER, filename)
            file_size = os.path.getsize(file_path)
            clips.append({
                'filename': filename,
                'url': url_for('serve_clip', filename=filename, _external=True),
                'size': file_size
            })
    
    return jsonify({
        'success': True,
        'clips': clips,
        'total': len(clips)
    })

@app.route('/api/clips/<filename>', methods=['DELETE'])
def delete_clip(filename):
    """Clip dosyasını sil"""
    try:
        # Güvenlik kontrolü - sadece .mp4 dosyaları
        if not filename.endswith('.mp4'):
            return jsonify({
                'success': False,
                'error': 'Sadece .mp4 dosyaları silinebilir'
            }), 400
        
        file_path = os.path.join(CLIPS_FOLDER, filename)
        
        # Dosya var mı kontrol et
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Dosya bulunamadı'
            }), 404
        
        # Dosyayı sil
        os.remove(file_path)
        print(f"🗑️ Clip silindi: {filename}")
        
        return jsonify({
            'success': True,
            'message': f'{filename} başarıyla silindi'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/clips/clear', methods=['DELETE'])
def clear_all_clips():
    """Tüm clipleri sil"""
    try:
        deleted_count = 0
        
        for filename in os.listdir(CLIPS_FOLDER):
            if filename.endswith('.mp4'):
                file_path = os.path.join(CLIPS_FOLDER, filename)
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"🗑️ Silindi: {filename}")
                except Exception as e:
                    print(f"⚠️ Silinemedi {filename}: {e}")
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} clip silindi',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/')
def index():
    """API bilgisi"""
    return jsonify({
        'name': 'YouTube Clip API (Instagram Reels)',
        'version': '2.2',
        'endpoints': {
            'POST /api/create-clips': 'Kesitler oluştur (async, job ID döndürür)',
            'GET /api/check-job/<job_id>': 'Job durumunu kontrol et',
            'GET /api/clips': 'Mevcut kesitleri listele',
            'GET /clips/<filename>': 'Kesit dosyasını indir',
            'DELETE /api/clips/<filename>': 'Belirli clip dosyasını sil',
            'DELETE /api/clips/clear': 'Tüm clipleri sil'
        }
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)