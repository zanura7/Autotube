"""
Main Window with tabbed interface for Autotube
"""

import customtkinter as ctk
from .console_log import ConsoleLog
from .mode_a_tab import ModeATab
from .mode_b_tab import ModeBTab
from .mode_c_tab import ModeCTab


class MainWindow:
    """Main application window with 3-mode tabs"""

    def __init__(self, config=None, version="1.0.0"):
        """
        Initialize main window

        Args:
            config: ConfigManager instance
            version: Application version
        """
        self.config = config
        self.version = version

        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Create main window
        self.root = ctk.CTk()
        self.root.title(f"Autotube v{version} - YouTube Content Creator")
        self.root.geometry("1000x700")

        # Create main container
        self.setup_ui()

    def setup_ui(self):
        """Setup the main UI layout"""

        # Header frame
        header_frame = ctk.CTkFrame(self.root)
        header_frame.pack(fill="x", pady=10)

        # Header label
        header = ctk.CTkLabel(
            header_frame,
            text="🎬 Autotube - YouTube Long-Form Content Creator",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        header.pack(side="left", padx=20)

        # Update button
        update_btn = ctk.CTkButton(
            header_frame,
            text=f"v{self.version} - Check Updates",
            font=ctk.CTkFont(size=10),
            width=150,
            height=30,
            command=self.check_for_updates_manual,
        )
        update_btn.pack(side="right", padx=20)

        # Tabview for 3 modes
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        # Console log (create first so tabs can use it)
        console_frame = ctk.CTkFrame(self.root)
        console_frame.pack(fill="both", expand=False, padx=10, pady=5, ipady=5)

        console_label = ctk.CTkLabel(
            console_frame,
            text="📋 Console Log:",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        console_label.pack(anchor="w", padx=5)

        self.console = ConsoleLog(console_frame)
        self.console.pack(fill="both", expand=True, padx=5, pady=5)

        # Create tabs
        self.tab_mode_a = self.tabview.add("Mode A: Loop Creator")
        self.tab_mode_b = self.tabview.add("Mode B: Downloader")
        self.tab_mode_c = self.tabview.add("Mode C: Generator")

        # Setup each tab
        self.setup_mode_a()
        self.setup_mode_b()
        self.setup_mode_c()

        # Welcome message
        self.console.log("✅ Autotube siap digunakan!")
        self.console.log("ℹ️  Pilih mode di tab atas untuk memulai.")

    def setup_mode_a(self):
        """Setup Mode A: Loop Creator tab"""
        # Create the Mode A tab UI
        mode_a = ModeATab(self.tab_mode_a, self.console, config=self.config)
        mode_a.pack(fill="both", expand=True)

    def setup_mode_b(self):
        """Setup Mode B: Downloader tab"""
        # Create the Mode B tab UI
        mode_b = ModeBTab(self.tab_mode_b, self.console, config=self.config)
        mode_b.pack(fill="both", expand=True)

    def setup_mode_c(self):
        """Setup Mode C: Generator tab"""
        # Create the Mode C tab UI
        mode_c = ModeCTab(self.tab_mode_c, self.console, config=self.config)
        mode_c.pack(fill="both", expand=True)

    def check_for_updates_manual(self):
        """Manually check for updates (triggered by button)"""
        import threading
        from __version__ import GITHUB_REPO
        from utils.auto_updater import AutoUpdater
        from .update_dialog import show_update_dialog, perform_update_with_dialog

        def check_updates_thread():
            """Check for updates in background thread"""
            self.console.log("🔍 Checking for updates...")

            updater = AutoUpdater(self.version, GITHUB_REPO)
            has_update, latest_version, release_data = updater.check_for_updates()

            if not has_update:
                self.console.log("✅ You're already using the latest version!", "SUCCESS")
                return

            # Get release notes
            release_notes = release_data.get("body", "No release notes available")

            # Show update dialog (must run on main thread)
            def show_dialog():
                choice = show_update_dialog(
                    self.root,
                    self.version,
                    latest_version,
                    release_notes
                )

                if choice == "update":
                    self.console.log(f"📥 Downloading update to v{latest_version}...")
                    # Perform update with progress dialog
                    success = perform_update_with_dialog(
                        self.root,
                        updater,
                        self.version,
                        latest_version
                    )

                    if success:
                        self.console.log("✅ Update installed! Restarting...", "SUCCESS")
                        # Application will restart automatically
                        self.root.quit()
                    else:
                        self.console.log("❌ Update failed. Please try again.", "ERROR")

                elif choice == "skip":
                    self.console.log(f"⏭️  Skipping version {latest_version}", "WARNING")
                    # Save skipped version in config
                    if self.config:
                        self.config.set("general", "skipped_version", latest_version)
                        self.config.save_config()
                else:
                    self.console.log("⏸️  Update postponed", "INFO")

            # Run dialog on main thread
            self.root.after(0, show_dialog)

        # Start check in background thread
        thread = threading.Thread(target=check_updates_thread, daemon=True)
        thread.start()

    def run(self):
        """Start the main event loop"""
        self.root.mainloop()
