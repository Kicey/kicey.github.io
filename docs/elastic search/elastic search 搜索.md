# elastic search 搜索

## 简单的条件搜索

*es 中不存在条件搜索这么一个概念，这里的这中说法仅仅为了便于理解*

从下面的样例看出，搜索设计 es 的 *_search* 端点，并且使用 json 格式请求体（实际以请求参数的形式发送）。

```
GET books/_search
{
	"query": { # es 请求语法的一部分
		"match": { # 指定判断方式
    		"author": "Joshua"	# 以”字段：值“的形式指定搜索条件
 		}
 	}
}
```

es 的请求体中 **query** 的子节点除了 **match** 之外还有 **multi_match（进行多个字段的匹配）**，**prefix（匹配字段前缀）**，**match_phrase（匹配短语）**，**fuzzy（模糊匹配等）**，**term（严格匹配）**，**range（范围匹配）** 等，这些代表了不同的搜索方式，自然格式不同。

es 在为这些简单的条件搜索增加了一些功能，比如可以设置匹配值的与或关系，多字段匹配可以设定不同值（区别与键）的全重，匹配短语可以设置可以跳过的单词数量等，简单的查询都可以在 https://github.com/madhusudhankonda/elasticsearch-in-action/blob/main/kibana_scripts/ch2_getting_started.txt 看到。