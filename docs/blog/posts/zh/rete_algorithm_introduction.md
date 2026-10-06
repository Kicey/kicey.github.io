---
date: 2026-04-22
updated: 2026-10-06
slug: rete-算法从基本原理到-go-增量规则匹配器
summary: 从朴素规则匹配器推导 Rete，并用可运行的 Go 示例实现共享过滤、真实关联、事实撤回，以及独立的待执行议程。
---

# Rete 算法：从基本原理到 Go 增量规则匹配器

规则引擎反复回答一个问题：当前事实的哪些组合满足规则？Rete 保存已经过滤的事实和部分匹配结果，让变化沿共享网络传播，从而持续维护匹配结果。本文先推导这个网络，再用 Go 实现一个小型匹配器。

<!-- more -->

## 1. 从匹配问题出发

假设应用保存了一批账户和航班记录。一条规则的**左部（LHS）**描述条件，**右部（RHS）**描述动作。匹配器需要找出所有满足左部条件的事实绑定；同一条规则可以同时具有多个匹配。

下面这些术语分别指向系统的不同部分：

| 术语 | 本文中的含义 |
| --- | --- |
| 事实（fact） | 断言到引擎中的记录，具有引擎分配的身份标识 |
| 工作内存（working memory） | 当前所有已断言的事实，也包括不匹配任何规则的事实 |
| 模式（pattern） | 对事实的约束，可以引用此前模式绑定的变量 |
| 部分匹配 / 元组（tuple） | 满足规则条件某个前缀的有序事实序列 |
| 激活项（activation） | 一条规则及其完整匹配元组，具备执行动作的资格 |
| 议程（agenda） | 等待选择和执行的激活项集合 |

