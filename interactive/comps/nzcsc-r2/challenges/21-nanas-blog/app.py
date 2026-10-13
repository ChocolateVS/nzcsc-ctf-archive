"""21 - Nana's Blog

A reproduction of the live WordPress 7.0.1 "Turtle Blog" challenge.

The public blog looks empty: GET /index.php?rest_route=/wp/v2/posts returns [].
But one post exists and is password protected. The intended solve chain:

  1. Enumerate post IDs over the REST API (IDOR):
       /index.php?rest_route=/wp/v2/posts/<id>
     Every id returns 404 rest_post_invalid_id EXCEPT id 7, which returns
     401 rest_forbidden -- so post 7 exists but is not readable.

  2. Supplying a password reveals it is PASSWORD PROTECTED, not private:
       /index.php?rest_route=/wp/v2/posts/7&password=wrong
     -> 403 rest_post_incorrect_password  (a clean oracle)

  3. The REST `password` parameter is unauthenticated, has no cookie, no CSRF
     token and no rate limiting (unlike the front-end password form), so the
     post password can be brute forced with a wordlist (e.g. rockyou).

  4. The correct password returns the post, whose content is the flag.

Flag is read from $FLAG, else flag.txt.
"""

import os
import json
from pathlib import Path

from flask import Flask, request, Response, render_template

app = Flask(__name__)

# The post password. Intentionally a common wordlist entry so the post is
# brute-forceable -- that IS the intended vulnerability.
POST_PASSWORD = "turtles"

# The one (hidden, password-protected) post. Any other id is "invalid".
SECRET_POST_ID = 7

SITE_TITLE = "Turtle Blog"
WP_VERSION = "7.0.1"


def read_flag() -> str:
    env = os.environ.get("FLAG")
    if env:
        return env.strip()
    return Path(__file__).with_name("flag.txt").read_text().strip()


def site_url() -> str:
    # Mirror the links WordPress emits, based on the incoming request.
    return request.host_url.rstrip("/")


def wp_json(payload, status: int = 200) -> Response:
    resp = Response(
        json.dumps(payload, ensure_ascii=False),
        status=status,
        mimetype="application/json; charset=UTF-8",
    )
    resp.headers["Link"] = (
        f'<{site_url()}/index.php?rest_route=/>; rel="https://api.w.org/"'
    )
    resp.headers["X-Robots-Tag"] = "noindex"
    return resp


def rest_error(code: str, message: str, status: int) -> Response:
    return wp_json({"code": code, "message": message, "data": {"status": status}}, status)


# --------------------------------------------------------------------------
# REST endpoint handlers
# --------------------------------------------------------------------------

