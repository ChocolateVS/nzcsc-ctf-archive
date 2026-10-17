#!/usr/bin/env python3
"""Deploy the NZCSC archive challenges to a CTFd instance over its REST API.

Source of truth is data/*.json (+ attachments in files/). data/notes.json adds
short notes to challenges that already exist in CTFd but aren't in data/ (e.g.
the 2026 rounds, which live only in the platform); data/hints.json adds native
CTFd hints to them the same way. Designed to run in
CI: set CTFD_URL and CTFD_TOKEN, then `python tools/deploy_challenges.py`.

Idempotent & additive - it NEVER deletes challenges, flags, or files, and it
NEVER invents a flag (flags are set only when present in the data). Re-running
is safe: existing challenges are updated in place (matched by category + the
leading "<num> - " in the name), missing flags/tags/files are added, and
anything already present is left alone.

  python tools/deploy_challenges.py [--dry-run] [data/data_2024.json ...]

With no file args it deploys every data/*.json. --dry-run does all reads and
prints the plan but makes no writes (safe without a token for the read checks).
"""
import argparse
import glob
import html
import os
import re
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA_DIR = os.path.join(REPO, "data")
NOTES_FILE = os.path.join(DATA_DIR, "notes.json")
HINTS_FILE = os.path.join(DATA_DIR, "hints.json")
EXTRA_FILES = {"notes.json", "hints.json"}
FILES_DIR = os.path.join(REPO, "files")


def esc(s):
    return html.escape(s or "")


ABOUT_URL = "/about"


def flag_forms(flag):
    """Every string that should be accepted as a correct flag for `flag`.

    The 2025 round used bare 16-char tokens, but the challenges display them
    wrapped as FLAG[...] (that's literally what a solver sees and copies). So we
    accept BOTH the bare token and the FLAG[...] form - a player can submit
    either. Only 2025-style tokens match the pattern; NZCSC{...} flags from
    other years are returned unchanged.
    """
    forms = [flag]
    if re.fullmatch(r"[A-Z0-9]{16}", flag):
        forms.append("FLAG[%s]" % flag)
    return forms


def is_incomplete(ch):
    """Not playable in the archive. A challenge can only be attempted here if it
    ships downloadable files or has a live connection (hosted instance). Web /
    remote challenges whose original server is gone have a description but nothing
    to actually do, so they're flagged "under construction" too - not just the
    notes-only stubs."""
    return not (ch.get("files") or (ch.get("connection_info") or "").strip())


def _meta_line(ch):
    topic = ch.get("topic") or ""
    diff = ch.get("difficulty") or ""
    val = ch.get("value") or 0
    meta = []
    if topic:
        meta.append("<strong>Category:</strong> " + esc(topic))
    if diff:
        meta.append("<strong>Difficulty:</strong> " + esc(diff) + ((" (%d pts)" % val) if val else ""))
    return ("<p style='opacity:.85'>" + " &middot; ".join(meta) + "</p>") if meta else ""


def _body(ch):
    """meta line + the recovered challenge text (prompt/desc), if any."""
    d = _meta_line(ch)
    if ch.get("prompt"):
        d += ch["prompt"]  # trusted HTML prompt (recovered original)
    elif ch.get("desc"):
        d += "<p>" + esc(ch["desc"]) + "</p>"
    return d


def build_desc(year, ch):
    """CTFd description. For playable challenges it's the meta + prompt/desc. For
    under-construction ones (no files, no live host) we prepend a maintenance
    banner and keep any recovered text as context; if there's no text at all we
    fall back to a "not enough info" placeholder. The solve `method` is not here
    - it's stored as the writeup (see set_meta) and rendered as its own section."""
    if is_incomplete(ch):
        banner = (
            "<p style='padding:.6rem .8rem;border:1px solid rgba(245,184,46,.4);"
            "border-radius:10px;background:rgba(245,184,46,.08);margin:0 0 1rem'>"
            "<i class='fas fa-person-digging'></i> <strong>Under construction.</strong> "
            "We don't have the original files or a live server to rebuild this one yet, "
            "so it isn't playable here and flag submission is disabled. Any recovered "
            "writeup is shown below.</p>"
        )
        body = _body(ch)
        if ch.get("prompt") or (ch.get("desc") or "").strip():
            return banner + body
        return banner + (
            "<p style='opacity:.85'>We don't have enough information to recreate this "
            "one yet. Know it? See the <a href='%s'>About page</a> for how to help "
            "fill it in.</p>" % ABOUT_URL
        )
    d = _body(ch)
    if not ch.get("flag"):
        d += ("<p style='opacity:.6;font-size:.85em;margin-top:1rem'>"
              "<em>Flag not recovered - archived for reference.</em></p>")
    return d


