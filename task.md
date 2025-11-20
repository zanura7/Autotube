Development Task List

Phase 1: Setup & Basic UI

[ ] Install Python environment & dependencies (customtkinter, ffmpeg-python, yt-dlp, pydub).

[ ] Setup struktur folder proyek.

[ ] Buat Main Window dengan 3 Tab (Mode A, Mode B, Mode C).

[ ] Buat widget "Console Log" untuk menampilkan status proses.

[ ] Buat fungsi utilitas check_ffmpeg() untuk memastikan FFmpeg terinstall.

Phase 2: Mode B (Downloader) - Kerjakan ini dulu (paling mudah)

[ ] UI: Input area untuk multiline URL.

[ ] UI: Dropdown format (MP3 128/320, Video).

[ ] Backend: Implementasi yt-dlp class.

[ ] Backend: Tambahkan callback untuk update Progress Bar UI.

[ ] Backend: Implementasi Audio Normalization (menggunakan ffmpeg-normalize atau filter loudnorm).

[ ] Backend: Fitur generate .m3u playlist file setelah download selesai.

Phase 3: Mode A (Loop Creator)

[ ] UI: File picker untuk Input Video & Optional Audio.

[ ] UI: Slider/Input untuk durasi target (menit/jam).

[ ] UI: Dropdown resolusi output.

[ ] Backend: Logic get_video_duration().

[ ] Backend: Logic Crossfade:

[ ] Split video awal dan akhir.

[ ] Apply filter mix/blend.

[ ] Backend: Logic Looping (Concatenate file hasil blend berulang kali sampai target waktu).

[ ] Backend: Integrasi flag Hardware Acceleration (-c:v h264_nvenc etc).

Phase 4: Mode C (Generator)

[ ] UI: Input Playlist (Folder atau file .m3u).

[ ] UI: Input Visual (Gambar atau Video Loop dari Mode A).

[ ] Backend: Hitung total durasi semua file audio dalam playlist.

[ ] Backend: Logic Concatenate Audio (gabung semua mp3 jadi 1 file temp audio panjang).

[ ] Backend: Generate Metadata Chapters (Title - Start Time) berdasarkan durasi file individual.

[ ] Backend: Render Final Video (Loop Visual + Temp Audio).

[ ] Jika visual = Gambar -> tambahkan efek zoom halus (opsional).

[ ] Jika visual = Video -> loop video.

Phase 5: Polishing & Distribution

[ ] Error Handling: Munculkan popup jika file corrupt atau download gagal.

[ ] Tambahkan tombol "Open Output Folder".

[ ] Test rendering jangka panjang (1 jam+).

[ ] Packaging menjadi .exe menggunakan PyInstaller.
