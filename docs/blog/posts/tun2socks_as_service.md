---
date: 2026-04-09
summary: A practical tun2socks setup on an Ubuntu Proxmox VM, including safe routing, systemd persistence, IPv6 support, and troubleshooting notes from a full rehearsal.
---

# Run tun2socks as a systemd Service on Proxmox VM (Ubuntu 24.04, IPv4 + IPv6)

<!-- more -->

This post is a cleaned-up tutorial from a full command rehearsal.

Environment used in rehearsal:

- VM OS: Ubuntu 24.04.3 LTS
- Primary NIC: `<PRIMARY_IFACE>` (gateway `<LAN_GATEWAY_IP>`)
- Proxy endpoint: `http://<PROXY_HOST>:<PROXY_PORT>`
- Goal: route traffic through `tun2socks`, then make it persistent with `systemd`

Placeholders used in this post:

- `<PRIMARY_IFACE>`: your outbound NIC (for example `eth0`)
- `<LAN_GATEWAY_IP>`: your LAN gateway (for example `192.168.1.1`)
- `<PROXY_HOST>` / `<PROXY_PORT>`: your proxy endpoint
- `<LAN_SUBNET_CIDR>`: your LAN subnet (for example `192.168.1.0/24`)
- `<TUN2SOCKS_BIN>`: absolute path to `tun2socks` (or just `tun2socks` if in PATH)

<!-- more -->

The official wiki is a good starting point, but this walkthrough adds some practical adjustments for stability on reboot and safer route handling.

------

## 1. Check Current Network State

Run these first:

```bash
cat /etc/os-release
ip addr show
ip route show
sysctl net.ipv4.ip_forward
```

In our rehearsal, the important facts were:

- Default route came from DHCP (`default via <LAN_GATEWAY_IP> dev <PRIMARY_IFACE> ... metric 100`)
- Docker bridge existed (`172.17.0.0/16`)
- `net.ipv4.ip_forward = 1`

------

## 2. Create TUN Device

```bash
sudo ip tuntap add mode tun dev tun0
sudo ip addr add 198.18.0.1/24 dev tun0
sudo ip link set dev tun0 up
```

Verification:

```bash
ip link show dev tun0
ip addr show dev tun0
ip tuntap show
```

Notes:

- `198.18.0.0/15` is the common wiki convention (RFC 2544 benchmark block).
- `198.18.0.1/24` also works fine in this setup.
- Do not omit CIDR mask when assigning an address.

------

## 3. Start tun2socks First, Then Route

Prefer this order:

1. Start `tun2socks`
2. Add route to `tun0`

This avoids a short blackhole window where traffic is already routed to `tun0` but no process is reading packets yet.

Example start command:

```bash
sudo <TUN2SOCKS_BIN> \
	-device tun0 \
	-proxy http://<PROXY_HOST>:<PROXY_PORT> \
	-interface <PRIMARY_IFACE>
```

Then add preferred default route:

```bash
sudo ip route add default via 198.18.0.1 dev tun0 metric 1
```

Important adjustment:

- Do not delete the original DHCP default route unless you really need to.
- Keeping the original DHCP route (`metric 100`) is more robust.

Why loop does not happen here:

- `-interface <PRIMARY_IFACE>` forces outbound proxy sockets to use the physical NIC.
- Proxy server is on local subnet (`<LAN_SUBNET_CIDR>`), so it matches the specific connected route first.

------

## 4. rp_filter: Usually No Change Needed

Check:

```bash
sysctl net.ipv4.conf.all.rp_filter
sysctl net.ipv4.conf.<PRIMARY_IFACE>.rp_filter
```

In our case both were `2` (loose mode), which is usually enough.

So we did not need:

```bash
sysctl net.ipv4.conf.all.rp_filter=0
sysctl net.ipv4.conf.<PRIMARY_IFACE>.rp_filter=0
```

Use `0` only if you have a confirmed routing issue that requires it.

------

## 5. Why Manual IP/Route Config Disappears After Reboot