class CTFd:
    def __init__(self, url, token, dry_run=False):
        self.url = url.rstrip("/")
        self.dry = dry_run
        self.s = requests.Session()
        if token:
            self.s.headers["Authorization"] = "Token " + token
        self.s.headers["Content-Type"] = "application/json"

    def _get(self, path, **kw):
        r = self.s.get(self.url + path, timeout=30, **kw)
        r.raise_for_status()
        return r.json()

    def _write(self, method, path, **kw):
        if self.dry:
            return {"dry": True}
        r = getattr(self.s, method)(self.url + path, timeout=60, **kw)
        if r.status_code >= 400:
            raise SystemExit("%s %s -> %s %s" % (method.upper(), path, r.status_code, r.text[:300]))
        return r.json()

    def challenges(self):
        # admin view returns hidden challenges and full fields
        return self._get("/api/v1/challenges?view=admin")["data"]

    def challenge(self, cid):
        return self._get("/api/v1/challenges/%d?view=admin" % cid)["data"]

    def challenge_hints(self, cid):
        return self._get("/api/v1/hints", params={"challenge_id": cid})["data"]

    def add_hint(self, cid, content, cost):
        return self._write("post", "/api/v1/hints", json={
            "challenge_id": cid, "challenge": cid, "content": content, "cost": cost})

    def challenge_flags(self, cid):
        return self._get("/api/v1/challenges/%d/flags" % cid)["data"]

    def challenge_tags(self, cid):
        return self._get("/api/v1/challenges/%d/tags" % cid)["data"]

    def challenge_files(self, cid):
        return self._get("/api/v1/challenges/%d/files" % cid)["data"]

    def create_challenge(self, body):
        return self._write("post", "/api/v1/challenges", json=body)["data"]

    def patch_challenge(self, cid, body):
        return self._write("patch", "/api/v1/challenges/%d" % cid, json=body)["data"]

    def add_flag(self, cid, content):
        # send both FK spellings; marshmallow 2.x ignores the unknown one
        return self._write("post", "/api/v1/flags", json={
            "challenge_id": cid, "challenge": cid,
            "content": content, "type": "static", "data": ""})

    def set_meta(self, cid, incomplete, writeup):
        # best-effort: the nzcsc_feedback plugin owns this route. If it isn't
        # deployed yet (older box), don't fail the whole import.
        try:
            r = self.s.post(self.url + "/plugins/feedback/meta/%d" % cid, timeout=60,
                            json={"incomplete": bool(incomplete), "writeup": writeup or ""})
            return r.status_code < 400
        except Exception:
            return False

    def add_tag(self, cid, value):
        return self._write("post", "/api/v1/tags", json={
            "challenge_id": cid, "challenge": cid, "value": value})

    def add_file(self, cid, path):
        if self.dry:
            return {"dry": True}
        # multipart: drop the JSON content-type for this one request
        with open(path, "rb") as fh:
            r = self.s.post(self.url + "/api/v1/files",
                            data={"challenge_id": cid, "challenge": cid, "type": "challenge"},
                            files={"file": (os.path.basename(path), fh)},
                            headers={"Content-Type": None}, timeout=120)
        if r.status_code >= 400:
            raise SystemExit("POST /api/v1/files -> %s %s" % (r.status_code, r.text[:300]))
        return r.json()


def apply_notes(api, existing, path):
    """Append each note in notes.json to its challenge's description. The note is
    wrapped in marker comments and replaced (not duplicated) on re-run, so this
    is idempotent and safe to run after the main upsert rewrote a description."""
    import json
    if not os.path.isfile(path):
        return 0
    n = 0
    for note in json.load(open(path))["notes"]:
        cat, num, key = note["category"], str(note["num"]), note["key"]
        row = existing.get((cat, num))
        if row is None:
            print("  ! note %s: no challenge %s #%s" % (key, cat, num))
            continue
        start, end = "<!-- note:%s -->" % key, "<!-- /note:%s -->" % key
        block = "%s<p style='opacity:.85'>%s</p>%s" % (start, note["html"], end)
        cur = "" if api.dry else (api.challenge(row["id"]).get("description") or "")
        base = re.sub(r"\s*%s.*?%s" % (re.escape(start), re.escape(end)), "", cur, flags=re.S)
        new = base.rstrip() + "\n\n" + block
        if new != cur:
            api.patch_challenge(row["id"], {"description": new})
        n += 1
        print("  # note %s -> %s #%s" % (key, cat, num))
    return n


