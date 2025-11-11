"""
Test suite for multi-video processing
Tests the scenario where multiple videos are processed sequentially
"""
import requests
import json
import time
import unittest

BASE_URL = "http://localhost:5000"

class TestMultiVideoProcessing(unittest.TestCase):
    """Test multi-video processing scenarios"""
    
    def test_sequential_videos(self):
        """Test processing multiple videos sequentially"""
        print("\n" + "="*60)
        print("TEST: Sequential Video Processing")
        print("="*60)
        
        videos = [
            {
                "video_id": "Z3TMbaX_X0k",
                "clips": [{"start": 0, "end": 5}]
            },
            {
                "video_id": "KDV_-rXGy7A",
                "clips": [{"start": 0, "end": 5}]
            },
            {
                "video_id": "dQw4w9WgXcQ",  # Different video
                "clips": [{"start": 0, "end": 5}]
            }
        ]
        
        job_ids = []
        
        # Start all jobs
        for idx, video_data in enumerate(videos):
            print(f"\n📤 Starting job {idx+1}/{len(videos)} for video: {video_data['video_id']}")
            
            try:
                response = requests.post(
                    f"{BASE_URL}/api/create-clips",
                    json=video_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    job_id = result['job_id']
                    job_ids.append({
                        'job_id': job_id,
                        'video_id': video_data['video_id'],
                        'index': idx
                    })
                    print(f"✅ Job started: {job_id}")
                else:
                    print(f"❌ Failed to start job: {response.status_code}")
                    print(response.text)
                    job_ids.append({
                        'job_id': None,
                        'video_id': video_data['video_id'],
                        'index': idx,
                        'error': response.text
                    })
            except Exception as e:
                print(f"❌ Exception starting job: {str(e)}")
                job_ids.append({
                    'job_id': None,
                    'video_id': video_data['video_id'],
                    'index': idx,
                    'error': str(e)
                })
        
        # Monitor all jobs
        print(f"\n{'='*60}")
        print("Monitoring all jobs...")
        print(f"{'='*60}")
        
        max_wait_time = 300  # 5 minutes max
        start_time = time.time()
        completed_jobs = set()
        
        while len(completed_jobs) < len(job_ids) and (time.time() - start_time) < max_wait_time:
            for job_info in job_ids:
                job_id = job_info['job_id']
                if not job_id or job_id in completed_jobs:
                    continue
                
                try:
                    check_response = requests.get(f"{BASE_URL}/api/check-job/{job_id}")
                    
                    if check_response.status_code == 200:
                        job_status = check_response.json()
                        status = job_status['status']
                        processed = job_status['processed']
                        total = job_status['total']
                        
                        print(f"📊 Job {job_info['index']+1} ({job_info['video_id'][:8]}...): {status} | {processed}/{total}")
                        
                        if status in ['finished', 'failed']:
                            completed_jobs.add(job_id)
                            if status == 'finished':
                                print(f"✅ Job {job_info['index']+1} completed successfully")
                                clips = job_status.get('clips', [])
                                errors = job_status.get('errors', [])
                                print(f"   Clips: {len(clips)}, Errors: {len(errors)}")
                            else:
                                print(f"❌ Job {job_info['index']+1} failed: {job_status.get('error')}")
                    else:
                        print(f"❌ Job {job_info['index']+1}: HTTP {check_response.status_code}")
                        completed_jobs.add(job_id)
                        
                except Exception as e:
                    print(f"❌ Exception checking job {job_info['index']+1}: {str(e)}")
            
            if len(completed_jobs) < len(job_ids):
                time.sleep(3)
        
        # Final report
        print(f"\n{'='*60}")
        print("FINAL REPORT")
        print(f"{'='*60}")
        print(f"Total jobs: {len(job_ids)}")
        print(f"Completed: {len(completed_jobs)}")
        print(f"Time elapsed: {time.time() - start_time:.2f}s")
        
        # Assert all jobs completed
        self.assertEqual(len(completed_jobs), len([j for j in job_ids if j['job_id']]), 
                        "Not all jobs completed within timeout")
    
    def test_concurrent_same_video(self):
        """Test processing same video with different clips concurrently"""
        print("\n" + "="*60)
        print("TEST: Concurrent Same Video Processing")
        print("="*60)
        
        video_id = "Z3TMbaX_X0k"
        
        jobs = [
            {"video_id": video_id, "clips": [{"start": 0, "end": 5}]},
            {"video_id": video_id, "clips": [{"start": 5, "end": 10}]},
            {"video_id": video_id, "clips": [{"start": 10, "end": 15}]}
        ]
        
        job_ids = []
        
        # Start all jobs at once
        for idx, job_data in enumerate(jobs):
            print(f"📤 Starting job {idx+1}")
            response = requests.post(f"{BASE_URL}/api/create-clips", json=job_data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                job_ids.append(result['job_id'])
                print(f"✅ Job {idx+1} started: {result['job_id']}")
            else:
                print(f"❌ Job {idx+1} failed to start")
        
        # Wait for all to complete
        completed = 0
        max_iterations = 60
        iterations = 0
        
        while completed < len(job_ids) and iterations < max_iterations:
            completed = 0
            for job_id in job_ids:
                check_response = requests.get(f"{BASE_URL}/api/check-job/{job_id}")
                if check_response.status_code == 200:
                    status = check_response.json()['status']
                    if status in ['finished', 'failed']:
                        completed += 1
            
            print(f"📊 Completed: {completed}/{len(job_ids)}")
            time.sleep(2)
            iterations += 1
        
        print(f"\n✅ All jobs completed: {completed}/{len(job_ids)}")
        self.assertEqual(completed, len(job_ids), "Not all jobs completed")
    
    def test_error_recovery(self):
        """Test that system continues after an error"""
        print("\n" + "="*60)
        print("TEST: Error Recovery")
        print("="*60)
        
        # First, try with an invalid video ID
        print("📤 Starting job with invalid video ID...")
        invalid_job = {
            "video_id": "INVALID_VIDEO_ID_12345",
            "clips": [{"start": 0, "end": 5}]
        }
        
        response1 = requests.post(f"{BASE_URL}/api/create-clips", json=invalid_job, timeout=10)
        
        if response1.status_code == 200:
            job1_id = response1.json()['job_id']
            print(f"✅ Invalid job started: {job1_id}")
            
            # Wait for it to fail
            time.sleep(10)
            check1 = requests.get(f"{BASE_URL}/api/check-job/{job1_id}")
            if check1.status_code == 200:
                status1 = check1.json()['status']
                print(f"📊 Invalid job status: {status1}")
        
        # Now try with a valid video ID
        print("\n📤 Starting job with valid video ID...")
        valid_job = {
            "video_id": "Z3TMbaX_X0k",
            "clips": [{"start": 0, "end": 5}]
        }
        
        response2 = requests.post(f"{BASE_URL}/api/create-clips", json=valid_job, timeout=10)
        
        if response2.status_code == 200:
            job2_id = response2.json()['job_id']
            print(f"✅ Valid job started: {job2_id}")
            
            # Wait for it to complete
            max_wait = 60
            waited = 0
            while waited < max_wait:
                check2 = requests.get(f"{BASE_URL}/api/check-job/{job2_id}")
                if check2.status_code == 200:
                    status2 = check2.json()['status']
                    print(f"📊 Valid job status: {status2}")
                    if status2 in ['finished', 'failed']:
                        break
                time.sleep(3)
                waited += 3
            
            self.assertIn(status2, ['finished', 'failed'], "Job should complete")
            print(f"✅ System recovered and processed valid job")

if __name__ == "__main__":
    print("="*60)
    print("MULTI-VIDEO PROCESSING TEST SUITE")
    print("="*60)
    print("\nMake sure the Flask app is running on http://localhost:5000")
    print("\nStarting tests in 3 seconds...")
    time.sleep(3)
    
    unittest.main(verbosity=2)
