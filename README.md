# NZCSC CTF Archive

Challenge content for the public NZCSC CTF archive hosted at
**https://ctf.nzcsc.xyz** (CTFd) with always-on static web challenges at
**https://live.nzcsc.xyz**. The platform itself (CTFd, DNS, TLS, S3/CloudFront)
is infrastructure and lives in a separate repo, **`nzcsc-ctf-infra`**. This repo
is the *content* and its deploy pipeline.

Pushing to `main` deploys automatically (see [Pipeline](#pipeline)).

## Layout

| Path | What |
|------|------|
| `data/data_*.json` | Challenge definitions per year/round — the source of truth. |
| `files/` | Challenge attachments referenced by `data/*.json` (zips, scripts). |
| `live/` | Static site synced to the `live.nzcsc.xyz` bucket (web challenge snapshots). |
| `mirrors/` | Raw recovered source material the `live/` snapshots were built from (build input, not deployed). |
| `tools/deploy_challenges.py` | Upserts the challenges into CTFd over its REST API. |
| `tools/package_sites.py` | Rebuilds `live/` from `mirrors/`. |
| `.github/workflows/deploy.yml` | CI: deploy challenges + sync `live/`. |

### Challenge data format

Each `data/data_<year>.json` is `{ "year", "category", "challenges": [...] }`.
A challenge:

```json
{
  "num": 1,
  "title": "Robots",
  "topic": "Web Exploitation",
  "difficulty": "Easy",
  "value": 10,
  "flag": "NZCSC{...}",
  "method": "short solve note (shown in a collapsible 'Solve approach')",
  "prompt": "<trusted HTML prompt>",
  "files": ["2024-c1-robots.zip"],
  "connection_info": "https://ctf.nzcsc.xyz/live/2024/challenge1/"
}
```

`flag`, `files`, `prompt`, `connection_info`, `method` are all optional. **Flags
are set only when present — the tooling never invents one.**

## Pipeline

On push to `main` (and via **Run workflow**), `.github/workflows/deploy.yml` runs
two independent, idempotent jobs:

- **deploy-challenges** — `tools/deploy_challenges.py` upserts every `data/*.json`
  into CTFd via its REST API. Challenges are matched by category + the leading
  `"<num> - "` in the name, so edits update in place. It is **additive**: it
  never deletes challenges, flags, or files, and only adds a flag/tag/file that
  isn't already there.
- **sync-live** — syncs `live/` to the S3 bucket behind CloudFront and
  invalidates the cache. Skipped until its role variable is set (below).

Both jobs soft-skip when unconfigured, so the first push goes green regardless.

## One-time setup

### 1. CTFd API token (for `deploy-challenges`)

1. Log in to https://ctf.nzcsc.xyz as admin → **Settings → Access Tokens →
   Generate** (no expiry, or a long one).
2. In this repo: **Settings → Secrets and variables → Actions → Secrets**, add:
   - `CTFD_URL` = `https://ctf.nzcsc.xyz`
   - `CTFD_TOKEN` = the token you just generated

### 2. AWS role for `sync-live` (keyless, OIDC)

The role is defined in `nzcsc-ctf-infra` (`environments/prod/cicd.tf`). Apply it:

```sh
cd nzcsc-ctf-infra/environments/prod
tofu apply            # creates the nzcsc-ctf-archive-ci role (least-privilege)
tofu output archive_ci_role_arn
tofu output live_bucket_name
tofu output live_cloudfront_distribution_id
```

Then in this repo add Actions **Variables** (not secrets):

- `AWS_LIVE_DEPLOY_ROLE_ARN` = `archive_ci_role_arn`
- `AWS_REGION` = `ap-southeast-6`
- `LIVE_BUCKET` = `live_bucket_name`
- `LIVE_CF_DIST_ID` = `live_cloudfront_distribution_id`

## Running the deployer locally

```sh
pip install -r tools/requirements.txt

# safe preview — reads only, no writes, no token needed for the plan:
CTFD_URL=https://ctf.nzcsc.xyz python tools/deploy_challenges.py --dry-run

# real deploy:
CTFD_URL=https://ctf.nzcsc.xyz CTFD_TOKEN=xxxx python tools/deploy_challenges.py
# or a single file:  ... python tools/deploy_challenges.py data/data_2025.json
```

> **Local DNS note:** on the home network, pi-hole points `*.nzcsc.xyz` at the
> old home server. Test from off-LAN, clear that override, or pin the hostname
> to the AWS elastic IP in `/etc/hosts` so you hit the real platform.

## Notes

- The live platform currently holds the full imported set (~138 challenges);
  `data/*.json` describes the reconstructed subset (~93). Because the deployer is
  additive and never deletes, running it only ever updates/ensures the ones it
  knows about — it won't remove the rest.
- Some older files (e.g. 2021) live only on the platform (attached during the
  initial import) and aren't in `files/`. The deployer detects they're already
  attached and leaves them alone; it warns (doesn't fail) if one is neither in
  the repo nor attached.
