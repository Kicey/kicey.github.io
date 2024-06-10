# linux wifi 消失（MediaTek 7921e）

## 问题描述

这个问题出现过两次，都是在使用中途，wifi 断开，关闭重启 wifi 明显卡顿，且不能获取到 wifi 列表，重启之后 wifi 从状态栏中消失。

## 获取日志

syslog 相关日志如下：

```bash
mt7921e 0000:0c:00.0: Timeout for driver own
mt7921e 0000:0c:00.0: driver own failed
```

dmesg 中并无特殊日志记录。

## wifi 驱动问题

Linux 上大部分的硬件问题一般都是由驱动冲突，失效导致的。

使用 `lspci` 查看 pci 接口的硬件信息，其中 `Network Manager` 就是 Wifi 的设备。

我的（主板微星 B650 Pro-A）结果是：

```
Network controller: MEDIATEK Corp. Device 0616
```

使用 `sudo lshw` 查看 wifi 驱动信息。

我的结果如下：

```
description: Wireless interface
product: MEDIATEK Corp.
vendor: MEDIATEK Corp.
physical id: 0
bus info: pci@0000:0c:00.0
logical name: wlp12s0
erial: ac:50:de:60:15:7d
width: 64 bits
clock: 33MHz
capabilities: pciexpress msi pm bus_master cap_list ethernet physical wireless
configuration: broadcast=yes driver=mt7921e driverversion=5.15.0-56-generic firmware=____000000-20220322164011 ip=192.168.10.222 latency=0 link=yes multicast=yes wireless=IEEE 802.11
resources: iomemory:fc0-fbf irq:121 memory:fcf0300000-fcf03fffff memory:ec900000-ec907fff
```

可以看到使用的是 mt7921e 的驱动，版本即是当前的 linux 内核版本。如果是缺少驱动的同学直接重新安装网络模块即可，无需专门的驱动。

## 驱动/固件问题

在经过一番搜索之后，以日志中的 `mt7921e driver own failed` 为关键字找到 github 上的一个 issue：

https://github.com/openwrt/mt76/issues/681

相关的修改提交如下：

[kernel/git/torvalds/linux.git - Linux kernel source tree](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/drivers/net/wireless/mediatek/mt76?id=fa3fbe64037839f448dc569212bafc5a495d8219)

代码修改内容如下：

![img](https://blog.kicey.site/content/images/2023/04/image.png)

以多次重试的方式解决偶发的驱动获取失败问题（应该也是没有解决驱动获取失败的根本问题，只是以重试的方式补救，笑）

在浏览 linux 内核代码之后，发现该修改存在的最低正式的内核版本为 v6.0，而 ubuntu 当前最新版本 22.04.2 默认使用了 v5.19 这个版本。再等几个月等 ubuntu 官方更新内核版本或者手动升级一下内核版本即可。

下面也提供一个临时的解决方案。

## 重置 bios

到目前为止看不出任何问题，然后查询到一些同学的解决办法：在双系统下切换到 Windows 下，使用快捷键关闭飞行模式，然后切回 Ubuntu 系统即可。

那么我开始了合理的猜测：

Ubuntu 在某种情况下触发了对 bios 的设置，关闭了主板上的 wifi 模块，于是我进入 bios 设置中发现 wifi 处于 enable 并没有被关闭。

继续猜测，在之前修改神舟笔记本的功耗墙的时候，曾经通过刷 bios 固件的方式启用过隐藏设置，bios 的代码里对隐藏设置的处理并非是屏蔽并采用默认值，而是最简单的屏蔽设置项而已，猜测可能是 ubuntu 关闭了某个隐藏的设置项。

基于网上的这一个处理方法和两层猜测，我取下了 bios 电池重置 bios 固件，再次开机，wifi 恢复！

------

以上操作在 ubuntu 22.04，微星 B650 Pro-A 主板是进行。由于我对硬件和系统的知识并不深入，以上的解释可能存在错误，望大佬赐教。

------

在重置 bios 之后，之前使用 mokutil 通过 secure boot 信任的模块需要重新信任一次，也就是再录入一次公钥。

------

ubuntu 临时解决方式（重置 BIOS 只是暂时的修复）。

------

虽然微星的官网有一个 v13 版本的 BIOS 驱动描述为 Fix Wifi lan can not work properly，不过这里的 wifi 问题不是上面讨论的问题。

![img](https://blog.kicey.site/content/images/2023/01/image.png)

结束。