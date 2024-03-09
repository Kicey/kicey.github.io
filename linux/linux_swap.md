# linux swap 空间

## 虚拟内存

虚拟内存的出现的一部分原因是解决内存不足问题，使用磁盘上的一部分和真正的内存一起编址组成操作系统的内存空间，依据程序的局部性（时/空），使用交互算法将目前需要使用的内容换入真正的内存中，而暂时用不到的内存放入硬盘中。

这个特点刚好适用与目前云服务器的场景，我自己使用云服务器的大部分场景都是算力充足而内存不足（一台云服务器上挂载的服务太多……）。

## 创建 swap 空间

swap 空间一般再安装系统的时候以分区的形式创建，原因在于 swap 最好使用连续的一片磁盘空间。以分区的形式创建连续的磁盘空间避免剩余的磁盘空间碎片化。

swap 同时也支持文件形式的连续磁盘空间（又不是不能用）。

使用命令如下：

*命令需要 sudo*

```sh
# 创建一个作为交换空间的文件
dd if=/dev/zero of=/root/swapfile bs=1M count=4096
```

- dd：disk dump 磁盘拷贝命令
- if / of：input file 输入文件 / output file 输出文件
- /dev/zero：/dev/xx 是 linux 中的一个特殊的虚拟的“文件”，全为 0
- bs：block size 块的大小
- count：块的数量

```sh
# 以 swap 格式化文件
mkswap /root/swapfile
# 启用文件形式的 swap 分区
swapon /root/swapfile
# 开机启用
echo "/swapfile none swap sw 0 0" >> /etc/fstab
```

## 增加 swap 分区

增加 swap 分区需要先关闭对应的 swap 分区。这样可能造成的问题是，真正的内存中没有办法存放目前所有的虚拟内存中的内容，就会死机……，所以建议先创建新的 swap 文件（linux 支持同时使用多个 swap 文件），在关闭删除原有的 swap 文件。

### 创建新的 swap 分区

方式和上面第一次创建的时候一样。

### 禁用原有的 swap 分区

```sh
swapoff /root/swapfile
```

然后再删除 swap 文件

```sh
rm /root/swapfile
```