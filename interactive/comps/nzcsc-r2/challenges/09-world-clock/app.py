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

    # VULNERABILITY: the timezone is interpolated unquoted as a shell
    # assignment prefix to `date`. Because an assignment RHS is not subject
    # to word splitting, command substitution ($(...) / backticks) in `tz`
    # is executed, and a bare command after the assignment runs too, e.g.
    #   tz = x cat /app/flag.txt #
    #   -> TZ=x cat /app/flag.txt # date
    result = subprocess.run(
        f"TZ={tz} date",
        shell=True,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        abort(500)

    return Response(CLOCK_HEAD + result.stdout + CLOCK_TAIL, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
