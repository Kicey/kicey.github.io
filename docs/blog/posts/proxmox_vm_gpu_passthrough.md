---
date: 2026-04-06
summary: Step-by-step AMD + NVIDIA GPU passthrough setup on Proxmox, including BIOS, IOMMU, VFIO binding, and VM PCI attachment checks.
---

# Proxmox GPU Passthrough Tutorial (AMD Ryzen 9 7950X + NVIDIA RTX 5060 Ti)

<!-- more -->

This post is a cleaned-up tutorial from a real troubleshooting session. The target setup is:

- Host: Proxmox VE on AMD platform
- CPU: Ryzen 9 7950X (with integrated AMD Raphael graphics)
- Motherboard: MSI PRO B650M-A WIFI
- Discrete GPU to passthrough: NVIDIA GeForce RTX 5060 Ti
- Host display stays on the Ryzen iGPU, while the NVIDIA card is dedicated to the VM

If you are on a similar AM5 + NVIDIA setup, this walkthrough should map very closely.

------

## 1. What Success Looks Like

Before details, here is the expected end state:

1. BIOS has SVM and IOMMU enabled.
2. Kernel boots with `amd_iommu=on iommu=pt`.
3. IOMMU groups exist under `/sys/kernel/iommu_groups/`.
4. NVIDIA GPU functions are bound to `vfio-pci` on the host.
5. VM is created with `OVMF (UEFI)` + `q35`, and GPU is attached as PCI passthrough.

------

## 2. BIOS Configuration (MSI Click BIOS 5)

### Step 1: Enter Advanced BIOS

Enter BIOS (usually `Delete` at boot), then switch to Advanced Mode.

![img01_msi_bios_advanced_entry](images/proxmox_vm_gpu_passthrough/2026-04-06T10:50:01.783Z-image.png)

### Step 2: Navigate to AMD CBS

Go to:

- `OC` -> `Advanced CPU Configuration` -> `AMD CBS`

![img02_oc_menu_navigation](images/proxmox_vm_gpu_passthrough/2026-04-06T10:50:45.146Z-image.png)

### Step 3: Enable Virtualization Features

Inside AMD CBS, set:

- `SVM Enable` -> `Enabled`
- `IOMMU` -> `Enabled`

Use explicit `Enabled` instead of `Auto` for passthrough reliability.

![img03_amd_cbs_cpu_options](images/proxmox_vm_gpu_passthrough/2026-04-06T10:52:07.465Z-image.png)

### Step 4: Optional Stability Tweak

Optional on Ryzen hosts used as servers:

- `Global C-state Control` -> `Disabled`

Other options like `Pre-boot DMA Protection` and `PCIe ARI Support` can remain `Auto` unless you have a specific need.

![img04_amd_cbs_advanced_options.1](images/proxmox_vm_gpu_passthrough/2026-04-06T10:56:01.980Z-image.png)
![img04_amd_cbs_advanced_options.2](images/proxmox_vm_gpu_passthrough/2026-04-06T10:52:50.040Z-image.png)

### Step 5: Confirm Boot Mode

In `Settings` -> `Boot`, confirm UEFI boot mode.

- `Boot mode select` should be `UEFI`

![img05_boot_mode_uefi](images/proxmox_vm_gpu_passthrough/2026-04-06T10:48:52.865Z-image.png)

Save and reboot (`F10`).

------

## 3. Verify and Enable IOMMU in Proxmox

### Step 6: First Check in Host Shell

```bash
dmesg | grep -e DMAR -e IOMMU
```

On AMD, you may initially see detection lines such as:

```text
AMD-Vi: IOMMU performance counters supported
Detected AMD IOMMU #0
```

This confirms hardware is visible, but we still need kernel flags.

### Step 7: Add Kernel Parameters (GRUB)

Check current cmdline:

```bash
cat /proc/cmdline
```

In this session it showed `root=/dev/mapper/pve-root`, which indicates GRUB on LVM.

Edit:

```bash
nano /etc/default/grub
```

Set:

```bash
GRUB_CMDLINE_LINUX_DEFAULT="quiet amd_iommu=on iommu=pt"
```

Apply and reboot:

```bash
update-grub
reboot
```

