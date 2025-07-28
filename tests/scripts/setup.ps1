# Setup an environment for running tests.


$rootDir = "C:\DWRM-TEST"

$ErrorActionPreference = "Stop"

# --- Step 1: Erase the folder if it exists ---
if (Test-Path $rootDir) {
    Remove-Item -Path $rootDir -Recurse -Force
}

# --- Step 2: Create the root folder ---
New-Item -Path $rootDir -ItemType Directory -Force | Out-Null

# --- Step 3: Create text.txt with contents "Test File" ---
$filePathText = Join-Path $rootDir "text.txt"
Set-Content -Path $filePathText -Value "Test File"

# --- Step 4: Create 'Program Files' structure ---
$programFilesDir = Join-Path $rootDir "Program Files"
New-Item -Path $programFilesDir -ItemType Directory -Force | Out-Null

$program1Exe = Join-Path $programFilesDir "program1.exe"
New-Item -Path $program1Exe -ItemType File -Force | Out-Null

$program2Exe = Join-Path $programFilesDir "program2.exe"
New-Item -Path $program2Exe -ItemType File -Force | Out-Null

$folder1InProgramFiles = Join-Path $programFilesDir "folder1"
New-Item -Path $folder1InProgramFiles -ItemType Directory -Force | Out-Null

# --- Step 5: Create 'Program Files (x86)' structure ---
$programFilesX86Dir = Join-Path $rootDir "Program Files (x86)"
New-Item -Path $programFilesX86Dir -ItemType Directory -Force | Out-Null

# Corrected path for program1.exe and program2.exe under (x86)
$program1ExeX86 = Join-Path $programFilesX86Dir "program1.exe"
New-Item -Path $program1ExeX86 -ItemType File -Force | Out-Null

$program2ExeX86 = Join-Path $programFilesX86Dir "program2.exe"
New-Item -Path $program2ExeX86 -ItemType File -Force | Out-Null

$folder1InProgramFilesX86 = Join-Path $programFilesX86Dir "folder1"
New-Item -Path $folder1InProgramFilesX86 -ItemType Directory -Force | Out-Null

# --- Step 6: Create a 256MB file ---
$largeFilePath = Join-Path $rootDir "256mb.file"
$fileSizeMB = 256
$fileSizeInBytes = $fileSizeMB * 1024 * 1024

$fileStream = [System.IO.File]::Create($largeFilePath)
$fileStream.SetLength($fileSizeInBytes)
$fileStream.Close()
$fileStream.Dispose()