def apply_hints(api, existing, path):
    """Add each hint in hints.json to its challenge, in order, unless a hint with
    the same content is already there. Additive: never edits or deletes a hint, so
    rewording one adds a new hint - remove the old one in the admin UI."""
    import json
    if not os.path.isfile(path):
        return 0
    n = 0
    for entry in json.load(open(path))["hints"]:
        cat, num = entry["category"], str(entry["num"])
        row = existing.get((cat, num))
        if row is None:
            print("  ! hints: no challenge %s #%s" % (cat, num))
            continue
        have = {h.get("content") for h in ([] if api.dry else api.challenge_hints(row["id"]))}
        for h in entry["hints"]:
            h = h if isinstance(h, dict) else {"content": h}
            if h["content"] in have:
                continue
            api.add_hint(row["id"], h["content"], int(h.get("cost") or 0))
            n += 1
            print("  ? hint -> %s #%s" % (cat, num))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="data json files (default: all data/*.json)")
    ap.add_argument("--url", default=os.environ.get("CTFD_URL"))
    ap.add_argument("--token", default=os.environ.get("CTFD_TOKEN"))
    ap.add_argument("--data-dir", default=DATA_DIR)
    ap.add_argument("--files-dir", default=FILES_DIR)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.url:
        sys.exit("set CTFD_URL (or --url)")
    if not args.token and not args.dry_run:
        sys.exit("set CTFD_TOKEN (or --token); or use --dry-run")

    data_files = args.files or sorted(f for f in glob.glob(os.path.join(args.data_dir, "*.json"))
                                      if os.path.basename(f) not in EXTRA_FILES)
    if not data_files:
        sys.exit("no data files found")

    import json
    api = CTFd(args.url, args.token, dry_run=args.dry_run)

    # index existing challenges by (category, leading number)
    existing = {}
    for c in api.challenges():
        name = c.get("name") or ""
        lead = name.split(" - ", 1)[0].strip()
        existing[(c.get("category"), lead)] = c
    print("connected to %s - %d challenges already present\n" % (args.url, len(existing)))

    tot = dict(created=0, updated=0, flags=0, tags=0, files=0, missing=0, meta=0)
    for df in data_files:
        data = json.load(open(df))
        year, category = str(data["year"]), data["category"]
        print("== %s (%s) ==" % (os.path.basename(df), category))
        for ch in data["challenges"]:
            num = str(ch["num"])
            name = "%s - %s" % (num, ch["title"])
            value = int(ch.get("value") or 0)
            desc = build_desc(year, ch)
            body = {"name": name, "category": category, "description": desc,
                    "value": value, "type": "standard", "state": "visible"}
            if ch.get("connection_info") is not None:
                body["connection_info"] = ch["connection_info"]

            row = existing.get((category, num))
            if row is None:
                if args.dry_run:
                    print("  + CREATE %s (val %d)" % (name, value)); tot["created"] += 1
                    continue
                row = api.create_challenge(body)
                existing[(category, num)] = row
                tot["created"] += 1
                print("  + created %s" % name)
            else:
                if not args.dry_run:
                    api.patch_challenge(row["id"], body)
                tot["updated"] += 1
                print("  ~ updated %s" % name)

            cid = row["id"]

            # archive metadata: under-construction flag + recovered writeup
            # (rendered by the theme as its own section, not in the description)
            if not args.dry_run:
                if api.set_meta(cid, is_incomplete(ch), ch.get("method")):
                    tot["meta"] += 1

            # tag (topic) - add if absent
            topic = ch.get("topic")
            if topic:
                have = {t.get("value") for t in ([] if args.dry_run else api.challenge_tags(cid))}
                if topic not in have:
                    api.add_tag(cid, topic); tot["tags"] += 1

            # flag(s) - only if present in data, only those not already there.
            # flag_forms() may expand one data flag into several accepted forms
            # (e.g. a bare 2025 token + its FLAG[...] wrapper).
            fl = ch.get("flag")
            if fl:
                have = {f.get("content") for f in ([] if args.dry_run else api.challenge_flags(cid))}
                for form in flag_forms(fl):
                    if form not in have:
                        api.add_flag(cid, form); tot["flags"] += 1

            # files - attach any not already present (match by basename)
            for rel in (ch.get("files") or []):
                p = os.path.join(args.files_dir, rel)
                bn = os.path.basename(rel)
                if not os.path.isfile(p):
                    # a 2021-style path kept only in the live platform; fine if already attached
                    attached = {os.path.basename(f.get("location", "")) for f in ([] if args.dry_run else api.challenge_files(cid))}
                    if bn not in attached:
                        print("    ! file not in repo and not attached: %s" % rel); tot["missing"] += 1
                    continue
                attached = {os.path.basename(f.get("location", "")) for f in ([] if args.dry_run else api.challenge_files(cid))}
                if bn in attached:
                    continue
                api.add_file(cid, p); tot["files"] += 1
                print("    ^ attached %s" % bn)

    print("== notes ==")
    tot["notes"] = apply_notes(api, existing, NOTES_FILE)
    print("== hints ==")
    tot["hints"] = apply_hints(api, existing, HINTS_FILE)

    print("\nDONE (dry_run=%s): %s" % (args.dry_run, tot))


if __name__ == "__main__":
    main()
