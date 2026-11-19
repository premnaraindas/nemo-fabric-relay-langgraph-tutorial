"""Summarize the Relay event files written under artifacts/relay (verification helper)."""
import collections
import json
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts/relay")
for path in sorted(root.rglob("events.atof.jsonl")):
    raw = path.read_text()
    events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    kinds = collections.Counter(f"{e.get('kind')}:{e.get('category')}:{e.get('scope_category')}" for e in events)
    print("FILE", path, "| events", len(events))
    print("  by kind:", dict(kinds))
    print("  names:", collections.Counter(str(e.get("name")) for e in events).most_common(12))
    emails = raw.count("jane.doe@example.com") + raw.count("billing.owner@example.com")
    print("  email addresses left:", emails, "| [REDACTED] markers:", raw.count("[REDACTED]"), "| 'guardrail' mentions:", raw.lower().count("guardrail"))
    for e in events:
        if e.get("category") == "tool":
            print("  tool event:", e.get("name"), e.get("scope_category"), json.dumps({k: e.get(k) for k in ("data", "metadata")})[:330])
    if events:
        print("  first event keys:", sorted(events[0].keys()))
