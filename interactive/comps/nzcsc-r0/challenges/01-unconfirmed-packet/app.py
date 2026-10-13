#!/usr/bin/env python3
"""01 - Unconfirmed Packet (exact replica).

Serves the ORIGINAL page (index.html, fetched verbatim) unchanged. The solve is to read
the hidden directory tree in the page source and request the real leaf path; the flag
(from the FLAG env var) is served there, exactly like the original. Every other path 404s."""
import os
from flask import Flask, Response

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = open(os.path.join(HERE, "index.html"), "rb").read()
FLAG = os.environ.get("FLAG", "NZCSC{placeholder}")
FLAG_PATH = "/ttl_b2a8e/hdr_81367c/retx_00e5f0/flag.txt"   # the real hidden leaf (nzcsc/ root is a decoy)
app = Flask(__name__)


@app.get("/")
def index():
    return Response(HTML, mimetype="text/html")


@app.get(FLAG_PATH)
def flag():
    return Response(FLAG, mimetype="text/plain")


@app.errorhandler(404)
def not_found(_e):
    return Response("404 Not Found", status=404, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
