"""
FFmpeg Progress Parser
Parse FFmpeg output to provide real-time progress updates with ETA
"""

import subprocess
import re
import time
from threading import Thread
from queue import Queue


class FFmpegProgressParser:
    """Parse FFmpeg output for progress information"""

    def __init__(self, total_duration=None):
        """
        Initialize progress parser

        Args:
            total_duration: Total expected duration in seconds (for percentage calculation)
        """
        self.total_duration = total_duration
        self.start_time = None
        self.current_time = 0
        self.speed = 1.0

    def parse_time(self, time_str):
        """
        Parse FFmpeg time format (HH:MM:SS.ms) to seconds

        Args:
            time_str: Time string in HH:MM:SS.ms format

        Returns:
            float: Time in seconds
        """
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except:
            pass
        return 0

    def parse_line(self, line):
        """
        Parse a single line of FFmpeg output

        Args:
            line: Output line from FFmpeg stderr

        Returns:
            dict: Progress information (time, speed, fps, etc.) or None
        """
        # FFmpeg outputs progress like:
        # frame= 123 fps= 25 q=28.0 size= 1024kB time=00:00:05.00 bitrate=1677.7kbits/s speed=1.02x

        if 'time=' not in line:
            return None

        progress_info = {}

        # Extract time
        time_match = re.search(r'time=(\d+:\d+:\d+\.\d+)', line)
        if time_match:
            time_str = time_match.group(1)
            self.current_time = self.parse_time(time_str)
            progress_info['time'] = self.current_time

        # Extract speed
        speed_match = re.search(r'speed=\s*(\d+\.?\d*)x', line)
        if speed_match:
            self.speed = float(speed_match.group(1))
            progress_info['speed'] = self.speed

        # Extract fps
        fps_match = re.search(r'fps=\s*(\d+\.?\d*)', line)
        if fps_match:
            progress_info['fps'] = float(fps_match.group(1))

        # Extract frame
        frame_match = re.search(r'frame=\s*(\d+)', line)
        if frame_match:
            progress_info['frame'] = int(frame_match.group(1))

        # Calculate progress percentage
        if self.total_duration and self.total_duration > 0:
            progress_info['percentage'] = min(self.current_time / self.total_duration, 1.0)
        else:
            progress_info['percentage'] = 0

        # Calculate ETA
        if self.start_time and self.total_duration and self.speed > 0:
            elapsed_real = time.time() - self.start_time
            if self.current_time > 0:
                # Calculate remaining time based on speed
                remaining_video = self.total_duration - self.current_time
                remaining_real = remaining_video / self.speed if self.speed > 0 else 0
                progress_info['eta_seconds'] = remaining_real
                progress_info['eta_str'] = self.format_time(remaining_real)

        return progress_info

    def format_time(self, seconds):
        """Format seconds to human readable time"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds / 3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours}h {mins}m"

    def run_ffmpeg_with_progress(self, cmd, progress_callback=None, cancel_event=None):
        """
        Run FFmpeg command with real-time progress tracking

        Args:
            cmd: FFmpeg command as list
            progress_callback: Callback function(progress_info) for progress updates
            cancel_event: threading.Event() for cancellation

        Returns:
            tuple: (success: bool, stderr_output: str)
        """
        self.start_time = time.time()
        stderr_lines = []

        try:
            # Start FFmpeg process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )

            # Read stderr line by line
            while True:
                # Check for cancellation
                if cancel_event and cancel_event.is_set():
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return False, "Cancelled by user"

                line = process.stderr.readline()

                if not line:
                    break

                stderr_lines.append(line)

                # Parse progress
                progress_info = self.parse_line(line)
                if progress_info and progress_callback:
                    progress_callback(progress_info)

            # Wait for process to complete
            return_code = process.wait()

            stderr_output = ''.join(stderr_lines)

            return return_code == 0, stderr_output

        except Exception as e:
            return False, str(e)


def run_ffmpeg_with_progress(cmd, total_duration=None, progress_callback=None, cancel_event=None, log_callback=None):
    """
    Convenience function to run FFmpeg with progress

    Args:
        cmd: FFmpeg command as list
        total_duration: Total expected duration in seconds
        progress_callback: Callback(percentage, message, eta_str) for progress updates
        cancel_event: threading.Event() for cancellation
        log_callback: Callback(message, level) for logging

    Returns:
        bool: True if successful
    """
    parser = FFmpegProgressParser(total_duration)

    def internal_callback(progress_info):
        if progress_callback:
            percentage = progress_info.get('percentage', 0)
            speed = progress_info.get('speed', 0)
            eta_str = progress_info.get('eta_str', '')

            # Build message
            message_parts = []
            if speed > 0:
                message_parts.append(f"Speed: {speed:.2f}x")
            if eta_str:
                message_parts.append(f"ETA: {eta_str}")

            message = " | ".join(message_parts) if message_parts else "Processing..."

            progress_callback(percentage, message, eta_str if eta_str else None)

    if log_callback:
        log_callback(f"Running FFmpeg: {' '.join(cmd[:3])}...", "INFO")

    success, stderr = parser.run_ffmpeg_with_progress(
        cmd,
        progress_callback=internal_callback,
        cancel_event=cancel_event
    )

    if not success and log_callback:
        # Log error details
        error_lines = stderr.split('\n')
        # Get last few non-empty lines
        error_msg = '\n'.join([line for line in error_lines[-10:] if line.strip()])
        log_callback(f"FFmpeg error: {error_msg}", "ERROR")

    return success
