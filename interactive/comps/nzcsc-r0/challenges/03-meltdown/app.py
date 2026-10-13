#!/usr/bin/env python3
"""03 - Meltdown (exact replica).

Serves the ORIGINAL page + assets (index.html, static/style.css, static/app.js) verbatim,
and replays the ORIGINAL /api/records telemetry captured from the live challenge
(data.json) with identical paging and error behaviour — so the page, data and solve are
byte-identical to the real challenge."""
import os
import json
from flask import Flask, Response, request, jsonify, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = open(os.path.join(HERE, "index.html"), "rb").read()
DATA = json.load(open(os.path.join(HERE, "data.json")))
MAX_LIMIT = 200
app = Flask(__name__)


@app.get("/")
def index():
    return Response(HTML, mimetype="text/html")


@app.get("/static/<path:fn>")
def static_files(fn):
    return send_from_directory(os.path.join(HERE, "static"), fn)


@app.get("/api/records")
def records():
    field = request.args.get("field", "")
    if field not in DATA:
        return jsonify({"Error": "Nice try, but this isn't part of the challenge."}), 400
    rows = DATA[field]
    try: offset = max(0, int(request.args.get("offset", 0)))
    except Exception: offset = 0
    try: limit = int(request.args.get("limit", MAX_LIMIT))
    except Exception: limit = MAX_LIMIT
    limit = max(1, min(MAX_LIMIT, limit))
    page = rows[offset:offset + limit]
    end = offset + len(page)
    return jsonify({"has_more": end < len(rows), "next_offset": end,
                    "rows": page, "total": len(rows)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
