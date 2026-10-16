#!/usr/bin/env python3
"""Generate a competition's docker-compose.yml from its per-challenge manifests.

One sandboxed container per hostable challenge, standardised so replicating a whole
competition is "drop a folder per challenge, run one command".

Layout (per competition):
  comps/<comp>/config.env                       comp-wide settings (see below)
  comps/<comp>/flags.env                         GITIGNORED: <id|slug>=NZCSC{...}
  comps/<comp>/challenges/<nn-slug>/
        challenge.yml                            the manifest (see schema below)
        Dockerfile                               how to build this challenge
        <app files...>
  comps/<comp>/docker-compose.yml                GENERATED here (do not hand-edit)

Each hostable challenge becomes:
  container   ctf-<comp>-chall<id>               e.g. ctf-nzcsc-r0-chall3
  http/static <subdomain>.<BASE_DOMAIN>          e.g. chall03.r0.2026.ctf.int.rowansserver.com
              (served through Caddy, LOCAL NETWORK ONLY by default)
  tcp/nc      <server-ip>:<tcp_port>             raw TCP published on the host

challenge.yml schema (all keys except id/type optional):
  id: 3                     # challenge id (matches CTFd); drives name + default subdomain
  slug: meltdown            # short name (defaults to the folder name after "NN-")
  name: Meltdown            # human label (comment only)
  type: http               # http | static | tcp | files    (files/none = CTFd serves it, skipped)
  port: 5000                # the port the app LISTENS on inside the container
  subdomain: chall03        # http/static host = <subdomain>.<BASE_DOMAIN>  (default: chall<zero-padded id>)
  tcp_port: 10003           # tcp only: host port to publish (default 10000+id)
  local_only: true          # http/static: restrict to LOCAL_CIDRS (default true)
  flag: NZCSC{...}          # optional; prefer flags.env so the real flag stays out of git
  env: {KEY: value}         # extra env passed to the container
  read_only: false          # mount rootfs read-only (opt in per challenge)
  mem_limit: 256m           # optional memory cap
  cap_add: [NET_ADMIN]      # optional extra caps (all caps are dropped by default)

Run:
  python3 gen_compose.py <comp>
  docker compose -f comps/<comp>/docker-compose.yml up -d --build
(or use ./manage.sh <comp> up)
"""
import os, sys, re, json, pathlib, urllib.request, yaml

ROOT = pathlib.Path(__file__).resolve().parent

# Fallback Cloudflare edge ranges, used only if the live fetch fails (https://www.cloudflare.com/ips/).
BAKED_CF_CIDRS = ("173.245.48.0/20 103.21.244.0/22 103.22.200.0/22 103.31.4.0/22 141.101.64.0/18 "
                  "108.162.192.0/18 190.93.240.0/20 188.114.96.0/20 197.234.240.0/22 198.41.128.0/17 "
                  "162.158.0.0/15 104.16.0.0/13 104.24.0.0/14 172.64.0.0/13 131.0.72.0/22 "
                  "2400:cb00::/32 2606:4700::/32 2803:f800::/32 2405:b500::/32 2405:8100::/32 "
                  "2a06:98c0::/29 2c0f:f248::/32")


def cf_ranges_live(fallback):
    """Fetch Cloudflare's current edge IP ranges from its public API (no auth needed).
    Keeps the origin's 'Cloudflare-only' allow-list current without a hardcoded copy going
    stale; falls back to BAKED_CF_CIDRS if the network call fails."""
    try:
        d = json.loads(urllib.request.urlopen("https://api.cloudflare.com/client/v4/ips", timeout=15).read().decode())
        r = d.get("result", {}) or {}
        cidrs = (r.get("ipv4_cidrs") or []) + (r.get("ipv6_cidrs") or [])
        if cidrs:
            return " ".join(cidrs)
    except Exception as e:
        print("  (cf ips fetch failed: %s - using baked fallback)" % str(e)[:80])
    return fallback


