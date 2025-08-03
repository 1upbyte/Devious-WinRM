param(
    [Parameter(Mandatory=$true)]
    [string]$Path,

    [Parameter(Mandatory=$true)]
    [string]$Name,

    [Parameter(Mandatory=$true)]
    [string]$Url
)

try {
    $fullPath = $Path
    if (Test-Path $Path -PathType Container) {
        $fullPath = Join-Path -Path $Path -ChildPath $Name
    }
    Invoke-WebRequest -Uri $Url -OutFile $fullPath -ErrorAction Stop
} catch {
    Write-Error "Failed to download file: $_"
}