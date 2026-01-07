# aicodec/infrastructure/cli/commands/uninstall.py
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from .update import can_write_to_path, get_running_binary_path, is_prebuilt_install, is_sudo_available


def register_subparser(subparsers: Any) -> None:
    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="Uninstall aicodec (pre-built binary only)"
    )
    uninstall_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip confirmation prompt"
    )
    uninstall_parser.set_defaults(func=run)


def create_uninstall_script(
    binary_path: Path,
    install_dir: Path,
    symlink_path: Path | None,
    needs_sudo: bool,
    sudo_available: bool
) -> Path:
    """Create a platform-specific uninstall helper script."""
    os_name = platform.system().lower()

    if os_name == "windows":
        # Create PowerShell script for Windows
        script_path = install_dir / "uninstall_helper.ps1"
        log_path = install_dir / "uninstall_log.txt"
        script_content = f"""# Log file for debugging
$logFile = "{log_path}"
"Uninstall started at $(Get-Date)" | Out-File -FilePath $logFile

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

# Remove the binary
try {{
    "Attempting to remove binary: {binary_path}" | Out-File -FilePath $logFile -Append
    Remove-Item -Path "{binary_path}" -Force -ErrorAction Stop
    "Binary removed successfully" | Out-File -FilePath $logFile -Append
}} catch {{
    "ERROR: Failed to remove binary: $_" | Out-File -FilePath $logFile -Append
    Write-Host "Failed to remove binary: $_"
}}

# Remove the installation directory if it exists and is empty (except for logs/scripts)
try {{
    $remainingFiles = Get-ChildItem -Path "{install_dir}" -Exclude "uninstall_log.txt","uninstall_helper.ps1" -ErrorAction SilentlyContinue
    if ($remainingFiles.Count -eq 0) {{
        "Installation directory is empty, scheduling removal" | Out-File -FilePath $logFile -Append
    }}
}} catch {{
    "Note: Could not check installation directory: $_" | Out-File -FilePath $logFile -Append
}}

Write-Host ""
Write-Host "aicodec has been uninstalled successfully!"
Write-Host "Note: Project-specific .aicodec directories were not removed."
Write-Host ""
"Uninstall completed at $(Get-Date)" | Out-File -FilePath $logFile -Append

Start-Sleep -Seconds 3

# Clean up the installation directory (including this script and log)
try {{
    Remove-Item -Path "{install_dir}" -Recurse -Force -ErrorAction SilentlyContinue
}} catch {{
    # Ignore errors - directory might be in use
}}
"""
        script_path.write_text(script_content, encoding='utf-8')
        return script_path
    else:
        # Create shell script for Unix/Linux/macOS
        script_path = install_dir / "uninstall_helper.sh"
        log_path = install_dir / "uninstall_log.txt"

        # Determine if we should use sudo
        use_sudo = needs_sudo and sudo_available
        sudo_prefix = "sudo " if use_sudo else ""

        script_content = f"""#!/bin/bash
# Log file for debugging
LOG_FILE="{log_path}"
echo "Uninstall started at $(date)" > "$LOG_FILE"

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

# Remove the binary
echo "Attempting to remove binary: {binary_path}" >> "$LOG_FILE"
{sudo_prefix}rm -f "{binary_path}" 2>> "$LOG_FILE"
if [ $? -eq 0 ]; then
    echo "Binary removed successfully" >> "$LOG_FILE"
else
    echo "ERROR: Failed to remove binary" >> "$LOG_FILE"
fi

# Remove symlink if it exists
SYMLINK_PATH="{symlink_path if symlink_path else ''}"
if [ -n "$SYMLINK_PATH" ] && [ -L "$SYMLINK_PATH" ]; then
    echo "Attempting to remove symlink: $SYMLINK_PATH" >> "$LOG_FILE"
    {sudo_prefix}rm -f "$SYMLINK_PATH" 2>> "$LOG_FILE"
    if [ $? -eq 0 ]; then
        echo "Symlink removed successfully" >> "$LOG_FILE"
    else
        echo "WARNING: Failed to remove symlink (may require manual removal)" >> "$LOG_FILE"
    fi
fi

echo ""
echo "aicodec has been uninstalled successfully!"
echo "Note: Project-specific .aicodec directories were not removed."
echo ""
echo "Uninstall completed at $(date)" >> "$LOG_FILE"

sleep 3

# Clean up the installation directory (including this script and log)
{sudo_prefix}rm -rf "{install_dir}" 2>/dev/null

# If we couldn't remove the directory (e.g., it's not empty or no permissions),
# at least try to remove just the script
rm -f "$0" 2>/dev/null
"""
        script_path.write_text(script_content, encoding='utf-8')
        os.chmod(script_path, 0o755)  # nosec B103 - Standard executable permissions
        return script_path


