#!/usr/bin/env python3
"""13 - No More SQL Injections (type http).

Replica of an AI-written "SQL-injection-proof" login that switched to a
MongoDB/Mongoose-style NoSQL backend but passes the JSON request body's
username/password straight into the query without stripping Mongo query
operators. Result: a classic NoSQL injection.

  * {"username": {"$ne": null}, "password": {"$ne": null}}  -> auth bypass
  * {"username": "admin", "password": {"$regex": "..."}}    -> blind boolean oracle

The admin user's stored "password" IS the flag, so the $regex oracle exfiltrates
the flag one character at a time. The flag comes from the FLAG env var (set by the
generator from flags.env) -- read it, never hard-code it. Listen on 0.0.0.0:5000
(matches `port: 5000` in challenge.yml)."""
import os
import re
from flask import Flask, request, jsonify, Response

FLAG = os.environ.get("FLAG", "NZCSC{placeholder_set_the_real_flag_in_flags.env}")

app = Flask(__name__)

# In-memory "mongo-like" users collection. The admin password is the flag.
USERS = [
    {"username": "admin", "password": FLAG, "role": "admin"},
]


def _match_value(actual, condition):
    """Evaluate a single field condition, honouring Mongo-style operators.

    A scalar condition is an equality test. A dict condition is a set of
    query operators ($ne, $eq, $regex, $gt, $lt, $in, ...) -- exactly what an
    unsanitised `User.findOne(req.body)` would feed to MongoDB.
    """
    if isinstance(condition, dict):
        for op, operand in condition.items():
            if op in ("$ne", "$neq"):
                if actual == operand:
                    return False
            elif op == "$eq":
                if actual != operand:
                    return False
            elif op == "$gt":
                if not (actual is not None and operand is not None and actual > operand):
                    return False
            elif op == "$gte":
                if not (actual is not None and operand is not None and actual >= operand):
                    return False
            elif op == "$lt":
                if not (actual is not None and operand is not None and actual < operand):
                    return False
            elif op == "$lte":
                if not (actual is not None and operand is not None and actual <= operand):
                    return False
            elif op == "$in":
                if not (isinstance(operand, list) and actual in operand):
                    return False
            elif op == "$nin":
                if isinstance(operand, list) and actual in operand:
                    return False
            elif op == "$regex":
                if not isinstance(actual, str) or not isinstance(operand, str):
                    return False
                flags = 0
                options = condition.get("$options", "")
                if "i" in options:
                    flags |= re.IGNORECASE
                if "m" in options:
                    flags |= re.MULTILINE
                if "s" in options:
                    flags |= re.DOTALL
                try:
                    # Mongo $regex is an unanchored (partial) match, like re.search.
                    if re.search(operand, actual, flags) is None:
                        return False
                except re.error:
                    return False
            elif op == "$options":
                continue  # handled alongside $regex
            else:
                # Unknown operator -> no match (mirrors a query that finds nothing).
                return False
        return True
    # Plain scalar -> equality comparison.
    return actual == condition


def find_one(collection, query):
    """Return the first document matching every field condition in `query`."""
    if not isinstance(query, dict):
        return None
    for doc in collection:
        if all(_match_value(doc.get(field), cond) for field, cond in query.items()):
            return doc
    return None


# The public login page is served byte-for-byte from the real challenge's
# response body (captured verbatim into index.html). No CSS/JS assets are
# referenced by the page, so nothing else needs serving.
_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "index.html"), "rb") as _f:
    LOGIN_PAGE = _f.read()


def _json(payload, status=200):
    """Emit compact JSON matching the real Express server's wording/shape.

    Express `res.json(...)` produces separator-free JSON (no spaces after ':'
    or ','), so we serialise the same way to keep responses byte-identical.
    """
    import json
    data = json.dumps(payload, separators=(",", ":"))
    return Response(data, status=status, mimetype="application/json")


@app.get("/")
def index():
    return Response(LOGIN_PAGE, mimetype="text/html")


@app.post("/login")
def login():
    # Parse JSON leniently: accepts objects OR nested operator objects, exactly
    # like Express's express.json() would hand off to Mongoose unsanitised.
    body = request.get_json(silent=True, force=True)
    username = body.get("username") if isinstance(body, dict) else None
    password = body.get("password") if isinstance(body, dict) else None

    # VULNERABLE: the raw JSON values (which may be Mongo operator objects) are
    # passed straight into the query with no sanitisation.
    user = find_one(USERS, {"username": username, "password": password})
    if user is not None:
        # Real server: 200 {"success":true,"user":"admin"}
        return _json({"success": True, "user": user["username"]})
    # Real server: 401 {"success":false,"message":"Invalid credentials"} for any
    # failed / missing / non-matching login (no distinct 400 branch).
    return _json({"success": False, "message": "Invalid credentials"}, 401)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
