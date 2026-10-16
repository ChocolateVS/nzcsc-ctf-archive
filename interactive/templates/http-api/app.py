#!/usr/bin/env python3
"""Template HTTP-API challenge.

Recreate the challenge's real behaviour here from its provided source. The flag comes
from the FLAG env var (set by the generator from flags.env) - read it, never hard-code
it. Listen on 0.0.0.0:5000 (matches `port: 5000` in challenge.yml)."""
import os
from flask import Flask, request, jsonify

FLAG = os.environ.get("FLAG", "NZCSC{placeholder_set_the_real_flag_in_flags.env}")
app = Flask(__name__)


@app.get("/")
def index():
    return "Challenge API up. (Recreate the real endpoints from the provided source.)\n"


@app.get("/flag")
def flag():
    # EXAMPLE ONLY - replace with the challenge's actual (vulnerable) logic that
    # eventually reveals FLAG. Do not just hand it out like this in a real challenge.
    if request.args.get("debug") == "1":
        return jsonify(flag=FLAG)
    return jsonify(error="nope"), 403


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
