"""
Unit tests for notification system
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import platform
from utils.notifications import NotificationManager, get_notifier, init_notifier


class TestNotificationManager:
    """Test NotificationManager class"""

    def test_init_enabled(self):
        """Test initialization with notifications enabled"""
        notifier = NotificationManager(enabled=True)

        assert notifier.enabled is True
        assert notifier.method is not None

    def test_init_disabled(self):
        """Test initialization with notifications disabled"""
        notifier = NotificationManager(enabled=False)

        assert notifier.enabled is False

    def test_init_notifier_plyer_available(self, mocker):
        """Test notifier initialization when plyer is available"""
        mock_notification = Mock()
        mocker.patch.dict('sys.modules', {'plyer': Mock(), 'plyer.notification': mock_notification})

        notifier = NotificationManager(enabled=True)
        notifier._init_notifier()

        assert notifier.method == "plyer"

    def test_init_notifier_plyer_not_available_linux(self, mocker):
        """Test notifier initialization on Linux without plyer"""
        mocker.patch.dict('sys.modules', {'plyer': None})
        mocker.patch('platform.system', return_value='Linux')

        notifier = NotificationManager(enabled=True)
        notifier._init_notifier()

        assert notifier.method == "notify-send"

    def test_init_notifier_plyer_not_available_mac(self, mocker):
        """Test notifier initialization on macOS without plyer"""
        mocker.patch.dict('sys.modules', {'plyer': None})
        mocker.patch('platform.system', return_value='Darwin')

        notifier = NotificationManager(enabled=True)
        notifier._init_notifier()

        assert notifier.method == "osascript"

    def test_init_notifier_plyer_not_available_windows(self, mocker):
        """Test notifier initialization on Windows without plyer"""
        mocker.patch.dict('sys.modules', {'plyer': None})
        mocker.patch('platform.system', return_value='Windows')

        notifier = NotificationManager(enabled=True)
        notifier._init_notifier()

        assert notifier.method == "powershell"

    def test_show_notification_disabled(self):
        """Test that notification is not shown when disabled"""
        notifier = NotificationManager(enabled=False)

        # Should not raise any error
        notifier.show_notification("Title", "Message")

        # Method should not be set
        assert notifier.method is None or not notifier.enabled

    def test_show_notification_plyer(self, mocker):
        """Test showing notification with plyer"""
        mock_plyer_notification = Mock()
        mocker.patch.dict('sys.modules', {
            'plyer': Mock(),
            'plyer.notification': mock_plyer_notification
        })

        notifier = NotificationManager(enabled=True)
        notifier.method = "plyer"
        notifier.notifier = mock_plyer_notification

        notifier.show_notification("Test Title", "Test Message", timeout=10)

        mock_plyer_notification.notify.assert_called_once()
        call_args = mock_plyer_notification.notify.call_args[1]
        assert call_args['title'] == "Test Title"
        assert call_args['message'] == "Test Message"
        assert call_args['timeout'] == 10

    def test_show_notification_linux(self, mocker):
        """Test showing notification on Linux"""
        mock_subprocess = mocker.patch('subprocess.run')

        notifier = NotificationManager(enabled=True)
        notifier.method = "notify-send"

        notifier.show_notification("Test Title", "Test Message", timeout=5)

        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "notify-send" in call_args
        assert "Test Title" in call_args
        assert "Test Message" in call_args

    def test_show_notification_macos(self, mocker):
        """Test showing notification on macOS"""
        mock_subprocess = mocker.patch('subprocess.run')

        notifier = NotificationManager(enabled=True)
        notifier.method = "osascript"

        notifier.show_notification("Test Title", "Test Message")

        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "osascript" in call_args

    def test_show_notification_windows(self, mocker):
        """Test showing notification on Windows"""
        mock_subprocess = mocker.patch('subprocess.run')

        notifier = NotificationManager(enabled=True)
        notifier.method = "powershell"

        notifier.show_notification("Test Title", "Test Message")

        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "powershell" in call_args

    def test_show_notification_error_handling(self, mocker):
        """Test that notification errors are handled gracefully"""
        mocker.patch('subprocess.run', side_effect=Exception("Notification failed"))

        notifier = NotificationManager(enabled=True)
        notifier.method = "notify-send"

        # Should not raise exception
        notifier.show_notification("Test", "Message")

    def test_notify_success(self, mocker):
        """Test success notification"""
        mock_show = mocker.patch.object(NotificationManager, 'show_notification')

        notifier = NotificationManager(enabled=True)
        notifier.notify_success("Operation Complete", "Details here")

        mock_show.assert_called_once()
        call_args = mock_show.call_args[0]
        assert "✅" in call_args[0] or "Operation Complete" in call_args[0]
        assert "Details here" in call_args[1]

    def test_notify_error(self, mocker):
        """Test error notification"""
        mock_show = mocker.patch.object(NotificationManager, 'show_notification')

        notifier = NotificationManager(enabled=True)
        notifier.notify_error("Operation Failed", "Error details")

        mock_show.assert_called_once()
        call_args = mock_show.call_args[0]
        assert "❌" in call_args[0] or "Failed" in call_args[0]
        assert "Error details" in call_args[1]

    def test_notify_warning(self, mocker):
        """Test warning notification"""
        mock_show = mocker.patch.object(NotificationManager, 'show_notification')

        notifier = NotificationManager(enabled=True)
        notifier.notify_warning("Warning", "Warning details")

        mock_show.assert_called_once()
        call_args = mock_show.call_args[0]
        assert "⚠️" in call_args[0] or "Warning" in call_args[0]

    def test_set_enabled_true(self):
        """Test enabling notifications"""
        notifier = NotificationManager(enabled=False)
        assert notifier.enabled is False

        notifier.set_enabled(True)
        assert notifier.enabled is True

    def test_set_enabled_false(self):
        """Test disabling notifications"""
        notifier = NotificationManager(enabled=True)
        assert notifier.enabled is True

        notifier.set_enabled(False)
        assert notifier.enabled is False


class TestGlobalNotifier:
    """Test global notifier functions"""

    def test_get_notifier_creates_instance(self):
        """Test that get_notifier creates global instance"""
        # Clear global instance first
        import utils.notifications
        utils.notifications._global_notifier = None

        notifier = get_notifier()

        assert notifier is not None
        assert isinstance(notifier, NotificationManager)

    def test_get_notifier_returns_same_instance(self):
        """Test that get_notifier returns same instance"""
        # Clear global instance first
        import utils.notifications
        utils.notifications._global_notifier = None

        notifier1 = get_notifier()
        notifier2 = get_notifier()

        assert notifier1 is notifier2

    def test_init_notifier_enabled(self):
        """Test initializing notifier with enabled"""
        notifier = init_notifier(enabled=True)

        assert notifier is not None
        assert notifier.enabled is True

    def test_init_notifier_disabled(self):
        """Test initializing notifier with disabled"""
        notifier = init_notifier(enabled=False)

        assert notifier is not None
        assert notifier.enabled is False


class TestNotificationHelperFunctions:
    """Test notification helper functions"""

    def test_show_notification_helper(self, mocker):
        """Test show_notification helper function"""
        from utils.notifications import show_notification

        # Clear and mock global notifier
        import utils.notifications
        utils.notifications._global_notifier = None

        mock_notifier = Mock()
        mocker.patch('utils.notifications.get_notifier', return_value=mock_notifier)

        show_notification("Test", "Message", 5)

        mock_notifier.show_notification.assert_called_once_with("Test", "Message", 5)

    def test_notify_success_helper(self, mocker):
        """Test notify_success helper function"""
        from utils.notifications import notify_success

        # Clear and mock global notifier
        import utils.notifications
        utils.notifications._global_notifier = None

        mock_notifier = Mock()
        mocker.patch('utils.notifications.get_notifier', return_value=mock_notifier)

        notify_success("Operation", "Details")

        mock_notifier.notify_success.assert_called_once_with("Operation", "Details")

    def test_notify_error_helper(self, mocker):
        """Test notify_error helper function"""
        from utils.notifications import notify_error

        # Clear and mock global notifier
        import utils.notifications
        utils.notifications._global_notifier = None

        mock_notifier = Mock()
        mocker.patch('utils.notifications.get_notifier', return_value=mock_notifier)

        notify_error("Operation", "Error details")

        mock_notifier.notify_error.assert_called_once_with("Operation", "Error details")

    def test_notify_warning_helper(self, mocker):
        """Test notify_warning helper function"""
        from utils.notifications import notify_warning

        # Clear and mock global notifier
        import utils.notifications
        utils.notifications._global_notifier = None

        mock_notifier = Mock()
        mocker.patch('utils.notifications.get_notifier', return_value=mock_notifier)

        notify_warning("Operation", "Warning")

        mock_notifier.notify_warning.assert_called_once_with("Operation", "Warning")


class TestPlatformSpecific:
    """Test platform-specific notification methods"""

    def test_linux_notification_command(self, mocker):
        """Test Linux notification command structure"""
        mock_subprocess = mocker.patch('subprocess.run')
        mocker.patch('platform.system', return_value='Linux')

        notifier = NotificationManager(enabled=True)
        notifier.method = "notify-send"
        notifier._show_linux_notification("Title", "Message", 5)

        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0] == "notify-send"
        assert "-a" in call_args
        assert "Autotube" in call_args
        assert "Title" in call_args
        assert "Message" in call_args

    def test_macos_notification_command(self, mocker):
        """Test macOS notification command structure"""
        mock_subprocess = mocker.patch('subprocess.run')

        notifier = NotificationManager(enabled=True)
        notifier.method = "osascript"
        notifier._show_macos_notification("Title", "Message")

        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0] == "osascript"
        assert call_args[1] == "-e"
        assert "display notification" in call_args[2]
        assert "Message" in call_args[2]
        assert "Title" in call_args[2]

    def test_windows_notification_command(self, mocker):
        """Test Windows notification command structure"""
        mock_subprocess = mocker.patch('subprocess.run')

        notifier = NotificationManager(enabled=True)
        notifier.method = "powershell"
        notifier._show_windows_notification("Title", "Message")

        call_args = mock_subprocess.call_args[0][0]
        assert call_args[0] == "powershell"
        assert "-Command" in call_args


class TestNotificationContent:
    """Test notification content formatting"""

    def test_success_notification_format(self, mocker):
        """Test success notification format"""
        mock_show = mocker.patch.object(NotificationManager, 'show_notification')

        notifier = NotificationManager(enabled=True)
        notifier.notify_success("Download Complete")

        mock_show.assert_called_once()
        title, message = mock_show.call_args[0]
        assert "✅" in title or "Download Complete" in title

    def test_error_notification_format(self, mocker):
        """Test error notification format"""
        mock_show = mocker.patch.object(NotificationManager, 'show_notification')

        notifier = NotificationManager(enabled=True)
        notifier.notify_error("Process Failed")

        mock_show.assert_called_once()
        title, message = mock_show.call_args[0]
        assert "❌" in title or "Failed" in title

    def test_notification_with_empty_details(self, mocker):
        """Test notification with empty details"""
        mock_show = mocker.patch.object(NotificationManager, 'show_notification')

        notifier = NotificationManager(enabled=True)
        notifier.notify_success("Success", "")

        mock_show.assert_called_once()
        title, message = mock_show.call_args[0]
        assert message != ""  # Should have default message

    def test_notification_with_long_message(self, mocker):
        """Test notification with very long message"""
        mock_show = mocker.patch.object(NotificationManager, 'show_notification')

        notifier = NotificationManager(enabled=True)
        long_message = "A" * 500  # Very long message

        notifier.notify_success("Test", long_message)

        mock_show.assert_called_once()
        # Should handle long messages without error
