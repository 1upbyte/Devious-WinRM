# Devious-WinRM

A Pentester's Powershell Client.

![The help screen for Devious-WinRM, showing a variety of flags and options.](https://raw.githubusercontent.com/1upbyte/Devious-WinRM/refs/heads/main/assets/help-screen.png "Help screen")

## Description / Purpose
This tool allows one to access servers running WinRM or Powershell Remoting, with additional tools for capture the flag / pentesting. I created this project to fix a few grievances I have with existing tools (such as the amazing Evil-WinRM) and to contribute to the open-source hacking community.

Under the hood, Devious-WinRM is not directly based on WinRM. It is instead built on the PowerShell Remoting Protocol, which in turn uses WinRM. PSRP was chosen as it seems to require less user permissions than WinRM, at least in a rudementary Active Directory environment.

## Features / Planned
- [x] No-config Kerberos auth
- [x] Make it pretty
- [x] Pass the hash support
- [x] Pass the ticket support
- [x] File upload/download
- [x] Syntax highlighting
- [x] Ctrl+C command interupt
- [x] Remote path completion
- [x] In-Memory .NET loader
- [x] Local logon token upgrader via RunasCs 
- [ ] In-Memory Powershell loader
- [ ] Certificate auth
- [ ] SSL auth
- [ ] Logging


## Installation
0 - Install Kerberos (Linux only)

```bash
sudo apt install gcc python3-dev libkrb5-dev krb5-pkinit
```

1 - Install Devious-WinRM

```bash
uv tool install devious-winrm
```
or
```bash
pipx install devious-winrm
```


Sample usage:
```ps1
dwrm ws01.example.com -u 1upbyte -p supersecret123 -k --dc dc01.example.com
```

Check out the [Installation Guide](https://github.com/1upbyte/Devious-WinRM/wiki/Installation-Guide) for more technical information along with help for other distros.

## Credits
- [Evil-WinRM](https://github.com/Hackplayers/evil-winrm)  - This goes without saying, but Evil-WinRM is an incredible tool. It was the primary inspiration for this project.
- [pypsrp](https://github.com/jborean93/pypsrp) - A tremendously well-featured library for Powershell Remote in Python. Super friendly developer as well!
- [evil-winrm-py](https://github.com/adityatelange/evil-winrm-py) - Aditya and I had the same idea at almost the exact same time. I would be remissed if I didn't mention his project as well.
- [RunasCs](https://github.com/antonioCoco/RunasCs) - Used for the local token upgrader. Super useful tool when doing work over WinRM.