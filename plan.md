Technical Plan & Architecture

1. Tech Stack Detail

Bahasa: Python 3.10+

GUI Framework: CustomTkinter (Modern, support Dark Mode native, lebih bagus dari Tkinter biasa) atau PyQt6 (Lebih robust). Rekomendasi: CustomTkinter untuk kecepatan dev.

Media Processing: * ffmpeg-python: Wrapper untuk command FFmpeg.

yt-dlp: Library download core (fork dari youtube-dl).

pydub: Manipulasi audio ringan (cek durasi, normalisasi simpel).

System: threading atau multiprocessing untuk memisahkan UI thread dan Worker thread.

2. Struktur Direktori

ContentForge/
├── assets/             # Icons, logo, placeholder images
├── bin/                # FFmpeg binaries (opsional jika portable)
├── src/
│   ├── __init__.py
│   ├── main.py         # Entry point
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── mode_a_tab.py
│   │   ├── mode_b_tab.py
│   │   └── mode_c_tab.py
│   ├── core/
│   │   ├── ffmpeg_handler.py   # Wrapper logika FFmpeg
│   │   ├── downloader.py       # Wrapper yt-dlp
│   │   ├── generator.py        # Logika penggabungan Mode C
│   │   └── utils.py            # Helper (time conversion, file check)
│   └── config/
│       └── settings.json       # Simpan path output terakhir, preferensi
├── output/             # Default folder hasil
├── requirements.txt
└── README.md


3. Arsitektur Modul

A. Backend Logic (Core)

FFmpeg Builder: Class untuk menyusun command line argument secara dinamis.

Contoh logic loop: Menggunakan filter complex filter xfade (crossfade) dan concat.

Downloader Worker: Class yang menjalankan yt-dlp dengan hook untuk mengirim progress bar update ke UI.

Assembler Engine: Class yang menghitung total durasi audio, lalu membuat command FFmpeg untuk me-loop video input -stream_loop -1 -t [TOTAL_DETIK].

B. Frontend Logic (UI)

Tab View System: Menggunakan TabView container untuk memisahkan Mode A, B, dan C.

Console Log Widget: Text area read-only yang menampilkan output stdout dari FFmpeg secara real-time agar user tahu proses berjalan.

Settings: Pilihan deteksi GPU (Auto, CUDA, OpenCL).

4. Strategi Rendering (FFmpeg)

Agar performa maksimal, command FFmpeg akan dipanggil menggunakan subprocess.Popen.

Contoh Command Logic Mode A (Seamless Loop):
Teknik crossfade manual di FFmpeg agak rumit, strateginya:

Potong video asli menjadi 2 bagian: Body dan Tail.

Tail (misal 1 detik terakhir) di-overlap dengan Head (1 detik awal).

Gunakan filter xfade untuk transisi.

Output hasil transisi ini menjadi "Base Loop Unit".

Loop "Base Loop Unit" sebanyak durasi yang diinginkan.

Contoh Command Logic Mode C (Image to Video):

ffmpeg -loop 1 -i image.jpg -i audio_playlist.mp3 -shortest -c:v libx264 -tune stillimage -c:a copy out.mp4


5. Timeline Pengembangan

Minggu 1: Setup project, implementasi ffmpeg_handler dasar, dan UI Skeleton.

Minggu 2: Mode B (Downloader) + Logic Normalisasi Audio.

Minggu 3: Mode A (Loop Logic) + Crossfading algorithm.

Minggu 4: Mode C (Integrasi) + Testing + Bug Fixing.
