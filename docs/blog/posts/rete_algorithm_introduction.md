---
date: 2026-04-22
updated: 2026-10-06
slug: rete-algorithm-introduction-through-a-minimal-go-demo
summary: Derive Rete from a naïve rule matcher, then build a runnable Go example with shared filters, real joins, fact retraction, and a separate agenda.
---

# Rete: Incremental Rule Matching, from First Principles to Go

A rule engine repeatedly asks which combinations of current facts satisfy its rules. Rete keeps those matches up to date by remembering filtered facts and partial matches, then propagating changes through a shared network. We will derive that network and implement a small matcher in Go.

<!-- more -->

## 1. Start with the matching problem

Suppose an application holds account and flight records. A rule has a **left-hand side (LHS)** describing its conditions and a **right-hand side (RHS)** describing an action. The matcher must find every binding of facts that satisfies the LHS; one rule can have many simultaneous matches.

These terms name different parts of the system:

| Term | Meaning in this post |
| --- | --- |
| Fact | A record asserted into the engine, with an engine-assigned identity |
| Working memory | All currently asserted facts, including those that match no rule |
| Pattern | Constraints on a fact, possibly referring to variables bound by earlier patterns |
| Partial match / tuple | An ordered sequence of facts satisfying a prefix of a rule's conditions |
| Activation | A rule plus a complete matching tuple, eligible for action execution |
| Agenda | Pending activations waiting to be selected and executed |

