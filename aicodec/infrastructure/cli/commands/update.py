# aicodec/infrastructure/cli/commands/update.py
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

from aicodec import __version__


def register_subparser(subparsers: Any) -> None:
    update_parser = subparsers.add_parser(
        "update",
        help="Update aicodec to the latest version (pre-built binary only)"
    )
    update_parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for updates without installing"
    )
    update_parser.set_defaults(func=run)


def get_latest_version() -> str | None:
    """Fetch the latest version from GitHub releases."""
    try:
        url = "https://api.github.com/repos/Stevie1704/aicodec/releases/latest"
        with urllib.request.urlopen(url, timeout=10) as response:  # nosec B310 - GitHub API HTTPS only
            data = json.loads(response.read().decode())
            tag_name = data.get("tag_name", "")
            # Remove 'v' prefix if present
            return tag_name.lstrip("v")
    except Exception as e:
        print(f"Error fetching latest version: {e}", file=sys.stderr)
        return None


def compare_versions(current: str, latest: str) -> int:
    """
    Compare two version strings.
    Returns: -1 if current < latest, 0 if equal, 1 if current > latest
    """
    def parse_version(v: str) -> tuple:
        return tuple(int(x) for x in v.split("."))

    try:
        current_parts = parse_version(current)
        latest_parts = parse_version(latest)

        if current_parts < latest_parts:
            return -1
        elif current_parts > latest_parts:
            return 1
        else:
            return 0
    except ValueError:
        print(f"Warning: Could not parse version strings: {current}, {latest}", file=sys.stderr)
        return 0