Rete 负责“匹配—选择—执行”循环中的匹配环节。议程选出一个激活项，其动作可能修改工作内存，进而引发下一轮匹配。找到匹配和执行动作是两个独立操作。[Drools 的执行文档](https://docs.drools.org/6.5.0.Final/drools-docs/html/ch07.html)展示了这种分工。

```text
工作内存发生变化 -> 匹配器 -> 议程 -> 选择激活项并执行动作
       ^                                  |
       +------------ 可能修改事实 ---------+
```

一种直接的实现是在每次插入、删除或修改事实后，重新计算所有规则的匹配。这样做是正确的，但会反复处理没有变化的事实。Rete 保留中间结果，从而增量维护这些匹配。

## 2. 明确定义示例规则

我们使用 `Account{ID, Status}` 和 `Flight{ID, AccountID, Miles, Airline}`。`Flight.AccountID` 标识该航班所属的账户。两条规则如下：

```text
BaseMiles：
    航班 f 满足 f.Miles >= 500
    -> 提议奖励 f.Miles 基础里程

GoldBonus：
    账户 a 满足 a.Status == "Gold"
    且航班 f 满足 f.Miles >= 500
                 且 f.Airline != "Partner"
                 且 f.AccountID == a.ID
    -> 提议为 a 额外奖励 f.Miles 里程
```

这只是规则的描述方式，程序不会解析这种语法。`BaseMiles` 只要求一个航班事实，`GoldBonus` 还需要匹配的账户。因此，Silver 账户的合格航班可以产生基础奖励提议，而不产生额外奖励提议。

Gold 状态来自已断言的账户事实。如果应用还要根据累计里程处理升级，升级规则必须更新该事实并通知匹配器。航班归属则由关联条件单独检查。

程序的两个动作都只打印奖励提议，不修改里程余额，以便专注于匹配和激活项的生命周期。

作为对照，朴素的额外奖励匹配器可能在每次变化后执行：

```text
goldAccounts = filter(allAccounts, Status == "Gold")
eligibleFlights = filter(allFlights, Miles >= 500 AND Airline != "Partner")
matches = []
for a in goldAccounts:
    for f in eligibleFlights:
        if a.ID == f.AccountID:
            matches.append((a, f))
```

只新增一个航班时，为什么还要重新过滤所有既有账户和航班，并重新检查所有既有账户与航班的组合？

## 3. 推导一个保留中间结果的网络

先按条件需要检查的信息分类。`Status == "Gold"`、`Miles >= 500` 和 `Airline != "Partner"` 各自只检查一个事实，属于 **Alpha 测试**。`a.ID == f.AccountID` 需要来自两个事实的绑定，应该放在 **Beta 关联节点（join）**中。

**Alpha 内存**保存通过某条 Alpha 测试路径的事实。**Beta 内存**保存满足规则某个前缀的元组。关联节点把匹配的右侧事实追加到左侧元组中。这套术语沿用 [Drools 文档中的 Rete 章节](https://docs.drools.org/6.5.0.Final/drools-docs/html/ch05.html)。

本例的网络如下：

```text
Account --> [Status == Gold] --> M_G --> [tuple adapter] --> B_G --+
                                            	                   | left
                                                	               v
                                                    	         [Join] --> B_B --> T_bonus
                                                        	       ^
                                                            	   | right
Flight --> [Miles >= 500] --> M_E --> [Airline != Partner] --> M_N-+
                              |
                              +--> T_base
```

关联节点检查 `Account.ID == Flight.AccountID`。类型分流发生在第一个 Alpha 测试之前，所以账户不会进入航班过滤分支。

| 内存 | 保存的内容 | 下文 Go 实现中的对应字段 |
| --- | --- | --- |
| `M_G` | Gold 账户事实 | `gold.Memory` |
| `M_E` | 至少飞行 500 英里的航班 | `eligible.Memory` |
| `M_N` | `M_E` 中航司不是 Partner 的航班 | `other.Memory` |
| `B_G` | 单元素元组 `(Account)` | `left.Memory` |
| `B_B` | 关联后的元组 `(Account, Flight)` | `bonus.Memory` |

元组适配器（tuple adapter）把一个账户事实转换成单元素元组。本例中，`B_B` 中的二元组已经是完整匹配。如果规则还包含第三个模式，这个二元组可以继续作为下一个关联节点的左输入，生成包含三个事实的元组。

`M_E` 有两个下游：基础奖励终端和非合作航司过滤器。两条规则复用了同一个 `Miles >= 500` 测试及其内存，这就是**结构共享**。在连续的事实变化之间复用已经保存的结果，则是**时间上的复用**。

终端节点创建或取消激活项，不在传播过程中执行动作。通用引擎由编译器根据规则构建这张图；本例在构造函数中显式连接节点。

## 4. 跟踪左右两侧的插入

先断言 Gold 账户 `A1` 和 Silver 账户 `A2`。两个账户都保留在工作内存中，但只有 `A1` 进入 `M_G` 和单元素 Beta 内存 `B_G`。因为还没有航班，此时没有额外奖励匹配。

接着按顺序插入下表中的航班。每行展示的是插入**之后**的内存状态；名称代表相应的事实身份。

| 插入的航班 | `M_E` | `M_N` | `B_B` | 新增激活项 |
| --- | --- | --- | --- | --- |
| `F1: A1, 2419 miles, Original` | `F1` | `F1` | `(A1, F1)` | 基础奖励 `F1`；额外奖励 `(A1, F1)` |
| `F2: A2, 800 miles, Original` | `F1, F2` | `F1, F2` | `(A1, F1)` | 基础奖励 `F2` |
| `F3: A1, 300 miles, Original` | `F1, F2` | `F1, F2` | `(A1, F1)` | 无 |
| `F4: A1, 900 miles, Partner` | `F1, F2, F4` | `F1, F2` | `(A1, F1)` | 基础奖励 `F4` |

`F1` 通过两个航班过滤器。它的**右侧激活（right activation）**将其与已保存的左侧元组比较，生成 `(A1, F1)`。`F2` 通过过滤，但与 `A1` 的关联条件不成立；`A2` 又不在 Gold 内存中。`F3` 在里程测试处停止。`F4` 通过共享的里程测试，到达基础奖励终端，但在航司测试处停止。

现在交换最初两个相关事实的到达顺序：先插入 `F1`，再插入 `A1`。右侧内存会保存 `F1`，但关联节点最初没有左侧元组。等 `A1` 到达时，它的**左侧激活（left activation）**把 `(A1)` 与已保存的右侧事实比较，找到 `F1`。正确的关联节点必须支持这两个方向。

对于这些纯粹的正向条件，最终匹配集合取决于当前事实，而不取决于插入顺序。但如果动作修改事实，或者在插入之间执行动作，就不能据此推断动作执行历史也相同。

## 5. 用 Go 实现匹配器

实现位于 [Kicey/rete-algorithm-demo](https://github.com/Kicey/rete-algorithm-demo)。它只依赖标准库，Go 模块要求 Go 1.25.4 或更高版本。可以结合下列文件阅读：

- [main.go](https://github.com/Kicey/rete-algorithm-demo/blob/main/main.go) 定义事实、构建规则网络，并提供动作和输入序列。
- [rete.go](https://github.com/Kicey/rete-algorithm-demo/blob/main/rete.go) 实现身份标识、内存、关联、传播和议程执行。
- [rete_test.go](https://github.com/Kicey/rete-algorithm-demo/blob/main/rete_test.go) 将增量结果与完整重算进行比较。

下面五个代码块按阅读顺序展示实现。

### 5.1 事实身份与元组

每次插入返回一个唯一的整数句柄（handle）。业务 ID 用于关联，句柄用于标识某一次断言产生的具体事实。在本实现中，两次插入相同的值会产生两个事实。如果应用要求每个业务 ID 只能对应一个账户，需要单独保证这个约束。

```go
package main

import (
	"fmt"
	"sort"
	"strconv"
)

type Account struct{ ID, Status string }
type Flight struct {
	ID, AccountID string
	Miles         int
	Airline       string
}

// Fact is an immutable value snapshot identified by an insertion handle.
type Fact struct {
	Handle int
	Value  any
}

// Tuple retains ordered fact identities for a rule prefix.
type Tuple struct {
	Key   string
	Facts []Fact
}

func singleton(f Fact) Tuple {
	return Tuple{strconv.Itoa(f.Handle), []Fact{f}}
}

// Copy the prefix so sibling results never share a writable backing array.
func extend(t Tuple, f Fact) Tuple {
	facts := append([]Fact(nil), t.Facts...)
	return Tuple{t.Key + "/" + strconv.Itoa(f.Handle), append(facts, f)}
}
```

`Tuple.Key` 编码了有序句柄，例如 `1/3`。`extend` 在追加前复制切片，避免同级元组覆盖共享的底层数组。事实以值结构体传入，字段只有字符串和整数，因此引擎保留的是不可变快照。如果事实包含指针、切片或 map，就需要重新考虑复制策略。

### 5.2 内存与传播

`Push(x, true)` 插入一个结果，`Push(x, false)` 删除一个结果。每个内存先更新自身内容，再通知下游。删除使用此前保存的值，不会拿一个可能已经改变的对象重新执行 Alpha 测试。

```go
// Alpha combines a single-fact filter with its retained passing facts.
type Alpha struct {
	Test   func(any) bool
	Memory map[int]Fact
	Out    []func(Fact, bool)
}

func (a *Alpha) Push(f Fact, add bool) {
	if add {
		if !a.Test(f.Value) {
			return
		}
		if _, exists := a.Memory[f.Handle]; exists {
			return
		}
		a.Memory[f.Handle] = f
	} else {
		stored, exists := a.Memory[f.Handle]
		if !exists {
			return
		}
		f = stored
		delete(a.Memory, f.Handle)
	}
	for _, out := range a.Out {
		out(f, add)
	}
}

// Beta retains tuples and propagates insertions and removals to consumers.
type Beta struct {
	Memory map[string]Tuple
	Out    []func(Tuple, bool)
}

func (b *Beta) Push(t Tuple, add bool) {
	if add {
		if _, exists := b.Memory[t.Key]; exists {
			return
		}
		b.Memory[t.Key] = t
	} else {
		stored, exists := b.Memory[t.Key]
		if !exists {
			return
		}
		t = stored
		delete(b.Memory, t.Key)
	}
	for _, out := range b.Out {
		out(t, add)
	}
}
```

两种内存保存不同的内容：Alpha 侧保存事实，Beta 侧保存元组。按句柄或元组键去重，可以阻止同一个已保存结果被重复传播。

### 5.3 将新结果与另一侧已保存的结果关联

```go
// Join extends a left tuple with a right fact satisfying a pure predicate.
type Join struct {
	Left  *Beta
	Right *Alpha
	Test  func(Tuple, Fact) bool
	Next  *Beta
}

func (j *Join) LeftEvent(t Tuple, add bool) {
	for _, f := range j.Right.Memory {
		if j.Test(t, f) {
			j.Next.Push(extend(t, f), add)
		}
	}
}

func (j *Join) RightEvent(f Fact, add bool) {
	for _, t := range j.Left.Memory {
		if j.Test(t, f) {
			j.Next.Push(extend(t, f), add)
		}
	}
}
```

这两个方法是对称的：左侧事件扫描已保存的右侧事实，右侧事件扫描已保存的左侧元组。插入时，匹配的组合进入下一个 Beta 内存；删除时，根据原来的句柄删除相同组合。由于已保存的事实快照不会变化，这里可以在删除时复用关联谓词。

本实现扫描另一侧内存，而没有保存反向依赖链接。这样容易理解删除过程，但删除成本也会与另一侧内存的大小成正比。

### 5.4 连接网络与终端

```go
// Engine owns working memory and the manually wired demonstration network.
type Engine struct {
	next                  int
	facts                 map[int]Fact
	gold, eligible, other *Alpha
	left, bonus           *Beta
	pending               map[string]func()
}

func NewEngine() *Engine {
	alpha := func(test func(any) bool) *Alpha {
		return &Alpha{Test: test, Memory: make(map[int]Fact)}
	}
	e := &Engine{
		facts:    make(map[int]Fact),
		pending:  make(map[string]func()),
		left:     &Beta{Memory: make(map[string]Tuple)},
		bonus:    &Beta{Memory: make(map[string]Tuple)},
		gold:     alpha(func(v any) bool { return v.(Account).Status == "Gold" }),
		eligible: alpha(func(v any) bool { return v.(Flight).Miles >= 500 }),
		other:    alpha(func(v any) bool { return v.(Flight).Airline != "Partner" }),
	}
	terminal := func(rule string, action func(Tuple)) func(Tuple, bool) {
		return func(t Tuple, add bool) {
			key := rule + "/" + t.Key
			if add {
				e.pending[key] = func() { action(t) }
			} else {
				delete(e.pending, key)
			}
		}
	}
	base := terminal("base", func(t Tuple) {
		f := t.Facts[0].Value.(Flight)
		fmt.Printf("base %s: %d miles\n", f.ID, f.Miles)
	})
	e.bonus.Out = append(e.bonus.Out, terminal("bonus", func(t Tuple) {
		a := t.Facts[0].Value.(Account)
		f := t.Facts[1].Value.(Flight)
		fmt.Printf("bonus %s/%s: %d miles\n", a.ID, f.ID, f.Miles)
	}))
	j := &Join{
		Left: e.left, Right: e.other, Next: e.bonus,
		Test: func(t Tuple, f Fact) bool {
			return t.Facts[0].Value.(Account).ID == f.Value.(Flight).AccountID
		},
	}
	e.gold.Out = append(e.gold.Out, func(f Fact, add bool) {
		e.left.Push(singleton(f), add)
	})
	e.left.Out = append(e.left.Out, j.LeftEvent)
	e.eligible.Out = append(e.eligible.Out,
		func(f Fact, add bool) { base(singleton(f), add) }, e.other.Push)
	e.other.Out = append(e.other.Out, j.RightEvent)
	return e
}
```

构造函数就是网络图的可执行版本。`eligible.Out` 让基础奖励终端和 `other` 共享里程过滤器。`gold.Out` 把账户转换成元组，关联节点则检查实际的账户 ID。

每个激活项的键由规则名称和元组身份共同组成。终端收到插入事件时安排动作，收到删除事件时取消该待执行动作。匹配过程本身不产生输出，也不修改业务记录。

### 5.5 工作内存操作与可运行的执行过程

```go
// Insert allocates a fresh handle, even when business values are identical.
func (e *Engine) Insert(v any) int {
	switch v.(type) {
	case Account, Flight:
	default:
		panic("unsupported fact type")
	}
	e.next++
	f := Fact{e.next, v}
	e.facts[f.Handle] = f
	switch v.(type) {
	case Account:
		e.gold.Push(f, true)
	case Flight:
		e.eligible.Push(f, true)
	}
	return f.Handle
}

// Retract invalidates dependent tuples and cancels their pending actions.
func (e *Engine) Retract(handle int) {
	f, exists := e.facts[handle]
	if !exists {
		return
	}
	delete(e.facts, handle)
	switch f.Value.(type) {
	case Account:
		e.gold.Push(f, false)
	case Flight:
		e.eligible.Push(f, false)
	}
}

// Fire executes pending actions in key order for reproducible demo output.
func (e *Engine) Fire() {
	for len(e.pending) > 0 {
		keys := make([]string, 0, len(e.pending))
		for key := range e.pending {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		for _, key := range keys {
			if action, exists := e.pending[key]; exists {
				delete(e.pending, key)
				action()
			}
		}
	}
}

func (e *Engine) Report(label string) {
	fmt.Printf("%s: eligible=%d nonPartner=%d gold=%d bonus=%d pending=%d\n",
		label, len(e.eligible.Memory), len(e.other.Memory),
		len(e.left.Memory), len(e.bonus.Memory), len(e.pending))
}

func main() {
	e := NewEngine()
	e.Insert(Account{"A1", "Gold"})
	silver := e.Insert(Account{"A2", "Silver"})
	f1 := e.Insert(Flight{"F1", "A1", 2419, "Original"})
	e.Insert(Flight{"F2", "A2", 800, "Original"})
	e.Insert(Flight{"F3", "A1", 300, "Original"})
	e.Insert(Flight{"F4", "A1", 900, "Partner"})
	e.Report("before retraction")
	e.Retract(f1)
	e.Report("after retraction")
	e.Fire()
	e.Retract(silver)
	e.Insert(Account{"A2", "Gold"})
	e.Report("after account replacement")
	e.Fire()
}
```

`Insert` 和 `Retract` 使用类型 switch 分流。`Fire` 按激活项键的排序结果执行议程，只是为了让示例输出可复现；它在调用动作前会再次确认该动作仍然待执行。这种排序是示例的执行策略，不属于 Rete 匹配算法本身。

克隆项目，然后运行程序和测试：

```bash
git clone https://github.com/Kicey/rete-algorithm-demo.git
cd rete-algorithm-demo
go run .
go test ./...
```

`git clone` 将源码下载到本地目录，`cd` 进入该目录。如果已经有项目检出目录，直接从 `go run .` 开始：它编译并执行当前包，不安装可执行程序。`go test ./...` 运行该目录下所有包的测试。Go 可能写入构建缓存；演示程序只维护内存状态并向标准输出打印结果，不需要外部依赖包或服务。

预期输出如下：

```text
before retraction: eligible=3 nonPartner=2 gold=1 bonus=1 pending=4
after retraction: eligible=2 nonPartner=1 gold=1 bonus=0 pending=2
base F2: 800 miles
base F4: 900 miles
after account replacement: eligible=2 nonPartner=1 gold=2 bonus=1 pending=1
bonus A2/F2: 800 miles
```

第一次调用 `Fire` 之前共有四个待执行激活项。删除 `F1` 会取消它的基础奖励和额外奖励激活项，只留下 `F2` 和 `F4` 的基础奖励提议。之后把 Silver 账户 `A2` 替换成 Gold 快照，会为已经保存的 `F2` 创建额外奖励激活项。

`rete_test.go` 中的测试使用独立的朴素匹配器作为参照，在每次变化后比较关联元组身份和待执行激活项，覆盖四个事实的全部 24 种到达排列，以及 1,000 次固定随机种子的插入 / 撤回操作。其他用例检查替换快照、谓词边界、执行前取消、重复调用 `Fire`，以及同级元组的独立存储，从而验证增量维护与完整重算产生相同的匹配。

## 6. 撤回、修改与动作生命周期

考虑通过句柄撤回 `F1`。它先离开工作内存和 `M_E`，随后删除事件传给两个下游：基础奖励终端取消其激活项；`M_N` 删除航班并通知关联节点。关联节点再从 `B_B` 删除 `(A1, F1)`，使额外奖励终端取消其激活项。

撤回 `A1` 则走另一条路径：从 `M_G` 删除账户，从 `B_G` 删除对应的单元素元组，再删除所有由它支持的关联元组。其他账户及其匹配仍然保留。

本例用两个操作表示修改：撤回旧句柄，再插入替换快照。`main` 对 `A2` 执行了这一过程，把状态从 Silver 改为 Gold。业务 ID 仍然是 `A2`，但引擎句柄发生了变化。新进入的左侧元组与已保存的 `F2` 关联，不需要重新断言这个航班。生产级引擎可以优化更新过程并保留句柄，但应用仍须通知引擎事实发生了变化，参见 [Drools 的更新和删除文档](https://docs.drools.org/6.5.0.Final/drools-docs/html/ch07.html)。

`Fire` 之后，元组仍在内存中，但对应激活项不再待执行。如果后续没有变化创建新激活项，再次调用 `Fire` 不会执行任何动作。撤回后重新插入事实会建立新的匹配生命周期，即使业务值完全相同，也可能再次激活规则。

**删除匹配不会撤销已经执行的动作。** 如果奖励已经写入账本，删除支持它的航班事实并不会自动冲销记录。补偿和幂等性由应用策略负责。同样，自动撤回规则逻辑推导出的事实需要真值维护（truth maintenance）支持，本匹配器没有实现这一机制。

## 7. 推导性能收益及其边界

对于一个关联节点，记其已保存的左侧元组集合为 `L`，右侧事实集合为 `R`，结果就是关系关联 `J = L ⋈ R`。当只在一侧插入、另一侧保持不变时：

```text
新增左侧元组 ΔL：新增关联元组 ΔJ = ΔL ⋈ R
新增右侧事实 ΔR：新增关联元组 ΔJ = L ⋈ ΔR
```

旧的关联结果保留在内存中，只需计算新输入带来的贡献。删除时，则移除由被删输入支持的关联元组。这就是 Rete 与关系查询结果增量维护之间的联系。

设 `l = |L|`、`r = |R|`、`j = |J|`。完整重算一个没有索引的关联，需要检查 `l × r` 个候选组合。在本例没有索引的实现中，插入一个右侧事实检查 `l` 个候选，插入一个左侧元组检查 `r` 个候选；删除一个输入也需要扫描另一侧内存。这些数字只统计关联谓词求值次数，过滤、元组构造、下游传播和议程处理还有各自的成本。

例如，有 1,000 个 Gold 元组和 10,000 个合格航班时，完整重算需要考虑 1,000 万个组合。新增一个合格航班只扫描 1,000 个 Gold 元组。按账户 ID 建立哈希索引，还可以把候选限定到相应账户的桶中，但索引是额外优化，并不是只要保存内存就自动获得的能力。

对于一个元组长度固定的关联节点，内存占用与 `l + r + j` 成正比，这还没有计入工作内存和议程。如果每个左侧元组都能匹配每个右侧事实，`j` 就可能达到 `l × r`；串联更多关联节点还可能产生更大的中间结果。保存匹配不能消除这种组合增长。

当规则共享条件、工作内存每次变化较小，而且保留的部分结果能被后续变化反复利用时，Rete 的收益更明显。如果只有少量简单规则且只求值一次，直接编写匹配代码可能更容易、成本也更低。Rete 不保证插入总是常数时间，也不保证在所有情况下都更快。

## 8. 实现范围与延伸阅读

这个程序实现了手工构建的正向条件网络、共享 Alpha 过滤器、元组关联、插入 / 删除传播，以及最小议程。生产级引擎还需要处理以下问题：

- 编译规则定义、安排模式顺序，以及共享兼容的 Beta 路径。
- 为关联建立索引，并跟踪依赖以减少删除时的扫描。
- 否定、存在性和聚合条件，这些匹配的生命周期需要额外记录。
- 议程优先级、动作引起的更新，以及防止不期望的重复副作用的策略。
- 并发、事实所有权，以及大型部分匹配内存的资源限制。

可以复用的核心原则是：保存规则每个前缀的匹配结果，再让结果的变化沿网络传播。Alpha 过滤、Beta 关联和激活项管理把这个原则变成了具体机制。

参考资料：

- Charles L. Forgy，[《Rete: A Fast Algorithm for the Many Pattern/Many Object Pattern Match Problem》](https://doi.org/10.1016/0004-3702(82)90020-0)，*Artificial Intelligence* 19(1)，17–37，1982。算法的原始论文。
- [Drools 6.5：Rete 与 ReteOO](https://docs.drools.org/6.5.0.Final/drools-docs/html/ch05.html)。关于网络结构与优化的版本化说明；其中独立的 PHREAK 章节介绍了后来的算法。
- [Drools 6.5：工作内存与议程](https://docs.drools.org/6.5.0.Final/drools-docs/html/ch07.html)。完整规则引擎中的事实生命周期和执行控制。
