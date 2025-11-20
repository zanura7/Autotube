# Autotube

adalah tool desktop berbasis Python dan FFmpeg untuk mengotomatisasi pembuatan konten video panjang (Long Form) seperti ASMR, Lofi Beats, dan Relaxation Videos untuk YouTube.

🌟 Fitur Utama

1. Mode A: Seamless Loop Creator

Ubah video pendek 5 detik menjadi loop 1 jam yang mulus tanpa patahan kasar.

Auto Crossfade Transition.

Support custom audio mixing.

GPU Acceleration support.

2. Mode B: Mass Downloader

Download aset audio/video secara massal untuk bahan konten.

Auto convert ke MP3 High Quality.

Audio Normalization (Volume rata).

Auto-generate Playlist file.

3. Mode C: YouTube Generator

Rakit bahan dari Mode A dan B menjadi video final siap upload.

Menggabungkan playlist audio dengan video loop.

Otomatis menyesuaikan durasi video dengan panjang lagu.

Generasi Metadata Chapter otomatis.

🛠️ Instalasi & Persyaratan

Prasyarat

Python 3.10+ terinstall.

FFmpeg terinstall dan masuk ke dalam SYSTEM PATH.

Windows: Download build dari gyan.dev, extract, lalu tambahkan folder bin ke Environment Variables.

Langkah Instalasi

# 1. Clone repository
git clone [https://github.com/zanura7/Autotube
cd contentforge

# 2. Buat Virtual Environment (Recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 3. Install Dependencies
pip install -r requirements.txt


Dependencies Utama

customtkinter (UI)

ffmpeg-python (Media Processing)

yt-dlp (Downloader)

Pillow (Image Processing)

🚀 Cara Penggunaan

Jalankan aplikasi:

python src/main.py


Untuk Membuat Loop: Pergi ke Tab Mode A. Pilih video sumber, atur durasi output (misal: 60 menit), klik Render.

Untuk Download Lagu: Pergi ke Tab Mode B. Paste link YouTube (satu per baris), pilih MP3, klik Download.

Untuk Finalisasi: Pergi ke Tab Mode C. Pilih folder hasil download Mode B, pilih video loop hasil Mode A, klik Generate.

🤝 Kontribusi

Pull request sangat diterima. Untuk perubahan besar, harap buka Issue terlebih dahulu untuk mendiskusikan apa yang ingin Anda ubah.

📝 Lisensi

MIT License