Commands like `ip route add ...` and `ip tuntap add ...` modify runtime kernel state.

That state is not persisted automatically across reboot.

So even if `tun2socks` is enabled as a service, the TUN device and custom routes will disappear unless you recreate them at service startup.

------

## 6. Full systemd Unit (Dual-Stack IPv4 + IPv6)

Create `/etc/systemd/system/tun2socks.service`:

```ini
[Unit]
Description=tun2socks transparent proxy daemon (Dual-Stack IPv4/IPv6)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root

# Startup phase
ExecStartPre=-/usr/bin/ip tuntap add mode tun dev tun0
ExecStartPre=/usr/bin/ip addr add 198.18.0.1/24 dev tun0
ExecStartPre=/usr/bin/ip -6 addr add fdfe::1/128 dev tun0
ExecStartPre=/usr/bin/ip link set dev tun0 up
ExecStartPre=/usr/bin/ip route add default via 198.18.0.1 dev tun0 metric 1
ExecStartPre=/usr/bin/ip -6 route add default dev tun0 metric 1

ExecStart=<TUN2SOCKS_BIN> -device tun0 -proxy http://<PROXY_HOST>:<PROXY_PORT> -interface <PRIMARY_IFACE>
Restart=on-failure
RestartSec=5
LimitNOFILE=1048576

# Teardown phase
ExecStopPost=-/usr/bin/ip route del default via 198.18.0.1 dev tun0 metric 1
ExecStopPost=-/usr/bin/ip -6 route del default dev tun0 metric 1
ExecStopPost=-/usr/bin/ip link set dev tun0 down
ExecStopPost=-/usr/bin/ip tuntap del mode tun dev tun0

[Install]
WantedBy=multi-user.target
```

Apply:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tun2socks
sudo systemctl status tun2socks
```

The `-` prefix in some `ExecStartPre`/`ExecStopPost` lines means: ignore non-zero exit for that command.

------

## 7. Verify After Start and After Reboot

```bash
ip addr show dev tun0
ip route show
ip -6 route show
systemctl is-active tun2socks
journalctl -u tun2socks -n 50 --no-pager
```

Expected:

- `tun0` exists and is `UP`
- IPv4 default route prefers `tun0` with low metric
- IPv6 default route goes to `tun0`
- service is `active`

------

## 8. FAQ From the Rehearsal

### Q1: Is `/15` required for `198.18.0.1`?

No. `/15` is a convention from the wiki examples. `/24` works too.

### Q2: Is `198.18.0.0/15` hardcoded in tun2socks?

No. That subnet choice is in your host routing design, not in tun2socks internals.

### Q3: Can I start tun2socks before adding default route to tun0?

Yes. That is the recommended order.

### Q4: Do I need `sudo` for tun2socks?

Usually yes for this mode, because it needs network capabilities for TUN and interface binding.

### Q5: Why did `sudo: tun2socks: command not found` happen?

Because `sudo` uses a restricted PATH (`secure_path`). Use absolute path or place binary in a directory visible to `sudo`.

### Q6: Is tun2socks foreground by default?

Yes. `Ctrl+C` is a normal way to stop it during manual tests.

### Q7: What is `network-online.target`?

A systemd synchronization target that means network configuration is considered online enough for dependent services.

Check with:

```bash
systemctl is-active network-online.target
systemctl status network-online.target
```

### Q8: Does this proxy IPv6 too?

Only if you add IPv6 TUN address and IPv6 default route. The unit file above does that.

### Q9: Why use `fdfe::1/128` instead of `/64`?

For a point-to-point virtual TUN endpoint, `/128` is a valid and tight scope.

------

## 9. What This Post Does Not Cover Yet

This post focuses on interface, routing, and service lifecycle.

DNS leak handling is a separate topic and should be configured explicitly depending on your DNS/proxy model.

------

## References

- https://github.com/xjasonlyu/tun2socks/wiki/Examples
- https://github.com/xjasonlyu/tun2socks/wiki/DNS-Configuration
- https://github.com/xjasonlyu/tun2socks/wiki/Interface-and-Routes
