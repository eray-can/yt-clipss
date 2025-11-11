# System Architecture & Flow

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT                                  │
│  (Browser, Python Script, curl, etc.)                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ HTTP POST /api/create-clips
                 │ {"video_id": "...", "clips": [...]}
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FLASK API SERVER                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐    │
│  │  create_clips() Endpoint                              │    │
│  │  1. Validate request                                  │    │
│  │  2. Get video URLs from Vidfly API                    │    │
│  │  3. Create job ID                                     │    │
│  │  4. Save job to disk (jobs/{job_id}.json)            │    │
│  │  5. Start async thread                                │    │
│  │  6. Return job_id immediately                         │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐    │
│  │  check_job() Endpoint                                 │    │
│  │  1. Read job from disk                                │    │
│  │  2. Return current status                             │    │
│  └───────────────────────────────────────────────────────┘    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ Async Thread
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  BACKGROUND WORKER                              │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐    │
│  │  process_clips_async()                                │    │
│  │                                                        │    │
│  │  FOR EACH CLIP:                                       │    │
│  │    ┌──────────────────────────────────────────┐      │    │
│  │    │ TRY:                                      │      │    │
│  │    │   1. Validate start/end                  │      │    │
│  │    │   2. Call cut_clip_from_url()            │      │    │
│  │    │   3. Add to results                      │      │    │
│  │    │ EXCEPT:                                   │      │    │
│  │    │   1. Log error                            │      │    │
│  │    │   2. Add to errors                        │      │    │
│  │    │ FINALLY:                                  │      │    │
│  │    │   1. Increment processed                  │      │    │
│  │    │   2. Save job status                      │      │    │
│  │    └──────────────────────────────────────────┘      │    │
│  │                                                        │    │
│  │  3. Mark job as 'finished'                            │    │
│  │  4. Start cleanup timer (10 min)                      │    │
│  └───────────────────────────────────────────────────────┘    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ FFmpeg subprocess
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FFMPEG PROCESSOR                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐    │
│  │  cut_clip_from_url()                                  │    │
│  │                                                        │    │
│  │  1. Check if file exists                              │    │
│  │  2. Download video stream (URL)                       │    │
│  │  3. Download audio stream (URL)                       │    │
│  │  4. Cut clip with FFmpeg (timeout: 5 min)            │    │
│  │  5. Validate output file                              │    │
│  │  6. Return result                                     │    │
│  └───────────────────────────────────────────────────────┘    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ Save to disk
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FILE SYSTEM                                │
│                                                                 │
│  jobs/                                                          │
│  ├── abc-123-def.json  (Job metadata)                          │
│  ├── xyz-456-ghi.json                                          │
│  └── ...                                                        │
│                                                                 │
│  clips/                                                         │
│  ├── video1-0-10.mp4   (Processed clips)                       │
│  ├── video2-10-20.mp4                                          │
│  └── ...                                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Request Flow

### 1. Create Clips Request

```
CLIENT                    API SERVER              WORKER THREAD           FFMPEG
  │                           │                         │                    │
  │ POST /api/create-clips    │                         │                    │
  ├──────────────────────────>│                         │                    │
  │                           │                         │                    │
  │                           │ Create job_id           │                    │
  │                           │ Save job (pending)      │                    │
  │                           │                         │                    │
  │                           │ Start thread            │                    │
  │                           ├────────────────────────>│                    │
  │                           │                         │                    │
  │ {job_id, status:pending}  │                         │                    │
  │<──────────────────────────┤                         │                    │
  │                           │                         │                    │
  │                           │                         │ Update: processing │
  │                           │                         │                    │
  │                           │                         │ Process clip 1     │
  │                           │                         ├───────────────────>│
  │                           │                         │                    │
  │                           │                         │ Cut video (5 min)  │
  │                           │                         │<───────────────────┤
  │                           │                         │                    │
  │                           │                         │ Process clip 2     │
  │                           │                         ├───────────────────>│
  │                           │                         │                    │
  │                           │                         │ Cut video (5 min)  │
  │                           │                         │<───────────────────┤
  │                           │                         │                    │
  │                           │                         │ Update: finished   │
  │                           │                         │                    │
```

