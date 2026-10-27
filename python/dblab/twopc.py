"""Two-phase commit (2PC), the classic atomic-commit protocol for distributed transactions.

Phase 1 (prepare): the coordinator asks every participant "can you commit?".
Phase 2 (decide):  if all voted yes it tells everyone to commit, otherwise to abort.

The coordinator writes its decision to a log *before* telling anyone, so that
after a crash it can finish the transaction instead of leaving participants
blocked in the PREPARED state.
"""

from __future__ import annotations

__all__ = ["Participant", "Coordinator"]


class Participant:
    """A resource manager (for example, one database shard)."""

    def __init__(self, name: str, will_commit: bool = True) -> None:
        self.name = name
        self.will_commit = will_commit
        self.state = "INIT"

    def prepare(self, txn_id: str) -> bool:
        self.state = "PREPARED" if self.will_commit else "ABORTED"
        return self.will_commit

    def commit(self, txn_id: str) -> None:
        if self.state != "PREPARED":
            raise RuntimeError(f"{self.name}: cannot commit from state {self.state}")
        self.state = "COMMITTED"

    def abort(self, txn_id: str) -> None:
        self.state = "ABORTED"


class Coordinator:
    def __init__(self, participants: list[Participant]) -> None:
        self.participants = participants
        self.log: list[tuple[str, str, str]] = []  # (event, txn_id, detail)

    def run(self, txn_id: str) -> bool:
        """Run one distributed transaction. Returns True if it committed."""
        self.log.append(("BEGIN", txn_id, ""))

        all_yes = True
        for p in self.participants:
            if not p.prepare(txn_id):
                all_yes = False
                break  # one "no" is enough to abort

        decision = "COMMIT" if all_yes else "ABORT"
        self.log.append(("DECISION", txn_id, decision))  # durable before any notification

        for p in self.participants:
            if decision == "COMMIT":
                p.commit(txn_id)
            else:
                p.abort(txn_id)
        self.log.append(("END", txn_id, decision))
        return all_yes
