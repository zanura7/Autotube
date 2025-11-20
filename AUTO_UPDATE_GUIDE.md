# Auto-Update System Guide

## Overview

Autotube includes a comprehensive auto-update system that can:
- Check for updates automatically on startup
- Download and install updates with one click
- Show update progress with ETA
- Safely rollback if installation fails
- Work across all platforms (Windows, Linux, macOS)

---

## Features

### 1. **Automatic Update Checking**
- Checks GitHub releases for new versions on startup
- Can be disabled in configuration
- Non-intrusive (runs in background)

### 2. **User-Friendly Update Dialog**
- Shows current and latest version
- Displays release notes
- Three options:
  - **Update Now**: Download and install immediately
  - **Remind Me Later**: Check again next startup
  - **Skip This Version**: Don't show for this version

### 3. **Progress Tracking**
- Real-time download progress
- Shows download speed and percentage
- Installation progress indicator

### 4. **Safe Installation**
- Creates backup of current version
- Automatic rollback on failure
- Graceful restart after update

### 5. **Manual Update Check**
- Button in main window: "v1.0.0 - Check Updates"
- Check anytime without restarting

---

## How It Works

### Version Checking

1. **On Startup**:
   ```
   - App starts
   - Loads config
   - If "check_for_updates" enabled:
     - Contacts GitHub API
     - Compares versions
     - Shows notification if update available
   ```

2. **Manual Check**:
   ```
   - User clicks "Check Updates" button
   - Checks GitHub releases in background
   - Shows dialog if update available
   ```

### Update Process

```
1. User chooses "Update Now"
2. Download update file from GitHub
   - Shows progress dialog
   - Displays download percentage
   - Shows download speed
3. Verify downloaded file
   - Check file size
   - Verify checksum (if provided)
4. Create backup of current executable
5. Install update
   - Windows: Use batch script
   - Linux/Mac: Use shell script
6. Restart application
   - Old version terminates
   - New version starts automatically
```

---

## Configuration

### Enable/Disable Auto-Update Check

Edit `~/.autotube/config.json`:

```json
{
  "general": {
    "check_for_updates": true,  // Set to false to disable
    "skipped_version": null
  }
}
```

### Skip Specific Version

If you click "Skip This Version" in the update dialog:

```json
{
  "general": {
    "skipped_version": "1.2.0"  // Won't show updates for this version
  }
}
```

To re-enable, set to `null` or delete the line.

---

## For Developers

### Creating a New Release

1. **Update Version**:
   ```python
   # src/__version__.py
   __version__ = "1.1.0"
   __version_info__ = (1, 1, 0)
   ```

2. **Commit Changes**:
   ```bash
   git commit -m "Bump version to 1.1.0"
   git tag v1.1.0
   git push origin main --tags
   ```

3. **Build Executables**:
   ```bash
   # Windows
   pyinstaller --onefile --name Autotube-v1.1.0-windows.exe src/main.py

   # Linux
   pyinstaller --onefile --name Autotube-v1.1.0-linux src/main.py

   # macOS
   pyinstaller --onefile --name Autotube-v1.1.0-macos src/main.py
   ```

4. **Create GitHub Release**:
   - Go to GitHub Releases
   - Click "Draft a new release"
   - Tag: `v1.1.0`
   - Title: `Autotube v1.1.0`
   - Description: Release notes
   - Attach executables:
     - `Autotube-v1.1.0-windows.exe`
     - `Autotube-v1.1.0-linux`
     - `Autotube-v1.1.0-macos`
   - Click "Publish release"

5. **Auto-Update Will Work**:
   - Users will see update notification
   - Can download and install with one click

### Version Naming Convention

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., `1.2.3`)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Examples:
- `1.0.0` → Initial release
- `1.1.0` → Added new feature
- `1.1.1` → Fixed bug
- `2.0.0` → Breaking change

### GitHub Release Asset Naming

**Important**: Use platform-specific names:

| Platform | Asset Name Example |
|----------|-------------------|
| Windows | `Autotube-v1.0.0-windows.exe` or `Autotube-windows.exe` |
| Linux | `Autotube-v1.0.0-linux` or `Autotube-linux` |
| macOS | `Autotube-v1.0.0-macos` or `Autotube-macos` |

The updater looks for keywords:
- Windows: `windows`, `win`, `.exe`
- Linux: `linux`, `ubuntu`, `debian`
- macOS: `macos`, `darwin`, `osx`

---

## API Reference

### AutoUpdater Class

```python
from utils.auto_updater import AutoUpdater

updater = AutoUpdater(current_version="1.0.0", github_repo="user/repo")
```

#### Methods

**check_for_updates()**
```python
has_update, latest_version, release_data = updater.check_for_updates()

# Returns:
# - has_update: bool - True if new version available
# - latest_version: str - Latest version number
# - release_data: dict - GitHub release API response
```

**download_update()**
```python
file_path = updater.download_update(
    download_url="https://github.com/user/repo/releases/download/v1.1.0/app.exe",
    filename="app.exe",
    progress_callback=lambda downloaded, total: print(f"{downloaded}/{total}")
)

# Returns:
# - file_path: Path - Path to downloaded file
```

**install_update()**
```python
success = updater.install_update(update_file)

# Returns:
# - success: bool - True if installation successful
```

**perform_update()**
```python
success, message = updater.perform_update(
    progress_callback=lambda status, percentage: print(f"{percentage}%: {status}")
)

# Returns:
# - success: bool - True if update completed
# - message: str - Status message
```

