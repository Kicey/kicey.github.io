---
date: 2026-04-22
summary: 基于一个最小 Go Demo 介绍 Rete 算法，重点说明事实如何在规则网络中传播，以及节点内存为何能显著提升匹配效率。
---

# 通过一个最小 Go Demo 理解 Rete 算法

<!-- more -->

这篇文章通过一个很小的 Go 实现来解释 Rete 算法：[Kicey/rete-algorithm-demo](https://github.com/Kicey/rete-algorithm-demo)。

目标很直接：不讲太多抽象概念，而是沿着一条真实运行日志，把 Rete 的处理过程走一遍。

我会聚焦两个核心问题：

1. Rete 是如何在规则集上处理事实（facts）的？
2. 为什么 Rete 借助节点内存（node memory）会更高效？

这个 Demo 虽然很简化，但已经覆盖了 Rete 的关键机制：

- 判别网络（按类型和单事实条件过滤）
- Join 节点（做跨事实组合匹配）
- Alpha/Beta 侧内存（保存中间结果，避免全量重复计算）

------

## 1. Demo 里的规则集

示例业务域是航空里程，包含两类事实：

- `Account`
- `Flight`

实现了 3 条规则：

1. 如果 `Account.RewardMiles > 100000`，则账户升级为 Gold。
2. 如果 `Flight.Miles >= 500`，则奖励飞行里程。
3. 如果账户是 Gold 且航班不是合作航司，则奖励 100% bonus miles。

在代码里，第 3 条规则通过一个 Join 表达：

- 左输入：通过 Gold 相关 alpha 条件的 Account
- 右输入：通过 `Flight.Airline != "Partner"` 的 Flight

------

## 2. 网络结构（一次构建，多次复用）

Demo 在启动时构建网络（`main.go`），运行时由各节点处理事实（`rete.go`）：

1. `ReteNode` 根节点接收所有事实断言。
2. `ObjectTypeNode` 按 Go 类型分流（`Account` / `Flight`）。
3. `AlphaNode` 评估单事实条件（例如 `Miles >= 500`）。
4. `AlphaMemory` 存储匹配成功的事实并向下游传播。
5. `BetaNode` 把左侧元组与右侧事实做 Join。
6. `BetaMemory` 保存左事实、右事实以及 Join 后的元组。
7. `TerminalNode` 在规则完整满足后执行动作。

这与两篇参考文章中讲的 alpha network + beta network 分层是一致的。

------

## 3. 事实是如何在规则集里被处理的

下面直接按运行日志来走。

### 步骤 A：断言 `Account{ID:Joe123, RewardMiles:150000, Status:Unknown}`

日志对应流程如下：

1. 根节点收到 Account 事实。
2. `ObjectTypeNode(Account)` 类型匹配成功。
3. Alpha 条件 `Account.RewardMiles > 100000` 通过。
4. `AlphaMemory` 存储该 Account。
5. 终端节点触发规则 "Assign Gold Status"。
6. 同一个匹配结果继续流向 Join 左输入（`BetaNode-LeftActivate`）。

关键点：此时 Join 规则还不会触发，因为右侧 Flight 事实尚未到达。

### 步骤 B：断言 `Flight{Miles:2419, Category:Economy, Airline:Original}`

日志显示该 Flight 在飞行分支上命中了两个 alpha 条件：

1. `Flight.Miles >= 500` 通过。
2. 终端节点触发规则 "Reward Flight Miles"。
3. `Flight.Airline != Partner` 也通过。
4. 该 Flight 被送入 Join 右输入（`BetaNode-RightActivate`）。

这时 Join 条件终于完整：

1. `BetaNode` 用右事实去匹配缓存的左事实。
2. 产生 joined tuple：`[Account, Flight]`。
3. `BetaMemory` 保存该组合。
4. 终端节点触发 "+100% Bonus Miles for Gold Status"。

所以在这次运行里，随着两个事实依次进入网络，依次触发了：

- Gold 状态赋值
- 航班里程奖励
- Gold 额外奖励

并且整个过程不需要“每来一个事实就从头遍历所有规则”。

------

## 4. 为什么“节点内存”让 Rete 高效

Rete 的效率核心在于：保存并复用部分匹配结果。

### 4.1 结构复用：一次匹配，多处使用

同一个 alpha 结果（`Account.RewardMiles > 100000`）被复用于：

- 直接触发 Gold 赋值规则
- 作为 Join 的左输入参与复合规则

规则越多、公共条件越多，这种复用收益越大。

### 4.2 时间复用：只处理变化，不全量重算

新事实进入时，只会走相关分支：

- Account 不会跑 Flight 的 alpha 检查
- Flight 不会跑 Account 的 alpha 检查

`ObjectTypeNode` + `AlphaMemory` 一起避免了大量无关计算。

### 4.3 增量 Join：利用两侧缓存做组合

`BetaMemory` 会缓存：

- `LeftFacts`
- `RightFacts`
- `Joined`

因此当某一侧新增事实时，只需要和另一侧已缓存结果做增量组合，而不是每次从零开始做全量笛卡尔式尝试。

### 4.4 本质权衡：用内存换速度

Rete 通过存储匹配态与部分匹配态换取运行效率，这是经典的时间-空间权衡：

- 代价：内存占用上升
- 收益：对“持续变化但每次变化不大”的事实集合，匹配速度显著提升

------

## 5. 一个便于记忆的心智模型

可以把这个 Demo 理解成三句话：

- Alpha 网络回答：哪些“单个事实”满足哪些基础条件？
- Beta 网络回答：哪些“事实组合”满足跨对象条件？
- 节点内存回答：哪些结论我们已经算过，不要再重复算？

第三句就是 Rete 高效的核心。

------

## 6. 这个 Demo 简化了什么（但不影响理解核心）

这个实现是教学导向，做了刻意简化：

- 动作是立即执行的，没有完整 agenda / conflict resolution 流程。
- 样例里的 Join 条件在 alpha 过滤后恒为 true（真实系统通常还会按业务键关联，例如账户 ID）。
- 主要展示了 assert（插入）路径。

即便如此，它仍然非常清楚地展示了 Rete 的两个本质：

1. 事实在预构建的网络中传播并逐层过滤。
2. 节点内存让匹配可以增量化，从而更快。

------

## 参考资料

- 仓库： https://github.com/Kicey/rete-algorithm-demo
- README 引用文章 1： https://community.sap.com/t5/technology-blog-posts-by-sap/introduction-to-the-rete-algorithm/ba-p/13534504
- README 引用文章 2： https://www.sparklinglogic.com/rete-algorithm-demystified-part-2/
- 本文运行轨迹来源：本次工作区对话中提供的运行日志。
