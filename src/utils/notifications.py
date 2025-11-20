"""
Notification System
Show desktop notifications for completed operations
"""

import sys
import platform


class NotificationManager:
    """Manage desktop notifications"""

    def __init__(self, enabled=True):
        """
        Initialize notification manager

        Args:
            enabled: Whether notifications are enabled
        """
        self.enabled = enabled
        self.notifier = None

        if self.enabled:
            self._init_notifier()

    def _init_notifier(self):
        """Initialize the appropriate notifier for the platform"""
        try:
            # Try to import plyer for cross-platform notifications
            from plyer import notification
            self.notifier = notification
            self.method = "plyer"
        except ImportError:
            # Fallback to platform-specific methods
            system = platform.system()

            if system == "Linux":
                self.method = "notify-send"
            elif system == "Darwin":  # macOS
                self.method = "osascript"
            elif system == "Windows":
                self.method = "powershell"
            else:
                self.method = None
                self.enabled = False

    def show_notification(self, title, message, timeout=5):
        """
        Show a desktop notification

        Args:
            title: Notification title
            message: Notification message
            timeout: Notification timeout in seconds
        """
        if not self.enabled:
            return

        try:
            if self.method == "plyer":
                self._show_plyer_notification(title, message, timeout)
            elif self.method == "notify-send":
                self._show_linux_notification(title, message, timeout)
            elif self.method == "osascript":
                self._show_macos_notification(title, message)
            elif self.method == "powershell":
                self._show_windows_notification(title, message)
        except Exception as e:
            # Silently fail if notifications don't work
            print(f"Notification error: {e}")

    def _show_plyer_notification(self, title, message, timeout):
        """Show notification using plyer"""
        self.notifier.notify(
            title=title,
            message=message,
            app_name="Autotube",
            timeout=timeout,
        )

    def _show_linux_notification(self, title, message, timeout):
        """Show notification on Linux using notify-send"""
        import subprocess

        timeout_ms = timeout * 1000

        subprocess.run(
            [
                "notify-send",
                "-a", "Autotube",
                "-t", str(timeout_ms),
                title,
                message,
            ],
            check=False,
            capture_output=True,
        )

    def _show_macos_notification(self, title, message):
        """Show notification on macOS using osascript"""
        import subprocess

        script = f'display notification "{message}" with title "Autotube" subtitle "{title}"'

        subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
        )

    def _show_windows_notification(self, title, message):
        """Show notification on Windows using PowerShell"""
        import subprocess

        # Windows 10+ toast notification
        ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$Template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)

$RawXml = [xml] $Template.GetXml()
($RawXml.toast.visual.binding.text|where {{$_.id -eq "1"}}).AppendChild($RawXml.CreateTextNode("{title}")) > $null
($RawXml.toast.visual.binding.text|where {{$_.id -eq "2"}}).AppendChild($RawXml.CreateTextNode("{message}")) > $null

$SerializedXml = New-Object Windows.Data.Xml.Dom.XmlDocument
$SerializedXml.LoadXml($RawXml.OuterXml)

$Toast = [Windows.UI.Notifications.ToastNotification]::new($SerializedXml)
$Toast.Tag = "Autotube"
$Toast.Group = "Autotube"

$Notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Autotube")
$Notifier.Show($Toast);
"""

        subprocess.run(
            ["powershell", "-Command", ps_script],
            check=False,
            capture_output=True,
        )

    def notify_success(self, operation, details=""):
        """
        Show success notification

        Args:
            operation: Operation that completed (e.g., "Loop Created", "Download Complete")
            details: Additional details
        """
        title = f"✅ {operation}"
        message = details if details else f"{operation} completed successfully!"
        self.show_notification(title, message)

    def notify_error(self, operation, details=""):
        """
        Show error notification

        Args:
            operation: Operation that failed
            details: Error details
        """
        title = f"❌ {operation} Failed"
        message = details if details else f"{operation} encountered an error"
        self.show_notification(title, message)

    def notify_warning(self, operation, details=""):
        """
        Show warning notification

        Args:
            operation: Operation with warning
            details: Warning details
        """
        title = f"⚠️ {operation}"
        message = details if details else f"{operation} completed with warnings"
        self.show_notification(title, message)

    def set_enabled(self, enabled):
        """Enable or disable notifications"""
        self.enabled = enabled


# Global notification manager instance
_global_notifier = None


def get_notifier():
    """Get or create global notification manager instance"""
    global _global_notifier

    if _global_notifier is None:
        _global_notifier = NotificationManager()

    return _global_notifier


def init_notifier(enabled=True):
    """
    Initialize global notification manager

    Args:
        enabled: Whether notifications are enabled
    """
    global _global_notifier

    _global_notifier = NotificationManager(enabled=enabled)

    return _global_notifier


def show_notification(title, message, timeout=5):
    """Show a notification using global notifier"""
    notifier = get_notifier()
    notifier.show_notification(title, message, timeout)


def notify_success(operation, details=""):
    """Show success notification using global notifier"""
    notifier = get_notifier()
    notifier.notify_success(operation, details)


def notify_error(operation, details=""):
    """Show error notification using global notifier"""
    notifier = get_notifier()
    notifier.notify_error(operation, details)


def notify_warning(operation, details=""):
    """Show warning notification using global notifier"""
    notifier = get_notifier()
    notifier.notify_warning(operation, details)
