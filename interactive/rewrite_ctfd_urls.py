#!/usr/bin/env python3
"""Point CTFd challenge descriptions at your LOCAL replicas instead of the real infra:

    challNN.r0.nzcsc.org.nz   ->   challNN.r0.2026.ctf.int.rowansserver.com

so the fleet (and you) hit the self-hosted copies. Run this AFTER the replica containers
are actually up - otherwise descriptions point at hosts that aren't serving yet.

  python3 rewrite_ctfd_urls.py [--base URL] [--token ctfd_...] [--dry-run] [--revert]

--token defaults to the admin token in /opt/containers/config/ctfd/admin_creds.txt.
--revert puts the original r0.nzcsc.org.nz hosts back.
"""
import sys, re, json, argparse, pathlib, urllib.request, urllib.error

CREDS = pathlib.Path("/opt/containers/config/ctfd/admin_creds.txt")


def admin_token():
    try:
        m = re.search(r"API token \(admin\):\s*(ctfd_\w+)", CREDS.read_text())
        return m.group(1) if m else ""
    except Exception:
        return ""


def api(base, token, method, path, data=None):
    req = urllib.request.Request(base + path, method=method,
                                 data=json.dumps(data).encode() if data is not None else None)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8781")
    ap.add_argument("--token", default=admin_token())
    ap.add_argument("--domain", default="r0.2026.ctf.int.rowansserver.com")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revert", action="store_true")
    a = ap.parse_args()
    if not a.token:
        print("no admin token (pass --token or fill admin_creds.txt)", file=sys.stderr)
        return 1

    to_local = (re.compile(r"chall(\d+)\.r0\.nzcsc\.org\.nz"), r"chall\1." + a.domain)
    to_orig = (re.compile(r"chall(\d+)\." + re.escape(a.domain)), r"chall\1.r0.nzcsc.org.nz")
    pat, repl = to_orig if a.revert else to_local

    lst = api(a.base, a.token, "GET", "/api/v1/challenges?view=admin").get("data", [])
    changed = 0
    for c in lst:
        cid = c["id"]
        full = api(a.base, a.token, "GET", "/api/v1/challenges/%d" % cid).get("data", {})
        desc = full.get("description") or ""
        new = pat.sub(repl, desc)
        if new != desc:
            changed += 1
            hit = pat.findall(desc)
            print("chal %-3s %s  (chall%s)" % (cid, "WOULD update" if a.dry_run else "updated",
                                               ",".join(hit)))
            if not a.dry_run:
                api(a.base, a.token, "PATCH", "/api/v1/challenges/%d" % cid, {"description": new})
    verb = "would change" if a.dry_run else ("reverted" if a.revert else "changed")
    print("\n%d challenge description(s) %s -> %s" %
          (changed, verb, "r0.nzcsc.org.nz" if a.revert else a.domain))
    return 0


if __name__ == "__main__":
    sys.exit(main())