def is_sudo_available() -> bool:
    """Check if sudo command is available."""
    try:
        result = subprocess.run(
            ["which", "sudo"],
            capture_output=True,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def can_write_to_path(path: Path) -> bool:
    """Check if we have write permissions to a path."""
    try:
        # Check if the directory exists and we can write to it
        if path.exists():
            return os.access(path, os.W_OK)
        # If it doesn't exist, check the parent directory
        return os.access(path.parent, os.W_OK)
    except Exception:
        return False


def get_running_binary_path() -> tuple[Path | None, Path | None]:
    """Find the actual path of the currently running aicodec binary.

    This resolves symlinks and finds the real binary location,
    which may differ from the default /opt/aicodec/ location.

    Returns:
        A tuple of (real_path, symlink_path) where symlink_path is set
        only if the binary was found via a symlink.
    """
    os_name = platform.system().lower()
    binary_name = "aicodec.exe" if os_name == "windows" else "aicodec"

    # First, try to find aicodec in PATH
    aicodec_in_path = shutil.which(binary_name)
    if aicodec_in_path:
        path_in_path = Path(aicodec_in_path)
        # Resolve symlinks to get the real path
        real_path = path_in_path.resolve()
        if real_path.exists() and real_path.is_file():
            # Check if it's a symlink
            symlink_path = path_in_path if path_in_path.is_symlink() else None
            return real_path, symlink_path

    # Fallback: Check default installation locations
    if os_name == "windows":
        default_path = Path.home() / "aicodec" / binary_name
    else:
        default_path = Path("/opt/aicodec") / binary_name

    if default_path.exists():
        return default_path.resolve(), None

    return None, None


def is_frozen_binary() -> bool:
    """Check if we're running from a frozen/compiled binary (PyInstaller, Nuitka, etc.).

    This checks if the current process is a standalone compiled binary,
    not a Python script running via the interpreter.
    """
    # PyInstaller sets sys.frozen = True
    if getattr(sys, 'frozen', False):
        return True

    # Nuitka compiled binaries: sys.executable is the binary itself, not python
    # Check if the executable name contains 'python'
    executable_name = Path(sys.executable).name.lower()
    if 'python' not in executable_name:
        # Additional check: frozen binaries typically don't have a __file__ in __main__
        # or the executable matches the expected binary name
        if 'aicodec' in executable_name:
            return True

    return False


def is_prebuilt_install() -> bool:
    """Check if we're running from a pre-built binary installation.

    This checks BOTH:
    1. That we're actually running from a frozen/compiled binary (not pip)
    2. That the binary exists in the expected location
    """
    # First, check if we're actually running from a frozen binary
    if not is_frozen_binary():
        return False

    # Then verify the binary exists in the expected location
    os_name = platform.system().lower()

    if os_name == "windows":
        # Windows installation is in user profile directory
        install_dir = Path.home() / "aicodec"
        binary_name = "aicodec.exe"
    else:
        # Linux/macOS installation is in /opt/aicodec
        install_dir = Path("/opt/aicodec")
        binary_name = "aicodec"

    return install_dir.exists() and (install_dir / binary_name).exists()


def get_download_url() -> str | None:
    """Determine the download URL based on OS and architecture."""
    os_name = platform.system().lower()
    machine = platform.machine().lower()

    # Map platform names
    if os_name == "darwin":
        os_name = "darwin"
    elif os_name == "linux":
        os_name = "linux"
    elif os_name == "windows":
        os_name = "windows"
    else:
        print(f"Unsupported OS: {os_name}", file=sys.stderr)
        return None

    # Map architecture names
    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        print(f"Unsupported architecture: {machine}", file=sys.stderr)
        return None

    return f"https://github.com/Stevie1704/aicodec/releases/latest/download/aicodec-{os_name}-{arch}.zip"


def create_update_script(new_binary_path: Path, target_binary: Path, needs_sudo: bool, sudo_available: bool) -> Path:
    """Create a platform-specific update helper script."""
    os_name = platform.system().lower()

    if os_name == "windows":
        # Create PowerShell script for Windows
        script_path = new_binary_path.parent / "update_helper.ps1"
        log_path = new_binary_path.parent / "update_log.txt"
        script_content = f"""# Log file for debugging
$logFile = "{log_path}"
"Update started at $(Get-Date)" | Out-File -FilePath $logFile

# Wait for the main process to exit
Start-Sleep -Seconds 3
"Waited 3 seconds for process to exit" | Out-File -FilePath $logFile -Append

# Get the current process ID to exclude
$parentPid = $PID

# Wait for aicodec.exe to fully exit (check for any aicodec process except this script)
$maxAttempts = 15
$attempt = 0
while ($attempt -lt $maxAttempts) {{
    $processes = Get-Process -Name "aicodec" -ErrorAction SilentlyContinue | Where-Object {{ $_.Id -ne $parentPid }}
    if ($processes.Count -eq 0) {{
        "No aicodec processes found after $attempt attempts" | Out-File -FilePath $logFile -Append
        break
    }}
    "Still waiting for aicodec to exit (attempt $attempt)" | Out-File -FilePath $logFile -Append
    Start-Sleep -Seconds 1
    $attempt++
}}

if ($attempt -eq $maxAttempts) {{
    "WARNING: Timed out waiting for aicodec to exit" | Out-File -FilePath $logFile -Append
}}

# Replace the binary
try {{
    "Attempting to copy from {new_binary_path} to {target_binary}" | Out-File -FilePath $logFile -Append
    Copy-Item -Path "{new_binary_path}" -Destination "{target_binary}" -Force -ErrorAction Stop
    "✅ Update installed successfully!" | Out-File -FilePath $logFile -Append
    Write-Host "✅ Update installed successfully!"
    Write-Host "You can now run 'aicodec --version' to verify the update."
    Write-Host "Log file: {log_path}"
}} catch {{
    "ERROR: Failed to install update: $_" | Out-File -FilePath $logFile -Append
    Write-Host "❌ Error installing update: $_"
    Write-Host "Check log file for details: {log_path}"
    exit 1
}}

# Clean up
Remove-Item -Path "{new_binary_path}" -ErrorAction SilentlyContinue
"Update completed at $(Get-Date)" | Out-File -FilePath $logFile -Append
Start-Sleep -Seconds 2
Remove-Item -Path $PSCommandPath -ErrorAction SilentlyContinue
"""
        script_path.write_text(script_content, encoding='utf-8')
        return script_path
    else:
        # Create shell script for Unix/Linux/macOS
        script_path = new_binary_path.parent / "update_helper.sh"
        log_path = new_binary_path.parent / "update_log.txt"

        # Determine if we should use sudo
        use_sudo = needs_sudo and sudo_available

        if use_sudo:
            script_content = f"""#!/bin/bash
# Log file for debugging
LOG_FILE="{log_path}"
echo "Update started at $(date)" > "$LOG_FILE"

# Wait for the main process to exit
sleep 3
echo "Waited 3 seconds for process to exit" >> "$LOG_FILE"

# Wait for aicodec process to fully exit
max_attempts=15
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if ! pgrep -x "aicodec" > /dev/null 2>&1; then
        echo "No aicodec processes found after $attempt attempts" >> "$LOG_FILE"
        break
    fi
    echo "Still waiting for aicodec to exit (attempt $attempt)" >> "$LOG_FILE"
    sleep 1
    attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
    echo "WARNING: Timed out waiting for aicodec to exit" >> "$LOG_FILE"
fi

# Replace the binary using sudo
echo "Attempting to move from {new_binary_path} to {target_binary}" >> "$LOG_FILE"
sudo mv "{new_binary_path}" "{target_binary}" 2>> "$LOG_FILE"
if [ $? -eq 0 ]; then
    sudo chmod +x "{target_binary}" 2>> "$LOG_FILE"
    echo "✅ Update installed successfully!" | tee -a "$LOG_FILE"
    echo "You can now run 'aicodec --version' to verify the update."
    echo "Log file: {log_path}"
else
    echo "❌ Error installing update. Check log file: {log_path}" | tee -a "$LOG_FILE"
    exit 1
fi

# Clean up
rm -f "{new_binary_path}"
echo "Update completed at $(date)" >> "$LOG_FILE"
sleep 2
rm -f "$0"
"""
        else:
            # For environments without sudo (devcontainers, etc.)
            script_content = f"""#!/bin/bash
# Log file for debugging
LOG_FILE="{log_path}"
echo "Update started at $(date)" > "$LOG_FILE"

# Wait for the main process to exit
sleep 3
echo "Waited 3 seconds for process to exit" >> "$LOG_FILE"

# Wait for aicodec process to fully exit
max_attempts=15
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if ! pgrep -x "aicodec" > /dev/null 2>&1; then
        echo "No aicodec processes found after $attempt attempts" >> "$LOG_FILE"
        break
    fi
    echo "Still waiting for aicodec to exit (attempt $attempt)" >> "$LOG_FILE"
    sleep 1
    attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
    echo "WARNING: Timed out waiting for aicodec to exit" >> "$LOG_FILE"
fi

# Replace the binary without sudo
echo "Attempting to move from {new_binary_path} to {target_binary}" >> "$LOG_FILE"
mv "{new_binary_path}" "{target_binary}" 2>> "$LOG_FILE"
if [ $? -eq 0 ]; then
    chmod +x "{target_binary}" 2>> "$LOG_FILE"
    echo "✅ Update installed successfully!" | tee -a "$LOG_FILE"
    echo "You can now run 'aicodec --version' to verify the update."
    echo "Log file: {log_path}"
else
    echo "❌ Error installing update. Check log file: {log_path}" | tee -a "$LOG_FILE"
    exit 1
fi

# Clean up
rm -f "{new_binary_path}"
echo "Update completed at $(date)" >> "$LOG_FILE"
sleep 2
rm -f "$0"
"""

        script_path.write_text(script_content, encoding='utf-8')
        os.chmod(script_path, 0o755)  # nosec B103 - Standard executable permissions
        return script_path


def update_binary() -> bool:
    """Download the latest version and prepare for installation."""
    print("Downloading latest version...")

    download_url = get_download_url()
    if not download_url:
        return False

    # Determine platform-specific settings
    os_name = platform.system().lower()

    # Find the actual binary location that needs to be updated
    running_binary_path, symlink_path = get_running_binary_path()

    if os_name == "windows":
        default_install_dir = Path.home() / "aicodec"
        binary_name = "aicodec.exe"
        new_binary_name = "aicodec.new.exe"
        needs_sudo = False
        sudo_available = False

        # Use the actual binary's directory, or fall back to default
        if running_binary_path:
            install_dir = running_binary_path.parent
            target_binary_path = running_binary_path
        else:
            install_dir = default_install_dir
            target_binary_path = install_dir / binary_name
    else:
        default_install_dir = Path("/opt/aicodec")
        binary_name = "aicodec"
        new_binary_name = "aicodec.new"

        # Use the actual binary's directory, or fall back to default
        if running_binary_path:
            install_dir = running_binary_path.parent
            target_binary_path = running_binary_path
            print(f"Found aicodec binary at: {target_binary_path}")
            if symlink_path:
                print(f"  (via symlink: {symlink_path})")
        else:
            install_dir = default_install_dir
            target_binary_path = install_dir / binary_name
            print(f"Using default installation path: {target_binary_path}")

        # Check if we need sudo and if it's available
        has_write_permission = can_write_to_path(target_binary_path)
        sudo_available = is_sudo_available()

        # Only require sudo if we don't have write permissions
        needs_sudo = not has_write_permission

        # If we need sudo but it's not available, check if we can proceed anyway
        if needs_sudo and not sudo_available:
            if not has_write_permission:
                print("❌ Error: Insufficient permissions to update aicodec.", file=sys.stderr)
                print(f"   Target binary: {target_binary_path}", file=sys.stderr)
                print("   The installation directory requires elevated permissions but sudo is not available.", file=sys.stderr)
                print("   This can happen in containers or restricted environments.", file=sys.stderr)
                print("   Please contact your system administrator or reinstall aicodec in a user-writable location.", file=sys.stderr)
                return False

    # Download to install directory with temporary name
    new_binary_path = install_dir / new_binary_name
    zip_file = install_dir / "aicodec.zip.tmp"

    try:
        # Download
        print(f"Downloading from: {download_url}")
        urllib.request.urlretrieve(download_url, zip_file)  # nosec B310 - GitHub releases HTTPS only

        # Unzip
        print("Extracting...")
        import zipfile
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            # List contents for debugging
            members = zip_ref.namelist()
            print(f"Zip contains: {members}")

            # Extract all files to install directory
            # This ensures metadata files (like .dist-info) are also extracted
            binary_found = False
            for member in members:
                # Skip directories
                if member.endswith('/'):
                    continue

                # Determine the target path
                # Strip any leading directory from the zip (e.g., "aicodec-linux-amd64/aicodec" -> "aicodec")
                base_name = Path(member).name

                if base_name == binary_name:
                    # Extract binary to temporary name first
                    target_path = new_binary_path
                    binary_found = True
                else:
                    # Extract other files (metadata, etc.) directly to install directory
                    target_path = install_dir / base_name

                with zip_ref.open(member) as source:
                    with open(target_path, 'wb') as target:
                        target.write(source.read())
                print(f"  Extracted: {base_name}")

        # Clean up zip file
        zip_file.unlink()

        if not binary_found or not new_binary_path.exists():
            print(f"Error: Could not find {binary_name} binary in downloaded package", file=sys.stderr)
            return False

        # Make it executable on Unix
        if os_name != "windows":
            os.chmod(new_binary_path, 0o755)  # nosec B103 - Standard executable permissions (rwxr-xr-x)

        # Create update helper script
        print("Preparing update installer...")
        print(f"Target binary: {target_binary_path}")
        script_path = create_update_script(new_binary_path, target_binary_path, needs_sudo, sudo_available)

        # Launch the update script
        print("Launching update installer...")
        log_path = install_dir / "update_log.txt"

        if os_name == "windows":
            # Launch PowerShell script in background on Windows
            # Use CREATE_NO_WINDOW instead of DETACHED_PROCESS for better background execution
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(script_path)],
                creationflags=CREATE_NO_WINDOW,
                # Don't redirect output - let it go to the console/log file
            )
        else:
            # Launch shell script in background on Unix
            subprocess.Popen(
                ["/bin/bash", str(script_path)],
                # Don't redirect output - let it go to the console/log file
                start_new_session=True
            )

        print("\n✅ Update downloaded successfully!")
        print("   The installer will complete after this program exits.")
        print(f"   Check the log file for details: {log_path}")
        print("   Exiting in 2 seconds...")

        import time
        time.sleep(2)

        return True

    except Exception as e:
        print(f"Error during update: {e}", file=sys.stderr)
        # Clean up on error
        if zip_file.exists():
            zip_file.unlink()
        if new_binary_path.exists():
            new_binary_path.unlink()
        return False


