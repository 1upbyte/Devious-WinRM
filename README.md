# Devious WinRM

A Pentester's (work-in-progress) Powershell Client.

## Description / Purpose
This tool allows one to access servers running WinRM or Powershell Remoting, with additional tools for capture the flag / pentesting. I created this project to fix a few grievances I have with existing tools (such as the amazing Evil-WinRM) and to contribute some to the open-source hacking community.

Technically, Devious WinRM is not directly based on WinRM. It is instead built on the Powershell Remoting Protocol, which in turn uses WinRM. PSRP was chosen as it seems to require less user permissions than WinRM, at least in a rudementary Active Directory environment.

## Features / Planned
- [x] Connect to WinRM / PSRP hosts
- [ ] Make it pretty
- [ ] File upload/download
- [ ] In-Memory .NET/Powershell loader
- [ ] No-config Kerberos auth
- [ ] Pass the hash support
- [ ] Local logon token upgrader via RunasCs 
- [ ] Maybe: Full TTY upgrader via ConPtyShell

## Credits
- [Evil-WinRM](https://github.com/Hackplayers/evil-winrm)  - This goes without saying, but Evil-WinRM is an incredible tool. It was the primary inspiration for this project.
- [pypsrp](https://github.com/jborean93/pypsrp) - A tremendously well-featured library for Powershell Remote in Python. Super friendly developer as well!