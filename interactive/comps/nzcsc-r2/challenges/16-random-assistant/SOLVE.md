# 16 - Random Assistant (R2, author: Cale) — writeup

> "I built a *random assistant* to help coinflip my everyday life. It uses
> server-side randomness to ensure ops can't influence my decisions. Investigate
> the client and server to ensure my life can continue being non-deterministic."

**Flag:** `NZCSC{S3RV3R_SID3_RAND0M_BUT_CLI3NT_SID3_S3CR3TS}`

The handout is a Windows GUI client (`RandomAssistant.exe`, native x64 MSVC, with
its `.pdb`). There is **no server** handout — the backend lived at
`chall16.ctf.nzcsc.org.nz`. This directory is a faithful reconstruction of that
backend, recovered by reverse-engineering the client. (The archive server runs
over the same wire protocol; only the hostname differs.)

## Recovering the protocol from the client

Strings + a little disassembly give the whole API:

* Base: `https://chall16.ctf.nzcsc.org.nz` (port 443, `WINHTTP_FLAG_SECURE`),
  UA `CTFClient`, `Content-Type: application/json`.
* `POST /api/v1/login` with body `{"username":"api","password":"SuperSecretP@ss123!"}`
  (both literals are in the client's `.data`). Response `{"token":"..."}`; the
  client then sends `Authorization: Bearer <token>` on every call.
* Three buttons issue `GET /api/v1/coin`, `/api/v1/dice`, `/api/v1/card` and read
  the `result` field.
* A fourth endpoint string, **`/api/v1/spec`**, is present in the binary but is
  wired to no button.

### Request signing (the important bit)

Every game request is signed. The client builds the URL with the format string
`"%s?sig=%s"`, where the signature is:

```
sig = hex( HMAC_SHA256(key = SIGN_KEY, msg = <request path>) )
```

The HMAC is computed with `BCryptOpenAlgorithmProvider("SHA256", …,
BCRYPT_ALG_HANDLE_HMAC_FLAG)` and the key is **not** the plaintext
`SuperSecretP@ss123!`. It's a string stored *obfuscated* in `.data` and decoded
at runtime (first 19 bytes `XOR 0x5a`, the rest `ROTR8(b XOR 0x7e, 3)`):

```
SIGN_KEY = b"you_will_never_get_this_la_la_la_la_la"
```

The message that is signed is just the bare path, e.g. `"/api/v1/coin"` — no
nonce, no timestamp, no body.

### A rabbit hole

The client also has a hidden "debug key" box (menu/`WM_COMMAND` id 6): it takes
your text, computes `AES-256 key = SHA256(text)`, and AES-256-CBC-decrypts a
64-byte blob (IV `00010203…0f`) embedded at `.rdata:0x140085f40`, then checks the
plaintext looks like `NZCSC{…}`. No key in the binary decrypts it to a flag — it's
a decoy / "Incorrect debug key!" dead end. The real flag is server-side.

## The vulnerability

The author's premise is sound: the coin/dice/card outcomes are chosen
**server-side** with a CSPRNG, so you can't bias the randomness. But the signing
key is a **client-side secret** — baked into the client and trivially
extractable. With it you can forge a valid signature for *any* path, including
the one the GUI never calls: `/api/v1/spec`.

> server-side random, **but client-side secrets**.

## Exploit

```python
import hmac, hashlib, requests
BASE = "https://chall16.r2.2026.nzcsc.xyz"         # archive host
KEY  = b"you_will_never_get_this_la_la_la_la_la"    # extracted from the client
sign = lambda p: hmac.new(KEY, p.encode(), hashlib.sha256).hexdigest()

s = requests.Session()
tok = s.post(f"{BASE}/api/v1/login",
             json={"username": "api", "password": "SuperSecretP@ss123!"}).json()["token"]
s.headers["Authorization"] = f"Bearer {tok}"

print(s.get(f"{BASE}/api/v1/spec", params={"sig": sign("/api/v1/spec")}).json())
# -> {'result': 'NZCSC{S3RV3R_SID3_RAND0M_BUT_CLI3NT_SID3_S3CR3TS}'}
```

## Reconstruction notes / assumptions

Recovered exactly from the client: the five endpoints, the login creds and body
shape, the `Bearer` token scheme, the `?sig=` signing (HMAC-SHA256 over the path,
hex), and the `SIGN_KEY`. Not observable from the client (chosen to be faithful
and solvable):

* The token value/format — the client only *reads* `token` from the login
  response, so the server mints an opaque one.
* The exact `result` strings for coin/dice/card and the precise contents of
  `/api/v1/spec` on the original server. We make `spec` the flag endpoint, gated
  by the same login + signature as the games, which matches the challenge name
  and the "hidden endpoint you must sign for" shape. The signature check accepts
  either hex case.
