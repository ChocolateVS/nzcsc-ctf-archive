import os
import sqlite3
from pathlib import Path

from flask import Flask, render_template, request

app = Flask(__name__)

# Per-worker file-backed SQLite DB, seeded on startup.
DB_PATH = f"/tmp/flags_{os.getpid()}.db"


def read_flag() -> str:
    return Path("flag.txt").read_text().strip()


# (country_name, emoji_flag) for ordinary rows. The challenge flag lives in a
# dedicated row whose country is "NZCSC", hidden by the query's NOT LIKE clause.
COUNTRIES = [
    ("Afghanistan", "\U0001F1E6\U0001F1EB"),
    ("Albania", "\U0001F1E6\U0001F1F1"),
    ("Argentina", "\U0001F1E6\U0001F1F7"),
    ("Australia", "\U0001F1E6\U0001F1FA"),
    ("Austria", "\U0001F1E6\U0001F1F9"),
    ("Belgium", "\U0001F1E7\U0001F1EA"),
    ("Brazil", "\U0001F1E7\U0001F1F7"),
    ("Canada", "\U0001F1E8\U0001F1E6"),
    ("Chile", "\U0001F1E8\U0001F1F1"),
    ("China", "\U0001F1E8\U0001F1F3"),
    ("Croatia", "\U0001F1ED\U0001F1F7"),
    ("Denmark", "\U0001F1E9\U0001F1F0"),
    ("Egypt", "\U0001F1EA\U0001F1EC"),
    ("Finland", "\U0001F1EB\U0001F1EE"),
    ("France", "\U0001F1EB\U0001F1F7"),
    ("Germany", "\U0001F1E9\U0001F1EA"),
    ("Greece", "\U0001F1EC\U0001F1F7"),
    ("India", "\U0001F1EE\U0001F1F3"),
    ("Indonesia", "\U0001F1EE\U0001F1E9"),
    ("Ireland", "\U0001F1EE\U0001F1EA"),
    ("Italy", "\U0001F1EE\U0001F1F9"),
    ("Japan", "\U0001F1EF\U0001F1F5"),
    ("Kenya", "\U0001F1F0\U0001F1EA"),
    ("Malaysia", "\U0001F1F2\U0001F1FE"),
    ("Mexico", "\U0001F1F2\U0001F1FD"),
    ("Netherlands", "\U0001F1F3\U0001F1F1"),
    ("New Zealand", "\U0001F1F3\U0001F1FF"),
    ("Norway", "\U0001F1F3\U0001F1F4"),
    ("Pakistan", "\U0001F1F5\U0001F1F0"),
    ("Peru", "\U0001F1F5\U0001F1EA"),
    ("Philippines", "\U0001F1F5\U0001F1ED"),
    ("Poland", "\U0001F1F5\U0001F1F1"),
    ("Portugal", "\U0001F1F5\U0001F1F9"),
    ("Russia", "\U0001F1F7\U0001F1FA"),
    ("Singapore", "\U0001F1F8\U0001F1EC"),
    ("South Africa", "\U0001F1FF\U0001F1E6"),
    ("Spain", "\U0001F1EA\U0001F1F8"),
    ("Sweden", "\U0001F1F8\U0001F1EA"),
    ("Switzerland", "\U0001F1E8\U0001F1ED"),
    ("Thailand", "\U0001F1F9\U0001F1ED"),
    ("Turkey", "\U0001F1F9\U0001F1F7"),
    ("Ukraine", "\U0001F1FA\U0001F1E6"),
    ("United Kingdom", "\U0001F1EC\U0001F1E7"),
    ("United States", "\U0001F1FA\U0001F1F8"),
    ("Vietnam", "\U0001F1FB\U0001F1F3"),
]


def seed_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS flags")
    cur.execute(
        """
        CREATE TABLE flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT NOT NULL,
            flag TEXT NOT NULL
        )
        """
    )
    cur.executemany(
        "INSERT INTO flags (country, flag) VALUES (?, ?)", COUNTRIES
    )
    # The real prize: a flag row hidden behind the query's NOT LIKE 'NZCSC' filter.
    cur.execute(
        "INSERT INTO flags (country, flag) VALUES (?, ?)", ("NZCSC", read_flag())
    )
    conn.commit()
    conn.close()


seed_db()


@app.route("/")
def index():
    country = request.args.get("country", "")
    debug = request.args.get("debug") == "1"

    query = None
    results = None

    if country:
        # Intentionally vulnerable: user input is concatenated straight into the
        # SQL string. The NOT LIKE 'NZCSC' clause is meant to keep the flag row
        # hidden -- but an injection can comment it out or OR past it.
        query = (
            "SELECT * FROM flags WHERE country LIKE '%"
            + country
            + "%' AND country NOT LIKE 'NZCSC';"
        )
        conn = sqlite3.connect(DB_PATH)
        try:
            cur = conn.cursor()
            cur.execute(query)
            results = cur.fetchall()
        except Exception:
            results = None
        finally:
            conn.close()

    return render_template(
        "index.html", country=country, debug=debug, query=query, results=results
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
