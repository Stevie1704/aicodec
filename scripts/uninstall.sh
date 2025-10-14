#!/bin/bash
set -e

# --- Configuration ---
TOOL_NAME="aicodec"
INSTALL_DIR="/opt/${TOOL_NAME}"
LINK_PATH="/usr/local/bin/${TOOL_NAME}"

# --- Main Uninstall Script ---
echo "Uninstalling '${TOOL_NAME}'..."

# 1. Remove the symbolic link
if [ -L "${LINK_PATH}" ]; then
    echo "Removing command link: ${LINK_PATH}"
    sudo rm "${LINK_PATH}"
else
    echo "⚠️  Command link not found. Skipping."
fi

# 2. Remove the application directory
if [ -d "${INSTALL_DIR}" ]; then
    echo "Removing application directory: ${INSTALL_DIR}"
    sudo rm -rf "${INSTALL_DIR}"
else
    echo "⚠️  Application directory not found. Skipping."
fi

echo "✅  '${TOOL_NAME}' has been successfully uninstalled."
