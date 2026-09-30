---
date: 2026-04-09
summary: Run tun2socks with an external proxy or local v2rayA Docker container, using systemd and policy routing to prevent routing loops.
---

# Run tun2socks as a systemd Service on Proxmox VM (Ubuntu 24.04, IPv4 + IPv6)

<!-- more -->

This post combines the original Ubuntu VM rehearsal with a later debugging session that fixed a routing loop when v2rayA ran in Docker on the same host.

There are two setups:

| Proxy location | How its outbound traffic avoids `tun0` |
| --- | --- |
| **Outside the host**, on another LAN machine | Bind tun2socks sockets to the primary NIC; the proxy also has a connected LAN route. |
| **Inside the host**, in a v2rayA Docker container | Give the container a stable bridge subnet and select a separate routing table for that subnet. |

Sections 2–6 describe the external proxy. For local v2rayA, follow section 7 and use its complete replacement unit. Here, “host” means the Linux machine running tun2socks, which may itself be a Proxmox VM.

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
- `<TUN2SOCKS_BIN>`: absolute path to `tun2socks` (for example `/usr/local/bin/tun2socks`)

Replace all angle-bracket placeholders before running commands or saving a unit. The local-proxy example keeps the tested Docker subnet `172.30.0.0/24`, bridge `br-v2raya`, and routing table `200`; adapt them consistently if they conflict with your network.

The official wiki is a good starting point, but this walkthrough adds some practical adjustments for stability on reboot and safer route handling.

------

## 1. Check Current Network State

These commands only inspect the OS, interfaces, routes, and forwarding setting:

```bash
cat /etc/os-release
ip addr show
ip route show
ip -6 route show
ip rule show
sysctl net.ipv4.ip_forward
```

In our rehearsal, the important facts were:

- Default route came from DHCP (`default via <LAN_GATEWAY_IP> dev <PRIMARY_IFACE> ... metric 100`)
- Docker bridge existed (`172.17.0.0/16`)
- `net.ipv4.ip_forward = 1`

------

## 2. Create TUN Device

For the external-proxy manual test, these commands create `tun0`, assign its IPv4 address, and bring the interface up:

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

## 3. External Proxy: Start tun2socks First, Then Route

Prefer this order:

1. Start `tun2socks`
2. Add route to `tun0`

This avoids a short blackhole window where traffic is already routed to `tun0` but no process is reading packets yet.

The proxy must already be reachable on another LAN machine. `--device` selects the TUN interface, `--proxy` selects the HTTP CONNECT endpoint, and `--interface` binds outbound proxy sockets to the physical NIC:

```bash
sudo <TUN2SOCKS_BIN> \
	--device tun0 \
	--proxy http://<PROXY_HOST>:<PROXY_PORT> \
	--interface <PRIMARY_IFACE>
```

Keep tun2socks running in that terminal. In a second terminal, add the preferred default route; the lower `metric 1` makes it preferred over the existing default:

```bash
sudo ip route add default via 198.18.0.1 dev tun0 metric 1
```

Important adjustment:

- Do not delete the original DHCP default route unless you really need to.
- Keeping the original DHCP route (`metric 100`) is more robust.

Why a loop does not happen in this external-proxy setup:

- `--interface <PRIMARY_IFACE>` forces outbound proxy sockets to use the physical NIC.
- Proxy server is on local subnet (`<LAN_SUBNET_CIDR>`), so it matches the specific connected route first.

```text
Host application → tun0 → tun2socks → physical NIC → LAN proxy → Internet
```

The proxy's own Internet connection is made on another machine. Moving that proxy into Docker on this host changes the routing problem: `--interface` controls tun2socks sockets, not the container's separate connections. See section 7.

After the manual test, remove only the route and device created above before starting the systemd service:

```bash
sudo ip route del default via 198.18.0.1 dev tun0 metric 1
# Stop the foreground tun2socks process with Ctrl+C in its terminal.
sudo ip link set dev tun0 down
sudo ip tuntap del mode tun dev tun0
```

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

## 6. External Proxy: Full systemd Unit (IPv4 + IPv6)

Create `/etc/systemd/system/tun2socks.service` with the following unit. It owns `tun0` and adds only the TUN defaults, leaving the physical defaults in place. For local v2rayA, use the alternative in section 7 instead.

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

ExecStart=<TUN2SOCKS_BIN> --device tun0 --proxy http://<PROXY_HOST>:<PROXY_PORT> --interface <PRIMARY_IFACE>
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

