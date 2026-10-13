# Interactive challenges (on-demand hosting)

The ~32 interactive NZCSC challenges (web services + pwn/`nc`) that can't be a
static file. On AWS they're hosted **on-demand**: the instance is stopped until a
player launches one, containers are leased for a short time, and the box spins
back down when idle. Full design: `nzcsc-ctf-infra/docs/on-demand-challenges.md`.

## Layout

- `comps/<comp>/challenges/<nn-slug>/{challenge.yml,Dockerfile,...}` — the challenge
  build contexts + manifests (vendored from the home `ctf-challenges` project).
- `comps/<comp>/config.env`, `flags.env` — comp settings / flags.
- `gen_compose.py`, `scaffold_comp.py`, `templates/` — the home tooling (kept for
  reference / local runs).
- `aws/build_catalog.py` — emits `aws/catalog.json`, the machine-readable list of
  hostable challenges (id, type, port, tcp_port, subdomain, image tag, flag, …).
  This is the contract shared by the CI build, the launcher, and the on-box agent.
- `aws/catalog.json` — generated; regenerate with
  `python3 interactive/aws/build_catalog.py > interactive/aws/catalog.json`.

## Flags

This repo is **public** and intentionally contains flags (historical comps,
writeups are public anyway — see the design doc's "Flag handling" decision).
`r0` flags come from `comps/nzcsc-r0/flags.env` and are injected as the `FLAG`
env at run; most `r2` flags are baked into the challenge source. Either way the
container's flag equals the CTFd-registered one.

## Build pipeline

`.github/workflows/build-challenges.yml` builds each challenge as a **linux/amd64**
image and pushes it to ECR (`<registry>/nzcsc-ctf-chal:<comp>-chall<id>`). The
on-demand instance only pulls. See the workflow header for the required repo
Variables (set after `tofu apply` creates the ECR repo + build role).