After reboot, verify:

```bash
cat /proc/cmdline
```

You should now see `amd_iommu=on iommu=pt`.

### Step 8: Verify IOMMU Groups Exist

Quick check:

```bash
find /sys/kernel/iommu_groups/ -maxdepth 0
```

Better check (shows actual group entries):

```bash
find /sys/kernel/iommu_groups/ -type l | head
```

If `/sys/kernel/iommu_groups/` exists and contains entries, IOMMU is active.

------

## 4. Load VFIO Modules at Boot

Historically people edited `/etc/modules`, but on systemd-based systems the cleaner way is a dedicated file in `/etc/modules-load.d/`.

Create:

```bash
nano /etc/modules-load.d/vfio.conf
```

Add:

```text
vfio
vfio_iommu_type1
vfio_pci
vfio_virqfd
```

Update initramfs:

```bash
update-initramfs -u -k all
```

If you see:

```text
No /etc/kernel/proxmox-boot-uuids found, skipping ESP sync.
```

that is normal for a GRUB/LVM layout.

Reboot:

```bash
reboot
```

------

## 5. Bind the NVIDIA GPU to vfio-pci

### Step 9: Identify GPU IDs

```bash
lspci -nnk | grep -A 3 "VGA"
```

In this setup:

- NVIDIA GPU: `01:00.0` -> `[10de:2d04]`
- NVIDIA audio: `01:00.1` -> `[10de:22eb]`
- Host iGPU (keep for Proxmox): AMD Raphael `11:00.0` (`amdgpu`)

### Step 10: Configure vfio-pci IDs

Create:

```bash
nano /etc/modprobe.d/vfio.conf
```

Add:

```text
options vfio-pci ids=10de:2d04,10de:22eb disable_vga=1
```

### Step 11: Blacklist Host NVIDIA Drivers

Create:

```bash
nano /etc/modprobe.d/blacklist.conf
```

Add:

```text
blacklist nvidia
blacklist nouveau
```

Notes:

- Do not blacklist `amdgpu` (host iGPU needs it).
- `blacklist radeon` is optional and usually unnecessary on modern Ryzen iGPU setups.

Apply and reboot:

```bash
update-initramfs -u -k all
reboot
```

### Step 12: Final Host-Side Verification

```bash
lspci -nnk -d 10de:
```

Success should look like:

```text
01:00.0 ... Kernel driver in use: vfio-pci
01:00.1 ... Kernel driver in use: vfio-pci
```

The chat session reached this exact success state.

------

## 6. Create the Ubuntu VM (Proxmox UI)

Once host-side binding is done, create a new VM instead of reusing old SeaBIOS templates.

Recommended wizard settings:

1. OS: your Ubuntu ISO
2. System:
	- BIOS: `OVMF (UEFI)`
	- Machine: `q35`
	- Graphics: keep `Default` or `VirtIO-GPU` during install
3. CPU:
	- Type: `host`
4. Memory:
	- Disable ballooning
5. Network:
	- `VirtIO`

Then add PCI device:

- `Hardware` -> `Add` -> `PCI Device`
- Select `01:00.0` (NVIDIA VGA)
- Check:
  - `All Functions`
  - `ROM-Bar`
  - `PCI-Express`

Why only `01:00.0`?

- Because `All Functions` also includes `01:00.1` audio automatically.

Install Ubuntu, then inside guest install NVIDIA driver and verify with:

```bash
nvidia-smi
```

------

## 7. Troubleshooting Notes

1. `vfio-pci` not in use after reboot:
	- Recheck `vfio.conf`, blacklist file, and rerun `update-initramfs -u -k all`.
2. No IOMMU groups:
	- Recheck BIOS SVM/IOMMU and kernel cmdline flags.
3. Black screen when starting VM installer:
	- Keep a virtual display enabled during initial install, then tune display later.
4. Confused by `Kernel modules:` output in `lspci`:
	- It only means modules exist; `Kernel driver in use` is what matters.

------

## 8. Summary

The host side is done when both `01:00.0` and `01:00.1` show `Kernel driver in use: vfio-pci`.

At that point, Proxmox is no longer using the NVIDIA card, and the VM can claim it directly for near-native performance.

