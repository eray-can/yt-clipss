from flask import Flask, request, jsonify, send_from_directory, url_for
import subprocess
import os
import time
import requests
from pathlib import Path
from urllib.parse import quote

app = Flask(__name__)

# Kesitlerin kaydedileceği klasör
CLIPS_FOLDER = "clips"
Path(CLIPS_FOLDER).mkdir(exist_ok=True)

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

def download_full_video(video_id):
    """Tam videoyu indir (video+audio merge)"""
    try:
        temp_video_path = os.path.join(CLIPS_FOLDER, f"temp_{video_id}.mp4")
        
        # Eğer zaten indirilmişse, tekrar indirme
        if os.path.exists(temp_video_path):
            print(f"✅ Video zaten indirilmiş: {video_id}")
            return {"success": True, "path": temp_video_path}
        
        print(f"📥 Tam video indiriliyor: {video_id}")
        
        # Video indirme linkini al
        video_info, error = get_video_download_url(video_id)
        
        if error:
            print(f"❌ {error}")
            return {"success": False, "error": error}
        
        video_url = video_info['video_url']
        audio_url = video_info['audio_url']
        title = video_info['title']
        resolution = video_info['resolution']
        
        # FFmpeg ile tam video+audio merge
        print(f"🔄 FFmpeg ile 720p video+audio merge ediliyor...")
        cmd = [
            "ffmpeg",
            "-i", video_url,
            "-i", audio_url,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-y",
            temp_video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Tam video indirildi: {video_id}")
            return {
                "success": True,
                "path": temp_video_path,
                "title": title,
                "resolution": resolution
            }
        else:
            error_msg = f"FFmpeg hatası: {result.stderr}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"Hata: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

def cut_clip_from_video(video_path, video_id, start, end, title, resolution):
    """İndirilmiş videodan kesit oluştur"""
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
        
        cmd = [
            "ffmpeg",
            "-ss", str(start),
            "-i", video_path,
            "-t", str(duration),
            "-c:v", "copy",
            "-c:a", "copy",
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Kesit oluşturuldu: {output_file}")
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
        else:
            error_msg = f"FFmpeg hatası: {result.stderr}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"Hata: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

@app.route('/api/create-clips', methods=['POST'])
def create_clips():
    """
    Kesitler oluştur ve URL'lerini döndür
    
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
        
        # Önce tam videoyu indir
        download_result = download_full_video(video_id)
        
        if not download_result.get('success'):
            return jsonify({
                'success': False,
                'error': download_result.get('error', 'Video indirilemedi')
            }), 500
        
        video_path = download_result['path']
        title = download_result.get('title', 'Unknown')
        resolution = download_result.get('resolution', '720p')
        
        results = []
        errors = []
        
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
                continue
            
            # Kesit oluştur
            result = cut_clip_from_video(video_path, video_id, start, end, title, resolution)
            
            if result.get('success'):
                filename = result['filename']
                video_info = result.get('video_info', {})
                
                # URL oluştur
                clip_url = url_for('serve_clip', filename=filename, _external=True)
                
                results.append({
                    'start': start,
                    'end': end,
                    'url': clip_url,
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
        
        # Temp video dosyasını sil
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
                print(f"🗑️ Temp video silindi: {video_id}")
        except Exception as e:
            print(f"⚠️ Temp video silinemedi: {str(e)}")
        
        return jsonify({
            'success': len(results) > 0,
            'video_id': video_id,
            'clips': results,
            'total': len(results),
            'errors': errors if errors else None,
            'error_count': len(errors)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        'version': '1.0',
        'endpoints': {
            'POST /api/create-clips': 'Kesitler oluştur',
            'GET /api/clips': 'Mevcut kesitleri listele',
            'GET /clips/<filename>': 'Kesit dosyasını indir',
            'DELETE /api/clips/<filename>': 'Belirli bir kesiti sil',
            'DELETE /api/clips/all': 'Tüm kesitleri sil'
        }
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
