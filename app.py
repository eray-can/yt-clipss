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

def get_video_download_url(video_id):
    """Vidfly.ai API'den video indirme linkini al"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        encoded_url = quote(video_url, safe='')
        
        api_url = f"https://api.vidfly.ai/api/media/youtube/download?url={encoded_url}"
        
        headers = {
            'accept': '*/*',
            'accept-language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'origin': 'https://vidfly.ai',
            'referer': 'https://vidfly.ai/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'x-app-name': 'vidfly-web',
            'x-app-version': '1.0.0'
        }
        
        print(f"🔄 Vidfly.ai API'ye istek atılıyor...")
        response = requests.get(api_url, headers=headers, timeout=30)
        
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
        
        # En iyi audio track'i bul (m4a 131kb/s)
        audio_url = None
        for item in items:
            if item.get('ext') == 'm4a' and item.get('type') == 'audio':
                audio_url = item.get('url')
                break
        
        if not audio_url:
            return None, "Audio track bulunamadı"
        
        print(f"✅ 720p video + audio linki alındı")
        return {
            'video_url': video_url,
            'audio_url': audio_url,
            'title': title,
            'resolution': '720p'
        }, None
        
    except Exception as e:
        return None, f"Hata: {str(e)}"

def get_video_urls(video_id):
    """Video URL'lerini al (indirme yapmadan)"""
    try:
        # Video indirme linkini al
        video_info, error = get_video_download_url(video_id)
        
        if error:
            print(f"❌ {error}")
            return {"success": False, "error": error}
        
        return {
            "success": True,
            "video_url": video_info['video_url'],
            "audio_url": video_info['audio_url'],
            "title": video_info['title'],
            "resolution": video_info['resolution']
        }
            
    except Exception as e:
        error_msg = f"Hata: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

def cut_clip_from_url(video_url, audio_url, video_id, start, end, title, resolution):
    """URL'den direkt kesit oluştur"""
    try:
        output_file = generate_clip_filename(video_id, start, end)
        output_path = os.path.join(CLIPS_FOLDER, output_file)
        
        # Eğer dosya zaten varsa, tekrar kesme
        if os.path.exists(output_path):
            print(f"✅ Kesit zaten mevcut: {output_file}")
            file_size = os.path.getsize(output_path)
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
        
        print(f"✂️ Kesit oluşturuluyor: {start}s - {end}s")
        duration = end - start
        
        # URL'den direkt kes (optimize edilmiş + audio senkronizasyonu)
        # Hibrit yaklaşım: Video copy (hızlı) + Audio encode (senkronizasyon)
        # -ss'yi input'tan önce koy ama audio'yu özel işle
        cmd = [
            "ffmpeg",
            "-ss", str(start),          # Video için hızlı seek
            "-i", video_url,
            "-ss", str(start),          # Audio için seek
            "-i", audio_url,
            "-t", str(duration),
            "-map", "0:v:0",            # Video stream
            "-map", "1:a:0",            # Audio stream
            "-c:v", "copy",             # Video copy (hızlı, kalite kaybı yok)
            "-c:a", "aac",              # Audio encode (senkronizasyon için)
            "-b:a", "192k",             # Audio bitrate
            "-af", "asetpts=PTS-STARTPTS", # Audio timestamp'i sıfırla
            "-video_track_timescale", "90000", # Video timescale
            "-movflags", "+faststart",  # Web için optimize et
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # FFmpeg stderr'ini her zaman logla (hata olsa da olmasa da)
        if result.stderr:
            print(f"📋 FFmpeg log: {result.stderr[:500]}")
        
        if result.returncode != 0:
            error_msg = f"FFmpeg hatası: {result.stderr}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Dosya oluşturuldu mu ve boyutu 0'dan büyük mü kontrol et
        if not os.path.exists(output_path):
            error_msg = "Dosya oluşturulamadı"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            error_msg = "Dosya boş oluşturuldu (0 byte)"
            print(f"❌ {error_msg}")
            os.remove(output_path)  # Boş dosyayı sil
            return {"success": False, "error": error_msg}
        
        print(f"✅ Kesit oluşturuldu: {output_file} ({file_size} bytes)")
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
            
    except Exception as e:
        error_msg = f"Hata: {str(e)}"
        print(f"❌ {error_msg}")
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
    try:
        results = []
        errors = []
        
        # Job'u processing olarak işaretle
        job = get_job(job_id)
        job['status'] = 'processing'
        job['total'] = len(clips)
        job['processed'] = 0
        save_job(job_id, job)
        
        # Tüm clipleri kes
        for idx, clip in enumerate(clips):
            start = clip.get('start')
            end = clip.get('end')
            
            if start is None or end is None:
                errors.append({
                    'index': idx,
                    'error': 'start ve end değerleri gerekli',
                    'clip': clip
                })
                job['processed'] += 1
                save_job(job_id, job)
                continue
            
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
            else:
                error_msg = result.get('error', 'Bilinmeyen hata')
                errors.append({
                    'index': idx,
                    'error': error_msg,
                    'clip': {'start': start, 'end': end}
                })
            
            job['processed'] += 1
            save_job(job_id, job)
        
        # Job'u finished olarak işaretle
        job['status'] = 'finished'
        job['results'] = results
        job['errors'] = errors
        job['completed_at'] = datetime.now().isoformat()
        save_job(job_id, job)
        
        # 10 dakika sonra job'u sil
        cleanup_thread = threading.Thread(target=cleanup_job, args=(job_id,))
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
    except Exception as e:
        job = get_job(job_id)
        if job:
            job['status'] = 'failed'
            job['error'] = str(e)
            save_job(job_id, job)

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
    """Belirli bir kesiti sil"""
    try:
        file_path = os.path.join(CLIPS_FOLDER, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Dosya bulunamadı'
            }), 404
        
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': f'{filename} silindi'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/clips/all', methods=['DELETE'])
def delete_all_clips():
    """Tüm kesitleri sil"""
    try:
        deleted_count = 0
        errors = []
        
        for filename in os.listdir(CLIPS_FOLDER):
            if filename.endswith('.mp4'):
                try:
                    file_path = os.path.join(CLIPS_FOLDER, filename)
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    errors.append({
                        'filename': filename,
                        'error': str(e)
                    })
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'errors': errors if errors else None
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
        'name': 'YouTube Clip API',
        'version': '2.0',
        'endpoints': {
            'POST /api/create-clips': 'Kesitler oluştur (async, job ID döndürür)',
            'GET /api/check-job/<job_id>': 'Job durumunu kontrol et',
            'GET /api/clips': 'Mevcut kesitleri listele',
            'GET /clips/<filename>': 'Kesit dosyasını indir',
            'DELETE /api/clips/<filename>': 'Belirli bir kesiti sil',
            'DELETE /api/clips/all': 'Tüm kesitleri sil'
        }
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