Apply the unit: `daemon-reload` rereads unit files, `enable --now` enables startup at boot and starts the service, and `status` inspects it. If the service is already running, use `sudo systemctl restart tun2socks` after reloading to apply edits.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tun2socks
sudo systemctl status tun2socks
```

The `-` prefix in some `ExecStartPre`/`ExecStopPost` lines means: ignore non-zero exit for that command.

These units install default routes in `ExecStartPre`, so startup or restart can briefly interrupt traffic before the daemon is ready. `ExecStopPost` removes the TUN routes and device when the service stops, including after startup failure.

------

## 7. Local Proxy: v2rayA in Docker Without a Routing Loop

### Why binding tun2socks alone is insufficient

With `--proxy http://127.0.0.1:10809`, tun2socks reaches a Docker-published v2rayA port. The proxy then opens its own connection to an upstream server. Without an exception, the host forwards that container traffic using the preferred default route through `tun0`:

```text
Host application → tun0 → tun2socks → localhost:10809 → v2rayA container
                          ↑                                  │
                          └──────── tun0 ← host routing ←────┘
```

That is the recursion: the proxy's outbound connection is fed back into the proxy. A working localhost listener does not prevent it, and changing only tun2socks' `--interface` cannot control v2rayA's sockets.

The fix is **source-based policy routing**: traffic from the dedicated v2rayA subnet uses table `200`, whose default points to the physical gateway. Ordinary host traffic continues to use the main table and `tun0`.

### Give v2rayA a stable Docker network

Use this `docker-compose.yaml`. It preserves the version and port mappings used during debugging:

```yaml
services:
  v2raya:
    image: mzz2017/v2raya:v2.5.7
    container_name: v2raya
    restart: always
    ports:
      - "2017:2017"
      - "10808-10810:10808-10810"
    environment:
      - V2RAYA_LOG_FILE=/tmp/v2raya.log
    volumes:
      - ./etc/v2raya:/etc/v2raya
      - /etc/localtime:/etc/localtime:ro
      - /lib/modules:/lib/modules:ro
    networks:
      - v2raya_direct

networks:
  v2raya_direct:
    name: v2raya_direct
    driver: bridge
    driver_opts:
      com.docker.network.bridge.name: br-v2raya
    ipam:
      config:
        - subnet: 172.30.0.0/24
          gateway: 172.30.0.1
```

The subnet and bridge name remain predictable after network recreation; the container's final IP octet may change. Docker supports both [Compose IPAM configuration](https://docs.docker.com/reference/compose-file/networks/#ipam) and an [explicit bridge name](https://docs.docker.com/engine/network/drivers/bridge/#options). Keep this network dedicated to v2rayA because every container on it receives the routing exemption. Use bridge networking for this recipe; `network_mode: host` would remove the source-subnet distinction.

These mappings publish TCP ports on all host interfaces. For host-only access, use `127.0.0.1:2017:2017` and `127.0.0.1:10808-10810:10808-10810` instead. The examples below assume v2rayA already has a working upstream and an HTTP CONNECT proxy listening on container port `10809`.

In the Compose directory, validate without starting anything:

```bash
docker compose config
```

For an existing installation, stop tun2socks before recreating the Docker network. The following interrupts both proxies; `down` removes this Compose project's containers and network but preserves the bind-mounted `./etc/v2raya` configuration. `up -d` recreates them in the background. For a fresh installation, only `up -d` is needed.

```bash
sudo systemctl stop tun2socks
docker compose down
docker compose up -d
```

Check the assigned address and bridge before installing the unit:

```bash
docker inspect -f \
  '{{range .NetworkSettings.Networks}}IP={{.IPAddress}} Gateway={{.Gateway}}{{end}}' \
  v2raya
ip link show dev br-v2raya
```

An example result is `IP=172.30.0.2 Gateway=172.30.0.1`. Use the actual container IP in later diagnostics. Docker forwarding must be enabled (`net.ipv4.ip_forward = 1`); its bridge networking normally supplies the forwarding and masquerading rules.

### Install the complete local-proxy unit

Reserve routing table `200` and rule priority `100` for this service. Inspect `ip rule show` and `ip route show table 200` first; an unused table may be reported as absent. The unit flushes **all routes in table 200**, so choose another unused table if it already belongs to a VPN or other service.

Replace `/etc/systemd/system/tun2socks.service` with this alternative. Substitute the same placeholders as before. The tested physical network used `wlp6s0`, LAN `192.168.101.0/24`, and gateway `192.168.101.1`.

