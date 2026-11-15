---
date: 2026-11-15
summary: Start Codex Remote Control at boot with systemd, with an optional tun2socks dependency for hosts that use a proxy.
---

# Run Codex Remote Control as a systemd Service

A systemd service can start Codex Remote Control at boot, before you log in to the Linux host.

<!-- more -->

## Create the unit

Run `codex login` as the Linux user who will run the service and sign in with your ChatGPT account. On a headless host, `codex login --device-auth` starts the device-code flow if your account or workspace allows it. [Codex authentication](https://learn.chatgpt.com/docs/auth?surface=cli#login-on-headless-devices)

Save this unit as `/etc/systemd/system/codex-remote-control.service`. Adjust the user, group, home directory, and absolute path to `codex` for your host.

```ini
[Unit]
Description=Codex Remote Control
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=kicey
Group=kicey
Environment=HOME=/home/kicey
WorkingDirectory=/home/kicey
ExecStart=/home/kicey/.local/bin/codex remote-control start
ExecStop=/home/kicey/.local/bin/codex remote-control stop
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

`start` launches the background daemon and exits. `RemainAfterExit=yes` keeps the unit active so systemd can run `ExecStop=` when the service stops. [Codex CLI reference](https://learn.chatgpt.com/docs/cli/reference#codex-remote-control) · [systemd.service](https://www.freedesktop.org/software/systemd/man/253/systemd.service.html)

Startup waits for `network-online.target`, whose timing depends on the network manager’s wait-online configuration. [systemd network ordering](https://systemd.io/NETWORK_ONLINE/)

## If the host uses tun2socks

If your host routes Codex traffic through tun2socks, replace the `Wants=` and `After=` lines with these. `Requires=` pulls in the proxy service, and `After=` orders Codex after it. The tun2socks unit already waits for the network. [tun2socks setup](tun2socks_as_service.md)

```ini
Requires=tun2socks.service
After=tun2socks.service
```

## Enable and check

`daemon-reload` rereads unit files. `enable --now` enables boot startup and starts the service immediately. `status` shows the unit state.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now codex-remote-control.service
systemctl status codex-remote-control.service
```

Expect `active (exited)` after the start command succeeds. To verify Remote Control, connect from a paired client. If you need a pairing code, run `codex remote-control pair` as the service user. [Codex CLI reference](https://learn.chatgpt.com/docs/cli/reference#codex-remote-control)
