# --- Configuration ---
$ToolName = "aicodec"
# The installation folder will be created under the user's home directory.
# e.g., C:\Users\YourName\aicodec
$InstallPath = [System.IO.Path]::Combine([System.Environment]::GetFolderPath('UserProfile'), $ToolName)

# --- Main Installation Script ---
Write-Host "⚙️  Starting installation for $($ToolName)..."

# 1. Create the installation directory if it doesn't exist
if (-not (Test-Path -Path $InstallPath)) {
    New-Item -Path $InstallPath -ItemType Directory | Out-Null
}
Write-Host "✅ Files will be installed to: $($InstallPath)"

# 2. Determine OS/Arch and Download the zip
$OS = "windows"
$Arch = "amd64"
$ZipFilePath = [System.IO.Path]::Combine($env:TEMP, "$($ToolName).zip")
$DownloadUrl = "https://github.com/Stevie1704/aicodec/releases/latest/download/$($ToolName)-$($OS)-$($Arch).zip"

Write-Host "⚙️  Downloading from $($DownloadUrl)..."
Invoke-WebRequest -Uri $DownloadUrl -OutFile $ZipFilePath

# 3. Unzip the contents into the installation subfolder
Write-Host "⚙️  Unzipping files..."
Expand-Archive -Path $ZipFilePath -DestinationPath $InstallPath -Force

# 4. Add the installation folder to the user's "Path" environment variable
Write-Host "⚙️  Updating your user Path environment variable..."

try {
    # Get the current user's Path
    $CurrentUserPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')

    # Check if our path is already there to avoid duplicates
    if ($CurrentUserPath -notlike "*$($InstallPath)*") {
        # If not present, append it
        $NewPath = $CurrentUserPath + ';' + $InstallPath
        [System.Environment]::SetEnvironmentVariable('Path', $NewPath, 'User')
        Write-Host "✅ Path updated successfully!"
    } else {
        Write-Host "☑️  Path already contains the installation directory. No changes needed."
    }
} catch {
    Write-Host "❌ An error occurred while updating the Path variable." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

# 5. Clean up the downloaded zip file
Remove-Item -Path $ZipFilePath -Force

# --- Final Instructions ---
Write-Host ""
Write-Host "✅ $($ToolName) installed successfully!" -ForegroundColor Green
Write-Host "⚠️  IMPORTANT: You must RESTART your PowerShell/Terminal for the 'aicodec' command to become available."
