---
title: spring中多模块，以及多模块中的配置问题
tags:
  - spring
---

**本文不是一篇spring多模块的实战，重在理解多模块，搞清楚多模块是做什么的，它不能做什么，以及多模块涉及的配置问题**

## 多模块与分布式

首先要明白，多模块和分布式应用是不同的（分布式简单的来说就是多个应用一起协作完成任务，每个应用负责的内容不同）。

多模块的项目可以是分布式的，即一个项目中存在一个以上的可以运行的应用，当这些应用配合完成任务时，他们就组成一个分布式的应用。因为存在与共同的项目中，他们的关系可能过于紧密，即耦合性高，但是因为方便调整，在项目的初期也许可以加快项目的建设。

多模块的项目不一定是分布式的，可能各个模块存在依赖关系，但是最终只有一个可以运行的项目，这样做的目的是降低模块之间的耦合性，方便项目的维护。

## 多模块与多配置

我们很自然的想到，对项目分模块之后，我们的应用的配置也该分模块去设置。比如我们应该又专门对持久化数据库的配置，专门的缓存配置，专门的安全性配置，等等。

对，也不对。

对的部分是，我们的确应将各个模块的配置区分，一个模块的配置应该与其他模块的配置隔离开来。

不对的是，这些配置都应该写在一个配置文件中，在这个配置文件中加以区分。

让我们来想想这是为什么：

1. 只有一个需要启动的应用需要配置文件。

   你可能会说，一些库就算不需要启动也是需要以些默认的配置，比如在那里存放缓存或临时文件，或者一些默认的设置项，比如开启的线程数，维护的各类池的大小，这些当然可以在类文件中编码，但总有一些放在那种非可执行文件中是更好的吧。

   的确。但是对于某些不需要启动的库来说需要一个这样的配置文件，并且配置文件中的内容需要被使用这个库的应用所覆盖，但是对于一个库来说，是绝对不会需要一个application.yaml这样的配置文件的。

   想一想，spring embed tomcat的端口8080或者是spring data默认的连接池大小是在哪里定义的，又是怎么实现覆盖的。

2. 配置文件因为是针对一个应用的，他们应该尽可能的集中，不要使对配置的管理过与复杂，至少不应该发生在配置文件这里。

3. 就算当前，几个应用中的配置可能是重复的，但是以后他们可能会在不同的服务器上运行，不要将这些应用绑定再一起，一定要他们运行在一台主机上。

4. 如果更为复杂的配置需求，那么该使用的是配置服务，而不是配置文件。