Rete performs matching within the larger match–resolve–act cycle. The agenda chooses an activation, and its action may change working memory, causing another matching cycle. Finding a match and executing an action are separate operations. The [Drools execution documentation](https://docs.drools.org/6.5.0.Final/drools-docs/html/ch07.html) illustrates this separation.

```text
working-memory changes -> matcher -> agenda -> select and execute an action
          ^                                               |
          +------------- possible fact changes -----------+
```

A straightforward matcher can recompute every rule's matches after every insertion, deletion, or modification. That is correct, but repeats work on facts that have not changed. Rete retains intermediate results so it can maintain the matches incrementally.

## 2. Give the rules precise semantics

We will use `Account{ID, Status}` and `Flight{ID, AccountID, Miles, Airline}`. `Flight.AccountID` identifies the account that took the flight. The two rules are:

```text
BaseMiles:
    Flight f where f.Miles >= 500
    -> propose f.Miles base reward miles

GoldBonus:
    Account a where a.Status == "Gold"
    AND Flight f where f.Miles >= 500
                       AND f.Airline != "Partner"
                       AND f.AccountID == a.ID
    -> propose f.Miles additional reward miles for a
```

This is descriptive notation, not a rule language that our program parses. `BaseMiles` requires only a flight. `GoldBonus` requires a matching account as well. A qualifying flight for a Silver account can therefore receive a base proposal without a bonus proposal.

Gold status comes from the asserted account fact. If the application also models upgrades based on accumulated miles, an upgrade rule must update that fact and notify the matcher. Account ownership is checked separately by the join condition.

Both actions in our program print proposals. They do not update a reward balance, so the example can focus on matching and activation lifetime.

For comparison, a naïve implementation of the bonus rule might do this after each change:

```text
goldAccounts = filter(allAccounts, Status == "Gold")
eligibleFlights = filter(allFlights, Miles >= 500 AND Airline != "Partner")
matches = []
for a in goldAccounts:
    for f in eligibleFlights:
        if a.ID == f.AccountID:
            matches.append((a, f))
```

When one flight arrives, why repeat the filters for every existing account and flight, or retest all existing account–flight pairs?

## 3. Derive a network that retains the intermediate results

First separate conditions by what they need to inspect. `Status == "Gold"`, `Miles >= 500`, and `Airline != "Partner"` each inspect one fact: they are **alpha tests**. `a.ID == f.AccountID` needs bindings from two facts: it belongs in a **beta join**.

An **alpha memory** stores facts that pass a path of alpha tests. A **beta memory** stores tuples that match a prefix of the rule. A join extends each matching left tuple with a right fact. This vocabulary follows the [Rete section of the Drools documentation](https://docs.drools.org/6.5.0.Final/drools-docs/html/ch05.html).

For our rules, the network is:

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

The join tests `Account.ID == Flight.AccountID`. Type routing occurs before the first alpha test, so accounts never enter the flight filters.

| Memory | Contents | Go representation below |
| --- | --- | --- |
| `M_G` | Gold account facts | `gold.Memory` |
| `M_E` | Flights with at least 500 miles | `eligible.Memory` |
| `M_N` | Flights in `M_E` whose airline is not Partner | `other.Memory` |
| `B_G` | Singleton tuples `(Account)` | `left.Memory` |
| `B_B` | Joined tuples `(Account, Flight)` | `bonus.Memory` |

The tuple adapter turns one account fact into a one-element tuple. In this example, a pair in `B_B` is already a complete match. For a rule with a third pattern, that pair could instead become the left input of another join, producing a three-fact tuple.

`M_E` has two consumers: the base terminal and the non-partner filter. Both rules reuse the same `Miles >= 500` test and its memory. This is **structural sharing**. Reusing those stored results across successive fact changes is **temporal reuse**.

The terminals create or cancel activations. They do not execute actions during propagation. In a general engine, a compiler builds this graph from rule definitions; our constructor wires it explicitly.

## 4. Trace insertion from both sides

Assert `A1` with Gold status and `A2` with Silver status. Both remain in working memory, but only `A1` enters `M_G` and the singleton beta memory `B_G`. There is no bonus match yet because no flight has arrived.

Now insert these flights in order. Each row shows the memories **after** the insertion; names stand for the corresponding fact identities.

| Inserted flight | `M_E` | `M_N` | `B_B` | New activations |
| --- | --- | --- | --- | --- |
| `F1: A1, 2419 miles, Original` | `F1` | `F1` | `(A1, F1)` | Base `F1`; bonus `(A1, F1)` |
| `F2: A2, 800 miles, Original` | `F1, F2` | `F1, F2` | `(A1, F1)` | Base `F2` |
| `F3: A1, 300 miles, Original` | `F1, F2` | `F1, F2` | `(A1, F1)` | None |
| `F4: A1, 900 miles, Partner` | `F1, F2, F4` | `F1, F2` | `(A1, F1)` | Base `F4` |

`F1` passes both flight filters. Its **right activation** compares it with retained left tuples and produces `(A1, F1)`. `F2` passes the filters but fails the join with `A1`; `A2` is not in the Gold memory. `F3` stops at the miles test. `F4` passes the shared miles test and reaches the base terminal, but stops at the airline test.

Reverse the first two relevant arrivals: insert `F1` before `A1`. The right memory retains `F1`, but the join initially has no left tuple. When `A1` later arrives, its **left activation** compares `(A1)` with retained right facts and finds `F1`. A correct join must handle both directions.

For these pure positive conditions, the final match set depends on the current facts, not their insertion order. That does not guarantee identical action histories when actions modify facts or are fired between insertions.

## 5. Implement the matcher in Go

The implementation is available in [Kicey/rete-algorithm-demo](https://github.com/Kicey/rete-algorithm-demo). It uses only the standard library, and its Go module requires Go 1.25.4 or later. Read these files alongside the explanation:

- [main.go](https://github.com/Kicey/rete-algorithm-demo/blob/main/main.go) defines the facts, constructs the rule network, and supplies the actions and input sequence.
- [rete.go](https://github.com/Kicey/rete-algorithm-demo/blob/main/rete.go) implements identities, memories, joins, propagation, and agenda execution.
- [rete_test.go](https://github.com/Kicey/rete-algorithm-demo/blob/main/rete_test.go) compares incremental results with full recomputation.

The five code blocks below present the implementation in reading order.

### 5.1 Fact identity and tuples

An insertion returns a unique integer handle. Business IDs are used for joins; handles identify particular asserted facts. Inserting equal values twice creates two facts in this implementation. Applications requiring one account per business ID must enforce that separately.

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

`Tuple.Key` encodes the ordered handles, such as `1/3`. `extend` copies the slice before appending so sibling tuples cannot overwrite a shared backing array. Facts are passed as value structs containing only strings and integers; the engine retains immutable snapshots. This copy strategy would need reconsideration for pointers, slices, or maps inside facts.

### 5.2 Memories and propagation

`Push(x, true)` inserts a result; `Push(x, false)` removes it. Each memory updates its contents before notifying its consumers. Removal uses the retained value and does not repeat an alpha test against a potentially changed object.

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

The two memory types retain different things: facts on the alpha side and tuples on the beta side. Deduplication by handle or tuple key suppresses repeated propagation of the same retained result.

### 5.3 Join a new result with the retained opposite side

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

These methods are symmetric. A left event scans retained right facts; a right event scans retained left tuples. On insertion, matching pairs are added to the next beta memory. On removal, the same pairs are removed using their original handles. Reusing the predicate on removal is valid here because the retained fact snapshots never change.

This implementation scans the opposite memory instead of maintaining reverse dependency links. That keeps deletion understandable, but makes its cost proportional to the opposite memory's size.

### 5.4 Wire the graph and terminals

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

The constructor is the executable version of the diagram. `eligible.Out` shares the miles filter between the base terminal and `other`. `gold.Out` adapts accounts into tuples, and the join checks the actual account ID.

Each activation key combines a rule name and tuple identity. A terminal's insertion event schedules an action; its removal event cancels that pending action. Matching itself produces no output and changes no business records.

### 5.5 Working-memory operations and the executable trace

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

`Insert` and `Retract` use a type switch for routing. `Fire` drains the agenda in sorted activation-key order solely to make this example's output reproducible. It checks that each action is still pending before calling it. This ordering is a demonstration policy, not part of the Rete matching algorithm.

Clone the project and run its package and tests:

```bash
git clone https://github.com/Kicey/rete-algorithm-demo.git
cd rete-algorithm-demo
go run .
go test ./...
```

`git clone` downloads the source into a local directory, and `cd` enters it. From an existing checkout, start with `go run .`: it compiles and executes the current package without installing a binary. `go test ./...` runs tests for all packages under that directory. Go may write to its build cache; the demonstration keeps state in memory and prints to standard output, with no external packages or service.

Expected output:

```text
before retraction: eligible=3 nonPartner=2 gold=1 bonus=1 pending=4
after retraction: eligible=2 nonPartner=1 gold=1 bonus=0 pending=2
base F2: 800 miles
base F4: 900 miles
after account replacement: eligible=2 nonPartner=1 gold=2 bonus=1 pending=1
bonus A2/F2: 800 miles
```

Before the first `Fire`, there are four pending activations. Removing `F1` cancels its base and bonus activations, leaving only the base proposals for `F2` and `F4`. Replacing the Silver `A2` fact with a Gold snapshot later creates a bonus activation for the already retained `F2`.

The test suite in `rete_test.go` uses a separate naïve matcher as an oracle. It compares joined tuple identities and pending activations after every change, covering all 24 arrival permutations of four facts and 1,000 seeded insert/retract operations. Additional cases exercise replacement snapshots, predicate boundaries, cancellation before firing, repeated `Fire` calls, and independent storage for sibling tuples. This checks that incremental maintenance produces the same matches as full recomputation.

## 6. Retraction, modification, and action lifetime

Consider retracting `F1` by its handle. It leaves working memory and `M_E`. The removal then follows both consumers: the base terminal cancels its activation, and `M_N` removes the flight and notifies the join. The join removes `(A1, F1)` from `B_B`, causing the bonus terminal to cancel its activation.

Retracting `A1` follows the other path: remove it from `M_G`, remove its singleton tuple from `B_G`, then remove every joined tuple it supported. Other accounts and their matches remain retained.

Our example models a modification as two operations: retract the old handle, then insert a replacement snapshot. `main` does this for `A2`, changing its status from Silver to Gold. The business ID stays `A2`, while the engine handle changes. The newly admitted left tuple joins with the retained `F2` without reasserting that flight. Production engines can optimize updates and preserve handles; applications must still notify the engine of changes. See the [Drools update and deletion documentation](https://docs.drools.org/6.5.0.Final/drools-docs/html/ch07.html).

After `Fire`, the tuple remains in memory but its activation is no longer pending. Calling `Fire` again does nothing unless a subsequent change creates a new activation. Retracting and reinserting a fact creates a new match lifetime and may activate the rule again, even if its business values are identical.

**Removing a match does not undo an executed action.** If a reward was already written to a ledger, removing its supporting flight does not reverse that write. Compensation and idempotency belong to application policy. Likewise, automatically retracting facts logically derived by rules requires truth-maintenance support, which this matcher does not implement.

## 7. Derive the performance benefit and its limits

For one join, let `L` be its retained left tuples and `R` its retained right facts. Its result is the relational join `J = L ⋈ R`. For an insertion on one side while the other side stays unchanged:

```text
new left tuples ΔL:  new joined tuples ΔJ = ΔL ⋈ R
new right facts ΔR:  new joined tuples ΔJ = L ⋈ ΔR
```

The old join results stay in memory. We only compute the contribution of the new input. With deletions, we remove the joined tuples supported by the removed input. This is the connection between Rete and incremental maintenance of relational query results.

Let `l = |L|`, `r = |R|`, and `j = |J|`. Recomputing an unindexed join checks `l × r` candidate pairs. In our unindexed implementation, inserting one right fact checks `l` candidates; inserting one left tuple checks `r`. Removing one input also scans the opposite memory. These counts describe join-predicate evaluations; filtering, tuple construction, downstream propagation, and agenda processing add their own costs.

For example, with 1,000 Gold tuples and 10,000 qualifying flights, full recomputation considers 10 million pairs. One additional qualifying flight scans 1,000 Gold tuples. A hash index keyed by account ID could further restrict the candidates to the relevant account bucket, but that index is an additional optimization, not a consequence of merely storing memories.

The memories for one fixed-length join require space proportional to `l + r + j`, apart from working memory and the agenda. If every left tuple matches every right fact, `j` can reach `l × r`; chaining more joins can create even larger intermediate results. Storing matches does not eliminate that combinatorial growth.

Rete's benefit is strongest when rules share conditions, working memory changes incrementally, and retained partial results are useful across many changes. For a few simple rules evaluated once, direct code can be easier and cheaper. Rete has no blanket constant-time insertion guarantee and no unconditional speed advantage.

## 8. Scope and further reading

This program implements a manually constructed network for positive conditions, shared alpha filters, tuple joins, insertion/removal propagation, and a minimal agenda. A production engine also needs decisions about:

- Compiling rule definitions, ordering patterns, and sharing compatible beta paths.
- Indexing joins and tracking dependencies to reduce removal scans.
- Negation, existence, and aggregation, whose match lifetimes need additional bookkeeping.
- Agenda priorities, action-driven updates, and policies preventing unwanted repeated effects.
- Concurrency, fact ownership, and resource limits for large partial-match memories.

The reusable principle is to retain the results of each rule prefix and propagate changes to those results through the network. Alpha filtering, beta joining, and activation management make that principle concrete.

References:

- Charles L. Forgy, [*Rete: A Fast Algorithm for the Many Pattern/Many Object Pattern Match Problem*](https://doi.org/10.1016/0004-3702(82)90020-0), *Artificial Intelligence* 19(1), 17–37, 1982. The original algorithm paper.
- [Drools 6.5: Rete and ReteOO](https://docs.drools.org/6.5.0.Final/drools-docs/html/ch05.html). A versioned explanation of network structure and optimizations; its separate PHREAK section describes a later algorithm.
- [Drools 6.5: working memory and agenda](https://docs.drools.org/6.5.0.Final/drools-docs/html/ch07.html). Fact lifecycle and execution control in a full rule engine.
