# Fix the Electron Fiddle issue about user namespace privileges on ubuntu 24.04

If you install Electron Fiddle on Ubuntu 24.04. Then want to run a Fiddle, you will get errors like 
```
The SUID sandbox helper binary was found, but is not configured correctly. Rather than run without sandboxing I'm aborting now. You need to make sure that /home/aadcg/.config/Electron Fiddle/electron-bin/current/chrome-sandbox is owned by root and has mode 4755.
```
or 

```
LaunchProcess: failed to execvp:
/home/kicey/.config/Electron
[62772:0524/190051.235193:FATAL:zygote_host_impl_linux.cc(211)] Check failed: . : Invalid argument (22) 
```

This is because Ubuntu has changed the Ubuntu 24.04 kernel so that programs like electron are not allowed to create a new user namespace unless they are given an AppArmor profile that contains the userns permission.

To fix this, you need to grant the privilege to the executable by create an apparmor profile. Execute the following commands (maybe `sudo` needed):

```bash
echo 'abi <abi/4.0>,
include <tunables/global>
profile fiddle-electron /home/'$USER'/.config/Electron\ Fiddle/electron-bin/current/electron flags=(unconfined) {
    userns,
}' > /etc/apparmor.d/fiddle-electron
```

```bash
apparmor_parser -r /etc/apparmor.d/fiddle-electron
```

```bash
systemctl reload apparmor
```

For mote information, you can refer to the [electron/fiddle SIGTRAP error on Ubuntu #1598](https://github.com/electron/fiddle/issues/1598)