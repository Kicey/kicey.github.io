# 构建工具 gradle （Java）

*gradle 的学习不推荐看书*

## 参考

Groovy 的语法可以直接参考官方文档。

https://groovy-lang.org/documentation.html

Gradle 的语法全部基于 Groovy，不过默认加入一些变量，方法等，具体可以参看 Gradle 手册。

https://docs.gradle.org/current/userguide/userguide.html

https://docs.gradle.org/current/dsl/


## 一个引入

```groovy
task sourcesJar(type: Jar, dependsOn: classes, description: 'Creates a jar from the source files.') {
  classifier = 'sources'
  from sourceSets.main.allSource
}
```

这个 task 是如何起作用的呢？

首先将 sourcesJar 视为一个方法，其参数是 Jar, classes, 'Creates ...' 以及其后的一个闭包。build.gradle 中隐式的 Project 实例并没有这个方法，那么就会将这些参数（包括闭包）传给一个缺省方法执行，这个方法又创建并返回一个闭包，这个返回的闭包作为参数传递给 task 方法执行。

## 项目结构

使用 gradle 的项目的构建一般来说和 3 个脚本相关（build.gradle, init.gradle, settings.gradle），这 3 个脚本对应 Groovy语言的 3 个实例（Project, Gradle, Settings）。

```text
├── gradle 
│   └── wrapper
│       ├── gradle-wrapper.jar
│       └── gradle-wrapper.properties
├── gradlew 
├── gradlew.bat 
├── settings.gradle 
└── app
    ├── build.gradle 
    └── src
        ├── main
        │   └── java 
        │       └── demo
        │           └── App.java
        └── test
            └── java 
                └── demo
                    └── AppTest.java
```

整个目录作为根项目，其中的 *app* 作为一个子项目。

### Settings

在根项目中存在一个 gradle 脚本文件（准确的说是 groovy 或者 kotlin 脚本）settings.gradle， `Settings` 实例和 settings.gradle 脚本是一对一的关系，一般来说一个 gralde 的项目（可能包含多个子项目）只有一个 setting.gradle 脚本。

gradle 将创建一个 `Settings` 对象，在这个 `Settings` 对象执行 settings.gradle 脚本（这意味着不需要指定 `Settings` 对象，下面的 rootRroject.name 实际上是访问了当前 `Settings` 的 rootProject 字段上的 name 字段，即 `settings.rootProject.name = 'gradle-sample'` 其中 settings 是 `Settings` 实例的引用，gralde 中的脚本都有类似执行基础对象）。

```Groovy
rootProject.name = 'gradle-sample'
include('app', 'list', 'utilities')
```

一个最基础的 Settings.gradle 脚本如上。

等价预下面的写法（settings 实例由）。

```Grovvy
settings.rootProject.name = 'gradle-sample'
settings.include('app', 'list', 'utilities')
```

其中 rootProject 和 include 分别是 Settings 对象的一个字段和方法，在这里设置了根项目的名称，以及包含的子项目。

### Project

在每个子项目存在一个 build.gradle 脚本，与一个 `Project` 实例对应。一个基础的 build.gradle 内容如下。

```Groovy
plugins {
    id 'site.kicey.java-application-conventions'
}

dependencies {
    implementation 'org.apache.commons:commons-text'
    implementation project(':utilities')
}

application {
    // Define the main class for the application.
    mainClass = 'site.kicey.app.App'
}
```

和 `Settings` 一样，在 build.gradle 可以直接访问相应的 `Project` 实例的字段和方法，对于字段和方法，域稍有不同。

#### 直接访问字段

`Project` 有 6 个域，在直接访问时，会顺序的从这 6 个域中寻找：

1. project 实例本身的属性
2. project 的额外（ext）属性，即 project.ext.*
3. project 上插件增加的扩展（extensions）属性
4. project 上插件增加的协定属性（convention）属性
5. project 中的 task
6. 从父项目中继承的额外和协定属性

#### 直接访问方法

1. project 实例本身的方法
2. build.gradle 中的方法
3. project 上插件增加的扩展方法
4. project 上插件增加的协定方法
5. project 中的 task
6. 从父项目继承的方法
7. project 字段上的函数闭包将被作为方法

具体的可以查阅：[Project - Gradle DSL Version 7.6](https://docs.gradle.org/current/dsl/org.gradle.api.Project.html)

## 构建阶段

- 初始化：执行 settings.gradle 脚本，检测需要相关的项目，创建 `Project` 实例
- 配置：所有的 `Project` 实例在这个阶段依据 build.gradle 进行配置（build.gradle 中的脚本将会执行，这些脚本大部分用于配置，也可以使用 println 在这个阶段执行时打印字符串）
- 执行：执行用户通过命令行指定的 task

gradle 支持通过定义任务创建，执行等时间点上的回调函数。