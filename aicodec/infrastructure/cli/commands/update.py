# aicodec/infrastructure/cli/commands/update.py
import json
import os
import platform
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


def is_prebuilt_install() -> bool:
    """Check if aicodec is installed as a pre-built binary."""
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
        script_content = f"""# Wait for the main process to exit
Start-Sleep -Seconds 2

# Get the current process ID to exclude
$parentPid = $PID

# Wait for aicodec.exe to fully exit (check for any aicodec process except this script)
$maxAttempts = 10
$attempt = 0
while ($attempt -lt $maxAttempts) {{
    $processes = Get-Process -Name "aicodec" -ErrorAction SilentlyContinue | Where-Object {{ $_.Id -ne $parentPid }}
    if ($processes.Count -eq 0) {{
        break
    }}
    Start-Sleep -Seconds 1
    $attempt++
}}

# Replace the binary
try {{
    Copy-Item -Path "{new_binary_path}" -Destination "{target_binary}" -Force
    Write-Host "Update installed successfully!"
    Write-Host "You can now run 'aicodec --version' to verify the update."
}} catch {{
    Write-Host "Error installing update: $_"
    Write-Host "Please try running the update command again."
    exit 1
}}

# Clean up
Remove-Item -Path "{new_binary_path}" -ErrorAction SilentlyContinue
Remove-Item -Path $PSCommandPath -ErrorAction SilentlyContinue
"""
        script_path.write_text(script_content, encoding='utf-8')
        return script_path
    else:
        # Create shell script for Unix/Linux/macOS
        script_path = new_binary_path.parent / "update_helper.sh"

        # Determine if we should use sudo
        use_sudo = needs_sudo and sudo_available

        if use_sudo:
            script_content = f"""#!/bin/bash
# Wait for the main process to exit
sleep 2

# Wait for aicodec process to fully exit
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if ! pgrep -x "aicodec" > /dev/null; then
        break
    fi
    sleep 1
    attempt=$((attempt + 1))
done

# Replace the binary using sudo
sudo mv "{new_binary_path}" "{target_binary}"
if [ $? -eq 0 ]; then
    sudo chmod +x "{target_binary}"
    echo "✅ Update installed successfully!"
    echo "You can now run 'aicodec --version' to verify the update."
else
    echo "❌ Error installing update. Please try again."
    exit 1
fi

# Clean up
rm -f "$0"
"""
        else:
            # For environments without sudo (devcontainers, etc.)
            script_content = f"""#!/bin/bash
# Wait for the main process to exit
sleep 2

# Wait for aicodec process to fully exit
max_attempts=10
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if ! pgrep -x "aicodec" > /dev/null; then
        break
    fi
    sleep 1
    attempt=$((attempt + 1))
done

# Replace the binary without sudo
mv "{new_binary_path}" "{target_binary}"
if [ $? -eq 0 ]; then
    chmod +x "{target_binary}"
    echo "✅ Update installed successfully!"
    echo "You can now run 'aicodec --version' to verify the update."
else
    echo "❌ Error installing update. Please try again."
    exit 1
fi

# Clean up
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
    if os_name == "windows":
        install_dir = Path.home() / "aicodec"
        binary_name = "aicodec.exe"
        new_binary_name = "aicodec.new.exe"
        needs_sudo = False
        sudo_available = False
    else:
        install_dir = Path("/opt/aicodec")
        binary_name = "aicodec"
        new_binary_name = "aicodec.new"

        # Check if we need sudo and if it's available
        target_binary_path = install_dir / binary_name
        has_write_permission = can_write_to_path(target_binary_path)
        sudo_available = is_sudo_available()

        # Only require sudo if we don't have write permissions
        needs_sudo = not has_write_permission

        # If we need sudo but it's not available, check if we can proceed anyway
        if needs_sudo and not sudo_available:
            if not has_write_permission:
                print("❌ Error: Insufficient permissions to update aicodec.", file=sys.stderr)
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
            # Extract the binary directly
            for member in zip_ref.namelist():
                if member.endswith(binary_name) or member == binary_name:
                    with zip_ref.open(member) as source:
                        with open(new_binary_path, 'wb') as target:
                            target.write(source.read())
                    break

        # Clean up zip file
        zip_file.unlink()

        if not new_binary_path.exists():
            print(f"Error: Could not find {binary_name} binary in downloaded package", file=sys.stderr)
            return False

        # Make it executable on Unix
        if os_name != "windows":
            os.chmod(new_binary_path, 0o755)  # nosec B103 - Standard executable permissions (rwxr-xr-x)

        # Create update helper script
        print("Preparing update installer...")
        target_binary = install_dir / binary_name
        script_path = create_update_script(new_binary_path, target_binary, needs_sudo, sudo_available)

        # Launch the update script
        print("Launching update installer...")
        if os_name == "windows":
            # Launch PowerShell script in background on Windows
            # Use DETACHED_PROCESS to run without a console window
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(script_path)],
                creationflags=DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            # Launch shell script in background on Unix
            subprocess.Popen(
                ["/bin/bash", str(script_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

        print("\n✅ Update downloaded successfully!")
        print("   The installer will complete after this program exits.")
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

    # Check if running as pre-built binary
    if not is_prebuilt_install():
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
        print("   Run 'aicodec update' to install the update.")
        sys.exit(0)

    # Ask for confirmation
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
