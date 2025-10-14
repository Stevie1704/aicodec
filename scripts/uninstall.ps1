# --- Configuration ---
$ToolName = "aicodec"
# Define the exact path to the installation folder to be removed
$InstallPath = [System.IO.Path]::Combine([System.Environment]::GetFolderPath('UserProfile'), $ToolName)

# --- Main Uninstallation Script ---
Write-Host "⚙️  Starting uninstallation for $($ToolName)..."

# 1. Remove the directory from the user's Path environment variable
Write-Host "⚙️  Removing '$($InstallPath)' from your user Path..."

try {
    $CurrentUserPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    # Split the path by semicolons, filter out our specific directory, and rejoin
    $NewPath = ($CurrentUserPath -split ';' | Where-Object { $_ -ne $InstallPath }) -join ';'
    
    # Set the new, cleaned-up Path
    [System.Environment]::SetEnvironmentVariable('Path', $NewPath, 'User')
    Write-Host "✅ Path cleaned successfully."
} catch {
    Write-Host "❌ An error occurred while updating the Path variable." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}


# 2. Delete the installation directory
if (Test-Path -Path $InstallPath) {
    Write-Host "⚙️  Deleting installation directory: $($InstallPath)..."
    Remove-Item -Path $InstallPath -Recurse -Force
    Write-Host "✅ Directory deleted."
} else {
    Write-Host "☑️  Installation directory not found. Nothing to delete."
}

# --- Final Instructions ---
Write-Host ""
Write-Host "✅ $($ToolName) has been uninstalled." -ForegroundColor Green
Write-Host "⚠️  Changes to the Path will take effect in any new PowerShell/Terminal sessions."
