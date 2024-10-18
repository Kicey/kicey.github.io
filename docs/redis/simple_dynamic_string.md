redis 中以 sds （simple dynamic string，简单动态字符串）来表示字符串（既是 redis 中一种基础数据结构，也是 redis 内部用于代替 c 语言中 char* 的数据结构）。

## 定义

```c
typedef char *sds;

/* Note: sdshdr5 is never used, we just access the flags byte directly.
 * However is here to document the layout of type 5 SDS strings. */
struct __attribute__ ((__packed__)) sdshdr5 {
    unsigned char flags; /* 3 lsb of type, and 5 msb of string length */
    char buf[];
};
struct __attribute__ ((__packed__)) sdshdr8 {
    uint8_t len; /* used */
    uint8_t alloc; /* excluding the header and null terminator */
    unsigned char flags; /* 3 lsb of type, 5 unused bits */
    char buf[];
};
struct __attribute__ ((__packed__)) sdshdr16 {
    uint16_t len; /* used */
    uint16_t alloc; /* excluding the header and null terminator */
    unsigned char flags; /* 3 lsb of type, 5 unused bits */
    char buf[];
};
struct __attribute__ ((__packed__)) sdshdr32 {
    uint32_t len; /* used */
    uint32_t alloc; /* excluding the header and null terminator */
    unsigned char flags; /* 3 lsb of type, 5 unused bits */
    char buf[];
};
struct __attribute__ ((__packed__)) sdshdr64 {
    uint64_t len; /* used */
    uint64_t alloc; /* excluding the header and null terminator */
    unsigned char flags; /* 3 lsb of type, 5 unused bits */
    char buf[];
};
```

![img](https://blog.kicey.site/content/images/2022/08/image-3.png)

## 扩容

如果你有稍微看过一点 java 中 ArrayList 的实现的话，两者的实现是类似的。在需要重新分配内存时，如果所需的内存不超过某个限制，那么分配两倍的内存，避免频繁内存分配，如果超过某个限制，那么只分配需要的内存空间。

## 紧凑排列（内存不对齐）

内存对齐：简单的说，cpu 读取内存并不是以 byte 为单位的，通常以 64/32 位（也和 cache 的缓存行有关），内存对齐就是将所用的内存填补为读取内存单位的整数倍，下图中的 pad 部分。

![img](https://blog.kicey.site/content/images/2022/08/image-4.png)

redis 中的 sds 没有图中的 pad 部分 8 bit 的 flag 后直接是 buf 数组。worse is better，能够较简单的实现是最重用的。如果引入内存对齐，那么需要在 32/64 位，以及不同的单位内存长度的 sds 结构做不同的调整，而且为了兼容 char*（sds 使用指针的一些操作兼容了 char* ）指针直接指向数据的首位，而不利于获取当前的状态（即不能直接通过 buf[-1] 来获取 flag 内容），做内存对齐将会引入这一部分的工作使结构变复杂。

参考内容：

[要懂redis，首先得看懂sds](https://juejin.cn/post/6888592403301662728)
[简单动态字符串 — Redis 设计与实现](https://redisbook.readthedocs.io/en/latest/internal-datastruct/sds.html)