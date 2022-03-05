# 初见Nginx

nginx是一个建立在http协议上的web服务器（因为https是在ssl上使用http，所以nginx也支持https）

## Nginx功能

使用nginx具有以下功能（包括但不限于）：

1. 反向代理，即作为服务器的代理接受请求，并转发给真正的后端程序，在此基础上可以实现
   * 根据uri（包括域名部分）转发到不到机器的不同端口
   * 负载均衡
   * 解决跨域
2. 提供静态资源访问
   * 将前端编译完成的内容直接挂载供访问

使用Nginx主要通过更改配置文件

也需要一些命令，以下简单罗列一些常用命令

## Nginx命令

```bash
nginx -s stop       快速关闭Nginx，可能不保存相关信息，并迅速终止web服务。
nginx -s quit       平稳关闭Nginx，保存相关信息，有安排的结束web服务。
nginx -s reload     因改变了Nginx相关配置，需要重新加载配置而重载。
nginx -s reopen     重新打开日志文件。
nginx -c filename   为 Nginx 指定一个配置文件，来代替缺省的。
nginx -t            不运行，仅仅测试配置文件。nginx 将检查配置文件的语法的正确性，并尝试打开配置文件中所引用到的文件。
nginx -v            显示 nginx 的版本。
nginx -V            显示 nginx 的版本，编译器版本和配置参数。
```

## Nginx配置

### 配置结构

nginx的配置位于`/etc/nginx/`目录下

只有一个主配置文件，nginx.conf（也可以通过命令重新指定另外的文件作为主配置文件）

nginx.conf中会使用`include`的形式引用其他的命令，注意`include`是在原地引入，类似C/C++中的宏展开

主要有两个目录sites-available和sites-enable，sites-available中存在有效的配置文件，sites-enable是启用的配置文件，以快捷方式引用sites-available中的配置文件，默认情况下导入sites-enable目录中的配置文件，也可以在nginx.conf中修改

注意结构如下

```te
events {

}
http {
	upstream {
	
	}
	
	server {
		listen
		location $uri {
		
		}
	}
	
	server {
		listen
		location $another_uri {
		
		}
	}
}
```

关于配置文件中的配置项，请关注下面的链接

* [server_name和location](https://segmentfault.com/a/1190000021771733)
* [root和alias](https://blog.csdn.net/liuxl57805678/article/details/102754750)
* [index](https://www.cnblogs.com/kukudi/p/11496315.html)

[一篇实战意味的引入](https://github.com/dunwu/nginx-tutorial)
