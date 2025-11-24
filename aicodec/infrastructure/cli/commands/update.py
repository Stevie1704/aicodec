# aicodec/infrastructure/cli/commands/update.py
import json
import os
import platform
import subprocess
import sys
import tempfile
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


def is_prebuilt_install() -> bool:
    """Check if aicodec is installed as a pre-built binary."""
    install_dir = Path("/opt/aicodec")
    return install_dir.exists() and (install_dir / "aicodec").exists()


def get_download_url() -> str | None:
    """Determine the download URL based on OS and architecture."""
    os_name = platform.system().lower()
    machine = platform.machine().lower()

    # Map platform names
    if os_name == "darwin":
        os_name = "darwin"
    elif os_name == "linux":
        os_name = "linux"
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


def update_binary() -> bool:
    """Download and install the latest version."""
    print("Downloading latest version...")

    download_url = get_download_url()
    if not download_url:
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        zip_file = tmpdir_path / "aicodec.zip"

        try:
            # Download
            print(f"Downloading from: {download_url}")
            urllib.request.urlretrieve(download_url, zip_file)  # nosec B310 - GitHub releases HTTPS only

            # Unzip
            print("Extracting...")
            import zipfile
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(tmpdir_path)

            # Find the binary (should be in the extracted directory)
            binary_path = None
            for item in tmpdir_path.iterdir():
                if item.is_file() and item.name == "aicodec":
                    binary_path = item
                    break
                elif item.is_dir():
                    # Check inside subdirectory
                    for subitem in item.iterdir():
                        if subitem.name == "aicodec":
                            binary_path = subitem
                            break

            if not binary_path:
                print("Error: Could not find aicodec binary in downloaded package", file=sys.stderr)
                return False

            # Make it executable
            os.chmod(binary_path, 0o755)  # nosec B103 - Standard executable permissions (rwxr-xr-x)

            # Replace the existing binary
            print("Installing update...")
            install_dir = Path("/opt/aicodec")
            target_binary = install_dir / "aicodec"

            # Use sudo to replace the binary
            try:
                subprocess.run(
                    ["sudo", "cp", str(binary_path), str(target_binary)],
                    check=True,
                    capture_output=True
                )
                subprocess.run(
                    ["sudo", "chmod", "+x", str(target_binary)],
                    check=True,
                    capture_output=True
                )
            except subprocess.CalledProcessError as e:
                print(f"Error installing update (sudo required): {e.stderr.decode()}", file=sys.stderr)
                return False

            print("✅ Update installed successfully!")
            return True

        except Exception as e:
            print(f"Error during update: {e}", file=sys.stderr)
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
        print(f"\n✅ Successfully updated to version {latest_version}!")
        print("   Run 'aicodec --version' to verify.")
    else:
        print("\n❌ Update failed. Please try again or install manually.")
        sys.exit(1)
