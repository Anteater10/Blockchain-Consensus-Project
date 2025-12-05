## Running the System & Manual Tests

### How to Run the Nodes

From the **project root directory**:

1. Open **5 separate terminals**.
2. In each terminal, run one of:

```bash
./run/run_p1.sh
./run/run_p2.sh
./run/run_p3.sh
./run/run_p4.sh
./run/run_p5.sh
```

Each node should print something like:

```
=== Node Startup Summary ===
  Node ID     : 1
  Host        : 127.0.0.1
  Port        : 9101
  Data dir    : data/P1
  Peers       : [2, 3, 4, 5]
============================
[NODE 1] Network initialized
[CLI 1] Ready...
```

---

## Manual Test Plan

---

## ✅ PART 1 — Basic Sanity Tests

### Test 1 — 5 Nodes Start Correctly

**Goal:** Ensure networking initializes and all nodes boot without crashing.

**Steps:**

1. Open 5 terminals.
2. Run:

```bash
./run/run_p1.sh
./run/run_p2.sh
./run/run_p3.sh
./run/run_p4.sh
./run/run_p5.sh
```

**Expected:**

- Each node prints startup summary.
- Some initial “connect failed” messages are normal.
- All peers eventually connect.
- CLI prompt appears on all nodes.

---

### Test 2 — printBalance, printBlockchain

On any node:

```
printBalance
printBlockchain
```

Expected balances:

```
P1: 100
P2: 100
P3: 100
P4: 100
P5: 100
```

Expected blockchain:

```
=== Blockchain ===
(empty)
```

---

### Test 3 — Single moneyTransfer

On P1:

```
moneyTransfer 2 10
```

Expected logs:

- start_proposal
- PROMISE
- ACCEPTED
- DECIDE

Blockchain should contain:

```
depth 0: P1 -> P2, amount=10
```

Balances should be:

- P1 = 90  
- P2 = 110  
- Others = 100  

---

## ✅ PART 2 — Intermediate Tests

### Test 4 — Multiple Transfers in Sequence

Commands:

P1:
```
moneyTransfer 2 10
```

P2:
```
moneyTransfer 3 5
```

P3:
```
moneyTransfer 4 20
```

Expected blockchain:

| depth | tx              |
|-------|-----------------|
| 0     | P1 → P2 (10)    |
| 1     | P2 → P3 (5)     |
| 2     | P3 → P4 (20)    |

---

### Test 5 — Simultaneous Proposals

On P1 (don’t hit enter yet):

```
moneyTransfer 2 10
```

On P2 (don’t hit enter yet):

```
moneyTransfer 3 15
```

Hit ENTER on both quickly.

Expected:

One and only one value chosen at depth 0.

---

### Test 6 — Crash During Consensus

On P1:

```
moneyTransfer 2 10
```

During PREPARE logs, on P5:

```
failProcess
```

Expected:

- Paxos still reaches DECIDE (quorum=3).
- P1–P4 apply the block.
- Restarting P5 loads blockchain.json correctly.

---

### Test 7 — Crash Before DECIDE Delivery

Kill a node during ACCEPTED messages.

Expected:

A majority already accepted → value still decides.

---

## ✅ PART 3 — Edge Cases

### Edge Case 1 — Insufficient Funds

```
moneyTransfer 2 999999
```

Expected:

- "Insufficient funds"
- No Paxos messages
- No block added

---

### Edge Case 2 — Out-of-Order Startup

Start P3, P4, P5.
Then start P1, P2.

Expected:

- Many initial connect-failed messages (normal)
- Eventually stabilize and work

---

### Edge Case 3 — Node Down at Later Depth

1. Do 3 transfers.
2. Kill P3:
   ```
   failProcess
   ```
3. Do 2 more transfers.
4. Restart P3.

Expected:

- P3 remains behind
- P3 must not propose conflicting blocks

---

### Edge Case 4 — Repeated Transfers at Same Node

Spam:

```
moneyTransfer 2 1
moneyTransfer 2 1
moneyTransfer 2 1
...
```

Expected:

- Depth increments by 1 each time
- All nodes agree on the entire chain

---

### Edge Case 5 — Corrupt Files (Optional)

Manually delete the last entry in blockchain.json for one node.

Restart.

Expected:

- Node loads shorter chain
- Paxos prevents conflicting proposals