### 2. Check Job Status

```
CLIENT                    API SERVER              FILE SYSTEM
  │                           │                         │
  │ GET /api/check-job/{id}   │                         │
  ├──────────────────────────>│                         │
  │                           │                         │
  │                           │ Read job file           │
  │                           ├────────────────────────>│
  │                           │                         │
  │                           │ Job data                │
  │                           │<────────────────────────┤
  │                           │                         │
  │ {status, processed, ...}  │                         │
  │<──────────────────────────┤                         │
  │                           │                         │
```

## Multi-Video Processing

### Before Fix (Problematic) ❌

```
VIDEO 1 ──> [PROCESSING] ──> Exception! ──> ❌ STUCK
                                             │
VIDEO 2 ──> [WAITING] ─────────────────────> ⏳ Never starts
                                             │
VIDEO 3 ──> [WAITING] ─────────────────────> ⏳ Never starts
```

**Problem:** Exception in Video 1 blocks entire system.

### After Fix (Robust) ✅

```
VIDEO 1 ──> [PROCESSING] ──> Exception! ──> ✅ FINISHED (with errors)
            │                                 │
            │                                 └─> Errors logged
            │
VIDEO 2 ──> [PROCESSING] ──> Success ──────> ✅ FINISHED
            │
            │
VIDEO 3 ──> [PROCESSING] ──> Success ──────> ✅ FINISHED
```

**Solution:** Each video processed independently in separate thread.

## Exception Handling Flow

```
┌─────────────────────────────────────────────────────────┐
│  FOR EACH CLIP                                          │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ TRY BLOCK                                       │   │
│  │                                                 │   │
│  │  ┌──────────────────────────────────────┐     │   │
│  │  │ Validate start/end                    │     │   │
│  │  │   ├─> Invalid? ──> Add to errors ──┐ │     │   │
│  │  │   └─> Valid? ──> Continue          │ │     │   │
│  │  └──────────────────────────────────────┘     │   │
│  │                                                 │   │
│  │  ┌──────────────────────────────────────┐     │   │
│  │  │ cut_clip_from_url()                  │     │   │
│  │  │   ├─> Success? ──> Add to results    │     │   │
│  │  │   └─> Failure? ──> Add to errors     │     │   │
│  │  └──────────────────────────────────────┘     │   │
│  │                                                 │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ EXCEPT BLOCK                                    │   │
│  │   ├─> Log exception                             │   │
│  │   └─> Add to errors                             │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ FINALLY BLOCK (ALWAYS RUNS)                     │   │
│  │   ├─> Increment processed count                 │   │
│  │   └─> Save job status                           │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Job State Machine

```
                    ┌──────────┐
                    │ PENDING  │
                    └────┬─────┘
                         │
                         │ Worker thread starts
                         │
                         ▼
                    ┌──────────┐
                    │PROCESSING│◄──────┐
                    └────┬─────┘       │
                         │             │
                         │ For each    │ Update progress
                         │ clip        │
                         │             │
                         ├─────────────┘
                         │
                         │ All clips processed
                         │
                         ▼
                    ┌──────────┐
              ┌────>│ FINISHED │
              │     └────┬─────┘
              │          │
              │          │ After 10 minutes
              │          │
              │          ▼
              │     ┌──────────┐
              │     │ DELETED  │
              │     └──────────┘
              │
              │
    Critical  │
    error     │
              │
         ┌────┴─────┐
         │  FAILED  │
         └────┬─────┘
              │
              │ After 10 minutes
              │
              ▼
         ┌──────────┐
         │ DELETED  │
         └──────────┘
```

## Timeout Protection

```
┌─────────────────────────────────────────────────────────┐
│  FFmpeg Process                                         │
│                                                         │
│  Start Time: T0                                         │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ Download video stream                          │   │
│  │ Download audio stream                          │   │
│  │ Cut and encode                                 │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  Current Time: T0 + X                                   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ IF X > 300 seconds (5 minutes):                │   │
│  │   ├─> Kill FFmpeg process                      │   │
│  │   ├─> Delete partial file                      │   │
│  │   ├─> Return timeout error                     │   │
│  │   └─> Continue to next clip                    │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## File Validation

