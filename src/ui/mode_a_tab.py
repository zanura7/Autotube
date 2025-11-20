"""
Mode A: Seamless Loop Creator Tab UI
Create seamless video loops with crossfade transitions
"""

import customtkinter as ctk
from tkinter import filedialog
import threading
from pathlib import Path


class ModeATab(ctk.CTkFrame):
    """Mode A: Loop Creator UI"""

    def __init__(self, master, console_log):
        super().__init__(master)
        self.console_log = console_log
        self.is_rendering = False

        self.setup_ui()

    def setup_ui(self):
        """Setup the Mode A UI"""

        # Header
        header = ctk.CTkLabel(
            self,
            text="🔁 Mode A: Seamless Loop Creator",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.pack(pady=10)

        description = ctk.CTkLabel(
            self,
            text="Ubah video pendek (5-10 detik) menjadi loop seamless 1+ jam\ndengan crossfade transition yang halus.",
            font=ctk.CTkFont(size=12),
        )
        description.pack(pady=5)

        # Main container
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # Input Video Section
        input_frame = ctk.CTkFrame(container)
        input_frame.pack(fill="x", pady=10)

        video_label = ctk.CTkLabel(
            input_frame,
            text="🎥 Input Video:",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        video_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.video_path_var = ctk.StringVar(value="")
        video_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.video_path_var,
            width=400,
        )
        video_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        video_btn = ctk.CTkButton(
            input_frame,
            text="Browse",
            width=80,
            command=self.browse_video,
        )
        video_btn.grid(row=0, column=2, padx=5, pady=5)

        # Optional Audio Section
        audio_label = ctk.CTkLabel(
            input_frame,
            text="🎵 Audio (Optional):",
            font=ctk.CTkFont(size=12),
        )
        audio_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.audio_path_var = ctk.StringVar(value="")
        audio_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.audio_path_var,
            width=400,
        )
        audio_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        audio_btn = ctk.CTkButton(
            input_frame,
            text="Browse",
            width=80,
            command=self.browse_audio,
        )
        audio_btn.grid(row=1, column=2, padx=5, pady=5)

        # Settings Section
        settings_frame = ctk.CTkFrame(container)
        settings_frame.pack(fill="x", pady=10)

        # Duration
        duration_label = ctk.CTkLabel(
            settings_frame,
            text="⏱️  Target Duration:",
            font=ctk.CTkFont(size=11),
        )
        duration_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.duration_var = ctk.StringVar(value="60")
        duration_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.duration_var,
            width=100,
        )
        duration_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        duration_unit = ctk.CTkLabel(settings_frame, text="menit")
        duration_unit.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # Resolution
        resolution_label = ctk.CTkLabel(
            settings_frame,
            text="📐 Resolution:",
            font=ctk.CTkFont(size=11),
        )
        resolution_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.resolution_var = ctk.StringVar(value="1920x1080")
        resolution_menu = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.resolution_var,
            values=["1920x1080", "1280x720", "3840x2160", "Original"],
        )
        resolution_menu.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Crossfade Duration
        crossfade_label = ctk.CTkLabel(
            settings_frame,
            text="🔄 Crossfade Duration:",
            font=ctk.CTkFont(size=11),
        )
        crossfade_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.crossfade_var = ctk.StringVar(value="1.0")
        crossfade_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.crossfade_var,
            width=100,
        )
        crossfade_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        crossfade_unit = ctk.CTkLabel(settings_frame, text="detik")
        crossfade_unit.grid(row=2, column=2, padx=5, pady=5, sticky="w")

        # GPU Acceleration
        self.gpu_var = ctk.BooleanVar(value=False)
        gpu_check = ctk.CTkCheckBox(
            settings_frame,
            text="⚡ GPU Acceleration (NVIDIA only)",
            variable=self.gpu_var,
        )
        gpu_check.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Output Folder
        output_label = ctk.CTkLabel(
            settings_frame,
            text="📁 Output Folder:",
            font=ctk.CTkFont(size=11),
        )
        output_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")

        self.output_folder_var = ctk.StringVar(value="./output/loops")
        output_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.output_folder_var,
            width=300,
        )
        output_entry.grid(row=4, column=1, padx=10, pady=5, sticky="w")

        output_btn = ctk.CTkButton(
            settings_frame,
            text="Browse",
            width=80,
            command=self.browse_output_folder,
        )
        output_btn.grid(row=4, column=2, padx=5, pady=5)

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(container)
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            container,
            text="Ready to render",
            font=ctk.CTkFont(size=10),
        )
        self.progress_label.pack()

        # Action Buttons
        button_frame = ctk.CTkFrame(container)
        button_frame.pack(pady=10)

        self.render_btn = ctk.CTkButton(
            button_frame,
            text="🎬 Render Loop",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            width=200,
            command=self.start_render,
        )
        self.render_btn.pack(side="left", padx=5)

        open_folder_btn = ctk.CTkButton(
            button_frame,
            text="📁 Open Output Folder",
            font=ctk.CTkFont(size=12),
            height=40,
            width=180,
            command=self.open_output_folder,
        )
        open_folder_btn.pack(side="left", padx=5)

    def browse_video(self):
        """Browse for input video"""
        file_path = filedialog.askopenfilename(
            title="Pilih Video Input",
            filetypes=[
                ("Video Files", "*.mp4 *.avi *.mov *.mkv *.webm"),
                ("All Files", "*.*"),
            ],
        )
        if file_path:
            self.video_path_var.set(file_path)

    def browse_audio(self):
        """Browse for optional audio"""
        file_path = filedialog.askopenfilename(
            title="Pilih Audio (Optional)",
            filetypes=[
                ("Audio Files", "*.mp3 *.wav *.m4a *.aac"),
                ("All Files", "*.*"),
            ],
        )
        if file_path:
            self.audio_path_var.set(file_path)

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

    def start_render(self):
        """Start the rendering process"""
        if self.is_rendering:
            self.console_log.log_warning("Rendering sedang berjalan!")
            return

        # Validate input
        video_path = self.video_path_var.get()
        if not video_path:
            self.console_log.log_error("Pilih video input terlebih dahulu!")
            return

        if not Path(video_path).exists():
            self.console_log.log_error("Video input tidak ditemukan!")
            return

        try:
            duration = int(self.duration_var.get())
            if duration <= 0:
                raise ValueError("Duration must be positive")
        except ValueError:
            self.console_log.log_error("Durasi harus berupa angka positif!")
            return

        try:
            crossfade = float(self.crossfade_var.get())
            if crossfade < 0:
                raise ValueError("Crossfade must be non-negative")
        except ValueError:
            self.console_log.log_error("Crossfade duration harus berupa angka!")
            return

        self.console_log.log_info(f"🚀 Memulai rendering loop {duration} menit...")

        # Disable button
        self.is_rendering = True
        self.render_btn.configure(state="disabled", text="⏳ Rendering...")

        # Run render in separate thread
        thread = threading.Thread(
            target=self._render_worker,
            daemon=True,
        )
        thread.start()

    def _render_worker(self):
        """Worker thread for rendering"""
        from backend.loop_creator import LoopCreator

        # Get settings
        video_path = Path(self.video_path_var.get())
        audio_path = Path(self.audio_path_var.get()) if self.audio_path_var.get() else None
        output_folder = Path(self.output_folder_var.get())
        duration = int(self.duration_var.get()) * 60  # Convert to seconds
        resolution = self.resolution_var.get()
        crossfade = float(self.crossfade_var.get())
        use_gpu = self.gpu_var.get()

        # Create loop creator
        loop_creator = LoopCreator(
            output_folder=output_folder,
            console_log=self.console_log,
        )

        # Render
        success = loop_creator.create_loop(
            video_path=video_path,
            target_duration=duration,
            crossfade_duration=crossfade,
            resolution=resolution,
            audio_path=audio_path,
            use_gpu=use_gpu,
            progress_callback=self.update_progress,
        )

        # Reset UI
        self.is_rendering = False
        self.render_btn.configure(state="normal", text="🎬 Render Loop")
        self.progress_bar.set(0 if not success else 1)

        if success:
            self.progress_label.configure(text="✅ Rendering complete!")
        else:
            self.progress_label.configure(text="❌ Rendering failed!")

    def update_progress(self, progress, message=""):
        """Update progress bar"""
        self.progress_bar.set(progress)

        if message:
            self.progress_label.configure(text=message)
