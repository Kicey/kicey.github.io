---
date: 2025-06-29 
---

# 在 Ubuntu 上为新一代显卡（如 5060 Ti）安装 NVIDIA 驱动和 CUDA Toolkit

大家好！如果你最近升级到了新一代 NVIDIA 显卡（如强大的 5060 Ti），并且正在运行 Ubuntu 24.04 或更高版本，你可能会发现直接从标准 Ubuntu 软件源安装最新驱动和 CUDA Toolkit 时遇到问题。这通常是因为新硬件需要比默认软件源中更为新颖的驱动程序。

本文将指导你如何通过添加 NVIDIA 官方维护的软件源，安装 NVIDIA 驱动（建议 575 及以上版本）和 CUDA Toolkit（建议 12.8 及以上版本）。这种方式可以确保你获得最新兼容的软件，并便于后续升级。

------

## 1. 前置条件与系统准备

在开始之前，请确保你的系统已更新，并具备必要的工具。

- 操作系统：Ubuntu 24.04 LTS（或更高）
- 显卡：NVIDIA 5060 Ti（或类似新发布的 NVIDIA 显卡）
- 网络连接：需要联网下载软件包

强烈建议在进行重大驱动安装前备份系统。

首先，更新你的软件包列表并升级现有软件包：

```bash
sudo apt update
sudo apt upgrade -y
```

你还需要确保已安装内核头文件和必要的构建工具，这对于驱动编译至关重要：

```bash
sudo apt update
sudo apt install gcc
sudo apt install make
sudo apt install linux-headers-$(uname -r) -y
```

------

## 2. 添加 NVIDIA 官方软件源

安装新驱动的关键在于将 NVIDIA 官方软件源添加到系统的 APT 源中。该源提供了最新的驱动和 CUDA Toolkit。

请参考 NVIDIA 官方链接 [CUDA Toolkit for ubuntu](https://developer.nvidia.com/cuda-downloads?target_os=Linux&target_arch=x86_64&Distribution=Ubuntu&target_version=24.04&target_type=deb_network) `https://developer.nvidia.com/cuda-downloads?target_os=Linux&target_arch=x86_64&Distribution=Ubuntu&target_version=24.04&target_type=deb_network`

添加软件源后，再次更新软件包列表以获取新信息：

```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
```

------

## 3. 安装 NVIDIA 驱动和 CUDA Toolkit

现在已经配置好 NVIDIA 软件源，可以安装推荐的驱动了。对于 5060 Ti，建议驱动版本至少为 575。

### 安装 CUDA Toolkit

```bash
sudo apt-get update
sudo apt-get -y install cuda-toolkit-12-9
```

如果你不需要这么新的 CUDA Toolkit，支持 50 系列显卡的最低版本是 12.8。

### 安装驱动

```bash
sudo apt-get update
sudo apt-get install -y nvidia-open
```

`cuda-drivers` 也是可以的，但推荐使用开源的 `nvidia-open`。

安装过程中，你可能会看到如下信息：
```bash
Building initial module nvidia/575.57.08 for 6.8.0-62-generic
Sign command: /usr/bin/kmodsign
Signing key: /var/lib/shim-signed/mok/MOK.priv
Public certificate (MOK): /var/lib/shim-signed/mok/MOK.der
```

如果你启用了安全启动（Secure Boot），需要注册公钥。如果主机未启用安全启动，可以忽略此输出并跳过第 4 节。

------

## 4. 处理安全启动与 MOK 管理

如果系统启用了 Secure Boot，NVIDIA 内核模块默认不会被自动加载。你需要将 NVIDIA 的公钥注册到系统的 MOK（Machine Owner Key）列表。

1. 使用命令导入 NVIDIA 公钥：
   ```bash
   sudo mokutil --import /var/lib/shim-signed/mok/MOK.der
   ```

   你会被要求输入密码 2~3 次，最后两次是为 Secure Boot 设置和确认密码。

2. 重启后，系统会进入 "MOK 管理" 或 "安全启动密钥管理" 界面（属于 UEFI/BIOS）。

3. 选择 "Enroll MOK"，然后 "continue"，输入刚才设置的密码，完成公钥注册。

4. 注册完成后，选择继续启动系统。

------

## 5. 添加 CUDA Toolkit 可执行文件到 PATH

我们在第 3 步已经安装了 CUDA Toolkit，但有些可执行文件默认不在 PATH 中，需要手动添加。

安装后，建议将 CUDA 路径加入系统的 `PATH` 和 `LD_LIBRARY_PATH`。可以将以下内容添加到 `~/.bashrc`（或 Zsh 用户的 `~/.zshrc`），然后执行 source：

```bash
echo 'export PATH=/usr/local/cuda-12/bin:$PATH' >> ~/.bashrc 
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc 
source ~/.bashrc
```

通过 `nvcc --version` 验证安装：

你应该能看到类似如下输出：
```bash
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2025 NVIDIA Corporation
Built on Tue_May_27_02:21:03_PDT_2025
Cuda compilation tools, release 12.9, V12.9.86
Build cuda_12.9.r12.9/compiler.36037853_0
```

------

## 6. 配置支持 GPU 的 Docker（NVIDIA Container Toolkit）

如果你使用 Docker 进行开发，需要让容器访问 GPU。这需要安装 NVIDIA Container Toolkit。由于我们已经添加了 NVIDIA 软件源，安装非常简单。

1. 安装 NVIDIA Container Toolkit：
   ```bash
   sudo apt install nvidia-container-toolkit
   ```

2. 配置 Docker 使用 NVIDIA 运行时，并重启 Docker 服务：
   ```bash
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```
   
   你会在 `/etc/docker/daemon.json` 看到类似如下内容：
   
   ```json
   { 
       "runtimes": {
           "nvidia": {
               "args": [],
               "path": "nvidia-container-runtime"
           }
       }
   }
   ```

3. 测试 Docker GPU 支持：
   ```bash
   sudo docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi
   ```

   你应该能看到容器内 `nvidia-smi` 的输出，说明 GPU 可用。

   ![image-20250629113600207](../images/install_nvidia_driver_for_5060ti_on_ubuntu/image-20250629113600207.png)

------

## 7. 总结

通过以上步骤，你应该已经在 Ubuntu 系统上成功安装了最新的 NVIDIA 驱动和 CUDA Toolkit，并让新一代显卡可以用于开发和计算。同时也配置好了 Docker 支持 GPU。

## 参考资料

* https://developer.nvidia.com/cuda-downloads?target_os=Linux&target_arch=x86_64&Distribution=Ubuntu&target_version=24.04&target_type=deb_network
* https://forums.developer.nvidia.com/t/we-would-like-to-know-when-the-nvidia-drivers-for-5060ti-on-ubuntu-will-be-released/331207
* https://forums.developer.nvidia.com/t/nvidia-drivers-not-working-while-secure-boot-is-enabled-after-updating-to-ubuntu-24-04/305351/6?u=kiceyscream
* https://forums.developer.nvidia.com/t/could-not-select-device-driver-with-capabilities-gpu/80200
* https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

