# Installation

Before you begin, you need to install the `aicodec` CLI tool. Choose one of the following methods.

---

## Method 1: Using pip (Recommended)

If you have Python and pip installed, this is the easiest way to install `aicodec`.

```bash
pip install aicodec
```

This command downloads the package from the Python Package Index (PyPI) and makes the `aicodec` command available in your terminal.

---

## Method 2: From Pre-built Binaries

Alternatively, you can download a standalone executable for your operating system from the [latest GitHub release](https://github.com/Stevie1704/aicodec/releases/latest).

### Automated Installation (CLI)

You can use the following commands to automatically download the latest release, make it executable, and move it to a common system path.

**For Linux & macOS**

Copy and run the following command in your terminal. It detects your OS and architecture, downloads the correct binary, and installs it to `/usr/local/bin`. You may be prompted for your password for the `sudo` command.

```bash
curl -sL "[https://github.com/Stevie1704/aicodec/releases/latest/download/aicodec-$(uname](https://github.com/Stevie1704/aicodec/releases/latest/download/aicodec-$(uname) -s | tr '[:upper:]' '[:lower:]')-$(uname -m | sed 's/x86_64/amd64/' | sed 's/aarch64/arm64/')" -o aicodec && chmod +x aicodec && sudo mv aicodec /usr/local/bin/aicodec
```

**For Windows (using PowerShell)**

Open PowerShell **as an Administrator** and run the following command. It will download the executable and place it in `C:\Program Files\aicodec`.

```powershell
$installDir = "$env:ProgramFiles\aicodec"; New-Item -ItemType Directory -Path $installDir -ErrorAction SilentlyContinue; Invoke-WebRequest -Uri "[https://github.com/Stevie1704/aicodec/releases/latest/download/aicodec-windows-amd64.exe](https://github.com/Stevie1704/aicodec/releases/latest/download/aicodec-windows-amd64.exe)" -OutFile "$installDir\aicodec.exe"
```

After running the script, you should manually add `$installDir` (`C:\Program Files\aicodec`) to your system's `Path` environment variable to make the `aicodec` command available everywhere.

### Manual Installation

If you prefer not to run a script, you can perform the steps manually.

**For macOS and Linux:**

1.  Download the binary for your system from the releases page (e.g., `aicodec-macos-amd64`).
2.  Open your terminal and make the file executable:
    ```bash
    chmod +x /path/to/downloaded/aicodec-binary
    ```
3.  Move the executable to a directory in your system's `PATH`. A common choice is `/usr/local/bin`:
    ```bash
    sudo mv /path/to/downloaded/aicodec-binary /usr/local/bin/aicodec
    ```

**For Windows:**

1.  Download the `.exe` binary for your system (e.g., `aicodec-windows-amd64.exe`).
2.  Place the executable in a permanent folder, for example, `C:\Tools\aicodec\`.
3.  Add this folder to your system's `Path` environment variable.

After any of these methods, open a **new terminal** and verify the installation:

```bash
aicodec --version
```
