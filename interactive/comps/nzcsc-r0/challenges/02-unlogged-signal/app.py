#!/usr/bin/env python3
"""02 - Unlogged Signal (exact replica).

The original is a single self-contained client-side page. We serve the ORIGINAL page
(index.html, fetched verbatim from the live challenge) unchanged — the cipher data and
per-line hashes are the real ones, so the page and solve are byte-identical."""
import os
from flask import Flask, Response

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = open(os.path.join(HERE, "index.html"), "rb").read()
app = Flask(__name__)


@app.get("/")
def index():
    return Response(HTML, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