### Update Dialog

```python
from ui.update_dialog import show_update_dialog

choice = show_update_dialog(
    parent=main_window,
    current_version="1.0.0",
    latest_version="1.1.0",
    release_notes="Bug fixes and improvements"
)

# Returns: "update", "skip", or "later"
```

### Simple Update Check

```python
from utils.auto_updater import check_for_updates_simple

has_update, latest_version = check_for_updates_simple("1.0.0", "user/repo")
```

---

## Files Created

1. **src/__version__.py** - Version information
2. **src/utils/auto_updater.py** - Update logic (350+ lines)
3. **src/ui/update_dialog.py** - Update UI dialogs (350+ lines)
4. **Updated src/main.py** - Auto-check on startup
5. **Updated src/ui/main_window.py** - Manual update button
6. **Updated src/utils/config_manager.py** - Update settings

---

## Platform-Specific Behavior

### Windows
- Downloads `.exe` file
- Uses batch script for installation
- Script runs after app exits
- Replaces exe file
- Restarts application
- Cleans up automatically

### Linux
- Downloads executable binary
- Uses shell script for installation
- Makes file executable
- Replaces binary
- Restarts application
- Cleans up automatically

### macOS
- Downloads `.app` or binary
- Uses shell script for installation
- Handles code signing
- Replaces application
- Restarts application
- Cleans up automatically

---

## Troubleshooting

### Update Check Fails

**Problem**: "Could not check for updates"

**Solutions**:
1. Check internet connection
2. Verify GitHub repository URL in `src/__version__.py`
3. Check GitHub API rate limits
4. Disable firewall temporarily

### Download Fails

**Problem**: Download gets stuck or fails

**Solutions**:
1. Check internet connection
2. Try manual download from GitHub releases
3. Check available disk space
4. Verify file size isn't too large

### Installation Fails

**Problem**: Update downloads but won't install

**Solutions**:
1. **Windows**: Run as Administrator
2. **Linux/Mac**: Check file permissions
3. Check antivirus isn't blocking
4. Try manual installation:
   - Download from GitHub
   - Close Autotube
   - Replace executable manually

### App Won't Restart After Update

**Problem**: Update completes but app doesn't restart

**Solutions**:
1. Manually start application
2. Check if process is still running
3. Check installation logs
4. Rollback to backup if available

---

## Security Considerations

### File Verification

The updater verifies downloads by:
1. **File size check**: Rejects suspiciously small files
2. **Checksum verification**: Verifies SHA256 if provided
3. **Source verification**: Only downloads from official GitHub releases

### Backup & Rollback

Before installation:
1. Creates `.backup` copy of current executable
2. If installation fails, automatically rolls back
3. Backup deleted after successful install

### Safe Installation

Update process:
1. Never overwrites current exe while running
2. Uses separate script that runs after app exits
3. Script waits for app to fully close
4. Only then replaces executable
5. Starts new version
6. Self-destructs script

---

## Example: Complete Update Flow

```python
# 1. User starts Autotube
# 2. Auto-update check runs in background

✅ FFmpeg detected!
📦 Autotube v1.0.0
🔍 Checking for updates...
✨ New version available: v1.1.0 (current: v1.0.0)
🚀 Starting Autotube...

# 3. User clicks "Check Updates" button
🔍 Checking for updates...

# 4. Update dialog appears
┌──────────────────────────────────┐
│   🎉 New Version Available!      │
│                                  │
│ Current Version: v1.0.0          │
│ Latest Version: v1.1.0           │
│                                  │
│ What's New:                      │
│ - Fixed bug in Mode A            │
│ - Added feature X                │
│ - Performance improvements       │
│                                  │
│ [Update Now] [Later] [Skip]      │
└──────────────────────────────────┘

# 5. User clicks "Update Now"
📥 Downloading update to v1.1.0...

# 6. Progress dialog shows
┌──────────────────────────────────┐
│      Downloading Update          │
│                                  │
│  Downloading... 5.2MB/10MB       │
│  ████████░░░░░░░░░░░░░░░         │
│              52%                 │
└──────────────────────────────────┘

# 7. After download completes
┌──────────────────────────────────┐
│      Updating Autotube           │
│                                  │
│  Installing update...            │
│  ████████████████████████        │
│              90%                 │
└──────────────────────────────────┘

# 8. Success!
✅ Update installed! Restarting...

# 9. App closes and reopens with new version
📦 Autotube v1.1.0
🚀 Starting Autotube...
```

---

## Changelog

### v1.0.0 (Initial Release)
- Auto-update system implementation
- GitHub releases integration
- Cross-platform support
- Progress tracking
- Safe installation with backup
- Manual update check button
- Configuration options

---

## Future Enhancements

Planned features:
- [ ] Delta updates (only download changes)
- [ ] Automatic update scheduling
- [ ] Update notifications in system tray
- [ ] Rollback to previous version from UI
- [ ] Update history in settings
- [ ] Beta/stable channel selection
- [ ] Automatic update installation
- [ ] Email notifications for updates

---

## License

Same as Autotube (MIT License)

---

## Support

For issues related to auto-update:
1. Check this guide
2. See troubleshooting section
3. Open GitHub issue with:
   - Current version
   - Platform (Windows/Linux/Mac)
   - Error message
   - Logs from `~/.autotube/logs/`
