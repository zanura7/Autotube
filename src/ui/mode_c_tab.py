"""
Mode C: YouTube Video Generator Tab UI
Combine audio playlist with video loop
"""

import customtkinter as ctk
from tkinter import filedialog
import threading
from pathlib import Path


class ModeCTab(ctk.CTkFrame):
    """Mode C: Video Generator UI"""

    def __init__(self, master, console_log):
        super().__init__(master)
        self.console_log = console_log
        self.is_generating = False

        self.setup_ui()

    def setup_ui(self):
        """Setup the Mode C UI"""

        # Header
        header = ctk.CTkLabel(
            self,
            text="🎥 Mode C: YouTube Video Generator",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.pack(pady=10)

        description = ctk.CTkLabel(
            self,
            text="Gabungkan playlist audio dengan video loop\nmenjadi video final siap upload ke YouTube.",
            font=ctk.CTkFont(size=12),
        )
        description.pack(pady=5)

        # Main container
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # Input Section
        input_frame = ctk.CTkFrame(container)
        input_frame.pack(fill="x", pady=10)

        # Audio Playlist
        playlist_label = ctk.CTkLabel(
            input_frame,
            text="🎵 Audio Playlist:",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        playlist_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.playlist_var = ctk.StringVar(value="")
        playlist_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.playlist_var,
            width=350,
        )
        playlist_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        playlist_btn = ctk.CTkButton(
            input_frame,
            text="Browse M3U",
            width=100,
            command=self.browse_playlist,
        )
        playlist_btn.grid(row=0, column=2, padx=5, pady=5)

        # Or Audio Folder
        folder_label = ctk.CTkLabel(
            input_frame,
            text="📁 Or Audio Folder:",
            font=ctk.CTkFont(size=11),
        )
        folder_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.audio_folder_var = ctk.StringVar(value="")
        folder_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.audio_folder_var,
            width=350,
        )
        folder_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        folder_btn = ctk.CTkButton(
            input_frame,
            text="Browse Folder",
            width=100,
            command=self.browse_audio_folder,
        )
        folder_btn.grid(row=1, column=2, padx=5, pady=5)

        # Visual Input (Video or Image)
        visual_label = ctk.CTkLabel(
            input_frame,
            text="🖼️  Visual (Video/Image):",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        visual_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.visual_var = ctk.StringVar(value="")
        visual_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.visual_var,
            width=350,
        )
        visual_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        visual_btn = ctk.CTkButton(
            input_frame,
            text="Browse",
            width=100,
            command=self.browse_visual,
        )
        visual_btn.grid(row=2, column=2, padx=5, pady=5)

        # Settings Section
        settings_frame = ctk.CTkFrame(container)
        settings_frame.pack(fill="x", pady=10)

        # Resolution
        resolution_label = ctk.CTkLabel(
            settings_frame,
            text="📐 Resolution:",
            font=ctk.CTkFont(size=11),
        )
        resolution_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.resolution_var = ctk.StringVar(value="1920x1080")
        resolution_menu = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.resolution_var,
            values=["1920x1080", "1280x720", "3840x2160"],
        )
        resolution_menu.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Generate Chapters
        self.chapters_var = ctk.BooleanVar(value=True)
        chapters_check = ctk.CTkCheckBox(
            settings_frame,
            text="📖 Generate YouTube Chapters",
            variable=self.chapters_var,
        )
        chapters_check.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Image Zoom Effect (only for images)
        self.zoom_var = ctk.BooleanVar(value=True)
        zoom_check = ctk.CTkCheckBox(
            settings_frame,
            text="🔍 Apply Zoom Effect (for images)",
            variable=self.zoom_var,
        )
        zoom_check.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Output Folder
        output_label = ctk.CTkLabel(
            settings_frame,
            text="📁 Output Folder:",
            font=ctk.CTkFont(size=11),
        )
        output_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")

        # Use absolute path for output
        import os
        default_output = os.path.abspath("./output/final")
        self.output_folder_var = ctk.StringVar(value=default_output)
        output_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.output_folder_var,
            width=300,
        )
        output_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        output_btn = ctk.CTkButton(
            settings_frame,
            text="Browse",
            width=80,
            command=self.browse_output_folder,
        )
        output_btn.grid(row=3, column=2, padx=5, pady=5)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(container)
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            container,
            text="Ready to generate",
            font=ctk.CTkFont(size=10),
        )
        self.progress_label.pack()

        # Action Buttons
        button_frame = ctk.CTkFrame(container)
        button_frame.pack(pady=10)

        self.generate_btn = ctk.CTkButton(
            button_frame,
            text="🎬 Generate Video",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            width=200,
            command=self.start_generate,
        )
        self.generate_btn.pack(side="left", padx=5)

        open_folder_btn = ctk.CTkButton(
            button_frame,
            text="📁 Open Output Folder",
            font=ctk.CTkFont(size=12),
            height=40,
            width=180,
            command=self.open_output_folder,
        )
        open_folder_btn.pack(side="left", padx=5)

    def browse_playlist(self):
        """Browse for M3U playlist"""
        file_path = filedialog.askopenfilename(
            title="Pilih M3U Playlist",
            filetypes=[
                ("M3U Playlist", "*.m3u *.m3u8"),
                ("All Files", "*.*"),
            ],
        )
        if file_path:
            self.playlist_var.set(file_path)
            self.audio_folder_var.set("")  # Clear folder if playlist selected

    def browse_audio_folder(self):
        """Browse for audio folder"""
        folder = filedialog.askdirectory(title="Pilih Audio Folder")
        if folder:
            self.audio_folder_var.set(folder)
            self.playlist_var.set("")  # Clear playlist if folder selected

    def browse_visual(self):
        """Browse for visual (video or image)"""
        file_path = filedialog.askopenfilename(
            title="Pilih Visual (Video/Image)",
            filetypes=[
                ("Media Files", "*.mp4 *.avi *.mov *.mkv *.png *.jpg *.jpeg"),
                ("Video Files", "*.mp4 *.avi *.mov *.mkv"),
                ("Image Files", "*.png *.jpg *.jpeg"),
                ("All Files", "*.*"),
            ],
        )
        if file_path:
            self.visual_var.set(file_path)

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

    def start_generate(self):
        """Start the generation process"""
        if self.is_generating:
            self.console_log.log_warning("Generation sedang berjalan!")
            return

        # Validate input
        playlist_path = self.playlist_var.get()
        audio_folder = self.audio_folder_var.get()
        visual_path = self.visual_var.get()

        if not playlist_path and not audio_folder:
            self.console_log.log_error("Pilih playlist atau audio folder!")
            return

        if not visual_path:
            self.console_log.log_error("Pilih visual (video atau image)!")
            return

        if playlist_path and not Path(playlist_path).exists():
            self.console_log.log_error("Playlist file tidak ditemukan!")
            return

        if audio_folder and not Path(audio_folder).exists():
            self.console_log.log_error("Audio folder tidak ditemukan!")
            return

        if not Path(visual_path).exists():
            self.console_log.log_error("Visual file tidak ditemukan!")
            return

        self.console_log.log_info("🚀 Memulai video generation...")

        # Disable button
        self.is_generating = True
        self.generate_btn.configure(state="disabled", text="⏳ Generating...")

        # Run generation in separate thread
        thread = threading.Thread(
            target=self._generate_worker,
            daemon=True,
        )
        thread.start()

    def _generate_worker(self):
        """Worker thread for generation"""
        from backend.video_generator import VideoGenerator

        # Get settings
        playlist_path = Path(self.playlist_var.get()) if self.playlist_var.get() else None
        audio_folder = Path(self.audio_folder_var.get()) if self.audio_folder_var.get() else None
        visual_path = Path(self.visual_var.get())
        output_folder = Path(self.output_folder_var.get())
        resolution = self.resolution_var.get()
        generate_chapters = self.chapters_var.get()
        apply_zoom = self.zoom_var.get()

        # Create video generator
        generator = VideoGenerator(
            output_folder=output_folder,
            console_log=self.console_log,
        )

        # Generate
        success = generator.generate_video(
            playlist_path=playlist_path,
            audio_folder=audio_folder,
            visual_path=visual_path,
            resolution=resolution,
            generate_chapters=generate_chapters,
            apply_zoom=apply_zoom,
            progress_callback=self.update_progress,
        )

        # Reset UI
        self.is_generating = False
        self.generate_btn.configure(state="normal", text="🎬 Generate Video")
        self.progress_bar.set(0 if not success else 1)

        if success:
            self.progress_label.configure(text="✅ Generation complete!")
        else:
            self.progress_label.configure(text="❌ Generation failed!")

    def update_progress(self, progress, message=""):
        """Update progress bar"""
        self.progress_bar.set(progress)

        if message:
            self.progress_label.configure(text=message)
