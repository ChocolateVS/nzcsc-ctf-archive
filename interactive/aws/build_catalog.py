#!/usr/bin/env python3
"""Emit catalog.json - the machine-readable list of interactive challenges that
the AWS on-demand system builds (CI), runs (agent), and advertises (launcher).

It reads the same per-challenge `challenge.yml` manifests + per-comp `config.env`
that gen_compose.py uses, so the AWS catalog stays in lockstep with the source of
truth. It does NOT apply the home box's Cloudflare/LAN gating - on AWS the
challenges are public and access is mediated by the launcher (lease + cap).

  python3 interactive/aws/build_catalog.py > interactive/aws/catalog.json

Each entry:
  { comp, id, slug, name, type(http|static|tcp|files), port, tcp_port, subdomain,
    host, image_tag, mem_limit, privileged, read_only, cap_add, env, flag }

`files`/`static` challenges with no server are skipped (CTFd serves those).
"""
import glob
import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
INTERACTIVE = os.path.dirname(HERE)
COMPS = os.path.join(INTERACTIVE, "comps")

# Public DNS parents for each comp's web subdomains on AWS (challNN.<parent>).
# These match the CTFd connection_info domains so links line up.
PARENT_DOMAIN = {
    "nzcsc-r0": "r0.2026.nzcsc.xyz",
    "nzcsc-r2": "r2.2026.nzcsc.xyz",
}
# default raw-TCP host-port base per comp (overridable per challenge via tcp_port)
TCP_BASE = {"nzcsc-r0": 10000, "nzcsc-r2": 11000}
# host-port base for web challenges (caddy reverse-proxies the subdomain here)
WEB_BASE = {"nzcsc-r0": 20000, "nzcsc-r2": 21000}


def read_env(path):
    cfg = {}
    if not os.path.isfile(path):
        return cfg
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.split("#", 1)[0].strip()
    return cfg


def load_flags(comp_dir):
    """flags.env: `<id|slug>=NZCSC{...}` per line (gitignored on the home box)."""
    return read_env(os.path.join(comp_dir, "flags.env"))


def main():
    catalog = []
    for comp_dir in sorted(glob.glob(os.path.join(COMPS, "*"))):
        if not os.path.isdir(comp_dir):
            continue
        comp = os.path.basename(comp_dir)
        flags = load_flags(comp_dir)
        parent = PARENT_DOMAIN.get(comp, comp + ".nzcsc.xyz")
        tcp_base = TCP_BASE.get(comp, 10000)
        for man in sorted(glob.glob(os.path.join(comp_dir, "challenges", "*", "challenge.yml"))):
            m = yaml.safe_load(open(man)) or {}
            cdir = os.path.basename(os.path.dirname(man))
            cid = m.get("id")
            if cid is None:
                continue
            slug = m.get("slug") or (cdir.split("-", 1)[1] if "-" in cdir else cdir)
            ctype = (m.get("type") or "http").lower()
            if ctype in ("files", "none"):
                continue  # CTFd serves these; nothing to host
            sub = m.get("subdomain") or ("chall%02d" % int(cid) if str(cid).isdigit() else slug)
            flag = m.get("flag") or flags.get(str(cid)) or flags.get(slug)
            entry = {
                "comp": comp,
                "id": cid,
                "slug": slug,
                "name": m.get("name") or ("%s %s" % (comp, cid)),
                "type": ctype,
                "port": int(m.get("port", 22 if ctype == "ssh" else (5000 if ctype in ("http", "static") else 1337))),
                "subdomain": sub,
                "host": "%s.%s" % (sub, parent),
                "image_tag": "%s-chall%s" % (comp, cid),
                "context": os.path.relpath(os.path.dirname(man), INTERACTIVE),
                "mem_limit": m.get("mem_limit", "256m"),
                "privileged": bool(m.get("privileged", False)),
                "read_only": bool(m.get("read_only", False)),
                "cap_add": m.get("cap_add", []),
                "env": m.get("env", {}) or {},
                "flag": flag,
                "user": m.get("user", "arteta"),
            }
            idnum = int(cid) if str(cid).isdigit() else 0
            if ctype in ("tcp", "ssh"):
                # host_port == the published port the player connects to (nc / ssh)
                entry["host_port"] = entry["tcp_port"] = int(m.get("tcp_port", tcp_base + idnum))
            else:
                # web: caddy proxies <host> -> 127.0.0.1:host_port
                entry["host_port"] = WEB_BASE.get(comp, 20000) + idnum
            catalog.append(entry)
    json.dump(catalog, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stderr.write("catalog: %d hostable challenges (%d tcp, %d web)\n" % (
        len(catalog),
        sum(1 for e in catalog if e["type"] == "tcp"),
        sum(1 for e in catalog if e["type"] in ("http", "static")),
    ))


if __name__ == "__main__":
    main()
