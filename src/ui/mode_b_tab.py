"""
Mode B: Mass Downloader Tab UI
Download audio/video from YouTube with normalization
"""

import customtkinter as ctk
from tkinter import filedialog
import threading
from pathlib import Path


class ModeBTab(ctk.CTkFrame):
    """Mode B: Mass Downloader UI"""

    def __init__(self, master, console_log):
        super().__init__(master)
        self.console_log = console_log
        self.is_downloading = False

        self.setup_ui()

    def setup_ui(self):
        """Setup the Mode B UI"""

        # Header
        header = ctk.CTkLabel(
            self,
            text="⬇️ Mode B: Mass Downloader",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.pack(pady=10)

        description = ctk.CTkLabel(
            self,
            text="Download audio/video secara massal dari YouTube\ndengan normalisasi audio otomatis.",
            font=ctk.CTkFont(size=12),
        )
        description.pack(pady=5)

        # Main container
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # URL Input Section
        url_label = ctk.CTkLabel(
            container,
            text="📋 Paste URL YouTube (satu per baris):",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        url_label.pack(anchor="w", pady=(10, 5))

        self.url_text = ctk.CTkTextbox(container, height=150)
        self.url_text.pack(fill="both", expand=True, pady=5)

        # Settings Section
        settings_frame = ctk.CTkFrame(container)
        settings_frame.pack(fill="x", pady=10)

        # Format Selection
        format_label = ctk.CTkLabel(
            settings_frame,
            text="🎵 Format:",
            font=ctk.CTkFont(size=11),
        )
        format_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.format_var = ctk.StringVar(value="mp3_320")
        format_options = {
            "MP3 320kbps (High Quality)": "mp3_320",
            "MP3 128kbps (Standard)": "mp3_128",
            "Video (Best Quality)": "video_best",
        }

        self.format_menu = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.format_var,
            values=list(format_options.keys()),
        )
        self.format_menu.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Output Folder Selection
        folder_label = ctk.CTkLabel(
            settings_frame,
            text="📁 Output Folder:",
            font=ctk.CTkFont(size=11),
        )
        folder_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        # Use absolute path for output
        import os
        default_output = os.path.abspath("./output/downloads")
        self.output_folder_var = ctk.StringVar(value=default_output)
        folder_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.output_folder_var,
            width=300,
        )
        folder_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        folder_btn = ctk.CTkButton(
            settings_frame,
            text="Browse",
            width=80,
            command=self.browse_output_folder,
        )
        folder_btn.grid(row=1, column=2, padx=5, pady=5)

        # Normalize Audio Option
        self.normalize_var = ctk.BooleanVar(value=True)
        normalize_check = ctk.CTkCheckBox(
            settings_frame,
            text="🔊 Normalize Audio (Volume rata)",
            variable=self.normalize_var,
        )
        normalize_check.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Generate Playlist Option
        self.playlist_var = ctk.BooleanVar(value=True)
        playlist_check = ctk.CTkCheckBox(
            settings_frame,
            text="📝 Generate M3U Playlist",
            variable=self.playlist_var,
        )
        playlist_check.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(container)
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            container,
            text="Ready to download",
            font=ctk.CTkFont(size=10),
        )
        self.progress_label.pack()

        # Action Buttons
        button_frame = ctk.CTkFrame(container)
        button_frame.pack(pady=10)

        self.download_btn = ctk.CTkButton(
            button_frame,
            text="⬇️ Start Download",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            width=200,
            command=self.start_download,
        )
        self.download_btn.pack(side="left", padx=5)

        open_folder_btn = ctk.CTkButton(
            button_frame,
            text="📁 Open Output Folder",
            font=ctk.CTkFont(size=12),
            height=40,
            width=180,
            command=self.open_output_folder,
        )
        open_folder_btn.pack(side="left", padx=5)

    def browse_output_folder(self):
        """Browse for output folder"""
        folder = filedialog.askdirectory(
            title="Pilih Output Folder",
            initialdir=self.output_folder_var.get(),
        )
        if folder:
            self.output_folder_var.set(folder)

    def open_output_folder(self):
        """Open output folder in file manager"""
        from utils.file_utils import open_folder

        folder = self.output_folder_var.get()
        if open_folder(folder):
            self.console_log.log_success(f"📁 Opened folder: {folder}")
        else:
            self.console_log.log_error("❌ Could not open folder")

    def start_download(self):
        """Start the download process"""
        if self.is_downloading:
            self.console_log.log_warning("Download sedang berjalan!")
            return

        # Get URLs
        urls_text = self.url_text.get("1.0", "end").strip()
        if not urls_text:
            self.console_log.log_error("Tidak ada URL yang dimasukkan!")
            return

        urls = [url.strip() for url in urls_text.split("\n") if url.strip()]

        if not urls:
            self.console_log.log_error("Tidak ada URL yang valid!")
            return

        self.console_log.log_info(f"🚀 Memulai download {len(urls)} file...")

        # Disable button
        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳ Downloading...")

        # Run download in separate thread
        thread = threading.Thread(
            target=self._download_worker,
            args=(urls,),
            daemon=True,
        )
        thread.start()

    def _download_worker(self, urls):
        """Worker thread for downloading"""
        from backend.downloader import Downloader

        # Get settings
        format_map = {
            "MP3 320kbps (High Quality)": "mp3_320",
            "MP3 128kbps (Standard)": "mp3_128",
            "Video (Best Quality)": "video_best",
        }

        selected_format = self.format_var.get()
        format_key = format_map.get(selected_format, "mp3_320")

        output_folder = Path(self.output_folder_var.get())
        normalize = self.normalize_var.get()
        generate_playlist = self.playlist_var.get()

        # Create downloader
        downloader = Downloader(
            output_folder=output_folder,
            console_log=self.console_log,
        )

        # Download
        success = downloader.download_batch(
            urls=urls,
            format_type=format_key,
            normalize=normalize,
            progress_callback=self.update_progress,
        )

        # Generate playlist if requested
        if success and generate_playlist:
            playlist_file = downloader.generate_playlist()
            if playlist_file:
                self.console_log.log_success(f"✅ Playlist created: {playlist_file}")

        # Reset UI
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⬇️ Start Download")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Download complete!")

    def update_progress(self, current, total, message=""):
        """Update progress bar and label"""
        if total > 0:
            progress = current / total
            self.progress_bar.set(progress)

        label_text = f"Progress: {current}/{total}"
        if message:
            label_text += f" - {message}"

        self.progress_label.configure(text=label_text)
