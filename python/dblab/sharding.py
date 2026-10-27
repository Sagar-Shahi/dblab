"""Consistent hashing and a toy sharded, replicated key-value store.

Why consistent hashing? With ``hash(key) % n`` almost every key moves when
``n`` changes. On a hash ring only about ``1/n`` of the keys move when a node
joins or leaves, which is what makes elastic sharding practical.
"""

from __future__ import annotations

import bisect
import hashlib
from typing import Any, Iterable

__all__ = ["HashRing", "ShardedStore", "QuorumError"]


class QuorumError(Exception):
    """Not enough live replicas to accept a write."""


class HashRing:
    """Consistent hash ring with virtual nodes for an even key spread."""

    def __init__(self, nodes: Iterable[str] = (), vnodes: int = 128) -> None:
        if vnodes < 1:
            raise ValueError("vnodes must be >= 1")
        self.vnodes = vnodes
        self._ring: list[tuple[int, str]] = []  # sorted (position, node)
        self._nodes: set[str] = set()
        for node in nodes:
            self.add_node(node)

    @staticmethod
    def _hash(key: str) -> int:
        return int.from_bytes(hashlib.md5(key.encode("utf-8")).digest()[:8], "big")

    @property
    def nodes(self) -> list[str]:
        return sorted(self._nodes)

    def add_node(self, node: str) -> None:
        if node in self._nodes:
            return
        self._nodes.add(node)
        for i in range(self.vnodes):
            bisect.insort(self._ring, (self._hash(f"{node}#{i}"), node))

    def remove_node(self, node: str) -> None:
        if node not in self._nodes:
            raise KeyError(node)
        self._nodes.remove(node)
        self._ring = [entry for entry in self._ring if entry[1] != node]

    def get_node(self, key: str) -> str:
        return self.get_nodes(key, 1)[0]

    def get_nodes(self, key: str, count: int) -> list[str]:
        """Return up to ``count`` distinct nodes walking clockwise from the key."""
        if not self._ring:
            raise LookupError("the ring has no nodes")
        count = min(count, len(self._nodes))
        start = bisect.bisect_right(self._ring, (self._hash(key), "\U0010ffff"))
        found: list[str] = []
        for offset in range(len(self._ring)):
            node = self._ring[(start + offset) % len(self._ring)][1]
            if node not in found:
                found.append(node)
                if len(found) == count:
                    break
        return found


class ShardedStore:
    """In-memory key-value store spread over nodes with N-way replication.

    Writes go to every live replica and succeed when a quorum acknowledges.
    Reads are served by the first live replica that has the key. Rebalancing
    uses last-writer-wins, which is fine for a teaching model.
    """

    def __init__(self, nodes: Iterable[str], replicas: int = 3, vnodes: int = 128) -> None:
        nodes = list(nodes)
        if not 1 <= replicas <= len(nodes):
            raise ValueError("replicas must be between 1 and the number of nodes")
        self.replicas = replicas
        self.ring = HashRing(nodes, vnodes)
        self.data: dict[str, dict[str, Any]] = {n: {} for n in nodes}
        self.down: set[str] = set()

    @property
    def quorum(self) -> int:
        return self.replicas // 2 + 1

    def put(self, key: str, value: Any) -> int:
        """Write to live replicas. Returns the number of acknowledgements."""
        owners = self.ring.get_nodes(key, self.replicas)
        live = [n for n in owners if n not in self.down]
        if len(live) < self.quorum:
            raise QuorumError(f"{len(live)} of {len(owners)} replicas up, need {self.quorum}")
        for node in live:
            self.data[node][key] = value
        return len(live)

    def get(self, key: str) -> Any:
        for node in self.ring.get_nodes(key, self.replicas):
            if node not in self.down and key in self.data[node]:
                return self.data[node][key]
        raise KeyError(key)

    def fail(self, node: str) -> None:
        self.down.add(node)

    def recover(self, node: str) -> None:
        self.down.discard(node)

    def add_node(self, node: str) -> int:
        self.ring.add_node(node)
        self.data.setdefault(node, {})
        return self._rebalance()

    def remove_node(self, node: str) -> int:
        """Gracefully decommission a node and move its data to the survivors."""
        self.ring.remove_node(node)
        moved = self._rebalance()
        self.data.pop(node, None)
        self.down.discard(node)
        return moved

    def _rebalance(self) -> int:
        """Re-place every key. Returns how many (node, key) copies were new."""
        latest: dict[str, Any] = {}
        for kv in self.data.values():
            latest.update(kv)
        before = {(n, k) for n, kv in self.data.items() for k in kv}
        self.data = {n: {} for n in self.ring.nodes}
        for key, value in latest.items():
            for node in self.ring.get_nodes(key, self.replicas):
                self.data[node][key] = value
        after = {(n, k) for n, kv in self.data.items() for k in kv}
        return len(after - before)