def run(args: Any) -> None:
    """Handle the update command."""
    current_version = __version__
    is_prebuilt = is_prebuilt_install()

    # For --check flag, allow checking updates regardless of installation type
    # For actual updates, only allow pre-built binary installations
    if not args.check and not is_prebuilt:
        print("❌ Update command is only available for pre-built binary installations.")
        print("   You appear to be running from a Python package installation.")
        print("   Use 'pip install --upgrade aicodec' instead.")
        sys.exit(1)

    print(f"Current version: {current_version}")

    # Fetch latest version
    print("Checking for updates...")
    latest_version = get_latest_version()

    if not latest_version:
        print("❌ Could not check for updates. Please try again later.")
        sys.exit(1)

    print(f"Latest version:  {latest_version}")

    # Compare versions
    comparison = compare_versions(current_version, latest_version)

    if comparison == 0:
        print("✅ You are already running the latest version!")
        sys.exit(0)
    elif comparison > 0:
        print("ℹ️  You are running a newer version than the latest release.")
        sys.exit(0)

    # New version available
    print(f"\n🎉 A new version is available: {latest_version}")

    if args.check:
        # Provide appropriate update instructions based on installation type
        if is_prebuilt:
            print("   Run 'aicodec update' to install the update.")
        else:
            print("   Run 'pip install --upgrade aicodec' to install the update.")
        sys.exit(0)

    # Ask for confirmation (only for prebuilt installations)
    try:
        response = input("\nDo you want to update now? [Y/n] ").strip().lower()
        if response and response not in ("y", "yes"):
            print("Update cancelled.")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\nUpdate cancelled.")
        sys.exit(0)

    # Perform update
    success = update_binary()

    if success:
        # Exit the program so the update helper script can replace the binary
        sys.exit(0)
    else:
        print("\n❌ Update failed. Please try again or install manually.")
        sys.exit(1)