```ini
[Unit]
Description=tun2socks with direct egress for local v2rayA (IPv4/IPv6)
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=root

# The Compose network must exist before its routes can be installed.
ExecStartPre=/usr/bin/ip link show dev br-v2raya

# v2rayA direct-egress routing; table 200 is dedicated to this service.
ExecStartPre=-/usr/bin/ip rule del priority 100 from 172.30.0.0/24 lookup 200
ExecStartPre=-/usr/bin/ip route flush table 200
ExecStartPre=/usr/bin/ip route add 172.30.0.0/24 dev br-v2raya table 200
ExecStartPre=/usr/bin/ip route add <LAN_SUBNET_CIDR> dev <PRIMARY_IFACE> table 200
ExecStartPre=/usr/bin/ip route add default via <LAN_GATEWAY_IP> dev <PRIMARY_IFACE> table 200
ExecStartPre=/usr/bin/ip rule add priority 100 from 172.30.0.0/24 lookup 200

# TUN setup; install the proxy's bypass before redirecting host traffic.
ExecStartPre=-/usr/bin/ip tuntap add mode tun dev tun0
ExecStartPre=/usr/bin/ip addr add 198.18.0.1/24 dev tun0
ExecStartPre=/usr/bin/ip -6 addr add fdfe::1/128 dev tun0
ExecStartPre=/usr/bin/ip link set dev tun0 up
ExecStartPre=/usr/bin/ip route add default via 198.18.0.1 dev tun0 metric 1
ExecStartPre=/usr/bin/ip -6 route add default dev tun0 metric 1

ExecStart=<TUN2SOCKS_BIN> --device tun0 --proxy http://127.0.0.1:10809 --interface <PRIMARY_IFACE>
Restart=on-failure
RestartSec=5
LimitNOFILE=1048576

# Remove host redirection before removing the proxy's bypass.
ExecStopPost=-/usr/bin/ip route del default via 198.18.0.1 dev tun0 metric 1
ExecStopPost=-/usr/bin/ip -6 route del default dev tun0 metric 1
ExecStopPost=-/usr/bin/ip rule del priority 100 from 172.30.0.0/24 lookup 200
ExecStopPost=-/usr/bin/ip route flush table 200
ExecStopPost=-/usr/bin/ip link set dev tun0 down
ExecStopPost=-/usr/bin/ip tuntap del mode tun dev tun0

[Install]
WantedBy=multi-user.target
```

`Requires=docker.service` starts Docker with this service, and `After=` orders startup after it. This does not create the Compose network or guarantee the proxy is ready: run Compose first and verify the listener. If the bridge is not ready at boot, the pre-start check fails and `Restart=on-failure` retries. After recreating the Docker network or restarting Docker, start/restart tun2socks to restore its custom routes.

