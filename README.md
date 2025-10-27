# Devious-WinRM

A Pentester's Powershell Client.

![The help screen for Devious-WinRM, showing a variety of flags and options.](https://raw.githubusercontent.com/1upbyte/Devious-WinRM/refs/heads/main/assets/help-screen.png "Help screen")


## Highlight Features
### Zero-confing Kerberos
Devious-WinRM's initial reason for creation was due to how complicated Kerberos auth can be. With Devious-WinRM, on most operating systems, it is as simple as appending the `-k` flag to the command line. Devious-WinRM will automatically handle the rest.

### Easy in-memory .NET execution
Any .NET binary can be ran directly in the Powershell process' memory using the [invoke](https://github.com/1upbyte/Devious-WinRM/wiki/2-%E2%80%90-Usage-Guide#invoke) command, usually **bypassing AV detection**. It's quick-and-easy way to covertly execute binaries without touching disk.

### Local token upgrader
Some commands, such as `Get-Service` or `qwinsta` will fail to execute via WinRM due to a permission error. Devious-WinRM leverages RunasCs for an effortless way to get around this limitation of WinRM. Simply prepending the desired command with [localexec](https://github.com/1upbyte/Devious-WinRM/wiki/2-%E2%80%90-Usage-Guide#localexec) will work.

## Installation
Check out the [Installation Guide](https://github.com/1upbyte/Devious-WinRM/wiki/Installation-Guide) for instructions.
TLDR: `uv tool install devious-winrm`

## Wiki
The [Usage Guide](https://github.com/1upbyte/Devious-WinRM/wiki/2-%E2%80%90-Usage-Guide) has extensive documentation on every single feature and command.

## Credits
- [Evil-WinRM](https://github.com/Hackplayers/evil-winrm)  - This goes without saying, but Evil-WinRM is an incredible tool. It was the primary inspiration for this project.
- [pypsrp](https://github.com/jborean93/pypsrp) - A tremendously well-featured library for Powershell Remote in Python. Super friendly developer as well!
- [evil-winrm-py](https://github.com/adityatelange/evil-winrm-py) - Aditya and I had the same idea at almost the exact same time. I would be remissed if I didn't mention his project as well.
- [RunasCs](https://github.com/antonioCoco/RunasCs) - Used for the local token upgrader. Super useful tool when doing work over WinRM.
