# Autotube - Quick Start Guide

## 🚀 Getting Started

### Prerequisites

1. **Python 3.10+** - Download from [python.org](https://www.python.org/downloads/)
2. **FFmpeg** - Required for video processing

#### Installing FFmpeg

**Windows:**
1. Download FFmpeg from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
2. Extract the zip file
3. Add the `bin` folder to your System PATH environment variable

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### Installation

1. Clone the repository:
```bash
git clone https://github.com/zanura7/Autotube.git
cd Autotube
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv

# Activate on Windows:
venv\Scripts\activate

# Activate on Linux/Mac:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running Autotube

```bash
python src/main.py
```

## 📖 How to Use Each Mode

### Mode A: Seamless Loop Creator 🔁

**Purpose:** Turn a short video (5-10 seconds) into a seamless 1+ hour loop for background content.

**Steps:**
1. Click on the **"Mode A: Loop Creator"** tab
2. **Select Input Video:** Click "Browse" and choose your short video clip
3. **Optional Audio:** Add custom audio if you want to replace the video's audio
4. **Set Duration:** Enter target duration in minutes (e.g., 60 for 1 hour)
5. **Choose Resolution:** Select output resolution (1080p, 720p, 4K, or Original)
6. **Crossfade Duration:** Set transition smoothness (default: 1.0 second)
7. **GPU Acceleration:** Enable if you have NVIDIA GPU (faster rendering)
8. **Output Folder:** Choose where to save the result
9. Click **"🎬 Render Loop"**

**Use Cases:**
- ASMR background videos
- Lofi beats visuals
- Meditation/relaxation backgrounds
- Study music visuals

---

### Mode B: Mass Downloader ⬇️

**Purpose:** Download multiple audio/video files from YouTube with automatic audio normalization.

**Steps:**
1. Click on the **"Mode B: Downloader"** tab
2. **Paste URLs:** Enter YouTube URLs (one per line) in the text area
3. **Select Format:**
   - MP3 320kbps (High Quality) - Best for music
   - MP3 128kbps (Standard) - Smaller file size
   - Video (Best Quality) - Download video
4. **Output Folder:** Choose download destination
5. **Options:**
   - ✅ **Normalize Audio:** Makes all tracks the same volume
   - ✅ **Generate M3U Playlist:** Creates a playlist file
6. Click **"⬇️ Start Download"**

**Tips:**
- Audio normalization ensures consistent volume across tracks
- M3U playlist is useful for Mode C
- Progress is shown in the console log

---

### Mode C: YouTube Video Generator 🎥

**Purpose:** Combine an audio playlist with a visual (video loop or image) to create a final video ready for YouTube.

**Steps:**
1. Click on the **"Mode C: Generator"** tab
2. **Audio Source** (choose one):
   - **M3U Playlist:** Click "Browse M3U" to select playlist from Mode B
   - **Audio Folder:** Click "Browse Folder" to select folder with MP3 files
3. **Visual:** Click "Browse" to select:
   - Video loop (from Mode A)
   - Static image (will be looped)
4. **Settings:**
   - **Resolution:** Choose output resolution
   - **Generate YouTube Chapters:** ✅ Creates chapter markers (recommended)
   - **Apply Zoom Effect:** ✅ Adds slow zoom to images (for visual interest)
5. **Output Folder:** Choose where to save the final video
6. Click **"🎬 Generate Video"**

**Result:**
- Final video file (`.mp4`)
- Chapter file (`.chapters.txt`) - copy/paste into YouTube description

**YouTube Chapter Format:**
```
00:00:00 Track 1 Name
00:03:45 Track 2 Name
00:07:12 Track 3 Name
```

---

## 🎯 Common Workflows

### Workflow 1: Creating a Lofi Music Video

1. **Mode B:** Download lofi music tracks from YouTube
   - Enable audio normalization
   - Generate M3U playlist

2. **Mode A:** Create a seamless loop from a short animation/visual
   - 5-10 second clip works best
   - Set to 1+ hour duration

3. **Mode C:** Combine them
   - Select the M3U playlist
   - Select the loop video
   - Enable chapters
   - Generate final video

### Workflow 2: ASMR Long-Form Video

1. **Mode B:** Download ASMR audio tracks

2. **Mode C:** Use a calming static image
   - Select audio folder
   - Use a relaxing image (nature, abstract, etc.)
   - Enable zoom effect
   - Generate with chapters

### Workflow 3: Study/Work Music Compilation

1. **Mode B:** Download study music tracks
   - Normalize audio for consistent volume
   - Generate playlist

2. **Mode A:** Create animated background
   - Use subtle motion graphics
   - Loop for several hours

3. **Mode C:** Final assembly
   - Combine music playlist with loop
   - Add chapters for easy navigation

---

## 💡 Tips & Best Practices

### For Mode A (Loop Creator):
- **Ideal clip length:** 5-10 seconds works best
- **Choose seamless content:** Abstract patterns, water, clouds work great
- **Crossfade duration:** 1-2 seconds prevents visible jumps
- **GPU acceleration:** Speeds up rendering significantly (NVIDIA only)

### For Mode B (Downloader):
- **Always normalize audio** for consistent listening experience
- **Use MP3 320kbps** for best quality
- **Organize downloads** by creating specific folders for each project

### For Mode C (Generator):
- **Generate chapters** for better user experience on YouTube
- **Zoom effect on images** adds visual interest to static backgrounds
- **Test with short playlists** first to ensure settings are correct

### General Tips:
- **Use "Open Output Folder"** button to quickly access your files
- **Monitor the console log** for progress and error messages
- **Keep FFmpeg updated** for best compatibility

---

## ⚠️ Troubleshooting

### "FFmpeg not found" error
- Verify FFmpeg is installed: `ffmpeg -version`
- Make sure FFmpeg is in your system PATH
- Restart terminal/computer after installing FFmpeg

### Download fails in Mode B
- Check internet connection
- Verify YouTube URL is valid
- Some videos may have download restrictions

### Video rendering is slow
- Enable GPU acceleration (Mode A) if you have NVIDIA GPU
- Lower output resolution
- Use shorter crossfade duration
- Close other applications

### Audio/Video out of sync
- This is rare, but ensure:
  - All audio files are valid (not corrupted)
  - Video source is not variable frame rate

---

## 🆘 Need Help?

If you encounter issues:
1. Check the **Console Log** in the app for detailed error messages
2. Ensure all prerequisites are installed correctly
3. Verify input files are not corrupted
4. Open an issue on [GitHub](https://github.com/zanura7/Autotube/issues)

---

## 📝 License

MIT License - See LICENSE file for details

---

**Happy Creating! 🎬🎵**
