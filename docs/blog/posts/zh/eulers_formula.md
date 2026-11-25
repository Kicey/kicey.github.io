---
date: 2026-11-25
slug: 欧拉公式
summary: 从单位圆上的旋转理解欧拉公式，再看傅里叶级数中方向相反的两项怎样合成一个余弦波。
---

# 欧拉公式：从复数到旋转的波

一个点沿圆周转动时，余弦描述它的横坐标，正弦描述它的纵坐标。欧拉公式把这两个坐标合在一个复数里。这样，只用一个指数就能描述匀速旋转；给指数加个负号，旋转方向就反过来了。

<!-- more -->

## 一个复数，两个坐标

复数 $z=x+iy$ 在复平面上对应点 $(x,y)$：$x$ 是横坐标，$y$ 是纵坐标，且 $i^2=-1$。以原点为圆心、半径为 1 的圆叫**单位圆**。从横轴正方向逆时针量出角度 $\theta$，圆上对应点的坐标就是 $(\cos\theta,\sin\theta)$。

**欧拉公式**把同一个点写成指数形式：

$$
e^{i\theta}=\cos\theta+i\sin\theta.
$$

角度用**弧度**表示：半圈是 $\pi$，一整圈是 $2\pi$。当 $\theta=0$ 时，点在右侧的 $1$；转四分之一圈到上方的 $i$；转半圈到左侧的 $-1$。最后这个例子就是常见的恒等式 $e^{i\pi}+1=0$。

指数形式的好处是，相乘时指数相加：$e^{i\alpha}e^{i\theta}=e^{i(\alpha+\theta)}$。在圆上，乘以 $e^{i\alpha}$ 就相当于让角度增加 $\alpha$。例如，乘以 $i=e^{i\pi/2}$，就是逆时针转四分之一圈。

