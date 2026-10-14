#!/usr/bin/env python3
"""Deploy the NZCSC archive challenges to a CTFd instance over its REST API.

Source of truth is data/*.json (+ attachments in files/). Designed to run in
CI: set CTFD_URL and CTFD_TOKEN, then `python tools/deploy_challenges.py`.

Idempotent & additive — it NEVER deletes challenges, flags, or files, and it
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
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA_DIR = os.path.join(REPO, "data")
FILES_DIR = os.path.join(REPO, "files")


def esc(s):
    return html.escape(s or "")


ABOUT_URL = "/about"


def is_incomplete(ch):
    """A notes-only stub: nothing a solver can actually attempt — no prompt, no
    description, no files, no connection info. All we recovered is the solve
    method. These are shown as "under construction" rather than dressing the
    solve notes up as the challenge."""
    return not (
        (ch.get("prompt") or "").strip()
        or (ch.get("desc") or "").strip()
        or ch.get("files")
        or (ch.get("connection_info") or "").strip()
    )


def build_desc(year, ch):
    """The CTFd description = the *playable* part only. The recovered solve
    `method` is no longer embedded here; it is stored as the challenge's writeup
    (see set_meta) and rendered by the theme as its own section. Notes-only
    stubs get an "under construction" placeholder instead."""
    if is_incomplete(ch):
        return (
            "<p><i class='fas fa-person-digging'></i> <strong>Under construction.</strong> "
            "We don't have enough information to recreate this challenge yet — "
            "only notes from the solve archive, which you'll find in the writeup "
            "below.</p>"
            "<p style='opacity:.85'>Know this one? See the "
            "<a href='%s'>About page</a> for how to help fill it in.</p>" % ABOUT_URL
        )
    topic = ch.get("topic") or ""
    diff = ch.get("difficulty") or ""
    val = ch.get("value") or 0
    meta = []
    if topic:
        meta.append("<strong>Category:</strong> " + esc(topic))
    if diff:
        meta.append("<strong>Difficulty:</strong> " + esc(diff) + ((" (%d pts)" % val) if val else ""))
    d = ""
    if meta:
        d += "<p style='opacity:.85'>" + " &middot; ".join(meta) + "</p>"
    if ch.get("prompt"):
        d += ch["prompt"]  # trusted HTML prompt (recovered original)
    elif ch.get("desc"):
        d += "<p>" + esc(ch["desc"]) + "</p>"
    if not ch.get("flag"):
        d += ("<p style='opacity:.6;font-size:.85em;margin-top:1rem'>"
              "<em>Flag not recovered — archived for reference.</em></p>")
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

    data_files = args.files or sorted(glob.glob(os.path.join(args.data_dir, "*.json")))
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
    print("connected to %s — %d challenges already present\n" % (args.url, len(existing)))

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

            # tag (topic) — add if absent
            topic = ch.get("topic")
            if topic:
                have = {t.get("value") for t in ([] if args.dry_run else api.challenge_tags(cid))}
                if topic not in have:
                    api.add_tag(cid, topic); tot["tags"] += 1

            # flag — only if present in data, only if not already there
            fl = ch.get("flag")
            if fl:
                have = {f.get("content") for f in ([] if args.dry_run else api.challenge_flags(cid))}
                if fl not in have:
                    api.add_flag(cid, fl); tot["flags"] += 1

            # files — attach any not already present (match by basename)
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

    print("\nDONE (dry_run=%s): %s" % (args.dry_run, tot))


if __name__ == "__main__":
    main()
