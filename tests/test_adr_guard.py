"""Tests for the ADR immutability guard.

Each test builds a throwaway records directory, so nothing here touches the real
`docs/adr/`. The guard is exercised through its CLI entry point, which is what CI calls.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.adr_guard import main

RECORD = """# ADR-{num}: {title}

- **Status:** {status}
- **Date:** 2026-07-12
- **Supersedes:** none
- **Superseded-by:** {superseded_by}
- **Related:** {related}

## Context
{context}

## Options Considered
- **The rejected one.** Rejected: it does not hold.
- **The chosen one (chosen).**

## Decision
{decision}

## Consequences
- **Positive:** the record is durable.
- **Accepted cost:** a short authoring step.

## Invariants
{invariants}
"""


def write_record(adr_dir: Path, num: str, *, status: str = "Accepted", superseded_by: str = "none",
                 related: str = "none", context: str = "Something had to be decided.",
                 decision: str = "This is what was decided.",
                 invariants: str = "This must always hold.", title: str = "A decision") -> Path:
    path = adr_dir / f"ADR-{num}-a-decision.md"
    path.write_text(
        RECORD.format(num=num, title=title, status=status, superseded_by=superseded_by,
                      related=related, context=context, decision=decision, invariants=invariants),
        encoding="utf-8")
    return path


def lock(adr_dir: Path) -> int:
    return main(["--update-lock", "--adr-dir", str(adr_dir)])


def check(adr_dir: Path) -> int:
    return main(["--check", "--adr-dir", str(adr_dir)])


@pytest.fixture()
def adr_dir(tmp_path: Path) -> Path:
    d = tmp_path / "adr"
    d.mkdir()
    write_record(d, "0000")
    assert lock(d) == 0
    assert check(d) == 0
    return d


def test_editing_the_decision_of_an_accepted_record_fails(adr_dir: Path) -> None:
    """(a) The whole point: a frozen decision cannot be quietly rewritten."""
    write_record(adr_dir, "0000", decision="Actually, something else was decided.")
    assert check(adr_dir) == 1


def test_superseding_an_accepted_record_passes(adr_dir: Path) -> None:
    """(b) Status and the pointer move; the body does not. This is the sanctioned path."""
    write_record(adr_dir, "0000", status="Superseded-by ADR-0001", superseded_by="ADR-0001",
                 related="ADR-0001")
    assert check(adr_dir) == 0


def test_adding_a_new_accepted_record_passes(adr_dir: Path) -> None:
    """(c) A new record is not a violation; it is adopted into the lock."""
    write_record(adr_dir, "0001", title="A later decision")
    assert check(adr_dir) == 0
    assert lock(adr_dir) == 0
    records = json.loads((adr_dir / ".adr-lock.json").read_text(encoding="utf-8"))["records"]
    assert set(records) == {"ADR-0000", "ADR-0001"}


def test_deleting_a_locked_record_fails(adr_dir: Path) -> None:
    """(d) There is no Deleted state. Removing the file is caught by the lock."""
    (adr_dir / "ADR-0000-a-decision.md").unlink()
    assert check(adr_dir) == 1


def test_reviving_a_superseded_record_fails(adr_dir: Path) -> None:
    """(e) A superseded decision cannot be brought back to life (ADR-0007)."""
    write_record(adr_dir, "0000", status="Superseded-by ADR-0001", superseded_by="ADR-0001")
    assert lock(adr_dir) == 0
    write_record(adr_dir, "0000", status="Accepted")
    assert check(adr_dir) == 1


def test_editing_a_proposed_record_passes(adr_dir: Path) -> None:
    """(f) A draft is not frozen yet, so it can still be worked on."""
    write_record(adr_dir, "0001", status="Proposed", decision="First attempt.")
    assert check(adr_dir) == 0
    write_record(adr_dir, "0001", status="Proposed", decision="Second attempt, quite different.")
    assert check(adr_dir) == 0


def test_whitespace_and_line_ending_changes_pass(adr_dir: Path) -> None:
    """(g) Normalisation: a CRLF checkout or a stray trailing space is not tampering.

    Without this the guard would fire on every Windows clone and be turned off within a day.
    """
    path = adr_dir / "ADR-0000-a-decision.md"
    text = path.read_text(encoding="utf-8")
    noisy = text.replace("\n", "   \n").replace("\n", "\r\n") + "\r\n\r\n"
    path.write_bytes(noisy.encode("utf-8"))
    assert check(adr_dir) == 0


def test_returning_a_frozen_record_to_proposed_fails(adr_dir: Path) -> None:
    """A frozen decision cannot be demoted back to a draft to make it editable again."""
    write_record(adr_dir, "0000", status="Proposed")
    assert check(adr_dir) == 1


def test_update_lock_refuses_to_launder_an_edited_body(adr_dir: Path) -> None:
    """--update-lock is not a bypass: it will not absorb a body that was edited."""
    write_record(adr_dir, "0000", decision="Rewritten behind the guard's back.")
    assert lock(adr_dir) == 1
    records = json.loads((adr_dir / ".adr-lock.json").read_text(encoding="utf-8"))["records"]
    original = records["ADR-0000"]["frozen_hash"]
    assert check(adr_dir) == 1
    # the lock still holds the original hash -- nothing was laundered
    assert records["ADR-0000"]["frozen_hash"] == original


def test_the_real_records_are_consistent_with_the_committed_lock() -> None:
    """The repository's own records match their lock. This is what CI enforces."""
    assert main(["--check"]) == 0
