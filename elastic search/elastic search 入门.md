# elastic search 入门

*学习 elasticsearch 也会在很大程度上帮助你理解 RESTful 的设计*

**基于 elasticsearhc 7，由 《elasticsearch 实战 第二版》总结而来（暂时没有翻译），随书源码仓库：**https://github.com/madhusudhankonda/elasticsearch-in-action**（源码中可能有些小问题暂时没有被修改，可以使用我的 fork 仓库** https://github.com/Kicey/elasticsearch-in-action**）**

*可能将 elasticsearch 称为 es。*

## 逻辑概念

- 索引 index：elasticsearch 中的索引和数据库索引不同，数据库索引索引是一种数据结构，而 elasticsearch 中的索引更像是某个数据库本身，一个 elasticsearch 中可以包含多个索引。
- 类型：类型并不是必须的，他用于规定某一类文档的通用的 metadata（元数据），目的是加快 elasticsearch 处理的速度和保证字段类型的准确。在没有类型，或者类型上的字段定义不能完全覆盖文档中出现的字段时，elasticsearch 将自动处理（可能存在“猜错“ 的情况）。**需要注意的是 elasticsearch 在 6 之后建议每个索引只保存一种类型的文档，在一个索引使用多个类型将会触发警告。**
- 文档：一个文档是 elasticsearch 中的最小记录逻辑记录单元，类似于数据库中的一条记录，是一个 NoSql 的数据结构，大多数时候以 Json 表示。

## 文档基本操作

elasticsearch 提供 RESTful 的 API 对文档的操作也是增删查改，语法设计的主要内容就是 HTTP 请求的动作，HTTP 请求的路径，请求体（这似乎是一句废话，不急，接着往下看）。

**注意不要去背语法！注意不要去背语法！注意不要去背语法！**

### 增

elasticsearch 中的增是由 HTTP PUT 方法完成的，路径指定使用的索引和文档 Id（索引无则自动创建，没有 Id 则随即生成），请求体是文档体（以 json 形式）。

使用 **_doc** 端点新增一个文档（books 即为文档归属的索引），1 即文档 Id

```
PUT books/_doc/1
{
  "title":"Effective Java",
  "author":"Joshua Bloch",
  "release_date":"2001-06-01",
  "amazon_rating":4.7,
  "best_seller":true,
  "prices": {
    "usd":9.95,
  }
}
```

除此之后可以通过一个请求新增多个文档，使用 **_mock** 端点

```
POST _bulk
{"index":{"_index":"books","_id":"1"}}
{"title": "Core Java Volume I â€“ Fundamentals","author": "Cay S. Horstmann","edition": 11, "synopsis": "Java reference book that offers a detailed explanation of various features of Core Java, including exception handling, interfaces, and lambda expressions. Significant highlights of the book include simple language, conciseness, and detailed examples.","amazon_rating": 4.6,"release_date": "2018-08-27","tags": ["Programming Languages, Java Programming"]}
{"index":{"_index":"books","_id":"2"}}
{"title": "Effective Java","author": "Joshua Bloch", "edition": 3,"synopsis": "A must-have book for every Java programmer and Java aspirant, Effective Java makes up for an excellent complementary read with other Java books or learning material. The book offers 78 best practices to follow for making the code better.", "amazon_rating": 4.7, "release_date": "2017-12-27", "tags": ["Object Oriented Software Design"]}
{"index":{"_index":"books","_id":"3"}}
```

注意这里的请求体并非是一个常规的 json，这里是使用 多个 json 组成的，每两个 json 为一组，前一个制定索引和 Id，后一个指定文档体。

### 查

*es 最主要的功能*

#### 计数

通过索引下的 **_count** 端点

```
GET /books/_count
```

根路径下的 **_count** 端点返回所有索引的文档数量。

#### 查询文档

##### 通过 Id 查询文档

通过索引下的 **_doc** 或 **_source** 端点和文档 Id

```
GET /books/_doc/1

GET /books/_source/1
```

#### 搜索文档（包括聚合）

通过索引下的 **_search** 端点和查询请求体

```
GET books/_search
{
  "query": {
    "match": {
      "author": "Joshua"
    }
  }
}
```

es 存在许多复杂请求基本都是依靠请求体进行的，于是新一篇：https://blog.kicey.site/elasticsearch-sou-suo/

## es 的模式结构

es 基于 Apache Lucene，一个 Java 语言的搜索库。一般依靠 Logstash 作为中间件获取数据，Kibana 展示。

es 支持集群以均衡负载方式增加可用性和冗余备份的方式增加分区容错性，本身以 NoSql（非关系）的形式组织数据，使用倒排索引等数据结构加快查找的速度。

新开一篇大致介绍一下 es 的结构：https://blog.kicey.site/elasticsearch-luo-ji-jie-gou/

## es 数据类型和相关操作

es 支持多种的数据类型，对不同的数据类型上有不同的操作。例如常用的 text 类型，用于全文搜索（full-text），在文档插入时，需要先进行符号化，以及正规化。