def rest_root():
    base = site_url()
    return wp_json({
        "name": SITE_TITLE,
        "description": "",
        "url": base,
        "home": base,
        "gmt_offset": "0",
        "timezone_string": "",
        "namespaces": [
            "oembed/1.0",
            "wp/v2",
            "wp-site-health/v1",
            "wp-block-editor/v1",
            "wp-abilities/v1",
        ],
        "authentication": {"application-passwords": {"endpoints": {
            "authorization": f"{base}/wp-admin/authorize-application.php"}}},
        "routes": {
            "/": {"namespace": "", "methods": ["GET"]},
            "/wp/v2/posts": {"namespace": "wp/v2", "methods": ["GET", "POST"]},
            "/wp/v2/posts/(?P<id>[\\d]+)": {"namespace": "wp/v2", "methods": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
            "/wp/v2/pages": {"namespace": "wp/v2", "methods": ["GET", "POST"]},
            "/wp/v2/comments": {"namespace": "wp/v2", "methods": ["GET", "POST"]},
            "/wp/v2/users": {"namespace": "wp/v2", "methods": ["GET", "POST"]},
            "/wp/v2/users/(?P<id>[\\d]+)": {"namespace": "wp/v2", "methods": ["GET"]},
            "/wp/v2/categories": {"namespace": "wp/v2", "methods": ["GET", "POST"]},
            "/wp/v2/tags": {"namespace": "wp/v2", "methods": ["GET", "POST"]},
            "/wp/v2/search": {"namespace": "wp/v2", "methods": ["GET"]},
            "/wp/v2/settings": {"namespace": "wp/v2", "methods": ["GET", "POST"]},
        },
        "_links": {"help": [{"href": "https://developer.wordpress.org/rest-api/"}]},
    })


def rest_users():
    base = site_url()
    return wp_json([{
        "id": 1,
        "name": "admin",
        "url": "http://localhost:8888",
        "description": "",
        "link": f"{base}/?author=1",
        "slug": "admin",
        "avatar_urls": {
            "24": "https://secure.gravatar.com/avatar/31438b454d7febbc6c5f32b39800ec314972a041500679d013952a91654d55a0?s=24&d=mm&r=g",
            "48": "https://secure.gravatar.com/avatar/31438b454d7febbc6c5f32b39800ec314972a041500679d013952a91654d55a0?s=48&d=mm&r=g",
            "96": "https://secure.gravatar.com/avatar/31438b454d7febbc6c5f32b39800ec314972a041500679d013952a91654d55a0?s=96&d=mm&r=g",
        },
        "meta": [],
        "_links": {
            "self": [{"href": f"{base}/index.php?rest_route=/wp/v2/users/1",
                      "targetHints": {"allow": ["GET"]}}],
            "collection": [{"href": f"{base}/index.php?rest_route=/wp/v2/users"}],
        },
    }])


def rest_user_single(uid: int):
    if uid == 1:
        data = rest_users()
        # unwrap the single object
        return wp_json(json.loads(data.get_data())[0])
    return rest_error("rest_user_invalid_id", "Invalid user ID.", 404)


def rest_categories():
    base = site_url()
    return wp_json([{
        "id": 1, "count": 1, "description": "",
        "link": f"{base}/?cat=1", "name": "Uncategorized",
        "slug": "uncategorized", "taxonomy": "category", "parent": 0, "meta": [],
        "_links": {
            "self": [{"href": f"{base}/index.php?rest_route=/wp/v2/categories/1",
                      "targetHints": {"allow": ["GET"]}}],
            "collection": [{"href": f"{base}/index.php?rest_route=/wp/v2/categories"}],
        },
    }])


def rest_statuses():
    base = site_url()
    return wp_json({"publish": {
        "name": "Published", "public": True, "queryable": True,
        "slug": "publish", "date_floating": False,
        "_links": {"archives": [{"href": f"{base}/index.php?rest_route=/wp/v2/posts"}]},
    }})


def secret_post_payload():
    base = site_url()
    flag = read_flag()
    return {
        "id": SECRET_POST_ID,
        "date": "2026-02-02T09:00:00",
        "date_gmt": "2026-02-02T09:00:00",
        "guid": {"rendered": f"{base}/?p={SECRET_POST_ID}"},
        "modified": "2026-02-02T09:00:00",
        "slug": "nanas-secret-recipe",
        "status": "publish",
        "type": "post",
        "link": f"{base}/?p={SECRET_POST_ID}",
        "title": {"rendered": "Nana&#8217;s Secret Recipe"},
        "content": {
            "rendered": (
                "<p>Shh &mdash; don&#8217;t tell the other turtles. "
                "Nana finally wrote it down:</p>\n"
                f"<p><strong>{flag}</strong></p>\n"
                "<p>Keep it in the family.</p>\n"
            ),
            "protected": True,
        },
        "excerpt": {
            "rendered": "<p>There is no excerpt because this is a protected post.</p>\n",
            "protected": True,
        },
        "author": 1,
        "featured_media": 0,
        "comment_status": "open",
        "ping_status": "open",
        "sticky": False,
        "template": "",
        "format": "standard",
        "meta": [],
        "categories": [1],
        "tags": [],
        "_links": {
            "self": [{"href": f"{base}/index.php?rest_route=/wp/v2/posts/{SECRET_POST_ID}",
                      "targetHints": {"allow": ["GET"]}}],
            "collection": [{"href": f"{base}/index.php?rest_route=/wp/v2/posts"}],
            "author": [{"href": f"{base}/index.php?rest_route=/wp/v2/users/1"}],
        },
    }


def rest_post_single(pid: int):
    if pid != SECRET_POST_ID:
        return rest_error("rest_post_invalid_id", "Invalid post ID.", 404)

    # Post 7 exists but is password protected.
    password = request.args.get("password")
    if password is None:
        # No password offered -> WordPress refuses to hand over the post.
        return rest_error("rest_forbidden", "Sorry, you are not allowed to do that.", 401)
    if password != POST_PASSWORD:
        return rest_error("rest_post_incorrect_password", "Incorrect post password.", 403)

    # Correct password -> full post, flag inside content.rendered.
    return wp_json(secret_post_payload())


# Map a rest_route string to a handler. Collection endpoints that are empty
# for unauthenticated users mirror the live site (posts/pages/comments/search).
def dispatch_rest(route: str) -> Response:
    route = "/" + route.strip("/") if route not in ("", "/") else "/"

    if route == "/":
        return rest_root()
    if route == "/wp/v2/posts":
        return wp_json([])
    if route == "/wp/v2/pages":
        return wp_json([])
    if route == "/wp/v2/comments":
        return wp_json([])
    if route == "/wp/v2/search":
        return wp_json([])
    if route == "/wp/v2/tags":
        return wp_json([])
    if route == "/wp/v2/users":
        return rest_users()
    if route == "/wp/v2/categories":
        return rest_categories()
    if route == "/wp/v2/statuses":
        return rest_statuses()

    # /wp/v2/posts/<id>
    if route.startswith("/wp/v2/posts/"):
        tail = route[len("/wp/v2/posts/"):]
        if tail.isdigit():
            return rest_post_single(int(tail))
        if tail.endswith("/revisions") and tail[:-len("/revisions")].isdigit():
            return rest_error("rest_cannot_read",
                              "Sorry, you are not allowed to view revisions of this post.", 401)
        if tail.endswith("/autosaves") and tail[:-len("/autosaves")].isdigit():
            return rest_error("rest_cannot_read",
                              "Sorry, you are not allowed to view autosaves of this post.", 401)

    # /wp/v2/users/<id>
    if route.startswith("/wp/v2/users/"):
        tail = route[len("/wp/v2/users/"):]
        if tail.isdigit():
            return rest_user_single(int(tail))
        if tail == "me":
            return rest_error("rest_not_logged_in", "You are not currently logged in.", 401)

    # Privileged / editor-only surfaces: forbidden, like the live site.
    if route in ("/wp/v2/settings",
                 "/wp-abilities/v1/abilities",
                 "/wp-abilities/v1/categories"):
        return rest_error("rest_forbidden", "Sorry, you are not allowed to do that.", 401)

    return rest_error("rest_no_route",
                      "No route was found matching the URL and request method.", 404)


# --------------------------------------------------------------------------
# HTTP routes (WordPress uses query-string routing, pretty permalinks off)
# --------------------------------------------------------------------------

@app.route("/index.php")
def index_php():
    if "rest_route" in request.args:
        return dispatch_rest(request.args.get("rest_route", "/"))
    return homepage()


# WordPress also serves the REST API under /wp-json when available.
@app.route("/wp-json/")
@app.route("/wp-json")
def wp_json_root():
    return dispatch_rest("/")


@app.route("/wp-json/<path:route>")
def wp_json_route(route):
    return dispatch_rest("/" + route)


@app.route("/")
def homepage():
    # Match the live behaviour of the query-string front controller.
    if "rest_route" in request.args:
        return dispatch_rest(request.args.get("rest_route", "/"))
    if request.args.get("feed"):
        return feed()
    # ?p=, ?author=, ?cat= front-end views: nothing public to show.
    if "p" in request.args or "author" in request.args or "cat" in request.args:
        return render_template("notfound.html",
                               site_title=SITE_TITLE, wp_version=WP_VERSION,
                               site_url=site_url()), 404
    return render_template("index.html",
                           site_title=SITE_TITLE, wp_version=WP_VERSION,
                           site_url=site_url())


@app.route("/xmlrpc.php")
def xmlrpc():
    if request.args.get("rsd") is not None:
        rsd = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rsd version="1.0" xmlns="http://archipelago.phrasewise.com/rsd">\n'
            '  <service><engineName>WordPress</engineName>\n'
            f'    <homePageLink>{site_url()}</homePageLink>\n'
            f'    <apis><api name="WordPress" blogID="1" preferred="true" '
            f'apiLink="{site_url()}/xmlrpc.php"/></apis>\n'
            '  </service>\n</rsd>\n'
        )
        return Response(rsd, mimetype="text/xml")
    return Response("XML-RPC server accepts POST requests only.", mimetype="text/plain")


def feed():
    base = site_url()
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" '
        'xmlns:atom="http://www.w3.org/2005/Atom">\n<channel>\n'
        f'\t<title>{SITE_TITLE}</title>\n'
        f'\t<atom:link href="{base}/?feed=rss2" rel="self" type="application/rss+xml" />\n'
        f'\t<link>{base}</link>\n\t<description></description>\n'
        f'\t<generator>https://wordpress.org/?v={WP_VERSION}</generator>\n'
        '</channel>\n</rss>'
    )
    return Response(xml, mimetype="application/rss+xml; charset=UTF-8")


@app.route("/wp-login.php", methods=["GET", "POST"])
def wp_login():
    return render_template("login.html", site_title=SITE_TITLE, site_url=site_url())


@app.errorhandler(404)
def not_found(_e):
    return render_template("notfound.html", site_title=SITE_TITLE,
                           wp_version=WP_VERSION, site_url=site_url()), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
