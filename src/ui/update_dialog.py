"""
Update Dialog UI
Dialog for notifying users about available updates and downloading them
"""

import customtkinter as ctk
import threading
from typing import Optional


class UpdateDialog(ctk.CTkToplevel):
    """Dialog for handling updates"""

    def __init__(self, parent, current_version: str, latest_version: str, release_notes: str = ""):
        super().__init__(parent)

        self.current_version = current_version
        self.latest_version = latest_version
        self.release_notes = release_notes
        self.user_choice = None  # "update", "skip", "later"

        self.setup_ui()

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center on screen
        self.center_window()

    def setup_ui(self):
        """Setup the update dialog UI"""
        self.title("Update Available")
        self.geometry("500x400")

        # Header
        header = ctk.CTkLabel(
            self,
            text="🎉 New Version Available!",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        header.pack(pady=20)

        # Version info
        version_frame = ctk.CTkFrame(self)
        version_frame.pack(fill="x", padx=20, pady=10)

        current_label = ctk.CTkLabel(
            version_frame,
            text=f"Current Version: v{self.current_version}",
            font=ctk.CTkFont(size=12),
        )
        current_label.pack(pady=5)

        latest_label = ctk.CTkLabel(
            version_frame,
            text=f"Latest Version: v{self.latest_version}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#4CAF50",
        )
        latest_label.pack(pady=5)

        # Release notes
        if self.release_notes:
            notes_label = ctk.CTkLabel(
                self,
                text="What's New:",
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            notes_label.pack(pady=(10, 5), padx=20, anchor="w")

            notes_textbox = ctk.CTkTextbox(
                self,
                height=150,
                wrap="word",
            )
            notes_textbox.pack(fill="both", expand=True, padx=20, pady=5)
            notes_textbox.insert("1.0", self.release_notes)
            notes_textbox.configure(state="disabled")

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=20)

        update_btn = ctk.CTkButton(
            button_frame,
            text="Update Now",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=self.on_update,
        )
        update_btn.pack(side="left", fill="x", expand=True, padx=5)

        later_btn = ctk.CTkButton(
            button_frame,
            text="Remind Me Later",
            font=ctk.CTkFont(size=12),
            height=40,
            fg_color="gray",
            command=self.on_later,
        )
        later_btn.pack(side="left", fill="x", expand=True, padx=5)

        skip_btn = ctk.CTkButton(
            button_frame,
            text="Skip This Version",
            font=ctk.CTkFont(size=12),
            height=40,
            fg_color="#666",
            command=self.on_skip,
        )
        skip_btn.pack(side="left", fill="x", expand=True, padx=5)

    def center_window(self):
        """Center the dialog on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def on_update(self):
        """User chose to update now"""
        self.user_choice = "update"
        self.destroy()

    def on_later(self):
        """User chose to update later"""
        self.user_choice = "later"
        self.destroy()

    def on_skip(self):
        """User chose to skip this version"""
        self.user_choice = "skip"
        self.destroy()

    def get_choice(self) -> str:
        """Get user's choice (blocks until dialog is closed)"""
        self.wait_window()
        return self.user_choice or "later"


class UpdateProgressDialog(ctk.CTkToplevel):
    """Dialog showing update download and installation progress"""

    def __init__(self, parent):
        super().__init__(parent)

        self.setup_ui()

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Center on screen
        self.center_window()

        # Prevent closing during update
        self.protocol("WM_DELETE_WINDOW", lambda: None)

    def setup_ui(self):
        """Setup the progress dialog UI"""
        self.title("Updating Autotube")
        self.geometry("450x200")

        # Header
        header = ctk.CTkLabel(
            self,
            text="Downloading Update",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.pack(pady=20)

        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="Preparing download...",
            font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(pady=10)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        # Percentage label
        self.percentage_label = ctk.CTkLabel(
            self,
            text="0%",
            font=ctk.CTkFont(size=12),
        )
        self.percentage_label.pack(pady=5)

    def center_window(self):
        """Center the dialog on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def update_progress(self, status: str, percentage: int):
        """
        Update progress display

        Args:
            status: Status message
            percentage: Progress percentage (0-100)
        """
        self.status_label.configure(text=status)
        self.progress_bar.set(percentage / 100)
        self.percentage_label.configure(text=f"{percentage}%")
        self.update()

    def complete(self, success: bool, message: str):
        """
        Show completion status

        Args:
            success: Whether update was successful
            message: Completion message
        """
        if success:
            self.status_label.configure(text=message, text_color="#4CAF50")
        else:
            self.status_label.configure(text=message, text_color="#F44336")

        self.progress_bar.set(1 if success else 0)
        self.percentage_label.configure(text="Complete!" if success else "Failed")


def show_update_dialog(
    parent,
    current_version: str,
    latest_version: str,
    release_notes: str = ""
) -> str:
    """
    Show update dialog and get user's choice

    Args:
        parent: Parent window
        current_version: Current version string
        latest_version: Latest version string
        release_notes: Release notes text

    Returns:
        User's choice: "update", "skip", or "later"
    """
    dialog = UpdateDialog(parent, current_version, latest_version, release_notes)
    return dialog.get_choice()


def perform_update_with_dialog(parent, updater, current_version: str, latest_version: str) -> bool:
    """
    Perform update with progress dialog

    Args:
        parent: Parent window
        updater: AutoUpdater instance
        current_version: Current version
        latest_version: Latest version

    Returns:
        True if update successful
    """
    progress_dialog = UpdateProgressDialog(parent)

    result = {"success": False, "message": ""}

    def update_thread():
        """Run update in background thread"""
        def progress_callback(status, percentage):
            progress_dialog.update_progress(status, percentage)

        success, message = updater.perform_update(progress_callback)
        result["success"] = success
        result["message"] = message

        # Show completion
        progress_dialog.complete(success, message)

        # Close dialog after 2 seconds
        if success:
            progress_dialog.after(2000, progress_dialog.destroy)
        else:
            # Allow manual close on failure
            progress_dialog.protocol("WM_DELETE_WINDOW", progress_dialog.destroy)

    # Start update in background thread
    thread = threading.Thread(target=update_thread, daemon=True)
    thread.start()

    # Wait for dialog to close
    progress_dialog.wait_window()

    return result["success"]