```
┌─────────────────────────────────────────────────────────┐
│  Check if file exists                                   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ File exists?                                    │   │
│  │   ├─> YES ──> Check size                       │   │
│  │   │            ├─> Size > 0? ──> Use file      │   │
│  │   │            └─> Size = 0? ──> Delete & retry│   │
│  │   └─> NO ───> Create new file                  │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
│  ┌────────────────────────────────────────────────┐   │
│  │ After FFmpeg processing                         │   │
│  │   ├─> File created?                             │   │
│  │   │    ├─> YES ──> Check size                  │   │
│  │   │    │            ├─> Size > 0? ──> Success  │   │
│  │   │    │            └─> Size = 0? ──> Error    │   │
│  │   │    └─> NO ───> Error                       │   │
│  │   └─> On error ──> Delete partial file         │   │
│  └────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Concurrent Processing

### Scenario: 3 Videos, Each with 2 Clips

```
TIME ────────────────────────────────────────────────────>

Video 1 Thread:
  │
  ├─ Clip 1 [====]
  └─ Clip 2      [====]
                      └─ FINISHED

Video 2 Thread:
  │
  ├─ Clip 1 [====]
  └─ Clip 2      [====]
                      └─ FINISHED

Video 3 Thread:
  │
  ├─ Clip 1 [====]
  └─ Clip 2      [====]
                      └─ FINISHED

All threads run independently!
```

## Error Isolation

```
┌─────────────────────────────────────────────────────────┐
│  Job 1 (Video 1)                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │ Clip 1 ──> ✅ Success                          │   │
│  │ Clip 2 ──> ❌ Error (timeout)                  │   │
│  │ Clip 3 ──> ✅ Success                          │   │
│  └────────────────────────────────────────────────┘   │
│  Result: FINISHED (2 success, 1 error)                 │
└─────────────────────────────────────────────────────────┘
                         │
                         │ Does NOT affect
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Job 2 (Video 2)                                        │
│  ┌────────────────────────────────────────────────┐   │
│  │ Clip 1 ──> ✅ Success                          │   │
│  │ Clip 2 ──> ✅ Success                          │   │
│  └────────────────────────────────────────────────┘   │
│  Result: FINISHED (2 success, 0 errors)                │
└─────────────────────────────────────────────────────────┘
```

## Key Improvements

### 1. Exception Handling
- ✅ Try-catch per clip
- ✅ Finally block ensures progress update
- ✅ Errors logged but don't stop processing

### 2. Timeout Protection
- ✅ 5-minute timeout per clip
- ✅ Automatic cleanup on timeout
- ✅ Continue to next clip

### 3. File Validation
- ✅ Check existing files
- ✅ Validate file size
- ✅ Clean up empty files

### 4. Logging
- ✅ Start/end of each operation
- ✅ Progress tracking
- ✅ Error details

### 5. Job State Management
- ✅ Atomic updates
- ✅ Fresh reads from disk
- ✅ Consistent state

## Performance Characteristics

### Single Clip
- API call: 2-3s
- FFmpeg: 5-10s
- **Total: 7-13s**

### Multiple Clips (Same Video)
- API call: 2-3s (once)
- FFmpeg: 5-10s per clip
- **Total: 2-3s + (5-10s × N clips)**

### Multiple Videos (Concurrent)
- Each video processes independently
- **Total: max(video1_time, video2_time, video3_time)**

## Scalability

### Current (Threading)
- ✅ Good for: 1-10 concurrent jobs
- ⚠️ Limited by: Python GIL, thread overhead

### Recommended (Production)
- Use Celery + Redis
- Distributed workers
- Horizontal scaling
- Better monitoring

## Conclusion

The system now has:
- ✅ Robust error handling
- ✅ Timeout protection
- ✅ File validation
- ✅ Detailed logging
- ✅ Independent job processing
- ✅ Graceful degradation

Each component is isolated and resilient!
