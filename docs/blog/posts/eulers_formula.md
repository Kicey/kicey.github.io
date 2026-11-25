---
date: 2026-11-25
slug: eulers-formula
summary: Read Euler's formula as rotation on the unit circle, then see how two opposite rotations make a cosine in the Fourier series.
---

# Euler's Formula: From Complex Numbers to Rotating Waves

A cosine tracks the horizontal position of a point going around a circle. A sine tracks its vertical position. Euler's formula puts both coordinates in one complex number. That's why a single exponential can describe a steady rotation and why a minus sign in its exponent reverses the direction.

<!-- more -->

## One number, two coordinates

A complex number $z=x+iy$ represents the point $(x,y)$ in the complex plane: $x$ is the horizontal coordinate, $y$ is the vertical coordinate, and $i^2=-1$. On a circle of radius 1 centered at zero, the point at an angle $\theta$ measured counterclockwise from the positive horizontal axis has coordinates $(\cos\theta,\sin\theta)$.

**Euler's formula** says that this same point can be written as an exponential:

$$
e^{i\theta}=\cos\theta+i\sin\theta.
$$

The angle is measured in **radians**, so half a turn is $\pi$ and a full turn is $2\pi$. At $\theta=0$ the point is $1$ on the right. After a quarter turn it's $i$ at the top; after a half turn it's $-1$ on the left. That last case gives the familiar identity $e^{i\pi}+1=0$.

The exponential notation is useful because multiplying exponentials adds their exponents: $e^{i\alpha}e^{i\theta}=e^{i(\alpha+\theta)}$. On the circle, multiplying by $e^{i\alpha}$ simply adds $\alpha$ to the angle. For example, multiplying by $i=e^{i\pi/2}$ makes a quarter turn counterclockwise.

??? note "Derive the formula from power series"

    **1. Substitute $i\theta$ into the exponential series.** The Taylor series for $e^z$ about zero is

    $$
    e^z=\sum_{n=0}^{\infty}\frac{z^n}{n!}
       =1+z+\frac{z^2}{2!}+\frac{z^3}{3!}+\cdots.
    $$

    The index $n$ runs through the nonnegative integers, and $n!$ is the factorial (for example, $3!=3\cdot2\cdot1$). The same series defines the exponential for complex $z$, so we can put $z=i\theta$:

    $$
    \begin{aligned}
    e^{i\theta}
      &= 1+i\theta+\frac{(i\theta)^2}{2!}+\frac{(i\theta)^3}{3!}+\cdots\\
      &= 1+i\theta-\frac{\theta^2}{2!}-i\frac{\theta^3}{3!}+\cdots.
    \end{aligned}
    $$

    **2. Group the even and odd powers.** Since $i^2=-1$, every extra pair of factors of $i$ flips the sign. An even power gives $i^{2m}=(-1)^m$; an odd power leaves one extra $i$, so $i^{2m+1}=i(-1)^m$. The series converges absolutely, so grouping the terms this way leaves its sum unchanged:

    $$
    \begin{aligned}
    e^{i\theta}
      &=\left(1-\frac{\theta^2}{2!}+\frac{\theta^4}{4!}-\cdots\right)\\
      &\quad+i\left(\theta-\frac{\theta^3}{3!}+\frac{\theta^5}{5!}-\cdots\right).
    \end{aligned}
    $$

    **3. Build the cosine and sine series and compare.** For either function $g=\cos$ or $g=\sin$, the Taylor expansion about zero starts with the function value at zero. The next term uses the first derivative at zero, the term after that uses the second derivative, and so on:

    $$
    g(\theta)=g(0)+g'(0)\theta+\frac{g''(0)}{2!}\theta^2
              +\frac{g'''(0)}{3!}\theta^3+\cdots.
    $$

    Differentiate cosine once to get $-\sin\theta$, and again to get $-\cos\theta$. At zero these are $0$ and $-1$, so the linear term vanishes and the quadratic term is $-\theta^2/2!$. For sine, the first derivative is $\cos\theta$, which is $1$ at zero, so the linear term is $\theta$. The second derivative is $-\sin\theta$, which is $0$ at zero, so there's no quadratic term. Here are the values that go into the first six terms:

    $$
    \begin{array}{c|rrrrrr}
    \text{Derivative order} & 0 & 1 & 2 & 3 & 4 & 5\\ \hline
    \cos,\ \text{at }0 & 1 & 0 & -1 & 0 & 1 & 0\\
    \sin,\ \text{at }0 & 0 & 1 & 0 & -1 & 0 & 1
    \end{array}
    $$

    Order $0$ means the function itself. After four differentiations we get the original function back, so the pattern continues. Multiplying each entry by $\theta^n/n!$ for its column $n$ gives

    $$
    \begin{aligned}
    \cos\theta &= 1-\frac{\theta^2}{2!}+\frac{\theta^4}{4!}-\cdots,\\
    \sin\theta &= \theta-\frac{\theta^3}{3!}+\frac{\theta^5}{5!}-\cdots.
    \end{aligned}
    $$

    These series give the exact function values for every real $\theta$. All derivatives of cosine and sine have absolute value at most $1$, so the Taylor remainder after degree $N$ has absolute value at most $|\theta|^{N+1}/(N+1)!$, which tends to zero.

    Now compare with step 2: the even-power series is $\cos\theta$, and the odd-power series after factoring out $i$ is $\sin\theta$. Thus $e^{i\theta}=\cos\theta+i\sin\theta$.

## Let the angle change with time

Set $\theta=2\pi ft$, where $f$ is measured in hertz and $t$ in seconds. The factor $2\pi$ converts turns to radians. At $f=1\,\mathrm{Hz}$, $e^{2\pi i ft}$ moves once around the circle counterclockwise every second. At $f=-1\,\mathrm{Hz}$, it makes one turn per second **clockwise** instead. The sign of $f$ sets the direction; $|f|$ gives the number of turns per second.

At a given time, $e^{i\theta}$ and $e^{-i\theta}$ are reflections across the horizontal axis. They have the same horizontal coordinate and opposite vertical coordinates. Average them and the vertical coordinates cancel:

$$
\begin{aligned}
\frac{e^{i\theta}+e^{-i\theta}}{2}
&=\frac{(\cos\theta+i\sin\theta)+(\cos\theta-i\sin\theta)}{2}\\
&=\cos\theta.
\end{aligned}
$$

Substitute $\theta=2\pi ft$ with $f>0$ to write a cosine of amplitude 1 as

$$
\cos(2\pi ft)=\frac{1}{2}e^{2\pi i ft}+\frac{1}{2}e^{-2\pi i ft}.
$$

Picture two points that both start at $1$ and make $f$ turns per second. The $+f$ point goes counterclockwise; the $-f$ point goes clockwise. At every instant, their vertical coordinates cancel when added, but their horizontal coordinates are identical, so adding them doubles the horizontal coordinate. Multiplying each term by $\tfrac12$ restores the original amplitude: at $t=0$, the two terms contribute $\tfrac12+\tfrac12=1$.

The [complex Fourier series](fourier_series_and_harmonics.md#eulers-formula-and-negative-frequency) lists these as two terms because it keeps track of each direction separately. Together they describe **one real tone** at frequency $f$.

### Deriving the negative-angle form

Replace $\theta$ by $-\theta$ in Euler's formula. On the unit circle, negating the angle reflects the point across the horizontal axis: cosine stays the same, while sine changes sign.

$$
\begin{aligned}
e^{-i\theta}
  &=\cos(-\theta)+i\sin(-\theta)\\
  &=\cos\theta-i\sin\theta.
\end{aligned}
$$
