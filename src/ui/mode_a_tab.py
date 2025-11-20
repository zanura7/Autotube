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

    def __init__(self, master, console_log, config=None):
        super().__init__(master)
        self.console_log = console_log
        self.config = config
        self.is_rendering = False
        self.cancel_event = threading.Event()  # For cancellation

        self.setup_ui()
        self._load_settings()

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
            command=self.toggle_cpu_options,
        )
        gpu_check.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # CPU Performance Settings (only visible when GPU is off)
        cpu_label = ctk.CTkLabel(
            settings_frame,
            text="⚙️ CPU Settings:",
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        cpu_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.cpu_label = cpu_label

        # Encoding Speed
        speed_label = ctk.CTkLabel(
            settings_frame,
            text="   Speed Preset:",
            font=ctk.CTkFont(size=10),
        )
        speed_label.grid(row=5, column=0, padx=10, pady=2, sticky="w")
        self.speed_label = speed_label

        self.preset_var = ctk.StringVar(value="medium")
        preset_menu = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.preset_var,
            values=["ultrafast", "superfast", "veryfast", "fast", "medium", "slow"],
            width=150,
        )
        preset_menu.grid(row=5, column=1, padx=10, pady=2, sticky="w")
        self.preset_menu = preset_menu

        # Quality
        quality_label = ctk.CTkLabel(
            settings_frame,
            text="   Quality (CRF):",
            font=ctk.CTkFont(size=10),
        )
        quality_label.grid(row=6, column=0, padx=10, pady=2, sticky="w")
        self.quality_label = quality_label

        self.quality_var = ctk.StringVar(value="23 (Good)")
        quality_menu = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.quality_var,
            values=["18 (Best)", "23 (Good)", "28 (Faster)"],
            width=150,
        )
        quality_menu.grid(row=6, column=1, padx=10, pady=2, sticky="w")
        self.quality_menu = quality_menu

        # Threads
        threads_label = ctk.CTkLabel(
            settings_frame,
            text="   CPU Threads:",
            font=ctk.CTkFont(size=10),
        )
        threads_label.grid(row=7, column=0, padx=10, pady=2, sticky="w")
        self.threads_label = threads_label

        self.threads_var = ctk.StringVar(value="auto")
        threads_menu = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.threads_var,
            values=["auto", "2", "4", "6", "8"],
            width=150,
        )
        threads_menu.grid(row=7, column=1, padx=10, pady=2, sticky="w")
        self.threads_menu = threads_menu

        # Help text
        help_label = ctk.CTkLabel(
            settings_frame,
            text="   💡 Tip: ultrafast = cepat tapi ukuran besar | slow = lambat tapi ukuran kecil",
            font=ctk.CTkFont(size=9),
            text_color="gray",
        )
        help_label.grid(row=8, column=0, columnspan=3, padx=10, pady=2, sticky="w")
        self.help_label = help_label

        # Output Folder
        output_label = ctk.CTkLabel(
            settings_frame,
            text="📁 Output Folder:",
            font=ctk.CTkFont(size=11),
        )
        output_label.grid(row=9, column=0, padx=10, pady=5, sticky="w")

        # Use absolute path for output
        import os
        default_output = os.path.abspath("./output/loops")
        self.output_folder_var = ctk.StringVar(value=default_output)
        output_entry = ctk.CTkEntry(
            settings_frame,
            textvariable=self.output_folder_var,
            width=300,
        )
        output_entry.grid(row=9, column=1, padx=10, pady=5, sticky="w")

        output_btn = ctk.CTkButton(
            settings_frame,
            text="Browse",
            width=80,
            command=self.browse_output_folder,
        )
        output_btn.grid(row=9, column=2, padx=5, pady=5)

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

        self.cancel_btn = ctk.CTkButton(
            button_frame,
            text="⏹️ Cancel",
            font=ctk.CTkFont(size=12),
            height=40,
            width=120,
            fg_color="red",
            hover_color="darkred",
            command=self.cancel_render,
            state="disabled",
        )
        self.cancel_btn.pack(side="left", padx=5)

        open_folder_btn = ctk.CTkButton(
            button_frame,
            text="📁 Open Output Folder",
            font=ctk.CTkFont(size=12),
            height=40,
            width=180,
            command=self.open_output_folder,
        )
        open_folder_btn.pack(side="left", padx=5)

    def toggle_cpu_options(self):
        """Toggle CPU options visibility based on GPU checkbox"""
        gpu_enabled = self.gpu_var.get()

        # Hide CPU options when GPU is enabled
        if gpu_enabled:
            self.cpu_label.grid_remove()
            self.speed_label.grid_remove()
            self.preset_menu.grid_remove()
            self.quality_label.grid_remove()
            self.quality_menu.grid_remove()
            self.threads_label.grid_remove()
            self.threads_menu.grid_remove()
            self.help_label.grid_remove()
        else:
            self.cpu_label.grid()
            self.speed_label.grid()
            self.preset_menu.grid()
            self.quality_label.grid()
            self.quality_menu.grid()
            self.threads_label.grid()
            self.threads_menu.grid()
            self.help_label.grid()

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

        # Import validators
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.validators import validate_file_path, validate_duration, validate_file_size

        # Validate input video
        video_path = self.video_path_var.get()
        if not video_path:
            self.console_log.log_error("Pilih video input terlebih dahulu!")
            return

        is_valid, error_msg = validate_file_path(
            video_path,
            must_exist=True,
            allowed_extensions=['.mp4', '.avi', '.mov', '.mkv', '.webm']
        )
        if not is_valid:
            self.console_log.log_error(f"Video input tidak valid: {error_msg}")
            return

        # Check file size (max 1GB for input)
        is_valid, error_msg, size_mb = validate_file_size(video_path, max_size_mb=1000)
        if not is_valid:
            self.console_log.log_error(f"Video terlalu besar: {error_msg}")
            return

        self.console_log.log_info(f"ℹ️  Video size: {size_mb:.1f} MB")

        # Validate optional audio
        audio_path = self.audio_path_var.get()
        if audio_path:
            is_valid, error_msg = validate_file_path(
                audio_path,
                must_exist=True,
                allowed_extensions=['.mp3', '.wav', '.m4a', '.aac']
            )
            if not is_valid:
                self.console_log.log_error(f"Audio tidak valid: {error_msg}")
                return

        # Validate duration
        duration_str = self.duration_var.get()
        is_valid, error_msg, duration = validate_duration(
            duration_str,
            min_val=1,
            max_val=600  # Max 10 hours
        )
        if not is_valid:
            self.console_log.log_error(f"Durasi tidak valid: {error_msg}")
            return

        # Validate crossfade
        try:
            crossfade = float(self.crossfade_var.get())
            if crossfade < 0 or crossfade > 10:
                raise ValueError("Crossfade must be between 0 and 10 seconds")
        except ValueError as e:
            self.console_log.log_error(f"Crossfade tidak valid: {str(e)}")
            return

        self.console_log.log_info(f"🚀 Memulai rendering loop {duration} menit...")

        # Reset cancel event and enable cancel button
        self.cancel_event.clear()
        self.is_rendering = True
        self.render_btn.configure(state="disabled", text="⏳ Rendering...")
        self.cancel_btn.configure(state="normal")

        # Run render in separate thread
        thread = threading.Thread(
            target=self._render_worker,
            daemon=True,
        )
        thread.start()

    def _render_worker(self):
        """Worker thread for rendering"""
        from backend.loop_creator import LoopCreator

        # Save settings before rendering
        self._save_settings()

        # Get settings
        video_path = Path(self.video_path_var.get())
        audio_path = Path(self.audio_path_var.get()) if self.audio_path_var.get() else None
        output_folder = Path(self.output_folder_var.get())
        duration = int(self.duration_var.get()) * 60  # Convert to seconds
        resolution = self.resolution_var.get()
        crossfade = float(self.crossfade_var.get())
        use_gpu = self.gpu_var.get()

        # Get CPU settings
        preset = self.preset_var.get()
        quality_str = self.quality_var.get()
        # Extract CRF number from "18 (Best)" format
        crf = int(quality_str.split()[0])
        threads = self.threads_var.get()

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
            cpu_preset=preset,
            cpu_crf=crf,
            cpu_threads=threads,
            progress_callback=self.update_progress,
            cancel_event=self.cancel_event,
        )

        # Reset UI
        self.is_rendering = False
        self.render_btn.configure(state="normal", text="🎬 Render Loop")
        self.cancel_btn.configure(state="disabled")
        self.progress_bar.set(0 if not success else 1)

        if success:
            self.progress_label.configure(text="✅ Rendering complete!")

            # Show success notification
            try:
                from utils.notifications import notify_success
                notify_success(
                    "Loop Created",
                    f"Successfully created {duration//60} minute loop"
                )
            except:
                pass
        else:
            self.progress_label.configure(text="❌ Rendering failed!")

            # Show error notification
            try:
                from utils.notifications import notify_error
                notify_error("Loop Creation Failed", "Check console log for details")
            except:
                pass

    def cancel_render(self):
        """Cancel the rendering process"""
        if self.is_rendering:
            self.console_log.log_warning("🛑 Canceling render...")
            self.cancel_event.set()
            self.cancel_btn.configure(state="disabled")

    def update_progress(self, progress, message=""):
        """Update progress bar"""
        self.progress_bar.set(progress)

        if message:
            self.progress_label.configure(text=message)

    def _load_settings(self):
        """Load settings from config"""
        if not self.config:
            return

        try:
            settings = self.config.get_mode_a_settings()

            # Load output folder
            output_folder = settings.get("output_folder")
            if output_folder:
                self.output_folder_var.set(output_folder)

            # Load duration
            duration = settings.get("default_duration", 60)
            self.duration_var.set(str(duration))

            # Load resolution
            resolution = settings.get("default_resolution", "1920x1080")
            self.resolution_var.set(resolution)

            # Load crossfade
            crossfade = settings.get("default_crossfade", 1.0)
            self.crossfade_var.set(str(crossfade))

            # Load GPU setting
            use_gpu = settings.get("use_gpu", False)
            self.gpu_var.set(use_gpu)

            # Load CPU settings
            preset = settings.get("cpu_preset", "medium")
            self.preset_var.set(preset)

            crf = settings.get("cpu_crf", 23)
            self.quality_var.set(f"{crf} (Good)")  # Map to dropdown format

            threads = settings.get("cpu_threads", "auto")
            self.threads_var.set(threads)

            # Update UI visibility
            self.toggle_cpu_options()

        except Exception as e:
            self.console_log.log_warning(f"Could not load settings: {e}")

    def _save_settings(self):
        """Save current settings to config"""
        if not self.config:
            return

        try:
            settings = {
                "output_folder": self.output_folder_var.get(),
                "default_duration": int(self.duration_var.get()),
                "default_resolution": self.resolution_var.get(),
                "default_crossfade": float(self.crossfade_var.get()),
                "use_gpu": self.gpu_var.get(),
                "cpu_preset": self.preset_var.get(),
                "cpu_crf": int(self.quality_var.get().split()[0]),  # Extract number from "23 (Good)"
                "cpu_threads": self.threads_var.get(),
            }

            self.config.update_mode_a_settings(settings)

        except Exception as e:
            self.console_log.log_warning(f"Could not save settings: {e}")
