#!/bin/bash
set -e

# --- Configuration ---
TOOL_NAME="aicodec"
INSTALL_DIR="/opt/${TOOL_NAME}"
LINK_PATH="/usr/local/bin/${TOOL_NAME}"

# --- Check if sudo is available ---
USE_SUDO=""
if command -v sudo &> /dev/null; then
    USE_SUDO="sudo"
else
    echo "ℹ️  sudo not found, attempting uninstallation without it (you may need to be root)"
fi

# --- Helper function to run commands with or without sudo ---
run_elevated() {
    if [ -n "$USE_SUDO" ]; then
        $USE_SUDO "$@"
    else
        "$@"
    fi
}

# --- Main Uninstall Script ---
echo "Uninstalling '${TOOL_NAME}'..."

# 1. Remove the symbolic link
if [ -L "${LINK_PATH}" ]; then
    echo "Removing command link: ${LINK_PATH}"
    run_elevated rm "${LINK_PATH}"
else
    echo "⚠️  Command link not found. Skipping."
fi

# 2. Remove the application directory
if [ -d "${INSTALL_DIR}" ]; then
    echo "Removing application directory: ${INSTALL_DIR}"
    run_elevated rm -rf "${INSTALL_DIR}"
else
    echo "⚠️  Application directory not found. Skipping."
fi

echo "✅  '${TOOL_NAME}' has been successfully uninstalled."
