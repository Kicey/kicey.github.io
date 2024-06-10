# Java 码点和码元

## 概述

Java中String的设计是在Unicode编码尚未完成时进行的，原本用来表示世界上所有字符的16个位在后期不能胜任这个任务。Java使用了一种**可变长的，向后兼容的编码，UTF-16**。

- 典型的（可以在16位以内表示的字符）用一个16位编码来表示，占用一个char；
- 占用位数超过16位的字符用一组（几个）*来自编码空间中特殊区域的16位编码（称作surrogate characters）*来表示，占用多个char；

能表示一个字符的16位的（一个char）或n*16位（多个char）的编码称作码点，每个16位编码（每个char）称作码元。

这里需要了解一点 utf-16 的东西，即如何区分一个和两个码元组成的码点。

直接上结论：

在 utf-16 中，从 U+D800 到 U+DFFF 之间的码位区段是永久保留不映射到Unicode字符，即当一个码点只占用一个码元时，0xD800 到 0xDFFF 是不使用的。反之，如果遇到一个码元在这个区间中，那么这个码元一定和下一个码元一起组成一个码点。

具体的编码方式可以参考：

Unicode中UTF-8与UTF-16编码详解 - 掘金

本文通过介绍Unicode编码以及对应的两种编码方式UTF-8和UTF-16，让读者能够了解关于字符串编码的相关知识，同时能够弄清楚Unicode和UTF-8和UTF-16之间的关系。 本文作为utfx.js源码解析的基础知识储备文章，通过了解UTF-8和UTF-16这两种编码…

[Unicode中UTF-8与UTF-16编码详解](https://juejin.cn/post/6844903590155272199)

https://zh.m.wikipedia.org/wiki/UTF-16

## 实验

输出每个**码元（code unit）**

```java
String str = " ";
System.out.println(str.length());
for(char e : str.toCharArray()){
    System.out.print(e+": ");
    System.out.printf("\\u%04x\n", (inte);
}
```

这段代码的输出是

```tex
2
?: \ud835
?: \udd46
```

输出每个**码点（code point)**

```java
int i = 0;
while (i < str.length()) {
    int j = str.offsetByCodePoints(i, 1);   //j will be 2, offset 1 codepoint of( ) is 2 codeunit(2 char)
    String codePoint = str.substring(i, j);
    System.out.println(codePoint);
    i = j;
}
```

### 完整代码

```java
public class CodePointTest {
    public static void main(String[] args) {
        String str = " ";
        System.out.println(str.length());
        for (char e : str.toCharArray()) {
            System.out.print(e + ": ");
            System.out.printf("\\u%04x\n", (int) e);
        }

        int i = 0;
        while (i < str.length()) {
            int j = str.offsetByCodePoints(i, 1);   //j will be 2, offset 1 codepoint of( ) is 2 codeunit(2 char)
            String codePoint = str.substring(i, j);
            System.out.println(codePoint);
            i = j;
        }

    }
}
```

------