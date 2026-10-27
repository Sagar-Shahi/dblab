# Distributed database management (DDM)

A distributed database stores data on several machines but presents it as one. People do this for **scale** (more data
or traffic than one machine handles), **availability** (survive a machine failing), and **latency** (keep data near users).
The price is that the network can fail, so every design is a set of trade-offs.

## 1. Fragmentation (sharding)

Splitting one logical table across nodes.

| Kind | How it splits | Example |
|------|---------------|---------|
| **Horizontal** | By rows | Customers in Kathmandu on node A, Pokhara on node B. |
| **Vertical** | By columns | `customers(id, name, city)` on one node, `customers(id, avatar)` on another. |
| **Hybrid** | Both | Region-split rows, with heavy columns stored separately. |

How to choose which node owns a row:

- **Range**: `id 1-1M` on A, `1M-2M` on B. Great for range queries, prone to hot spots.
- **Hash**: `hash(key) % n`. Even spread, but changing `n` moves almost every key.
- **Consistent hashing**: keys and nodes share one ring, so a node change moves only about `1/n` of keys.
  Implemented in [Python](../python/dblab/sharding.py), [Java](../java/src/dblab/HashRing.java) and [C++](../cpp/hash_ring.hpp).

```
              node A
          .-----o-----.
        k1             o  node B
        |      ring     |      key -> first node clockwise
        o  node D      k2
          '-----o-----'
              node C
```

The tests prove the claim: adding a fifth node to a four-node ring moves under 30% of 5000 keys (ideal: 20%), and
every moved key lands on the new node. Plain modulo hashing would move about 80%.

**Virtual nodes** give each physical node many positions on the ring, which evens out load and lets stronger machines own more.

## 2. Replication

Keep several copies of each fragment.

- **Leader-follower**: writes go to one leader, which streams changes to followers. Simple, but the leader is a bottleneck and
  failover must be handled carefully.
- **Multi-leader**: several nodes accept writes, so you need conflict resolution (last-writer-wins, CRDTs, custom merge).
- **Leaderless / quorum** (Dynamo, Cassandra): a write goes to `N` replicas and succeeds with `W` acknowledgements; a read
  asks `R` replicas. If **`R + W > N`**, every read overlaps at least one up-to-date replica.

[`ShardedStore`](../python/dblab/sharding.py) is a small quorum model: with 3 replicas, a write needs 2 live copies and
raises `QuorumError` when only 1 is up, while reads survive any single failure.

## 3. CAP and PACELC

When the network partitions, you must choose between **Consistency** (every read sees the latest write, or an error) and
**Availability** (every request gets an answer, possibly stale). You cannot have both during a partition.

PACELC adds the everyday case: *else* (no partition), you still trade **Latency** against **Consistency**, because waiting
for more replicas is slower.

| System style | Leans toward |
|--------------|--------------|
| Single-leader SQL with sync replicas, etcd, ZooKeeper | CP |
| Dynamo-style stores, Cassandra with low quorums | AP |
| Spanner, CockroachDB | CP, with engineering to keep availability high |

## 4. Distributed transactions: two-phase commit

A transaction that touches several shards must commit on all of them or none.

1. **Prepare**: the coordinator asks every participant "can you commit?". A yes is a promise: the participant has made the
   change durable and holds its locks.
2. **Decide**: all yes → the coordinator logs `COMMIT` and tells everyone to commit; any no → `ABORT`.

The coordinator writes its decision to its log *before* notifying anyone, so a restarted coordinator can finish the job.
See [`twopc.py`](../python/dblab/twopc.py) and its tests.

**The weakness**: if the coordinator dies after participants have prepared, they are stuck holding locks until it returns
(2PC is *blocking*). Alternatives: **three-phase commit**, **consensus** (Paxos or Raft replicating the coordinator), and
**sagas** (a chain of local transactions with compensating actions, common in microservices).

## 5. Consensus

Raft and Paxos let a group of nodes agree on a sequence of values even if some fail, as long as a majority is alive.
Raft splits the problem into **leader election**, **log replication**, and **safety**. It is the foundation of etcd, Consul,
CockroachDB, and TiKV. A good next project for this repo: implement leader election over the in-process nodes.

## 6. Distributed query processing

- **Push work to the data**: filter and aggregate on each shard, then merge the small results.
- **Shuffle** only when you must (a join on a column that is not the shard key moves rows between nodes).
- **Co-locate** tables that are joined often by sharding both on the same key.
- A query that includes the shard key hits one node; one that does not becomes a **scatter-gather** across all nodes.

## 7. Checklist for designing a distributed data layer

1. What is the shard key, and does it spread both data and traffic evenly?
2. Which queries become cross-shard, and can the schema avoid them?
3. What consistency does each operation really need (a bank transfer vs. a "likes" counter)?
4. What happens during a partition, and during a node replacement?
5. How do you rebalance without downtime?

## Further reading

- *Designing Data-Intensive Applications*, chapters 5 to 9
- The Raft paper, "In Search of an Understandable Consensus Algorithm"
- The Dynamo paper, "Dynamo: Amazon's Highly Available Key-value Store"
- Jepsen.io analyses of real databases under failure
