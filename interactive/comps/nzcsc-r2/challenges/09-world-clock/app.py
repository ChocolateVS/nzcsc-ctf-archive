import subprocess
from pathlib import Path

from flask import Flask, request, abort, Response

app = Flask(__name__)

# Served verbatim; byte-for-byte identical to the original landing page.
INDEX_HTML = Path(app.root_path, "templates", "index.html").read_bytes()

# The clock page wraps the output of `date` in a <pre>. The original builds
# this by string concatenation (NOT str.format / f-string), so output that
# contains braces is emitted as-is.
CLOCK_HEAD = (
    "<html>\n"
    "    <body>\n"
    "        <div>\n"
    "            <p>Your local date: <pre>"
)
CLOCK_TAIL = (
    "</pre></p>\n"
    "        </div>\n"
    "    </body>\n"
    "</html>"
)


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


@app.route("/clock")
def clock():
    tz = request.args.get("tz")
    if tz is None:
        abort(400)

    # VULNERABILITY: the timezone is interpolated into a DOUBLE-QUOTED shell
    # assignment prefix to `date`, exactly like the original:  TZ="<tz>" date.
    # The quotes mean a bare `;cmd;` is literal (no command separator), but
    # command substitution ($(...) / backticks) still expands inside double
    # quotes, so the injection channel is substitution only, e.g.
    #   tz = $(id)            -> date's zone field shows `uid`
    #   tz = $(cat /app/flag.txt | od -An -tx1 | tr -dc 0-9a-f ...)
    # The output channel is just the TZ abbreviation `date` prints, which
    # glibc truncates at the first non-alpha char - so exfil is hex/letters.
    result = subprocess.run(
        f'TZ="{tz}" date',
        shell=True,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        abort(500)

    return Response(CLOCK_HEAD + result.stdout + CLOCK_TAIL, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
