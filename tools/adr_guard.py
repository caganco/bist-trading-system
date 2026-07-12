#!/usr/bin/env python3
"""ADR immutability guard.

ADR-0000 says an accepted decision record is frozen: it is changed by writing a new
record that supersedes it, never by editing it in place. Without enforcement that is a
promise, not a property. This turns it into one.

What is frozen, once a record leaves Proposed: the title, the Date, Supersedes, any
other front-matter field, and every `##` section body. What may still change: the
`Status` line, the `Superseded-by` pointer, and the `Related` list -- exactly the
fields you need to touch when a later record supersedes this one.

Anything that is not explicitly mutable is frozen. A new front-matter field or a new
section is therefore covered by default rather than silently exempt.

Modes:
  --check         verify every record against docs/adr/.adr-lock.json (CI; writes nothing)
  --update-lock   record new records and legal status transitions in the lock (local only)

`--update-lock` is not an escape hatch: it refuses to run if any record fails the check,
so it can never launder an edited body into the lock.

Exit 0 = clean, 1 = violation, 2 = usage/parse error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ADR_DIR = Path(__file__).resolve().parent.parent / "docs" / "adr"
LOCK_PATH = ADR_DIR / ".adr-lock.json"

# Front-matter fields that stay editable after a record is frozen. Everything else --
# including fields not listed here and any future field -- is part of the frozen body.
MUTABLE_FIELDS = {"status", "superseded-by", "related"}

PROPOSED, ACCEPTED, SUPERSEDED, DEPRECATED = "proposed", "accepted", "superseded", "deprecated"
FROZEN_STATES = {ACCEPTED, SUPERSEDED, DEPRECATED}

# Only these transitions are legal on a frozen record. Everything absent from this map is
# refused rather than assumed benign: a decision cannot be returned to draft, and a
# superseded or deprecated one cannot be brought back to life (ADR-0007).
LEGAL_TRANSITIONS = {
    (ACCEPTED, ACCEPTED),
    (ACCEPTED, SUPERSEDED),
    (ACCEPTED, DEPRECATED),
    (SUPERSEDED, SUPERSEDED),
    (DEPRECATED, DEPRECATED),
}

_FIELD_RE = re.compile(r"^-\s*\*\*(?P<name>[^:*]+):\*\*\s*(?P<value>.*)$")
_ADR_FILE_RE = re.compile(r"^ADR-(\d{4})-.+\.md$")


class AdrError(Exception):
    """A record could not be parsed. Never swallowed -- an unreadable record is a failure."""


def _normalize(text: str) -> str:
    """Canonical form for hashing.

    Line endings collapse to LF and trailing whitespace is stripped, so a checkout that
    converts to CRLF (or an editor that leaves a trailing space) cannot masquerade as a
    tampered decision. Blank lines are kept: they are content, and dropping them would
    make the hash blind to a real edit.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def classify_status(raw: str) -> str:
    """Map a Status value onto a lifecycle state. An unknown value is an error, not a pass."""
    s = raw.strip().lower()
    if s.startswith("proposed"):
        return PROPOSED
    if s.startswith("accepted"):
        return ACCEPTED
    if s.startswith("superseded"):
        return SUPERSEDED
    if s.startswith("deprecated"):
        return DEPRECATED
    raise AdrError(f"unrecognised Status value: {raw!r}")


def parse_record(path: Path) -> tuple[str, str]:
    """Return (lifecycle_state, frozen_hash) for one record.

    The frozen hash covers the whole file minus the mutable front-matter lines. The
    front matter ends at the first `##` heading -- bullets inside a section body (a
    Consequences list, say) are content, not fields.
    """
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    body_start = next((i for i, ln in enumerate(lines) if ln.startswith("## ")), len(lines))

    status_raw: str | None = None
    frozen_lines: list[str] = []
    for i, line in enumerate(lines):
        if i < body_start:
            m = _FIELD_RE.match(line)
            if m:
                name = m.group("name").strip().lower()
                if name == "status":
                    status_raw = m.group("value")
                if name in MUTABLE_FIELDS:
                    continue  # editable after freezing -- excluded from the hash
        frozen_lines.append(line)

    if status_raw is None:
        raise AdrError("no Status field")

    frozen = _normalize("\n".join(frozen_lines))
    return classify_status(status_raw), hashlib.sha256(frozen.encode("utf-8")).hexdigest()


