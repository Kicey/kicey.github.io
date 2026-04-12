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

## Technology Stack Behind This Tutorial

This guide touches multiple layers of the virtualization stack. Understanding these layers makes troubleshooting much easier:

1. Firmware layer (UEFI/BIOS)
	- `SVM` (AMD-V) enables CPU virtualization extensions.
	- `IOMMU` (AMD-Vi) enables DMA remapping and device isolation.
	- UEFI mode avoids legacy initialization behavior that can interfere with modern GPU passthrough.

2. Hypervisor layer (Proxmox VE)
	- Proxmox is the management layer; actual VM acceleration is provided by Linux `KVM` and device emulation by `QEMU`.
	- GPU passthrough means QEMU exposes a real PCIe device directly to the guest, instead of emulating a virtual GPU.

3. Isolation layer (Linux IOMMU groups)
	- `IOMMU` = `Input-Output Memory Management Unit`.
	- The kernel groups PCI devices by isolation boundaries.
	- Passthrough is safe/reliable only when devices are in proper IOMMU groups.

4. Driver binding layer (VFIO)
	- `VFIO` = `Virtual Function I/O`.
	- `vfio` (VFIO core framework), `vfio_iommu_type1` (Type-1 IOMMU backend), `vfio_pci` (PCI device binding driver), and `vfio_virqfd` (virtual interrupt eventfd support) allow userspace VMs to own PCI devices securely.
	- Binding the GPU to `vfio-pci` prevents host graphics drivers from taking the card first.

5. Boot and module orchestration layer
	- GRUB injects kernel flags (`amd_iommu=on iommu=pt`).
	- `initramfs` ensures required modules and binding logic are available early during boot.
	- `/etc/modules-load.d/` controls module auto-load; `/etc/modprobe.d/` controls module options and blacklists.

6. Guest VM platform layer
	- `OVMF (UEFI)` + `q35` gives a modern virtual platform aligned with PCIe passthrough.
	- `CPU type: host` exposes native CPU features.
	- Disabling memory ballooning avoids DMA-related instability for passthrough workloads.

7. Verification toolchain
	- `dmesg`, `/proc/cmdline`, `find /sys/kernel/iommu_groups`, and `lspci -nnk` validate host readiness.
	- `nvidia-smi` validates the guest-side driver and runtime state.

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

Under the hood:

- `SVM` enables hardware-assisted virtualization instructions used by KVM.
- `IOMMU` enables DMA remapping, which is the foundation for safe PCIe passthrough.
- If either is missing, VFIO can load but device assignment will typically fail or be unstable.

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

Why these flags matter:

- `amd_iommu=on`: explicitly enables AMD IOMMU support in kernel boot path.
- `iommu=pt`: keeps host-side overhead lower for non-assigned devices by using pass-through mappings where possible.
- Without correct boot flags, BIOS settings alone may not produce usable runtime isolation.

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

This is a key architectural checkpoint: IOMMU groups are the kernel's isolation model, and VFIO relies on this model to guarantee a device can be safely handed to a VM.

------

## 4. Load VFIO Modules at Boot

Historically people edited `/etc/modules`, but on systemd-based systems the cleaner way is a dedicated file in `/etc/modules-load.d/`.

Stack detail:

- `/etc/modules-load.d/*.conf` controls which kernel modules are loaded at boot.
- `/etc/modprobe.d/*.conf` controls module parameters (for example, VFIO device IDs) and blacklists.
- Keeping loading and policy in separate files makes maintenance and debugging clearer.

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

What this does:

- `ids=...` tells VFIO exactly which PCI functions to claim (GPU + HDMI/DP audio).
- `disable_vga=1` helps avoid legacy VGA routing conflicts on some boards/firmware combinations.

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

The binding order is critical: if `nouveau`/`nvidia` binds first, VFIO cannot cleanly claim the device later without manual unbind/rebind.

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

Why this VM stack is recommended:

- `OVMF` matches modern GPU firmware expectations and guest driver behavior.
- `q35` models a PCIe-first chipset, which is a better fit for passthrough than legacy `i440fx`.
- `VirtIO` keeps paravirtualized devices efficient so CPU/GPU resources are focused on real workloads.

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

