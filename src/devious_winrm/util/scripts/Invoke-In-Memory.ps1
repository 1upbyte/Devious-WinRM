# Invoke-In-Memory.ps1
# Executes a .NET assembly stored in the $bin variable (byte array) in memory

param (
    [Parameter(Mandatory = $true)]
    [string]$VariableName,

    [string[]]$Arguments = @()
)

$outputWriter = New-Object System.IO.StringWriter
$errorWriter = New-Object System.IO.StringWriter
[Console]::SetOut($outputWriter)
[Console]::SetError($errorWriter)

$bin = (Get-Variable $VariableName).Value
$assembly = [System.Reflection.Assembly]::Load($bin)
$entryPoint = $assembly.EntryPoint
$invocationArgs = , $Arguments

$entryPoint.Invoke($null, $invocationArgs)

$capturedOutput = $outputWriter.ToString()
$capturedError = $errorWriter.ToString()
Write-Output $capturedOutput
Write-Error $capturedError