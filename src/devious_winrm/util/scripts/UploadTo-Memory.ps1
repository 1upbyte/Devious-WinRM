# Copyright: (c) 2022, Jordan Borean (@jborean93) <jborean93@gmail.com>
# MIT License (see LICENSE or https://opensource.org/licenses/MIT)
# Adapted by Pablo Comino (@1upbyte) <pablo@pablocomino.com> 
# Writes a file to an in-memory variable and returns the variable name.
[CmdletBinding()]
param (
    [Parameter(ValueFromPipeline = $true)]
    [byte[]]
    $InputObject,

    [Parameter(Mandatory = $true, Position = 0)]
    [string]
    $variableName
)


begin {
    $ErrorActionPreference = "Stop"
    $WarningPreference = "Continue"

    $algo = [System.Security.Cryptography.SHA1CryptoServiceProvider]::Create()
    $bytes = $null
    $expectedHash = ""
    $memoryStream = New-Object System.IO.MemoryStream

    $bindingFlags = [System.Reflection.BindingFlags]'NonPublic, Instance'
    Function Get-Property {
        <#
        .SYNOPSIS
        Gets the private/internal property specified of the object passed in.
        #>
        Param (
            [Parameter(Mandatory = $true, ValueFromPipeline = $true)]
            [System.Object]
            $Object,

            [Parameter(Mandatory = $true, Position = 1)]
            [System.String]
            $Name
        )

        process {
            $Object.GetType().GetProperty($Name, $bindingFlags).GetValue($Object, $null)
        }
    }

    Function Set-Property {
        <#
        .SYNOPSIS
        Sets the private/internal property specified on the object passed in.
        #>
        Param (
            [Parameter(Mandatory = $true, ValueFromPipeline = $true)]
            [System.Object]
            $Object,

            [Parameter(Mandatory = $true, Position = 1)]
            [System.String]
            $Name,

            [Parameter(Mandatory = $true, Position = 2)]
            [AllowNull()]
            [System.Object]
            $Value
        )

        process {
            $Object.GetType().GetProperty($Name, $bindingFlags).SetValue($Object, $Value, $null)
        }
    }

    Function Get-Field {
        <#
        .SYNOPSIS
        Gets the private/internal field specified of the object passed in.
        #>
        Param (
            [Parameter(Mandatory = $true, ValueFromPipeline = $true)]
            [System.Object]
            $Object,

            [Parameter(Mandatory = $true, Position = 1)]
            [System.String]
            $Name
        )

        process {
            $Object.GetType().GetField($Name, $bindingFlags).GetValue($Object)
        }
    }

    # MaximumAllowedMemory is required to be set to so we can send input data
    # that exceeds the limit on a PS Runspace. We use reflection to access/set
    # this property as it is not accessible publicly. This is not ideal but
    # works on all PowerShell versions I've tested with. This isn't required
    # for smaller files so if it fails we just want to return the warning back
    # to the user.
    # https://github.com/PowerShell/PowerShell/blob/c8e72d1e664b1ee04a14f226adf655cced24e5f0/src/System.Management.Automation/engine/serialization.cs#L325
    try {
        $Host | Get-Property 'ExternalHost' | `
                Get-Field '_transportManager' | `
                Get-Property 'Fragmentor' | `
                Get-Property 'DeserializationContext' | `
                Set-Property 'MaximumAllowedMemory' $null
    }
    catch {
        $versionInfo = $PSVersionTable | Out-String
        $msg = -join @(
            "Failed to disable MaximumAllowedMemory input size: $($_.Exception.Message)`n"
            "Server PS Info:`r`n$versionInfo"
        )
        Write-Warning -Message $msg
    }
} process {
    # On the first input $bytes will be $null so this isn't run. This shifts
    # each input to the next run until the final input is reach (checksum of
    # the file) which is processed in end.
    if ($null -ne $bytes) {
        $memoryStream.Write($bytes, 0, $bytes.Length)
        $algo.TransformBlock($bytes, 0, $bytes.Length, $bytes, 0) > $null
    }
    # Pwsh v2 can't seem to use the bound parameter name, so just use $_.
    $bytes = $_
    Write-Verbose $bytes.Length
} end {
    

    $expectedHash = [System.Text.Encoding]::UTF8.GetString($bytes)
    $algo.TransformFinalBlock($bytes, 0, 0) > $null
    $actualHash = [System.BitConverter]::ToString($algo.Hash)
    $actualHash = $actualHash.Replace("-", "").ToLowerInvariant()

    Write-Verbose -Message "Copy expected hash $expectedHash - actual hash $actualHash"
    if ($actualHash -ne $expectedHash) {
        throw "Transport failure, hash mismatch`r`nActual: $actualHash`r`nExpected: $expectedHash"
    }
    New-Variable -Name $variableName -Force -Value $memoryStream.ToArray()
    $variableName
}
