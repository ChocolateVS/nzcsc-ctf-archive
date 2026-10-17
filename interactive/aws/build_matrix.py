#!/usr/bin/env python3
"""Emit the GitHub Actions build matrix for build-challenges.yml.

Reads interactive/aws/catalog.json plus the list of changed files (one path per
line on stdin) and the event name (argv[1]); prints {"include":[{tag,context}]}.

Builds EVERYTHING when:
  - the run is not a push (manual workflow_dispatch), or
  - the changed-file list is empty/unknown (e.g. first push, force-push), or
  - any shared tooling changed (catalog/build scripts, templates, this workflow),
otherwise builds ONLY the challenges whose build context has a changed file.
An empty include list means the downstream build job is skipped.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = (
    "interactive/aws/build_catalog.py",       # changes every entry's metadata
    "interactive/aws/build_matrix.py",        # this filter itself
    "interactive/gen_compose.py",
    "interactive/scaffold_comp.py",
    "interactive/templates/",                 # shared challenge templates
    ".github/workflows/build-challenges.yml",
)
# NOTE: interactive/aws/catalog.json is deliberately NOT shared - it is consumed
# by the launcher/agent/caddy at run time (flag/mem/env/port metadata), not baked
# into images, so a catalog-only change needs no image rebuild.


def main() -> int:
    cat = json.load(open(os.path.join(HERE, "catalog.json")))
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    changed = [ln.strip() for ln in sys.stdin.read().splitlines() if ln.strip()]

    build_all = (
        event != "push"
        or not changed
        or any(c.startswith(SHARED) for c in changed)
    )
    if build_all:
        entries = cat
    else:
        entries = [
            e for e in cat
            if any(c.startswith("interactive/" + e["context"] + "/") for c in changed)
        ]
    inc = [{"tag": e["image_tag"], "context": e["context"]} for e in entries]
    print(json.dumps({"include": inc}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
