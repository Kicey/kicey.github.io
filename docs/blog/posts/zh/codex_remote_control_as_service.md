---
date: 2026-11-15
summary: 用 systemd 在开机时启动 Codex 远程控制，并在使用 tun2socks 代理时添加服务依赖。
---

# 将 Codex 远程控制配置为 systemd 服务

配置 systemd 服务后，Codex 远程控制会随 Linux 主机开机启动，无需先登录主机。

<!-- more -->

## 创建服务单元

以运行服务的 Linux 用户执行 `codex login`，登录 ChatGPT 账号。如果主机没有图形界面，且你的账号或工作区允许设备码登录，可以用 `codex login --device-auth` 发起登录。
[Codex 身份验证](https://learn.chatgpt.com/docs/auth?surface=cli#login-on-headless-devices)

将以下配置保存为 `/etc/systemd/system/codex-remote-control.service`。按实际环境替换用户名、用户组、家目录和 `codex` 的绝对路径。

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

`start` 启动后台守护进程后退出。`RemainAfterExit=yes` 让服务单元保持活跃，systemd 停止服务时会执行 `ExecStop=`。
[Codex CLI 参考](https://learn.chatgpt.com/docs/cli/reference#codex-remote-control) · [systemd.service 手册](https://www.freedesktop.org/software/systemd/man/253/systemd.service.html)

服务在 `network-online.target` 就绪后启动。该目标何时就绪取决于网络管理器的 wait-online 配置。
[systemd 网络启动顺序](https://systemd.io/NETWORK_ONLINE/)

## 使用 tun2socks 代理时

如果主机通过 tun2socks 转发 Codex 流量，将 `[Unit]` 中的 `Wants=` 和 `After=` 两行替换为以下配置。`Requires=` 会一并启动代理服务，`After=` 让 Codex 在代理服务之后启动。tun2socks 服务本身已配置为等待网络就绪。
[tun2socks 配置指南](../tun2socks_as_service.md)

```ini
Requires=tun2socks.service
After=tun2socks.service
```

## 启用并验证

`daemon-reload` 重新加载单元文件。`enable --now` 设置开机自启，并立即启动服务。`status` 查看单元状态。

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now codex-remote-control.service
systemctl status codex-remote-control.service
```

启动命令成功后，状态应显示 `active (exited)`。用已配对的客户端连接主机，确认远程控制可用。如需配对码，以运行服务的用户执行 `codex remote-control pair`。
[Codex CLI 参考](https://learn.chatgpt.com/docs/cli/reference#codex-remote-control)