def perform_uninstall() -> bool:
    """Prepare and launch the uninstall process."""
    os_name = platform.system().lower()

    # Find the actual binary location
    running_binary_path, symlink_path = get_running_binary_path()

    if not running_binary_path:
        print("Could not find aicodec binary to uninstall.", file=sys.stderr)
        return False

    print(f"Binary location: {running_binary_path}")
    if symlink_path:
        print(f"  (via symlink: {symlink_path})")

    install_dir = running_binary_path.parent

    # Check permissions
    if os_name == "windows":
        needs_sudo = False
        sudo_available = False
    else:
        has_write_permission = can_write_to_path(running_binary_path)
        sudo_available = is_sudo_available()
        needs_sudo = not has_write_permission

        if needs_sudo and not sudo_available:
            print("Insufficient permissions to uninstall aicodec.", file=sys.stderr)
            print(f"   Target binary: {running_binary_path}", file=sys.stderr)
            print("   The installation directory requires elevated permissions but sudo is not available.", file=sys.stderr)
            return False

    # Create the uninstall helper script
    print("Preparing uninstall...")
    script_path = create_uninstall_script(running_binary_path, install_dir, symlink_path, needs_sudo, sudo_available)

    # Launch the uninstall script
    print("Launching uninstaller...")

    if os_name == "windows":
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(
            ["powershell", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(script_path)],
            creationflags=CREATE_NO_WINDOW,
        )
    else:
        subprocess.Popen(
            ["/bin/bash", str(script_path)],
            start_new_session=True
        )

    print("\nUninstall process started.")
    print("   The uninstaller will complete after this program exits.")
    print("   Exiting in 2 seconds...")

    import time
    time.sleep(2)

    return True


def run(args: Any) -> None:
    """Handle the uninstall command."""
    is_prebuilt = is_prebuilt_install()

    if not is_prebuilt:
        print("Uninstall command is only available for pre-built binary installations.")
        print("   You appear to be running from a Python package installation.")
        print("   Use 'pip uninstall aicodec' instead.")
        sys.exit(1)

    # Find the binary to show the user what will be removed
    running_binary_path, symlink_path = get_running_binary_path()

    if not running_binary_path:
        print("Could not find aicodec binary.", file=sys.stderr)
        sys.exit(1)

    install_dir = running_binary_path.parent

    print("This will uninstall aicodec from your system.")
    print("")
    print("The following will be removed:")
    print(f"  - Binary: {running_binary_path}")
    print(f"  - Directory: {install_dir}")
    if symlink_path:
        print(f"  - Symlink: {symlink_path}")
    print("")
    print("The following will NOT be removed:")
    print("  - Project-specific .aicodec/ directories")
    print("")

    if not args.force:
        try:
            response = input("Are you sure you want to uninstall? [y/N] ").strip().lower()
            if response not in ("y", "yes"):
                print("Uninstall cancelled.")
                sys.exit(0)
        except KeyboardInterrupt:
            print("\nUninstall cancelled.")
            sys.exit(0)

    success = perform_uninstall()

    if success:
        sys.exit(0)
    else:
        print("\nUninstall failed.", file=sys.stderr)
        sys.exit(1)
