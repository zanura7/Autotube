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

    def __init__(self, config=None):
        """
        Initialize main window

        Args:
            config: ConfigManager instance
        """
        self.config = config

        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Create main window
        self.root = ctk.CTk()
        self.root.title("Autotube - YouTube Content Creator")
        self.root.geometry("1000x700")

        # Create main container
        self.setup_ui()

    def setup_ui(self):
        """Setup the main UI layout"""

        # Header
        header = ctk.CTkLabel(
            self.root,
            text="🎬 Autotube - YouTube Long-Form Content Creator",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        header.pack(pady=10)

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

    def run(self):
        """Start the main event loop"""
        self.root.mainloop()
