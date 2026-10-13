#!/usr/bin/env python3
"""pJWT - "Token Claim Resolver".

Jason's "private JWTs" (pJWTs): a JWT can carry *private* claims. When a token
is generated, each private claim's value in the payload is replaced by a
``{{claim_name}}`` placeholder and the real value is remembered server-side.
The "Resolve Claims" action promises to reveal the real value of the private
claims - but only when the token carries a *valid signature*.

Two intentional design bugs combine into RCE:

  Bug 1 - JWK header key confusion:
      The signature is verified using whatever ``jwk`` object is supplied in
      the token *header*, rather than a fixed, server-side trusted key. An
      attacker can therefore embed their own public key, sign with their own
      private key, and produce a token the server happily accepts.

  Bug 2 - SSTI in private-claim resolution:
      Resolution renders the *raw claim value from the payload* as a Jinja2
      template (intended only to expand ``{{claim_name}}`` placeholders). With
      full payload control from bug 1, that is textbook Flask/Jinja2 SSTI.

The flag is read from the FLAG environment variable - never hard-coded.
Listens on 0.0.0.0:5000 (matches ``port: 5000`` in challenge.yml).

The browser-facing frontend (GET / and /static/style.css) is served verbatim
so it is byte-identical to the real challenge; only the dynamic result blocks
are filled in server-side.
"""
import base64
import json
import os
import time

import jwt
from jwt.exceptions import InvalidSignatureError
from jwt.algorithms import RSAAlgorithm
from cryptography.hazmat.primitives.asymmetric import rsa

from flask import Flask, request, render_template, render_template_string

FLAG = os.environ.get("FLAG", "NZCSC{placeholder_set_the_real_flag_in_flags.env}")

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Server signing key. Its public half is embedded in every generated token's
# header as a `jwk` object (this is what makes the key-confusion bug possible:
# resolution trusts the header jwk instead of pinning to THIS key).
# ---------------------------------------------------------------------------
def _b64u_uint(value):
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


_PRIV = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUB_NUMS = _PRIV.public_key().public_numbers()
SERVER_JWK = {
    "alg": "RS256",
    "e": _b64u_uint(_PUB_NUMS.e),
    "kid": "key-1",
    "kty": "RSA",
    "n": _b64u_uint(_PUB_NUMS.n),
    "use": "sig",
}

# Real values of private claims are remembered here, keyed by claim name, so
# that resolution can expand the `{{claim_name}}` placeholders. This is also
# the Jinja2 render context - and rendering attacker-controlled payload strings
# against it is bug #2.
PRIVATE_STORE = {}

# The generate form's initial (default) state, shown on GET / and whenever the
# generate form is re-rendered without a submission of its own.
DEFAULT_USERNAME = "admin"
DEFAULT_CLAIMS = [
    {"id": "1", "name": "role", "value": "user", "private": False},
    {"id": "2", "name": "department", "value": "engineering", "private": False},
    {"id": "3", "name": "notes", "value": "", "private": False},
]


def base_context():
    """Context with every template variable at its empty/default value."""
    return {
        "active": "generate",
        "username": DEFAULT_USERNAME,
        "claims": [dict(c) for c in DEFAULT_CLAIMS],
        "gen_error": None,
        "gen_token": None,
        "decode_token": "",
        "decode_error": None,
        "decode_result": None,
        "decode_header": None,
        "decode_payload": None,
        "resolve_token": "",
        "resolve_error": None,
        "resolve_rows": None,
    }


def render(ctx):
    return render_template("index.html", **ctx)


@app.get("/")
def index():
    return render(base_context())


@app.post("/")
def actions():
    action = request.form.get("action", "")
    if action == "generate":
        return do_generate()
    if action == "decode":
        return do_decode()
    if action == "resolve":
        return do_resolve()
    # Unknown / missing action: just show the default page.
    return render(base_context())


def do_generate():
    ctx = base_context()

    username = request.form.get("username", "guest")

    ids = request.form.getlist("claim_row_id")
    names = request.form.getlist("claim_name")
    values = request.form.getlist("claim_value")
    private_ids = set(request.form.getlist("claim_private"))

    # Reflect the submitted form state back into the generate form.
    rows = []
    for i in range(len(ids)):
        rid = ids[i]
        name = names[i] if i < len(names) else ""
        value = values[i] if i < len(values) else ""
        rows.append({
            "id": rid,
            "name": name,
            "value": value,
            "private": rid in private_ids,
        })

    ctx["username"] = username
    ctx["claims"] = rows

    # Build the JWT payload from the submitted claims.
    payload = {"username": username}
    private_names = []
    for row in rows:
        name = row["name"]
        if not name:
            continue
        payload[name] = row["value"]
    for row in rows:
        name = row["name"]
        if name and row["private"] and name in payload:
            # Remember the real value; hide it behind a placeholder.
            PRIVATE_STORE[name] = payload[name]
            payload[name] = "{{" + name + "}}"
            if name not in private_names:
                private_names.append(name)

    payload["_private"] = private_names
    payload["exp"] = int(time.time()) + 3600

    headers = {"jwk": SERVER_JWK}
    token = jwt.encode(payload, _PRIV, algorithm="RS256", headers=headers)
    ctx["gen_token"] = token
    return render(ctx)


def do_decode():
    ctx = base_context()
    ctx["active"] = "decode"
    token = request.form.get("token", "")
    ctx["decode_token"] = token
    try:
        header = jwt.get_unverified_header(token)
        payload = jwt.decode(token, options={"verify_signature": False})
    except Exception as exc:  # noqa: BLE001
        ctx["decode_error"] = str(exc)
        return render(ctx)
    ctx["decode_result"] = True
    ctx["decode_header"] = json.dumps(header, indent=2, sort_keys=True)
    ctx["decode_payload"] = json.dumps(payload, indent=2)
    return render(ctx)


def do_resolve():
    ctx = base_context()
    ctx["active"] = "resolve"
    token = request.form.get("token", "")
    ctx["resolve_token"] = token

    if not token:
        ctx["resolve_error"] = "No token provided"
        return render(ctx)

    try:
        header = jwt.get_unverified_header(token)

        # --- Bug 1: trust the jwk carried in the header to verify the sig. ---
        jwk = header.get("jwk")
        key = RSAAlgorithm.from_jwk(json.dumps(jwk))
        payload = jwt.decode(token, key=key, algorithms=["RS256"])
    except InvalidSignatureError as exc:
        ctx["resolve_error"] = str(exc)
        return render(ctx)
    except Exception:  # noqa: BLE001
        # Malformed token / missing jwk / etc: silently show the empty state.
        return render(ctx)

    private = payload.get("_private", []) or []
    rows = []
    for name, value in payload.items():
        if name == "_private":
            continue
        if name in private and isinstance(value, str):
            # --- Bug 2: render the raw private-claim value as a Jinja2
            # template against the private store. With attacker-controlled
            # payload from bug 1, this is SSTI -> RCE.
            try:
                rendered = render_template_string(value, **PRIVATE_STORE)
            except Exception as exc:  # noqa: BLE001
                rendered = "error: %s" % exc
            rows.append({"name": name, "value": rendered, "private": True})
        else:
            rows.append({"name": name, "value": value, "private": False})

    ctx["resolve_rows"] = rows
    return render(ctx)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
