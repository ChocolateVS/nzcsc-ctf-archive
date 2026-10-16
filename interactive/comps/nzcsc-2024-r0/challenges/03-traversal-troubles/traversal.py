"""NZCSC 2024 R0 - Challenge 3 "Traversal Troubles" (reconstruction).

Faithful reconstruction of a frontend-only capture: a page under /challenge3/
that reads a GET `?file=` parameter, reads that file off disk and echoes its
contents into a <pre>. The read is DELIBERATELY directory-traversal vulnerable,
so the intended solve `index.php?file=../../../../flag.txt` reveals the flag
sitting at /flag.txt. With no `?file=` it serves the original login page, and a
benign `?file=description.txt` shows an ordinary in-webroot file (no flag).

The vulnerable logic lives in `read_file()` and the routes live on a Blueprint
returned by `build_blueprint()`, so a future per-year "whole-site" container can
register the exact same blueprint under /challenge3 without copying any code.
Standalone hosting uses `create_app()`.
"""
import html
import os

from flask import Blueprint, Flask, Response, redirect, request, send_from_directory

# Directory holding the captured frontend (index.html, viewer.html, files/, ...).
# This is the challenge "web root": benign reads resolve against it; traversal
# payloads climb out of it.
CONTENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")

# Where the flag lives on disk. The original prose tells players it is at
# /flag.txt, and the canonical payload is `../../../../flag.txt` (climbing out of
# the webroot to the filesystem root). Overridable only for local testing.
FLAG_PATH = os.environ.get("FLAG_PATH", "/flag.txt")

# Default file shown when `?file=` is empty but present (benign, no flag).
DEFAULT_FILE = "description.txt"


def read_file(path, base_dir=None):
    """Read `path` relative to `base_dir` (the webroot) and return its text.

    DELIBERATELY VULNERABLE: the user-supplied path is joined onto the webroot
    with os.path.join and no sanitisation, exactly reproducing the original
    challenge's naive file include. os.path.join happily honours a leading
    `../` (or an absolute path), so `../../../../flag.txt` escapes the webroot
    and reaches /flag.txt. Do NOT "fix" this - the vulnerability is the point.
    """
    base = base_dir if base_dir is not None else CONTENT_DIR
    target = os.path.join(base, path)
    with open(target, "r", errors="replace") as fh:
        return fh.read()


def _render_viewer(contents):
    with open(os.path.join(CONTENT_DIR, "viewer.html"), "r") as fh:
        page = fh.read()
    # Echo file contents into the <pre>, HTML-escaped so markup in a read file
    # can't break the page (the traversal, not XSS, is the intended bug).
    return page.replace("@@FILE_CONTENTS@@", html.escape(contents))


def _login_page():
    with open(os.path.join(CONTENT_DIR, "index.html"), "r") as fh:
        return fh.read()


def build_blueprint(name="challenge3", url_prefix="/challenge3"):
    """Return the challenge as a Blueprint mountable at any prefix.

    The whole-site aggregate registers this at /challenge3 on its shared app;
    standalone hosting (create_app) does the same plus a `/` redirect. Either
    way the captured HTML's hard-coded `/challenge3/...` links line up.
    """
    bp = Blueprint(name, __name__)

    @bp.route("/", methods=["GET", "POST"])
    @bp.route("/index.php", methods=["GET", "POST"])
    def index():
        # No `file` parameter at all -> the original login landing page.
        if "file" not in request.args:
            return Response(_login_page(), mimetype="text/html")
        # `?file=` present -> the vulnerable file viewer.
        requested = request.args.get("file") or DEFAULT_FILE
        try:
            contents = read_file(requested)
        except (OSError, ValueError) as exc:
            contents = "Error reading %s: %s" % (requested, exc)
        return Response(_render_viewer(contents), mimetype="text/html")

    @bp.route("/files/<path:subpath>")
    def chrome(subpath):
        # Serve the captured css/js/img/font chrome.
        return send_from_directory(os.path.join(CONTENT_DIR, "files"), subpath)

    return bp, url_prefix


def ensure_flag_file():
    """Materialise /flag.txt from the FLAG env so the traversal target exists.

    Runs at container start. Harmless/no-op if the path isn't writable (e.g. in
    the whole-site container where another process owns it)."""
    flag = os.environ.get("FLAG", "NZCSC{A_TRULY_TR34CH3R0US_TR4V3RS4L}")
    try:
        with open(FLAG_PATH, "w") as fh:
            fh.write(flag + "\n")
    except OSError:
        pass


def create_app():
    """Standalone app: challenge mounted at /challenge3 + a root redirect to it."""
    ensure_flag_file()
    app = Flask(__name__)
    bp, prefix = build_blueprint()
    app.register_blueprint(bp, url_prefix=prefix)

    @app.route("/")
    def root():
        return redirect(prefix + "/")

    return app
