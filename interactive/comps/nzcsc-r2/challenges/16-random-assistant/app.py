#!/usr/bin/env python3
"""Random Assistant — R2 #16 (author: Cale).

Reconstructed server for the archive from the shipped Windows client
(RandomAssistant.exe + .pdb). The original backend source was not in the dump;
this re-implements the exact wire protocol the client speaks, recovered by
reverse-engineering the client:

  * host               chall16.ctf.nzcsc.org.nz (443, https) — behind Caddy here
  * POST /api/v1/login  {"username":"api","password":"SuperSecretP@ss123!"}
                        -> {"token": "..."}; later requests send
                        Authorization: Bearer <token> + Content-Type: application/json
  * GET  /api/v1/coin  ?sig=<hex>   -> {"result": "Heads"|"Tails"}
  * GET  /api/v1/dice  ?sig=<hex>   -> {"result": "1".."6"}
  * GET  /api/v1/card  ?sig=<hex>   -> {"result": "<rank> of <suit>"}
  * GET  /api/v1/spec  ?sig=<hex>   -> {"result": "<FLAG>"}   (the hidden one)

Every API call is signed:  sig = HMAC_SHA256(SIGN_KEY, <request path>) hex.
SIGN_KEY is a *client-side secret* baked into the client — the client computes
HMAC-SHA256 with the key b"you_will_never_get_this_la_la_la_la_la" (stored
obfuscated in .data) over the bare path, hex-encodes it, and appends ?sig=.

The outcome of coin/dice/card is chosen *server-side* with a CSPRNG, so a player
can't rig the randomness (the author's whole premise). But the signing key lives
in the client, so a player who reverse-engineers it can forge a valid signature
for ANY path — including /api/v1/spec, an endpoint the GUI never calls. A signed
request to /api/v1/spec returns the flag. Hence:
  server-side random, but client-side secrets.
"""
import hashlib
import hmac
import os
import secrets

from flask import Flask, jsonify, request

app = Flask(__name__)

# --- secrets recovered from the client -------------------------------------
# HMAC signing key (client-side secret): stored obfuscated in the client's
# .data and deobfuscated at runtime. This is the crux of the challenge.
SIGN_KEY = b"you_will_never_get_this_la_la_la_la_la"
# API credentials (also baked into the client, as username/password literals).
API_USER = "api"
API_PASS = "SuperSecretP@ss123!"

FLAG = os.environ.get("FLAG", "NZCSC{S3RV3R_SID3_RAND0M_BUT_CLI3NT_SID3_S3CR3TS}")

# Opaque bearer tokens are stateless: token = HMAC(TOKEN_KEY, username). The key
# is random per process, so tokens can't be forged, but validation needs no
# store. (There's only one account, so this is plenty.)
TOKEN_KEY = secrets.token_bytes(32)


def _token_for(username):
    return hmac.new(TOKEN_KEY, username.encode(), hashlib.sha256).hexdigest()


def _authed():
    """True iff a valid Authorization: Bearer <token> is present."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth[len("Bearer "):].strip()
    return hmac.compare_digest(token, _token_for(API_USER))


def _sig_ok():
    """True iff ?sig= matches HMAC_SHA256(SIGN_KEY, path) — exactly how the
    client signs. Compared case-insensitively so either hex case is accepted."""
    provided = (request.args.get("sig") or "").lower()
    expected = hmac.new(SIGN_KEY, request.path.encode(), hashlib.sha256).hexdigest()
    return bool(provided) and hmac.compare_digest(provided, expected)


def _guard():
    """Shared gate for every /api/v1/<game|spec> endpoint: login + signature.
    Returns an error response to short-circuit with, or None to proceed."""
    if not _authed():
        return jsonify(error="Unauthorized. Log in via /api/v1/login first."), 401
    if not _sig_ok():
        return jsonify(error="Bad or missing signature."), 403
    return None


@app.post("/api/v1/login")
def login():
    data = request.get_json(silent=True) or {}
    if data.get("username") == API_USER and data.get("password") == API_PASS:
        return jsonify(token=_token_for(API_USER))
    return jsonify(error="Invalid credentials."), 401


@app.get("/api/v1/coin")
def coin():
    err = _guard()
    if err:
        return err
    return jsonify(result=secrets.choice(["Heads", "Tails"]))


@app.get("/api/v1/dice")
def dice():
    err = _guard()
    if err:
        return err
    return jsonify(result=str(secrets.randbelow(6) + 1))


_RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace"]
_SUITS = ["Clubs", "Diamonds", "Hearts", "Spades"]


@app.get("/api/v1/card")
def card():
    err = _guard()
    if err:
        return err
    return jsonify(result="%s of %s" % (secrets.choice(_RANKS), secrets.choice(_SUITS)))


@app.get("/api/v1/spec")
def spec():
    # Not wired to any button in the GUI client — but it signs/authenticates
    # just like the others, so a forged signature reaches it. Returns the flag.
    err = _guard()
    if err:
        return err
    return jsonify(result=FLAG)


@app.get("/")
def index():
    return (
        "<h1>Random Assistant</h1>"
        "<p>Server-side randomness API for the Random Assistant client. "
        "Download and investigate the client.</p>"
        "<pre>POST /api/v1/login\nGET  /api/v1/coin\nGET  /api/v1/dice\n"
        "GET  /api/v1/card</pre>",
        200,
        {"Content-Type": "text/html"},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