def discover(adr_dir: Path) -> dict[str, Path]:
    return {
        m.group(0).split("-")[0] + "-" + m.group(1): p
        for p in sorted(adr_dir.glob("ADR-*.md"))
        if (m := _ADR_FILE_RE.match(p.name))
    }


def evaluate(adr_dir: Path, lock: dict) -> tuple[list[str], dict]:
    """Return (violations, next_lock). Never raises for a violation -- it reports one."""
    violations: list[str] = []
    records = discover(adr_dir)
    next_lock: dict[str, dict] = {}

    for adr_id, path in sorted(records.items()):
        try:
            state, frozen_hash = parse_record(path)
        except AdrError as exc:
            violations.append(f"{adr_id}: cannot parse ({exc}) [{path.name}]")
            continue

        prior = lock.get(adr_id)

        if prior is None:
            # Not yet locked. A draft is not tracked; a frozen record is adopted on the
            # next --update-lock. Reported so it cannot drift unnoticed, but not fatal.
            if state in FROZEN_STATES:
                next_lock[adr_id] = {"status": state, "frozen_hash": frozen_hash}
            continue

        prior_state = prior.get("status", "")
        prior_hash = prior.get("frozen_hash", "")

        if state == PROPOSED:
            violations.append(f"{adr_id}: frozen record returned to Proposed [{path.name}]")
            next_lock[adr_id] = prior
            continue

        if (prior_state, state) not in LEGAL_TRANSITIONS:
            violations.append(
                f"{adr_id}: illegal status transition {prior_state} -> {state} [{path.name}]"
            )
            next_lock[adr_id] = prior
            continue

        if frozen_hash != prior_hash:
            violations.append(f"{adr_id}: frozen body modified [{path.name}]")
            next_lock[adr_id] = prior
            continue

        next_lock[adr_id] = {"status": state, "frozen_hash": frozen_hash}

    for adr_id in lock:
        if adr_id not in records:
            violations.append(f"{adr_id}: locked record is missing (there is no Deleted state)")

    return violations, next_lock


def load_lock(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"ADR GUARD: lock file is not valid JSON ({exc})\n")
        raise SystemExit(2) from exc
    return data.get("records", data)


def write_lock(path: Path, records: dict) -> None:
    payload = {
        "_comment": "Byte reference for accepted decision records. Regenerate with "
                    "`python tools/adr_guard.py --update-lock`; CI verifies, never writes.",
        "records": dict(sorted(records.items())),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ADR immutability guard")
    ap.add_argument("--check", action="store_true", help="verify records against the lock (CI)")
    ap.add_argument("--update-lock", action="store_true", help="adopt new records and legal transitions")
    ap.add_argument("--adr-dir", default=str(ADR_DIR), help="records directory")
    args = ap.parse_args(argv)

    if args.check == args.update_lock:
        ap.error("choose exactly one of --check or --update-lock")

    adr_dir = Path(args.adr_dir)
    if not adr_dir.is_dir():
        sys.stderr.write(f"ADR GUARD: no records directory at {adr_dir}\n")
        return 2

    lock_path = adr_dir / ".adr-lock.json"
    lock = load_lock(lock_path)
    violations, next_lock = evaluate(adr_dir, lock)

    if violations:
        sys.stderr.write(f"ADR GUARD: {len(violations)} violation(s)\n\n")
        for v in violations:
            sys.stderr.write(f"  {v}\n")
        sys.stderr.write(
            "\nAn accepted decision is changed by superseding it, not by editing it.\n"
            "Write a new record; only Status, Superseded-by and Related may move.\n")
        return 1

    if args.update_lock:
        write_lock(lock_path, next_lock)
        sys.stderr.write(f"ADR GUARD: lock updated ({len(next_lock)} record(s))\n")
        return 0

    unlocked = sorted(set(next_lock) - set(lock))
    if unlocked:
        # Not a violation: a record can be added and locked in the same change. Surfaced
        # so an unlocked record cannot sit there unprotected without anyone noticing.
        sys.stderr.write(
            f"ADR GUARD: {len(unlocked)} record(s) not yet in the lock "
            f"({', '.join(unlocked)}); run --update-lock and commit it.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
