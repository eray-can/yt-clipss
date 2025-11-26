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
    """Dosya adı oluştur: videoID-start-end.mp4"""
    return f"{video_id}-{start}-{end}.mp4"

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
        
        # Sadece audio URL'ini çıkar
        audio_url_match = re.search(r'href="([^"]*videoplayback[^"]*itag=140[^"]*)"', html_content)
        
        if not audio_url_match:
            return None, "Audio URL bulunamadı (itag=140)"
        
        audio_url = audio_url_match.group(1).replace('&amp;', '&')
        
        print(f"✅ Audio linki alındı (TurboScribe.ai)")
        return {
            'audio_url': audio_url,
            'title': title
        }, None
        
    except Exception as e:
        return None, f"Hata: {str(e)}"

def get_video_from_vidfly(video_id):
    """Vidfly.ai API'den sadece video linkini al"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        encoded_url = quote(video_url, safe='')
        
        api_url = f"https://api.vidfly.ai/api/media/youtube/download?url={encoded_url}"
        
        headers = {
            'accept': '*/*',
            'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://vidfly.ai',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://vidfly.ai/',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'x-app-name': 'vidfly-web',
            'x-app-version': '1.0.0'
        }
        
        print(f"🔄 Vidfly.ai API'ye video için istek atılıyor...")
        response = requests.get(api_url, headers=headers, timeout=30, verify=False)
        
        if response.status_code != 200:
            return None, f"API hatası: {response.status_code}"
        
        data = response.json()
        
        if data.get('code') != 0:
            return None, f"API yanıt hatası: {data}"
        
        items = data.get('data', {}).get('items', [])
        title = data.get('data', {}).get('title', 'Unknown')
        
        # 720p video bul (sadece video track)
        video_url = None
        for item in items:
            if item.get('ext') == 'mp4' and item.get('height') == 720:
                video_url = item.get('url')
                break
        
        if not video_url:
            # Mevcut çözünürlükleri logla
            available_resolutions = []
            for item in items:
                if item.get('ext') == 'mp4':
                    res_type = item.get('type', 'unknown')
                    available_resolutions.append(f"{item.get('height')}p ({res_type})")
            return None, f"720p video bulunamadı. Mevcut: {', '.join(available_resolutions)}"
        
        print(f"✅ Video linki alındı (Vidfly.ai)")
        return {
            'video_url': video_url,
            'title': title,
            'resolution': '720p'
        }, None
        
    except Exception as e:
        return None, f"Hata: {str(e)}"

def get_video_urls(video_id):
    """Video URL'lerini al (hibrit: video Vidfly'dan, ses TurboScribe'dan)"""
    try:
        # Video'yu Vidfly.ai'den al
        video_info, video_error = get_video_from_vidfly(video_id)
        if video_error:
            print(f"❌ Video hatası: {video_error}")
            return {"success": False, "error": video_error}
        
        # Ses'i TurboScribe.ai'den al
        audio_info, audio_error = get_audio_from_turboscribe(video_id)
        if audio_error:
            print(f"❌ Audio hatası: {audio_error}")
            return {"success": False, "error": audio_error}
        
        return {
            "success": True,
            "video_url": video_info['video_url'],
            "audio_url": audio_info['audio_url'],
            "title": video_info['title'],  # Vidfly'dan başlık al
            "resolution": video_info['resolution']
        }
            
    except Exception as e:
        error_msg = f"Hata: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

def cut_clip_from_url(video_url, audio_url, video_id, start, end, title, resolution):
    """URL'den direkt kesit oluştur (eski sistem)"""
    output_path = None
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
        
        # User-Agent ve header'lar ile FFmpeg komutu
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
        
        cmd = [
            "ffmpeg",
            "-user_agent", user_agent,  # User-Agent
            "-referer", "https://vidfly.ai/",  # Referer
            "-ss", str(start),          # Başlangıç zamanı
            "-i", video_url,            # Video input (URL)
            "-user_agent", user_agent,  # Audio için User-Agent
            "-referer", "https://turboscribe.ai/",  # Audio için Referer
            "-ss", str(start),          # Audio için başlangıç zamanı
            "-i", audio_url,            # Audio input (URL)
            "-t", str(duration),        # Süre
            "-map", "0:v",              # Video stream
            "-map", "1:a",              # Audio stream
            "-c:v", "copy",             # Video copy
            "-c:a", "aac",              # Audio codec
            "-b:a", "128k",             # Audio bitrate
            "-movflags", "+faststart",  # Web için optimize
            "-y",                       # Üzerine yaz
            output_path
        ]
        
        # FFmpeg'i timeout ile çalıştır (max 5 dakika per clip)
        print(f"🔄 FFmpeg başlatılıyor...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # FFmpeg stderr'ini her zaman logla (hata olsa da olmasa da)
        if result.stderr:
            stderr_preview = result.stderr[:1000] if len(result.stderr) > 1000 else result.stderr
            print(f"📋 FFmpeg log: {stderr_preview}")
        
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

def cleanup_job(job_id):
    """Job'u 10 dakika sonra sil"""
    time.sleep(600)  # 10 dakika bekle
    job = get_job(job_id)
    if job:
        print(f"🗑️ Job siliniyor: {job_id}")
        delete_job(job_id)

def process_clips_async(job_id, video_id, clips, video_url, audio_url, title, resolution):
    """Clipleri async olarak işle"""
    job = None
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
        
        # Tüm clipleri kes
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
                
                print(f"🎬 Processing clip {idx+1}/{len(clips)}: {start}s - {end}s")
                
                # Kesit oluştur (URL'den direkt)
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
                    print(f"✅ Clip {idx+1} processed successfully")
                else:
                    error_msg = result.get('error', 'Bilinmeyen hata')
                    errors.append({
                        'index': idx,
                        'error': error_msg,
                        'clip': {'start': start, 'end': end}
                    })
                    print(f"❌ Clip {idx+1} failed: {error_msg}")
                
            except Exception as clip_error:
                # Clip işleme hatası - devam et
                error_msg = f"Clip processing exception: {str(clip_error)}"
                print(f"❌ {error_msg}")
                errors.append({
                    'index': idx,
                    'error': error_msg,
                    'clip': clip
                })
            finally:
                # Her durumda processed sayısını artır ve kaydet
                job = get_job(job_id)  # En güncel job'u al
                if job:
                    job['processed'] += 1
                    save_job(job_id, job)
        
        # Job'u finished olarak işaretle
        job = get_job(job_id)  # En güncel job'u al
        if job:
            job['status'] = 'finished'
            job['results'] = results
            job['errors'] = errors
            job['completed_at'] = datetime.now().isoformat()
            save_job(job_id, job)
            print(f"✅ Job {job_id} completed: {len(results)} clips, {len(errors)} errors")
        
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

@app.route('/')
def index():
    """API bilgisi"""
    return jsonify({
        'name': 'YouTube Clip API',
        'version': '2.1',
        'endpoints': {
            'POST /api/create-clips': 'Kesitler oluştur (async, job ID döndürür)',
            'GET /api/check-job/<job_id>': 'Job durumunu kontrol et',
            'GET /api/clips': 'Mevcut kesitleri listele',
            'GET /clips/<filename>': 'Kesit dosyasını indir'
        }
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)