??? note "用幂级数推导欧拉公式"

    **1. 把 $i\theta$ 代入指数函数的级数。** $e^z$ 在零点的泰勒级数为：

    $$
    e^z=\sum_{n=0}^{\infty}\frac{z^n}{n!}
       =1+z+\frac{z^2}{2!}+\frac{z^3}{3!}+\cdots.
    $$

    下标 $n$ 遍历非负整数，$n!$ 表示阶乘，例如 $3!=3\cdot2\cdot1$。同一个级数也可以用来定义复数的指数函数，因此可以代入 $z=i\theta$：

    $$
    \begin{aligned}
    e^{i\theta}
      &= 1+i\theta+\frac{(i\theta)^2}{2!}+\frac{(i\theta)^3}{3!}+\cdots\\
      &= 1+i\theta-\frac{\theta^2}{2!}-i\frac{\theta^3}{3!}+\cdots.
    \end{aligned}
    $$

    **2. 把偶次项和奇次项分开。** 因为 $i^2=-1$，每多乘两个 $i$，符号就翻转一次。偶次幂是 $i^{2m}=(-1)^m$；奇次幂还剩一个 $i$，所以 $i^{2m+1}=i(-1)^m$。这个级数绝对收敛，把各项按奇偶分组不会改变它的和：

    $$
    \begin{aligned}
    e^{i\theta}
      &=\left(1-\frac{\theta^2}{2!}+\frac{\theta^4}{4!}-\cdots\right)\\
      &\quad+i\left(\theta-\frac{\theta^3}{3!}+\frac{\theta^5}{5!}-\cdots\right).
    \end{aligned}
    $$

    **3. 展开余弦和正弦，再逐项比较。** 用 $g$ 表示余弦或正弦。在零点展开时，泰勒级数的第一项是函数在零点的值，下一项用到零点的一阶导数值，再下一项用到二阶导数值，依此类推：

    $$
    g(\theta)=g(0)+g'(0)\theta+\frac{g''(0)}{2!}\theta^2
              +\frac{g'''(0)}{3!}\theta^3+\cdots.
    $$

    余弦求一次导得到 $-\sin\theta$，再求一次导得到 $-\cos\theta$。代入 $\theta=0$，分别得到 $0$ 和 $-1$，所以一次项为零，二次项是 $-\theta^2/2!$。正弦的一阶导数是 $\cos\theta$，在零点等于 $1$，所以一次项是 $\theta$；二阶导数是 $-\sin\theta$，在零点等于 $0$，所以二次项为零。前六项用到的导数值如下：

    $$
    \begin{array}{c|rrrrrr}
    n & 0 & 1 & 2 & 3 & 4 & 5\\ \hline
    (\cos)^{(n)}(0) & 1 & 0 & -1 & 0 & 1 & 0\\
    (\sin)^{(n)}(0) & 0 & 1 & 0 & -1 & 0 & 1
    \end{array}
    $$

    $n=0$ 表示不求导，直接取函数值。每求四次导就回到原来的函数，所以这个规律会一直重复。把第 $n$ 阶导数值乘以 $\theta^n/n!$，就得到：

    $$
    \begin{aligned}
    \cos\theta &= 1-\frac{\theta^2}{2!}+\frac{\theta^4}{4!}-\cdots,\\
    \sin\theta &= \theta-\frac{\theta^3}{3!}+\frac{\theta^5}{5!}-\cdots.
    \end{aligned}
    $$

    对任意实数 $\theta$，这两个级数都给出精确的函数值。因为它们各阶导数的绝对值都不超过 $1$，泰勒展开保留到 $N$ 次项时，余项的绝对值不超过 $|\theta|^{N+1}/(N+1)!$，这个上界会趋于零。

    现在回到第 2 步：偶次项组成的级数就是 $\cos\theta$，奇次项提出 $i$ 后剩下的级数就是 $\sin\theta$。因此 $e^{i\theta}=\cos\theta+i\sin\theta$。

## 让角度随时间变化

令 $\theta=2\pi ft$，其中频率 $f$ 的单位是赫兹，时间 $t$ 的单位是秒。因子 $2\pi$ 把圈数换算成弧度。当 $f=1\,\mathrm{Hz}$ 时，$e^{2\pi i ft}$ 对应的点每秒逆时针转一圈。换成 $f=-1\,\mathrm{Hz}$，它每秒还是转一圈，只是变成了**顺时针**。$f$ 的符号决定方向，$|f|$ 则表示每秒转多少圈。

在同一时刻，$e^{i\theta}$ 和 $e^{-i\theta}$ 对应的两个点关于横轴对称。它们的横坐标相同，纵坐标互为相反数。取平均后，纵坐标正好抵消：

$$
\begin{aligned}
\frac{e^{i\theta}+e^{-i\theta}}{2}
&=\frac{(\cos\theta+i\sin\theta)+(\cos\theta-i\sin\theta)}{2}\\
&=\cos\theta.
\end{aligned}
$$

取 $f>0$，代入 $\theta=2\pi ft$，幅度为 1 的余弦波就可以写成：

$$
\cos(2\pi ft)=\frac{1}{2}e^{2\pi i ft}+\frac{1}{2}e^{-2\pi i ft}.
$$

想象两个点都从 $1$ 出发，每秒转 $f$ 圈。$+f$ 对应的点逆时针转，$-f$ 对应的点顺时针转。在任意时刻，把两点的坐标相加，纵坐标正好抵消，横坐标却因为相同而加倍。给每一项乘上 $\tfrac12$，就能还原原来的幅度。例如在 $t=0$ 时，两项相加得到 $\tfrac12+\tfrac12=1$。

[复数形式的傅里叶级数](fourier_series_and_harmonics.md#eulers-formula-and-negative-frequency)把两个方向的旋转分别记为一项，但这两项合起来只表示**一个频率为 $f$ 的实数纯音**。

### 推导负角度的形式

把欧拉公式中的 $\theta$ 换成 $-\theta$。在单位圆上，把角度取反相当于将对应的点沿横轴翻转：余弦不变，正弦变号。

$$
\begin{aligned}
e^{-i\theta}
  &=\cos(-\theta)+i\sin(-\theta)\\
  &=\cos\theta-i\sin\theta.
\end{aligned}
$$
