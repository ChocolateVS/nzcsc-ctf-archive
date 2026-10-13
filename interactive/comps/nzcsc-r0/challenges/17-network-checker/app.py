#!/usr/bin/env python3
"""Network Checker — a "vibe coded" ping tool.

POST a `target` to `/` and the app runs `ping` against it, telling you only
whether the host was reachable (success / failed). The ping target is spliced
straight into a shell command (subprocess with shell=True) with only a tiny
blacklist of characters, so it is vulnerable to blind OS command injection —
the success/failed boolean is the only side channel back to the attacker.

The flag comes from the FLAG env var (never hard-coded); at startup we drop it
into /app/flag.txt so the intended solve path (reading the file byte-by-byte
through the boolean oracle) works. Listens on 0.0.0.0:5000.

The HTML/CSS served here is a byte-for-byte replica of the live challenge; the
form value and result text are HTML-escaped (markupsafe) exactly as the real
app does. Only the presentation was mirrored — the vulnerable ping/blacklist
backend below is unchanged so the intended solve still works.
"""
import os
import subprocess
from flask import Flask, request
from markupsafe import escape

FLAG = os.environ.get("FLAG", "NZCSC{placeholder_set_the_real_flag_in_flags.env}")
FLAG_PATH = "/app/flag.txt"

# Materialise the flag into a file inside the container so blind command
# injection can exfiltrate it (e.g. `od -An -tu1 -jN -N1 /app/flag.txt`).
try:
    with open(FLAG_PATH, "w") as fh:
        fh.write(FLAG + "\n")
except OSError:
    pass

# The "security" the devs bolted on: a four-character blacklist. It stops the
# obvious ;, |, backtick and " but leaves &&, $( ), ( ), <, ' and bash
# arithmetic wide open — more than enough for full blind RCE.
BANNED = [";", "|", "`", '"']

# --- Byte-exact page fragments captured verbatim from the live challenge ---
# Layout: HEAD + escape(target) + MID + [OUT_PRE + escape(output) + OUT_POST] + TAIL
HEAD = '<!doctype html>\n<html lang="en">\n\n<head>\n    <meta charset="utf-8">\n    <title>Network Checker</title>\n\n    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.7/dist/css/bootstrap.min.css" rel="stylesheet">\n\n    <style>\n        body {\n            background: #f4f6f9;\n        }\n\n        .terminal {\n            background: #111;\n            color: #0f0;\n            font-family: monospace;\n            white-space: pre-wrap;\n            border-radius: 8px;\n            padding: 20px;\n            min-height: 320px;\n        }\n\n        .card {\n            margin-top: 60px;\n        }\n    </style>\n</head>\n\n<body>\n\n    <div class="container">\n\n        <div class="row justify-content-center">\n\n            <div class="col-lg-8">\n\n                <div class="card shadow">\n\n                    <div class="card-header bg-primary text-white">\n                        <h3 class="mb-0">🌐 Network Checker</h3>\n                    </div>\n\n                    <div class="card-body">\n\n                        <p class="text-muted">\n                            Check connectivity to any host using ICMP ping.\n                        </p>\n\n                        <form method="POST">\n\n                            <div class="input-group mb-3">\n\n                                <input class="form-control" name="target" placeholder="8.8.8.8 or example.com"\n                                    value="'
MID = '" required>\n\n                                <button class="btn btn-primary">\n                                    Run Check\n                                </button>\n\n                            </div>\n\n                        </form>\n\n                        \n'
OUT_PRE = '\n                        <h5>Output</h5>\n\n                        <div class="terminal">'
OUT_POST = '</div>\n\n                        \n'
TAIL = '\n                    </div>\n\n                </div>\n\n            </div>\n\n        </div>\n\n    </div>\n\n</body>\n\n</html>'

app = Flask(__name__)


def render(target="", output=None):
    # target and output are echoed HTML-escaped, matching the real app exactly.
    page = HEAD + str(escape(target)) + MID
    if output is not None:
        page += OUT_PRE + str(escape(output)) + OUT_POST
    page += TAIL
    return page


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render()

    target = request.form.get("target", "")

    # Blacklist check — reject the four "dangerous" characters.
    for ch in target:
        if ch in BANNED:
            return render(target=target, output="banned char: " + ch)

    # Run the check. Output is deliberately NOT captured/returned — the
    # caller only ever learns success vs failed (blind).
    cmd = "ping -c 1 -w 2 " + target
    try:
        rc = subprocess.call(
            cmd, shell=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        rc = 1

    output = "success" if rc == 0 else "failed"
    return render(target=target, output=output)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
