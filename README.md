# Devious-WinRM

A Pentester's PowerShell Client.

![The help screen for Devious-WinRM, showing a variety of flags and options.](https://raw.githubusercontent.com/1upbyte/Devious-WinRM/refs/heads/main/assets/help-screen.png "Help screen")


## Ruby Branch Status
This branch is a Ruby reimplementation backed by the `winrm` gem. The current
focus is CLI compatibility and Kerberos connection setup; the richer interactive
commands from the Python implementation have not been ported yet.

## Installation
Install the gem locally from this checkout:

```sh
gem build devious-winrm.gemspec
gem install ./devious-winrm-*.gem
```

The `dwrm` and `devious-winrm` executables are provided by the gem.

## Usage
Kerberos is currently required:

```sh
dwrm -u C.Neri -p 'Zer0the0ne' -k dc01.vintage.htb
```

Kerberos pass-the-hash is also supported with an NT hash:

```sh
dwrm -u C.Neri -H CC5156663CD522D5FA1931F6684AF639 -k dc01.vintage.htb
```

When username/password credentials are supplied on non-Windows systems,
Devious-WinRM writes a temporary Kerberos config, runs `kinit`, and points the
`winrm` gem at the resulting credential cache. When an NT hash is supplied,
Devious-WinRM uses impacket's `getTGT.py` to request a TGT and points the
`winrm` gem at the resulting credential cache.

Supported flags:

```text
Usage: dwrm [options] HOST

Options:
    -u, --username USER              Username used for authentication.
    -p, --password PASS              Password used for authentication. Cannot be used with an NTLM hash.
    -P, --port PORT                  Port of remote host. Defaults to 5985.
    -k, --kerberos                   Use Kerberos authentication.
    -H, --hash HASH                  NTLM hash. Accepts LM:NTLM or NTLM.
        --domain-controller, --dc DC FQDN for the domain controller.
    -v, --version                    Print version and exit.
    -h, --help                       Print help and exit.
```

## Wiki
The [Usage Guide](https://github.com/1upbyte/Devious-WinRM/wiki/2-%E2%80%90-Usage-Guide) has extensive documentation on every single feature and command.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=1upbyte/devious-winrm&type=date&legend=top-left)](https://www.star-history.com/#1upbyte/devious-winrm&type=date&legend=top-left)

## Credits
- [Evil-WinRM](https://github.com/Hackplayers/evil-winrm)  - This goes without saying, but Evil-WinRM is an incredible tool. It was the primary inspiration for this project.
- [pypsrp](https://github.com/jborean93/pypsrp) - A tremendously well-featured library for Powershell Remote in Python. Super friendly developer as well!
- [evil-winrm-py](https://github.com/adityatelange/evil-winrm-py) - Aditya and I had the same idea at almost the exact same time. I would be remissed if I didn't mention his project as well.
- [RunasCs](https://github.com/antonioCoco/RunasCs) - Used for the local token upgrader. Super useful tool when doing work over WinRM.
