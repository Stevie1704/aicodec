# Installation

To get started, you need to install the `aicodec` CLI tool. Choose the method that best fits your system.

---

## Method 1: Using pip (Recommended for Python users)

If you have Python and `pip` installed, this is the simplest way to get `aicodec`.

```bash
pip install aicodec
```

This command downloads the latest version from the Python Package Index (PyPI) and makes the `aicodec` command available in your terminal.

---

## Method 2: From Pre-built Binaries

If you don't have Python or prefer a standalone executable, you can download one for your operating system from the [latest GitHub release](https://github.com/Stevie1704/aicodec/releases/latest).

### Automated Installation (Recommended)

For a quick setup, you can run one of the following commands in your terminal. These scripts automatically download the correct binary, unpack it, and add it to your system's PATH.

**For macOS and Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/Stevie1704/aicodec/main/scripts/install.sh | bash
```

**For Windows (in PowerShell):**
```bash
powershell -Command "irm https://raw.githubusercontent.com/Stevie1704/aicodec/main/scripts/install.ps1 | iex"
```

### Manual Installation

If you prefer not to execute a remote script, you can perform the steps manually.

**For macOS and Linux:**

1.  Download the `.zip` for your system from the releases page (e.g., `aicodec-macos-amd64.zip`) and unzip it.
2.  Make the file executable:
    ```bash
    chmod +x /path/to/unzipped/aicodec-binary
    ```
3.  Move the executable to a directory in your system's `PATH`. A common choice is `/usr/local/bin`:
    ```bash
    sudo mv /path/to/unzipped/aicodec-binary /usr/local/bin/aicodec
    ```

**For Windows:**

1.  Download the `.zip` binary for your system (`aicodec-windows-amd64.zip`) and unzip it.
2.  Move the extracted folder to a permanent location (e.g., `C:\Tools\aicodec`).
3.  Add this folder's path to your user or system `Path` environment variable.

---

## Verify Installation

After any of these methods, open a **new terminal** and verify the installation:

```bash
aicodec --help
```

You should see the main help menu, confirming the tool is ready to use.

---

## Uninstallation

**If installed with pip:**
```bash
pip uninstall aicodec
```

**If installed with the automated script:**

-   macOS/Linux: 
```bash
curl -sSL https://raw.githubusercontent.com/Stevie1704/aicodec/main/scripts/uninstall.sh | bash
```
-   Windows: 
```bash
powershell -Command "irm https://raw.githubusercontent.com/Stevie1704/aicodec/main/scripts/uninstall.ps1 | iex"
```

**If installed manually:**
Simply delete the `aicodec` binary file and remove its directory from your system's PATH if you added it.
