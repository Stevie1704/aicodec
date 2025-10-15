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

**For macOS and Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/Stevie1704/aicodec/main/scripts/install.sh | bash
```
Uninstall with

**For macOS and Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/Stevie1704/aicodec/main/scripts/install.sh | bash
```

**For Windows**
```bash
powershell -Command "irm https://raw.githubusercontent.com/Stevie1704/aicodec/main/scripts/install.ps1 | iex"
```
Uninstall with
```bash
powershell -Command "irm https://raw.githubusercontent.com/Stevie1704/aicodec/main/scripts/uninstall.ps1 | iex"
```

### Manual Installation

If you prefer not to run a script, you can perform the steps manually.

**For macOS and Linux:**

1.  Download the `.zip` for your system from the releases page (e.g., `aicodec-macos-amd64.zip`) and unzip it.
2.  Open your terminal and make the file executable:
    ```bash
    chmod +x /path/to/unzipped/aicodec-binary
    ```
3.  Move the executable to a directory in your system's `PATH`. A common choice is `/usr/local/bin`:
    ```bash
    sudo mv /path/to/downloaded/aicodec-binary /usr/local/bin/aicodec
    ```

**For Windows:**

1.  Download the `.zip` binary for your system (`aicodec-windows-amd64.zip`) and unzip it.
2.  Add this folder (e.g., `C:\Tools\aicodec` to your user's or system's `Path` environment variable.

After any of these methods, open a **new terminal** and verify the installation:

```bash
aicodec -h
```
