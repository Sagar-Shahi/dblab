import unittest

from dblab import Coordinator, HashRing, Participant, QuorumError, ShardedStore

KEYS = [f"user:{i}" for i in range(5000)]


class HashRingTests(unittest.TestCase):
    def test_deterministic(self):
        a, b = HashRing(["n1", "n2", "n3"]), HashRing(["n3", "n1", "n2"])
        self.assertTrue(all(a.get_node(k) == b.get_node(k) for k in KEYS))

    def test_adding_a_node_moves_only_a_fraction_of_keys(self):
        ring = HashRing(["n1", "n2", "n3", "n4"])
        before = {k: ring.get_node(k) for k in KEYS}
        ring.add_node("n5")
        moved = sum(before[k] != ring.get_node(k) for k in KEYS)
        # Ideal is 1/5 = 20%. Plain `hash % n` would move about 80%.
        self.assertLess(moved / len(KEYS), 0.30)
        # Keys only ever move *to* the new node.
        self.assertTrue(all(ring.get_node(k) == "n5" for k in KEYS if before[k] != ring.get_node(k)))

    def test_load_is_roughly_balanced(self):
        ring = HashRing(["n1", "n2", "n3", "n4"])
        counts = {n: 0 for n in ring.nodes}
        for k in KEYS:
            counts[ring.get_node(k)] += 1
        self.assertGreater(min(counts.values()), 0.6 * len(KEYS) / 4)

    def test_replica_nodes_are_distinct(self):
        ring = HashRing(["n1", "n2", "n3"])
        for k in KEYS[:200]:
            nodes = ring.get_nodes(k, 3)
            self.assertEqual(len(set(nodes)), 3)

    def test_empty_ring(self):
        with self.assertRaises(LookupError):
            HashRing().get_node("x")


class ShardedStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = ShardedStore(["a", "b", "c", "d", "e"], replicas=3)
        for k in KEYS[:500]:
            self.store.put(k, k.upper())

    def test_reads_survive_one_failure(self):
        self.store.fail("a")
        self.assertTrue(all(self.store.get(k) == k.upper() for k in KEYS[:500]))

    def test_write_needs_quorum(self):
        key = KEYS[0]
        owners = self.store.ring.get_nodes(key, 3)
        self.store.fail(owners[0])
        self.assertEqual(self.store.put(key, "ok"), 2)  # 2 of 3 is a quorum
        self.store.fail(owners[1])
        with self.assertRaises(QuorumError):
            self.store.put(key, "nope")

    def test_adding_a_node_keeps_all_data_readable(self):
        moved = self.store.add_node("f")
        self.assertGreater(moved, 0)
        self.assertLess(moved, 0.6 * 500 * 3)  # far fewer than reshuffling everything
        self.assertTrue(all(self.store.get(k) == k.upper() for k in KEYS[:500]))

    def test_removing_a_node_keeps_all_data_readable(self):
        self.store.remove_node("c")
        self.assertNotIn("c", self.store.data)
        self.assertTrue(all(self.store.get(k) == k.upper() for k in KEYS[:500]))
        for k in KEYS[:500]:
            copies = sum(k in kv for kv in self.store.data.values())
            self.assertEqual(copies, 3)


class TwoPhaseCommitTests(unittest.TestCase):
    def test_all_yes_commits(self):
        parts = [Participant("s1"), Participant("s2"), Participant("s3")]
        coordinator = Coordinator(parts)
        self.assertTrue(coordinator.run("t1"))
        self.assertEqual({p.state for p in parts}, {"COMMITTED"})
        self.assertEqual([e[0] for e in coordinator.log], ["BEGIN", "DECISION", "END"])
        self.assertEqual(coordinator.log[1][2], "COMMIT")

    def test_one_no_aborts_everyone(self):
        parts = [Participant("s1"), Participant("s2", will_commit=False), Participant("s3")]
        coordinator = Coordinator(parts)
        self.assertFalse(coordinator.run("t2"))
        self.assertEqual({p.state for p in parts}, {"ABORTED"})
        self.assertEqual(coordinator.log[1][2], "ABORT")


if __name__ == "__main__":
    unittest.main()
