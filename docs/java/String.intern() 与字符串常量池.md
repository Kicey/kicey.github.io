# String.intern() 与字符串常量池

## String::new 和 String 常量

常量的 String 在编译阶段已经被确定了，那么 JVM 为了减少内存的使用，同样的 String 都指向了同一个 String 对象（包括由字符串常量连接而来的字符串，这点不能通过中间引用，因为引用可能被修改）。

## intern()

String.intern() 是一个Native（本地）方法，它的作用是如果字符串常量池已经包含一个等于此 String 对象的字符串，则返回字符串常量池中这个字符串的引用，否则将当前 String 对象的引用地址（堆中）添加到字符串常量池中并返回。

这里需要注意的是 intern() 方法只会返回，字符常量池中的引用（有就利用现有的缓存，没有就新创建）。

测试

```Java
public class Main {
    public static void main(String[] args) {
        String b = "h";
        String a = new String("h");
        String c = a.intern();
        
        System.out.println(a == c);	// false
        System.out.println(a == b);	// false
        System.out.println(b == c);	// true
    }
}
```

这篇文章写得很详细：

String.intern方法详解 - 掘金

记录创建String的两种方式，”″ 和 new String()区别，String intern方法的使用和常量池。 变量a： “lantao” 是字符串常量，在编译期就被确定了，先检查字符串常量池中是否含有“lantao”字符串,若没有则添加“lantao”到字符串常量池中…

https://juejin.cn/post/6844903913116680199
