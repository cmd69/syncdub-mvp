# SyncDub Audio Synchronization Bug Fix

## 🐛 Problem Identified

The Spanish audio was still delayed by 4 seconds in the final MKV file because of a **critical bug** in the `_apply_sync_offset` function in `app/services/sync_service.py`.

### The Bug
When the offset was positive (meaning the dubbed audio was delayed), the function was **adding more delay** instead of **removing the delay**.

**Original (WRONG) logic:**
- `offset > 0`: Used `adelay` filter to add delay ❌
- `offset < 0`: Used `-ss` to skip ahead ✅

**Corrected logic:**
- `offset > 0`: Use `-ss` to skip ahead and remove delay ✅
- `offset < 0`: Use `adelay` to add delay ✅

## 🔧 Changes Made

### 1. Fixed the Critical Bug
**File:** `app/services/sync_service.py` - `_apply_sync_offset` function

```python
# BEFORE (WRONG):
elif offset > 0:  # Retrasar audio
    cmd = [
        'ffmpeg', '-i', audio_path,
        '-af', f'adelay={int(abs(offset) * 1000)}|{int(abs(offset) * 1000)}',
        '-threads', '0',
        '-y', synced_audio_path
    ]

# AFTER (CORRECT):
elif offset > 0:  # Dubbed audio is DELAYED, need to ADVANCE it
    cmd = [
        'ffmpeg', '-ss', str(offset), '-i', audio_path,
        '-threads', '0',
        '-y', synced_audio_path
    ]
```

### 2. Added Comprehensive Logging
Added detailed logging throughout the entire synchronization process:

- **Main processing function** (`_process_sync_task`)
- **Audio extraction** (`_extract_audio_optimized`)
- **Offset calculation** (`_calculate_sync_offset_safe`, `_calculate_simple_offset_segments`, `_calculate_simple_offset_from_audio`)
- **Sync application** (`_apply_sync_offset`)
- **MKV generation** (`_generate_mkv_final`)

### 3. Created Debug Test Script
**File:** `test_sync_debug.py`

This script allows you to:
- Test FFmpeg commands directly
- Test the sync service methods without Flask context
- Debug the synchronization process step by step

## 🧪 How to Test

### Option 1: Use the Debug Test Script
```bash
python3 test_sync_debug.py
```

Choose option 1 to test FFmpeg commands directly, or option 2 to test the sync service.

### Option 2: Use the Web Interface
1. Start the application
2. Upload your test videos (original + Spanish version with 4-second delay)
3. Monitor the logs for detailed debugging information

### Option 3: Check the Logs
The application now logs every step of the process with clear markers:

```
=== STARTING SYNC TASK: [task_id] ===
=== EXTRACTING AUDIO: original ===
=== EXTRACTING AUDIO: dubbed ===
=== CALCULATING SYNC OFFSET WITH SEMANTIC ANALYSIS ===
=== CALCULATED TIME OFFSET: 4.000 seconds ===
=== APPLYING SYNC OFFSET ===
Positive offset detected: 4.000s - ADVANCING audio (removing delay)
FFmpeg command: ffmpeg -ss 4.0 -i /tmp/dubbed_[task_id].wav -threads 0 -y /tmp/synced_[task_id].wav
=== GENERATING FINAL MKV ===
```

## 🔍 Expected Behavior

With your test videos (Spanish version delayed by 4 seconds):

1. **Offset calculation** should detect ~4 seconds delay
2. **Sync application** should ADVANCE the Spanish audio by 4 seconds (remove the delay)
3. **Final MKV** should have both audio tracks perfectly synchronized

## 📋 Key Log Messages to Look For

- `=== CALCULATED TIME OFFSET: [X.XXX] seconds ===`
- `Positive offset detected: [X.XXX]s - ADVANCING audio (removing delay)`
- `FFmpeg command: ffmpeg -ss [X.X] -i [audio_path] ...`
- `=== MKV GENERATION COMPLETE ===`

## 🚨 If Issues Persist

1. **Check the logs** for the exact offset calculated
2. **Verify FFmpeg commands** are correct
3. **Test with the debug script** to isolate the issue
4. **Check file paths** and permissions

## 📝 Notes

- The fix ensures that when the dubbed audio is delayed, we advance it (remove the delay)
- When the dubbed audio is ahead, we delay it (add delay)
- All FFmpeg commands are now logged for debugging
- The test script can help verify the fix works correctly 