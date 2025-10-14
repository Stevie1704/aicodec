#!/bin/bash
set -e

# --- Configuration ---
TOOL_NAME="aicodec"
GITHUB_REPO="Stevie1704/aicodec"
INSTALL_DIR="/opt/${TOOL_NAME}"
LINK_DIR="/usr/local/bin"

# --- Dependency Check Function ---
check_and_install() {
    for tool in curl unzip; do
        if ! command -v "$tool" &> /dev/null; then
            echo "⚠️  '$tool' is not installed."
            read -p "Do you want to attempt to install it? [Y/n] " choice
            if [[ "$choice" =~ ^[Yy]$ || -z "$choice" ]]; then
                if command -v apt-get &> /dev/null; then
                    sudo apt-get update && sudo apt-get install -y "$tool"
                elif command -v dnf &> /dev/null; then
                    sudo dnf install -y "$tool"
                elif command -v pacman &> /dev/null; then
                    sudo pacman -Syu --noconfirm "$tool"
                else
                    echo "❌ Could not find a known package manager. Please install '$tool' manually."
                    exit 1
                fi
            else
                echo "❌ Installation aborted. '$tool' is required."
                exit 1
            fi
        fi
    done
}

# --- Main Script ---
check_and_install

# 1. Determine OS and Architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
HW_ARCH=$(uname -m)
case "$HW_ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64 | arm64) ARCH="arm64" ;;
    *)
        echo "❌ Unsupported hardware architecture: $HW_ARCH"
        exit 1
        ;;
esac

# 2. Download and Unzip
ZIP_FILE="/tmp/${TOOL_NAME}.zip"
DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/releases/latest/download/${TOOL_NAME}-${OS}-${ARCH}.zip"
TMP_UNZIP_DIR="/tmp/${TOOL_NAME}-install"

echo "⚙️  Downloading from: ${DOWNLOAD_URL}"
curl -sSL -o "${ZIP_FILE}" "${DOWNLOAD_URL}"
unzip -o "${ZIP_FILE}" -d "${TMP_UNZIP_DIR}"
UNZIPPED_FOLDER=$(find "${TMP_UNZIP_DIR}" -mindepth 1 -maxdepth 1 -type d -print -quit)

if [ -z "${UNZIPPED_FOLDER}" ]; then
    echo "❌ Failed to find the unzipped directory. Aborting."
    exit 1
fi

# 3. Move folder to /opt
echo "⚙️  Installing application to ${INSTALL_DIR}..."
sudo mv "${UNZIPPED_FOLDER}" "${INSTALL_DIR}"

# 4. Make the binary executable
#    THIS IS THE NEW, CRITICAL STEP!
echo "⚙️  Setting execute permissions..."
sudo chmod +x "${INSTALL_DIR}/${TOOL_NAME}"

# 5. Create symbolic link
echo "⚙️  Creating command link in ${LINK_DIR}..."
sudo ln -sf "${INSTALL_DIR}/${TOOL_NAME}" "${LINK_DIR}/${TOOL_NAME}"

# 6. Clean up and verify
rm "${ZIP_FILE}"
rm -rf "${TMP_UNZIP_DIR}"
echo "✅  '${TOOL_NAME}' installed successfully!"
echo "➡️  Run it with: ${TOOL_NAME} --help"
