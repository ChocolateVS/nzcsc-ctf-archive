#!/usr/bin/env python3
"""4 - Internal API (NZCSC r0).

A FastAPI "report fetching" proxy. GET / serves a decoy OpenAPI-looking
document (which leaks a slightly-wrong test credential); POST /login issues a
JWT; GET /challenge hands over the objective; POST /fetch is a Server-Side
Request Forgery primitive that reaches an internal-only service (recreated
in-process here) which holds the flag.

The flag comes from the FLAG env var (set by the generator from flags.env) --
read it, never hard-code it. Listen on 0.0.0.0:5000 (matches challenge.yml)."""
import json
import os
import time
from typing import Optional
from urllib.parse import urlsplit

import httpx
import jwt
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel

FLAG = os.environ.get("FLAG", "NZCSC{placeholder_set_the_real_flag_in_flags.env}")

# App-internal signing secret for the demo JWTs. Not part of the intended path.
JWT_SECRET = os.environ.get("JWT_SECRET", os.urandom(32).hex())
JWT_ALG = "HS256"

# Real credentials. Note the decoy document served at GET / leaks a
# slightly-wrong username ("nzcsdev") on purpose; the working value is
# "nzcscdev".
VALID_USER = "nzcscdev"
VALID_PASS = "ctf2026"

# Hostname of the internal-only service that /fetch can reach. In the original
# deployment this was a separate container; here it is served in-process and is
# only ever reachable via the SSRF in /fetch.
INTERNAL_HOST = "internal-api"

# FastAPI generates the public /openapi.json (title/version left at their
# defaults on purpose, exactly like the original deployment).
app = FastAPI(title="NZCS API")

# The decoy document returned verbatim from GET /. Captured from the original
# service; served byte-for-byte.
_ROOT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "root.json")
with open(_ROOT_JSON, "rb") as _fh:
    ROOT_BODY = _fh.read()


class LoginRequest(BaseModel):
    username: str
    password: str


class FetchRequest(BaseModel):
    url: str


def _require_auth(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[len("Bearer "):]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload.get("sub")


# --- Internal-only service (recreated in-process) --------------------------
# These handlers stand in for the separate "internal-api" host. They are NOT
# mounted as public routes; they are only reachable through the /fetch SSRF.
def _internal_response(path: str):
    path = path or "/"
    if path in ("", "/"):
        return 200, {
            "service": "NZCSC API",
            "status": "running",
            "version": "1.0.0",
            "endpoints": ["/health", "/secret"],
        }
    if path == "/health":
        return 200, {"status": "ok"}
    if path == "/secret":
        return 200, {
            "classified": True,
            "message": "Internal credentials store.",
            "flag": FLAG,
        }
    return 404, {"error": "not found"}


# --- Public routes ---------------------------------------------------------
@app.get("/")
def root():
    return Response(content=ROOT_BODY, media_type="application/json")


@app.post("/login")
def login(body: LoginRequest):
    if body.username != VALID_USER or body.password != VALID_PASS:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    now = int(time.time())
    token = jwt.encode(
        {"sub": body.username, "exp": now + 3600},
        JWT_SECRET,
        algorithm=JWT_ALG,
    )
    return {
        "token": token,
        "token_type": "Bearer",
        "note": "Use this token in the Authorization header for all requests.",
    }


@app.get("/challenge")
def challenge(authorization: Optional[str] = Header(None)):
    _require_auth(authorization)
    return {
        "title": "NZCSC - Internal API",
        "description": "API's.",
        "objective": "Find and read a sensitive resource that should not be accessible from outside.",
        "flag_format": "NZCSC{...}",
        "hint": "Not all services need to be public to be reachable.",
        "endpoint": "POST /fetch",
        "body": {"url": "http://internal-api"},
    }


@app.post("/fetch")
def fetch(body: FetchRequest, authorization: Optional[str] = Header(None)):
    _require_auth(authorization)

    parts = urlsplit(body.url)
    # The proxy reaches the internal service in-process. In the original this
    # was a separate host resolved over the network; here we intercept the
    # internal hostname and serve it directly, matching the upstream bytes.
    if parts.hostname == INTERNAL_HOST:
        status, data = _internal_response(parts.path)
        text = json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"
        return {
            "status_code": status,
            "content_type": "application/json",
            "body": text,
        }

    # Any other URL is fetched for real (as upstream did with httpx), so error
    # wording for unreachable/invalid URLs matches the original service.
    try:
        resp = httpx.get(body.url, timeout=5.0)
    except Exception as exc:  # noqa: BLE001 - mirror upstream error surface
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {exc}")
    return {
        "status_code": resp.status_code,
        "content_type": resp.headers.get("content-type", ""),
        "body": resp.text,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
