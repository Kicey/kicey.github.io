---
date: 2026-04-22
summary: A practical introduction to the Rete algorithm using a minimal Go demo, focusing on fact propagation through rules and why node memories make matching efficient.
---

# Rete Algorithm Introduction Through a Minimal Go Demo

<!-- more -->

This post explains the Rete algorithm through a small Go implementation in [Kicey/rete-algorithm-demo](https://github.com/Kicey/rete-algorithm-demo). The goal is to make Rete less abstract by following one concrete runtime trace.

I focus on two questions:

1. How does Rete process facts on a rule set?
2. Why is it efficient with node memory?

The demo is intentionally small, but it still shows the core ideas from classic Rete writeups:

- A discrimination network (type and single-fact condition filtering)
- Join nodes for cross-fact matching
- Memory on alpha and beta sides to avoid repeated full scans

------

## 1. The Rule Set Used in the Demo

The sample domain is airline rewards with two fact types:

- `Account`
- `Flight`

Three rules are modeled:

1. If `Account.RewardMiles > 100000`, assign Gold status.
2. If `Flight.Miles >= 500`, reward flight miles.
3. If account is Gold and flight airline is not partner, reward 100% bonus miles.

In the code, rule 3 is represented as a join between:

- Left side: accounts that passed the Gold-related alpha condition
- Right side: flights that passed `Flight.Airline != "Partner"`

------

## 2. Network Shape (What Gets Built Once)

The demo constructs the network at startup (`main.go`) and runs facts through it (`rete.go`):

1. `ReteNode` root receives all asserted facts.
2. `ObjectTypeNode` branches by Go type (`Account` vs `Flight`).
3. `AlphaNode` checks single-fact conditions (for example `Miles >= 500`).
4. `AlphaMemory` stores matched facts and forwards them.
5. `BetaNode` joins left tuples with right facts.
6. `BetaMemory` stores left facts, right facts, and joined tuples.
7. `TerminalNode` executes actions when a rule is fully matched.

This directly mirrors the alpha-network + beta-network separation described in the two referenced articles.

------

## 3. How Facts Are Processed on the Rule Set

Now follow the runtime log step by step.

### Step A: Assert `Account{ID:Joe123, RewardMiles:150000, Status:Unknown}`

The log shows this path:

1. Root receives the account fact.
2. `ObjectTypeNode(Account)` matches type.
3. Alpha condition `Account.RewardMiles > 100000` passes.
4. `AlphaMemory` stores the account fact.
5. Terminal for "Assign Gold Status" fires.
6. The same matched account is also sent to the join's left input (`BetaNode-LeftActivate`).

Important detail: after this step, there is still no joined rule firing yet, because the right-side flight fact for the join has not arrived.

### Step B: Assert `Flight{Miles:2419, Category:Economy, Airline:Original}`

The log then shows two independent alpha matches on the flight branch:

1. `Flight.Miles >= 500` passes.
2. Terminal for "Reward Flight Miles" fires.
3. `Flight.Airline != Partner` also passes.
4. That fact is stored and sent to join right input (`BetaNode-RightActivate`).

Now the join can complete:

1. `BetaNode` checks right fact against cached left facts.
2. A joined tuple `[Account, Flight]` is produced.
3. `BetaMemory` stores that tuple.
4. Terminal for "+100% Bonus Miles for Gold Status" fires.

So in one runtime cycle with two assertions, the engine executes:

- Gold assignment
- Flight miles reward
- Gold bonus reward

without manually re-checking every rule from scratch.

------

## 4. Why Memory Makes Rete Efficient

The speedup is mainly from remembering partial work.

### 4.1 Structural sharing: one test, many rules

The same alpha result (`Account.RewardMiles > 100000`) is reused:

- once for direct Gold assignment
- once as left input to the Gold+Flight join

Without a network, duplicated condition checks are common as rule count grows.

### 4.2 Temporal reuse: only process changes

When a new fact arrives, only relevant nodes are visited:

- Account fact never goes through flight alpha checks
- Flight fact never goes through account alpha checks

`ObjectTypeNode` and alpha memories prevent unrelated recomputation.

### 4.3 Incremental joins with cached sides

`BetaMemory` caches:

- `LeftFacts`
- `RightFacts`
- `Joined`

So when one side changes, the engine only combines the new/changed side with the cached opposite side, instead of recomputing all pairings from zero.

### 4.4 Tradeoff: memory for speed

Rete pays extra memory to store matched and partially matched states. This is exactly the classic tradeoff highlighted in Rete literature: higher memory usage, much faster repeated matching on evolving fact sets.

------

## 5. A Compact Mental Model

You can think of this demo as:

- Alpha network answers: "Which individual facts satisfy which simple predicates?"
- Beta network answers: "Which combinations of already-matched facts satisfy cross-fact predicates?"
- Memories answer: "What have we already proven so we do not prove it again?"

That last point is the heart of Rete efficiency.

------

## 6. What This Demo Simplifies (Still Useful)

This implementation is intentionally minimal:

- It executes actions immediately instead of using a full agenda/conflict-resolution strategy.
- Its join condition in the sample always returns true after alpha filtering (real engines often join on business keys, such as account id).
- It demonstrates insertion/assertion flow only.

Even with these simplifications, it clearly shows the two core Rete ideas:

1. Facts propagate through a prebuilt network of tests.
2. Node memories make matching incremental and fast.

------

## References

- Repository: https://github.com/Kicey/rete-algorithm-demo
- README reference article 1: https://community.sap.com/t5/technology-blog-posts-by-sap/introduction-to-the-rete-algorithm/ba-p/13534504
- README reference article 2: https://www.sparklinglogic.com/rete-algorithm-demystified-part-2/
- Runtime trace used in this post: output log provided in this workspace discussion.

