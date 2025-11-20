Product Requirements Document (PRD)

Nama Proyek: ContentForge (ASMR & Lofi Studio)

Versi: 1.0

Status: Draft

Tech Stack: Python, FFmpeg, UI Framework (PyQt/CustomTkinter)

1. Ringkasan Eksekutif

Aplikasi desktop "all-in-one" yang dirancang untuk kreator konten relaksasi, ASMR, dan musik Lofi. Aplikasi ini menyederhanakan proses produksi yang biasanya membutuhkan software editing berat (Premiere/After Effects) menjadi alur kerja otomatis yang ringan dan cepat.

2. Target Pengguna

Youtuber ASMR/Ambience.

Produser musik Lofi/Relaxation.

Pengguna umum yang ingin membuat playlist offline.

3. Fitur & Spesifikasi Fungsional

3.1 Mode A: Seamless ASMR Video Loop Creator

Mengubah klip pendek menjadi video durasi panjang dengan transisi yang tidak terlihat (seamless).

Input: Video (MP4, MOV, MKV).

Core Logic:

Crossfade Loop: Mengambil 10-20% akhir video dan memudarkannya (blend) ke awal video untuk menyamarkan potongan.

Optical Flow (Advanced): Menggunakan interpolasi frame untuk gerakan lambat (opsional, resource heavy).

Kontrol Durasi: Preset (1m, 1h, dll) dan Custom input.

Audio Mixing:

Mute original audio.

Overlay file audio eksternal.

Volume slider independen untuk Video asli vs Audio tambahan.

Rendering: Mendukung Hardware Acceleration (NVENC/QSV) untuk render cepat.

3.2 Mode B: Mass MP3 Downloader & Playlist

Alat pengunduh massal yang fokus pada kualitas audio dan manajemen metadata.

Input: Text area untuk paste URL (multi-line).

Processing:

Integrasi dengan yt-dlp library.

Konversi otomatis ke MP3.

Audio Normalization: Menyamakan volume semua track (misal: -14 LUFS).

Output:

File MP3 dengan ID3 Tags (Artist, Title, Cover Art) yang rapi.

File .m3u atau .json playlist untuk digunakan di Mode C.

3.3 Mode C: YouTube Video Generator (The Assembler)

Menggabungkan hasil Mode A (Visual) dan Mode B (Audio) menjadi satu video final.

Input:

Visual: Gambar statis (JPG/PNG) atau Video Loop (dari Mode A).

Audio: Playlist folder atau file playlist dari Mode B.

Logic:

Duration Calc: Total durasi video = Total durasi playlist audio.

Visual Loop: Jika video input 1 jam tapi playlist 2 jam, video di-loop 2x.

Image Logic: Jika input gambar, tambahkan efek "Ken Burns" (pan & zoom) lambat agar tidak statis.

Chapter Generator: Otomatis membuat timestamp text untuk deskripsi YouTube (00:00 Lagu A, 03:20 Lagu B).

Output: Video final MP4 (H.264/AAC) siap upload.

4. Kebutuhan Non-Fungsional

UI/UX: Tampilan gelap (Dark Mode), bersih, progres bar yang akurat, dan log terminal yang bisa disembunyikan.

Performa: Tidak boleh membekukan (freeze) UI saat rendering (harus multi-threading).

Ketergantungan: Harus menyertakan binary FFmpeg atau mendeteksi instalasi FFmpeg user.

5. Batasan (Constraints)

Rendering 4K membutuhkan spesifikasi PC menengah ke atas.

Download URL bergantung pada stabilitas koneksi internet dan update library yt-dlp (karena perubahan algoritma YouTube).
