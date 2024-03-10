# Java Integer 缓存

```java
public class Main {
    public static void main(String[] args) {
        Integer a = 128;
        Integer b = 128;
        Integer c = 127;
        Integer d = 127;
        System.out.println(a == b);
        System.out.println(c == d);
    }
}
```

输出为

```txt
false
true
```

???

这里需要注意的是 Java 即使会自动的装箱，Integer 在使用 == 比较的时候同样是比较的对象，也就是内存地址。

那么为什么 127 的比较结果为 true ? 原因在于 Java 的装箱时会使用 valueOf 这个函数，它有一个缓存，范围是 -128~127，如果在这个范围内（这个范围可以通过 jvm 参数调节），将返回缓存的对象（在启动时初始化缓存范围内的对象）。

Java 其他包装类也有类似的问题。

解决方法：建议除非明确比较对象，都使用 `Objects.equals` 方法（由于有自动装箱的存在，其同样能对基础数据类型使用）。