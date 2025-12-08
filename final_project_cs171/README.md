# 🚀 How to Run the Nodes

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

# 📘 Manual Test Plan

---

## ✅ PART 1 — Basic Sanity Tests

---

### **Test 1 — 5 Nodes Start Correctly**

**Goal:** Ensure networking initializes and all nodes boot without crashing.

**Steps:**
```
./run/run_p1.sh
./run/run_p2.sh
./run/run_p3.sh
./run/run_p4.sh
./run/run_p5.sh
```

**Expected:**
- Each node prints startup summary  
- Some initial connection-failed messages are normal  
- Peers eventually connect  
- CLI prompt appears on all nodes  

---

### **Test 2 — printBalance + printBlockchain**

On any node:
```
printBalance
printBlockchain
```

**Expected balances:**
```
P1: 100
P2: 100
P3: 100
P4: 100
P5: 100
```

**Expected blockchain:**
```
=== Blockchain ===
(empty)
```

---

### **Test 3 — Single moneyTransfer**

On **P1**:
```
moneyTransfer 2 10
```

**Expected logs:**
```
start_proposal
PROMISE
ACCEPTED
DECIDE
```

**Expected blockchain:**
```
depth 0: P1 -> P2, amount = 10
```

**Expected balances:**
```
P1 = 90
P2 = 110
Others = 100
```

---

## ✅ PART 2 — Intermediate Tests

---

### **Test 4 — Multiple Transfers in Sequence**

Commands:
```
# P1
moneyTransfer 2 10

# P2
moneyTransfer 3 5

# P3
moneyTransfer 4 20
```

**Expected blockchain:**

| depth | tx               |
|-------|------------------|
| 0     | P1 → P2 (10)     |
| 1     | P2 → P3 (5)      |
| 2     | P3 → P4 (20)     |

---

### **Test 5 — Simultaneous Proposals**

Prepare:

P1 (don’t press Enter yet):
```
moneyTransfer 2 10
```

P2 (don’t press Enter yet):
```
moneyTransfer 3 15
```

Press ENTER on both.

**Expected:**
- Only **one** proposal chosen at depth 0 (Paxos safety)

---

### **Test 6 — Crash During Consensus**

On P1:
```
moneyTransfer 2 10
```

During **PREPARE** logs on P5, run:
```
failProcess
```

**Expected:**
- Paxos still decides (quorum = 3)
- P1–P4 commit block
- Restart P5 → loads blockchain.json

---

### **Test 7 — Crash Before DECIDE Delivery**

Kill any follower during ACCEPTED logs (Ctrl-C).

**Expected:**
- Decision still completes (majority accepted)
- Restarted node catches up

---

## ✅ PART 3 — Edge Cases

---

### **Edge Case 1 — Insufficient Funds**

```
moneyTransfer 2 999999
```

**Expected:**
- `"Insufficient funds"`
- No Paxos messages
- No block added

---

### **Edge Case 2 — Out-of-Order Startup**

Startup order:
```
run_p3.sh
run_p4.sh
run_p5.sh
run_p1.sh
run_p2.sh
```

**Expected:**
- Many “connect failed” logs (normal)
- Nodes eventually sync

---

### **Edge Case 3 — Node Down at Later Depth**

Do 3 transfers.  
Kill P3:
```
failProcess
```

Do 2 more transfers.  
Restart P3:
```
./run/run_p3.sh
```

**Expected:**
- P3 remains behind initially
- Never proposes conflicting blocks
- Eventually syncs and matches others

---

### **Edge Case 4 — Repeated Transfers at Same Node**

Spam:
```
moneyTransfer 2 1
moneyTransfer 2 1
moneyTransfer 2 1
...
```

**Expected:**
- Depth increments steadily
- All nodes agree

---

### **Edge Case 5 — Corrupt Files (Optional)**

Delete last entry in blockchain.json for one node.  
Restart that node.

**Expected:**
- Node loads the shorter chain
- Paxos prevents divergence

---

## ✅ PART 4 — Additional Required Tests

---

### **Test 8 — Tentative vs Decided Logging**

On any node:
```
moneyTransfer 2 10
```

Open **ledger_log.json**.

**Expected:**
- PROMISE / ACCEPTED → **tentative**
- DECIDE → entry overwritten as **decided**

---

### **Test 9 — PoW Verification**

```
moneyTransfer 2 10
printBlockchain
```

**Expected:**
- hash ends in `{0,1,2,3,4}`
- prev_hash matches previous block
- nonce printed

---

### **Test 10 — Multi-Node Consistency (All 5 Nodes)**

On all nodes:
```
printBlockchain
printBalance
```

**Expected:**
- All blockchains identical
- All balances identical
- Total = **500**

---

### **Test 11 — Invalid Input Handling**

```
moneyTransfer 2 two
moneyTransfer 8 10
moneyTransfer 2 -5
moneyTransfer 2 0
```

**Expected:**
- Clean error messages
- No Paxos activity
- No new blocks

---

### **Test 12 — Proposer Crash + Recovery**

On P1:
```
moneyTransfer 2 10
```

Kill P1 **after DECIDE appears**.

Restart:
```
./run/run_p1.sh
```

**Expected:**
- P1 reloads blockchain from disk
- Matches other nodes

---

### **Test 13 — Long-Run Stress Test**

Repeatedly run:
```
moneyTransfer 2 1
moneyTransfer 3 1
moneyTransfer 4 1
moneyTransfer 5 1
```

**Expected:**
- Many blocks added without errors
- Total money = **500**

---

# ✅ End of Test Plan

---

If you want, I can also generate:

✅ A **TA-ready shortened version**  
✅ A **1-page demo script**  
✅ A **PDF version** with formatting  