def load_env(p):
    """Minimal KEY=value reader (ignores blanks/comments/`export`, strips quotes)."""
    d = {}
    if not p.exists():
        return d
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        ln = re.sub(r"^export\s+", "", ln)
        k, v = ln.split("=", 1)
        v = v.strip()
        if v[:1] in ("'", '"'):                 # quoted value: take the quoted span verbatim
            q = v[0]; end = v.find(q, 1)
            v = v[1:end] if end > 0 else v[1:]
        else:                                    # else strip a trailing " # inline comment"
            v = re.split(r"\s+#", v, 1)[0].strip()
        d[k.strip()] = v
    return d


def main():
    if len(sys.argv) < 2:
        print("usage: gen_compose.py <comp>", file=sys.stderr)
        return 2
    comp = sys.argv[1]
    cdir = ROOT / "comps" / comp
    if not cdir.exists():
        print("no such competition dir: %s" % cdir, file=sys.stderr)
        return 1
    cfg = load_env(cdir / "config.env")
    flags = load_env(cdir / "flags.env")
    base_domain = cfg.get("BASE_DOMAIN", "r0.2026.ctf.int.rowansserver.com")
    network = cfg.get("NETWORK", "docker_caddy-net")
    cidrs = cfg.get("LOCAL_CIDRS", "192.168.178.0/24 10.13.13.0/24")
    prefix = cfg.get("CONTAINER_PREFIX", "ctf-%s" % comp)
    public_domain = cfg.get("PUBLIC_DOMAIN", "").strip()
    cloudflare_only = str(cfg.get("CLOUDFLARE_ONLY", "true")).lower() in ("1", "true", "yes", "on")
    # When true, the PUBLIC domain is restricted to the LAN too (everything private "for now").
    public_local_only = str(cfg.get("PUBLIC_LOCAL_ONLY", "false")).lower() in ("1", "true", "yes", "on")
    # Optional host IP to bind published TCP (nc) ports to, e.g. the LAN IP, so raw-TCP
    # challenges listen only on the LAN and not on 0.0.0.0 (private-for-now). Blank = all ifaces.
    tcp_bind = cfg.get("TCP_BIND", "").strip()
    cf_cidrs = cfg.get("CF_CIDRS", "auto").strip()
    # When true, every challenge shares ONE wildcard site block per domain
    # (*.<domain>) with a per-challenge `host` matcher, so Caddy manages a single
    # wildcard cert instead of one cert per challenge. caddy-docker-proxy merges
    # labels from containers that share a site address. Set false for per-host sites.
    wildcard_certs = str(cfg.get("WILDCARD_CERTS", "true")).lower() in ("1", "true", "yes", "on")
    if public_domain and cloudflare_only and not public_local_only and cf_cidrs.lower() in ("", "auto"):
        cf_cidrs = cf_ranges_live(BAKED_CF_CIDRS)   # pull the current list from Cloudflare

    services = {}
    hostable = 0
    skipped = []
    for chdir in sorted((cdir / "challenges").glob("*")):
        mf = chdir / "challenge.yml"
        if not chdir.is_dir() or not mf.exists():
            continue
        m = yaml.safe_load(mf.read_text()) or {}
        cid = m.get("id")
        slug = m.get("slug") or re.sub(r"^\d+[-_]?", "", chdir.name)
        ctype = str(m.get("type") or "http").lower()
        if ctype in ("files", "none", ""):
            skipped.append("%s (files-only - CTFd serves it)" % slug)
            continue
        cname = "%s-chall%s" % (prefix, cid)
        sub = m.get("subdomain") or ("chall%02d" % int(cid) if str(cid).isdigit() else slug)
        port = int(m.get("port", 5000))
        flag = flags.get(str(cid)) or flags.get(slug) or m.get("flag") or ""

        svc = {
            "build": "./challenges/%s" % chdir.name,
            "container_name": cname,
            "restart": "unless-stopped",
            "networks": ["caddy"],
        }
        if m.get("privileged"):
            # nsjail-based pwn sandboxes (e.g. the DownUnderCTF vendor image) need full
            # privileges to set up their own jail; the default hardening below would break
            # them, so a challenge opts in with `privileged: true` and skips cap_drop/nnp.
            svc["privileged"] = True
        else:
            # sandbox defaults: drop every Linux capability, forbid privilege escalation.
            svc["cap_drop"] = ["ALL"]
            svc["security_opt"] = ["no-new-privileges:true"]
        if m.get("cap_add"):
            svc["cap_add"] = list(m["cap_add"])
        if m.get("read_only"):
            svc["read_only"] = True
            svc["tmpfs"] = ["/tmp"]
        if m.get("mem_limit"):
            svc["mem_limit"] = m["mem_limit"]
        env = []
        if flag:
            env.append("FLAG=%s" % flag)
        # Multi-flag challenges (e.g. Print2Win): any flags.env key "<id>_<name>" or
        # "<slug>_<name>" is injected as env <NAME> (upper-cased), e.g. 12_flag1 -> FLAG1.
        for k, v in sorted(flags.items()):
            for b in (str(cid), slug):
                if k.startswith(b + "_"):
                    env.append("%s=%s" % (k[len(b) + 1:].upper(), v))
                    break
        for k, v in (m.get("env") or {}).items():
            env.append("%s=%s" % (k, v))
        if env:
            svc["environment"] = env

        if ctype == "tcp":
            tcp_port = int(m.get("tcp_port", 10000 + (int(cid) if str(cid).isdigit() else 0)))
            svc["ports"] = ["%s:%d:%d" % (tcp_bind, tcp_port, port) if tcp_bind
                            else "%d:%d" % (tcp_port, port)]
        else:  # http / static -> one or more Caddy vhosts (site blocks caddy_0, caddy_1, …)
            labels = {}
            # Stable per-challenge index so merged route directives keep a deterministic
            # order (guard first at 000/001, then each challenge's matcher + upstream).
            idx = int(cid) if str(cid).isdigit() else (hostable + 1)

            def _site(slot, addr, host, filt):
                """Emit one site block. Wildcard mode shares `addr` across all
                challenges (caddy-docker-proxy merges them) and separates them with a
                `host` matcher; per-host mode gives each challenge its own site."""
                k = "caddy_%d" % slot
                if wildcard_certs:
                    labels[k] = "*.%s" % addr
                    i0 = 100 + 2 * idx
                    if filt:
                        labels["%s.route.000_@denied" % k] = "not remote_ip %s" % filt
                        labels["%s.route.001_respond" % k] = '@denied "Not available" 403'
                    labels["%s.route.%03d_@%s" % (k, i0, sub)] = "host %s.%s" % (sub, addr)
                    labels["%s.route.%03d_reverse_proxy" % (k, i0 + 1)] = \
                        "@%s {{upstreams %d}}" % (sub, port)
                else:
                    labels[k] = host
                    if filt:
                        labels["%s.route.0_@denied" % k] = "not remote_ip %s" % filt
                        labels["%s.route.1_respond" % k] = '@denied "Not available" 403'
                        labels["%s.route.2_reverse_proxy" % k] = "{{upstreams %d}}" % port
                    else:
                        labels["%s.reverse_proxy" % k] = "{{upstreams %d}}" % port

            # Site 0 - LOCAL: challNN.<BASE_DOMAIN>, restricted to the LAN (always on).
            _site(0, base_domain, "%s.%s" % (sub, base_domain), cidrs)
            # Site 1 - PUBLIC: challNN.<PUBLIC_DOMAIN> (Cloudflare-proxied), if configured
            # and the challenge didn't opt out with `public: false`.
            if public_domain and m.get("public", True):
                # LAN-only (private) beats Cloudflare-only beats fully-open.
                filt = cidrs if public_local_only else (cf_cidrs if (cloudflare_only and cf_cidrs) else "")
                _site(1, public_domain, "%s.%s" % (sub, public_domain), filt)
            svc["labels"] = labels

        services[cname] = svc
        hostable += 1

    compose = {
        "name": prefix,
        "services": services,
        "networks": {"caddy": {"name": network, "external": True}},
    }
    out = cdir / "docker-compose.yml"
    header = ("# GENERATED by gen_compose.py - do NOT hand-edit.\n"
              "# Edit the challenge.yml manifests (and config.env) then re-run:\n"
              "#   python3 gen_compose.py %s\n\n" % comp)
    out.write_text(header + yaml.safe_dump(compose, sort_keys=False, default_flow_style=False))
    print("wrote %s  (%d hostable container(s))" % (out, hostable))
    for s in skipped:
        print("  - skipped %s" % s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
