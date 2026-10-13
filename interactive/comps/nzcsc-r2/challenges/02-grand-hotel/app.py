import base64
import binascii
import json
import os
from pathlib import Path

from flask import Flask, redirect, render_template, request, make_response

app = Flask(__name__)


def read_flag() -> str:
    env = os.environ.get("FLAG")
    if env:
        return env.strip()
    return Path("flag.txt").read_text().strip()


def encode_session(username: str, is_admin: bool = False) -> str:
    payload = {"username": username, "is_admin": is_admin}
    blob = json.dumps(payload, separators=(",", ":"))
    return base64.b64encode(blob.encode()).decode()


def load_user():
    """Return (user, error).

    - No cookie at all -> (None, False): plain front desk, no error.
    - Cookie present but unreadable / malformed -> (None, True): front desk + error.
    - Cookie readable -> (user_dict, False).

    The session cookie is an UNSIGNED base64-encoded JSON blob, so a guest can
    simply flip "is_admin" to true to open the management safe.
    """
    raw = request.cookies.get("session")
    if not raw:
        return None, False
    try:
        data = json.loads(base64.b64decode(raw))
        user = {"username": data["username"], "is_admin": bool(data["is_admin"])}
        return user, False
    except (binascii.Error, ValueError, TypeError, KeyError):
        return None, True


@app.route("/")
def index():
    user, error = load_user()
    return render_template("index.html", user=user, error=error, flag=read_flag())


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    resp = redirect("/")
    if username:
        resp.set_cookie(
            "session",
            encode_session(username, is_admin=False),
            samesite="Lax",
        )
    return resp


@app.route("/logout", methods=["POST"])
def logout():
    resp = redirect("/")
    resp.delete_cookie("session")
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
