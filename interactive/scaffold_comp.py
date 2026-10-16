#!/usr/bin/env python3
"""Scaffold per-challenge folders for a competition from a CTFd challenges.json.

Classifies each challenge and drops a ready-to-fill folder under
comps/<comp>/challenges/<NN-slug>/ (copied from the matching template, with a populated
challenge.yml). Files-only challenges are skipped (CTFd serves those). Never overwrites
an existing folder, so it's safe to re-run as new challenges appear.

  python3 scaffold_comp.py <comp> [path/to/challenges.json]
"""
import os, sys, re, json, pathlib, shutil

ROOT = pathlib.Path(__file__).resolve().parent
TYPE_TEMPLATE = {"http": "http-api", "static": "static-site", "tcp": "tcp-service"}
DEFAULT_PORT = {"http": 5000, "static": 80, "tcp": 1337}
OSINT_RE = re.compile(r"osint|profile|github|linkedin|twitter|instagram|sighting|mayor|reddit|"
                      r"find (the|this) (person|account)", re.I)


def slugify(name):
    name = re.sub(r"^\s*\d+\s*-\s*", "", name or "")
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "challenge"


def classify(c):
    desc = c.get("description") or ""
    conn = c.get("connection_info") or ""
    m = re.search(r"chall(\d+)\.r0\.nzcsc\.org\.nz", desc)
    challnn = m.group(1) if m else ""
    nc = bool(re.search(r"\bnc\b|netcat", desc)) or bool(conn)
    if nc and not challnn:
        return "tcp", challnn
    if challnn:
        return "http", challnn
    return "files", challnn   # no site + no service -> CTFd serves the attachment


def main():
    if len(sys.argv) < 2:
        print("usage: scaffold_comp.py <comp> [challenges.json]", file=sys.stderr)
        return 2
    comp = sys.argv[1]
    src = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else \
        pathlib.Path("/opt/containers/config/apps/ctf-dashboard/state/challenges.json")
    if not src.exists():
        print("challenges.json not found: %s" % src, file=sys.stderr)
        return 1
    raw = json.loads(src.read_text())
    chs = raw if isinstance(raw, list) else raw.get("data", [])
    chdir = ROOT / "comps" / comp / "challenges"
    chdir.mkdir(parents=True, exist_ok=True)

    made, skipped_files, existed = [], [], []
    for c in sorted(chs, key=lambda x: x.get("id", 0)):
        cid = c.get("id")
        name = c.get("name") or ""
        typ, challnn = classify(c)
        slug = slugify(name)
        folder = chdir / ("%02d-%s" % (int(cid), slug) if str(cid).isdigit() else slug)
        if typ == "files":
            skipped_files.append("%s %s (files-only)" % (cid, slug))
            continue
        if folder.exists():
            existed.append(folder.name)
            continue
        shutil.copytree(ROOT / "templates" / TYPE_TEMPLATE[typ], folder)

        lines = ["id: %s" % cid, "slug: %s" % slug, "name: %s" % name.replace(":", " -"),
                 "type: %s" % typ, "port: %d" % DEFAULT_PORT[typ]]
        if typ in ("http", "static"):
            lines.append("subdomain: chall%s" % (challnn or ("%02d" % int(cid))))
            lines.append("local_only: true")
        if typ == "tcp":
            lines.append("tcp_port: %d" % (10000 + int(cid) if str(cid).isdigit() else 10000))
        lines.append("mem_limit: 256m")
        lines.append("# Real flag goes in comps/%s/flags.env (key %s or %s)." % (comp, cid, slug))
        if OSINT_RE.search(c.get("description") or ""):
            lines.append("# NOTE: looks OSINT-flavoured - the solve may depend on external")
            lines.append("#       profiles/pages the author controls; only the site is replicable here.")
        (folder / "challenge.yml").write_text("\n".join(lines) + "\n")
        made.append("%s -> %s" % (folder.name, typ))

    print("scaffolded %d challenge folder(s) for %s:" % (len(made), comp))
    for m in made:
        print("  + %s" % m)
    if existed:
        print("kept existing (not overwritten): %s" % ", ".join(existed))
    print("files-only (skipped, CTFd serves): %d" % len(skipped_files))
    print("\nNext: fill in each app from its source, add flags to flags.env, then:")
    print("  ./manage.sh %s up" % comp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
