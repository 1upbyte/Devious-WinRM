# Invoke-In-Memory.ps1
# Executes a .NET assembly stored in the $bin variable (byte array) in memory

param (
    [Parameter()]
    [string]$Arguments = ""
)

$outputWriter = New-Object System.IO.StringWriter
$errorWriter = New-Object System.IO.StringWriter
[Console]::SetOut($outputWriter)
# [Console]::SetError($errorWriter)

$args = $Arguments.split(",")

if ([string]::IsNullOrEmpty($args)) {
    # If there are no arguments, create an empty string array.
    $args = [string[]]@()
}

$assembly = [System.Reflection.Assembly]::Load($bin)
$entryPoint = $assembly.EntryPoint
$invocationArgs = , $args

$entryPoint.Invoke($null, $invocationArgs)

$capturedOutput = $outputWriter.ToString()
# $capturedError = $errorWriter.ToString()
Write-Output $capturedOutput
# Write-Error $capturedError