The rule runs at priority `100`, after the standard `local` lookup at `0` but before `main` at `32766`. Thus matching container traffic can use the physical default even though the main table prefers `tun0`. See the [ip-rule manual](https://www.man7.org/linux/man-pages/man8/ip-rule.8.html).

**Do not omit the Docker-subnet route:**

```text
172.30.0.0/24 dev br-v2raya table 200
```

In the debugging session, a unit containing only the LAN route and physical default still failed. Restoring this bridge route made both the direct HTTP-proxy test and the full tun2socks test succeed.

Table `200` needs its own connected routes. For lookups that reach this table, its default already matches; Linux does not then consult `main` for a more specific Docker route. The bridge entry keeps destinations in `172.30.0.0/24` on `br-v2raya`. Destinations owned by the host itself are still handled by the earlier `local` rule.

Reload the unit, enable boot startup, and restart it to rebuild the routes. Restarting briefly interrupts proxied traffic:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tun2socks
sudo systemctl restart tun2socks
```

### Verify both routing paths

These are read-only checks:

```bash
ip rule show
ip route show table 200
ip route get 1.1.1.1
ip route get 1.1.1.1 from 172.30.0.2 iif br-v2raya
```

With the tested physical network and container IP, the relevant output is:

```text
# Rules
0:      from all lookup local
100:    from 172.30.0.0/24 lookup 200
32766:  from all lookup main
32767:  from all lookup default

# Table 200
default via 192.168.101.1 dev wlp6s0
172.30.0.0/24 dev br-v2raya scope link
192.168.101.0/24 dev wlp6s0 scope link

# Ordinary host lookup
1.1.1.1 via 198.18.0.1 dev tun0

# Forwarded container lookup
1.1.1.1 from 172.30.0.2 via 192.168.101.1 dev wlp6s0 table 200
```

Use `iif br-v2raya` to simulate a packet arriving from Docker. Without `iif`, `ip route get` models locally generated traffic; a container source address not assigned to the host can produce a misleading `Network is unreachable`. This distinction is documented in [ip-route](https://www.man7.org/linux/man-pages/man8/ip-route.8.html).

Then test an IP-literal URL to avoid DNS as a variable. Both commands force IPv4 (`-4`), show connection details (`-v`), and stop after ten seconds (`--max-time 10`). `--proxy ''` disables proxy environment variables for the full TUN test; the second command explicitly selects v2rayA with `--proxy`, while `--noproxy ''` prevents environment exclusions from bypassing it.

```bash
# Full path: application → tun0 → tun2socks → v2rayA.
curl -4 -v --max-time 10 --proxy '' https://1.1.1.1/cdn-cgi/trace

# Connect directly to v2rayA's HTTP proxy, bypassing tun2socks.
curl -4 -v --max-time 10 --noproxy '' \
  --proxy http://127.0.0.1:10809 https://1.1.1.1/cdn-cgi/trace
```

| Result | Next area to inspect |
| --- | --- |
| Direct proxy works; full TUN test fails | tun2socks, its proxy endpoint, and the TUN routes |
| Both fail | v2rayA/upstream health, all three table-200 routes, Docker forwarding, and `rp_filter` |
| Both work | The tested TCP paths work; repeat after restart and reboot |

The corrected path is:

```text
Host application → tun0 → tun2socks → 127.0.0.1:10809
                                           │ Docker port forwarding
                                           ▼
                                    v2rayA (172.30.0.x)
                                           │ source rule, priority 100
                                           ▼
                                       table 200
                                           │ physical gateway
                                           ▼
                                    primary NIC → Internet
```

### IPv6 and UDP scope

This Compose network has no IPv6 subnet configured, so the container's upstream egress uses IPv4 and the bypass is an IPv4 rule. Host IPv6 TCP traffic can still enter `tun0` and reach an IPv6 destination through HTTP CONNECT over the IPv4 proxy connection, provided the proxy supports that destination. If you enable IPv6 egress for the container, add the corresponding IPv6 policy rule and connected/default routes before redirecting it through TUN.

HTTP proxy mode in tun2socks has [no UDP support](https://github.com/xjasonlyu/tun2socks/wiki/Proxy-Models#udp-support-table). SOCKS5 supports UDP, but switching to `socks5://127.0.0.1:10808` requires verifying the proxy's UDP relay and Docker UDP reachability; the Compose mappings above publish TCP only. The routing-loop fix does not by itself provide UDP transport or DNS leak protection.

------

## 8. Verify After Start and After Reboot

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

For local v2rayA, also repeat the rule/table checks and both curl tests in section 7. An active service alone does not prove that its upstream proxy works.

------

## 9. FAQ From the Rehearsal

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

Both unit alternatives add an IPv6 TUN address and default route. Successful IPv6 TCP connections also require proxy support for the destination; HTTP mode does not carry UDP.

### Q9: Why use `fdfe::1/128` instead of `/64`?

For a point-to-point virtual TUN endpoint, `/128` is a valid and tight scope.

------

## 10. What This Post Does Not Cover Yet

This post focuses on interface, routing, and service lifecycle.

DNS leak handling is a separate topic and should be configured explicitly depending on your DNS/proxy model.

------

## References

- [tun2socks examples and local-proxy loop warning](https://github.com/xjasonlyu/tun2socks/wiki/Examples)
- [tun2socks DNS configuration](https://github.com/xjasonlyu/tun2socks/wiki/DNS-Configuration)
- [tun2socks interfaces and routes](https://github.com/xjasonlyu/tun2socks/wiki/Interface-and-Routes)
- [tun2socks proxy models and UDP support](https://github.com/xjasonlyu/tun2socks/wiki/Proxy-Models)
- [Linux policy routing: ip-rule](https://www.man7.org/linux/man-pages/man8/ip-rule.8.html)
- [Linux route lookup: ip-route](https://www.man7.org/linux/man-pages/man8/ip-route.8.html)
- [Docker bridge networking](https://docs.docker.com/engine/network/drivers/bridge/)
- [Docker Compose network configuration](https://docs.docker.com/reference/compose-file/networks/)
