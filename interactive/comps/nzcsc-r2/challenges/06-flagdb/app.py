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
    ("Algeria", "\U0001F1E9\U0001F1FF"),
    ("American Samoa", "\U0001F1E6\U0001F1F8"),
    ("Andorra", "\U0001F1E6\U0001F1E9"),
    ("Angola", "\U0001F1E6\U0001F1F4"),
    ("Anguilla", "\U0001F1E6\U0001F1EE"),
    ("Antarctica", "\U0001F1E6\U0001F1F6"),
    ("Antigua and Barbuda", "\U0001F1E6\U0001F1EC"),
    ("Argentina", "\U0001F1E6\U0001F1F7"),
    ("Armenia", "\U0001F1E6\U0001F1F2"),
    ("Aruba", "\U0001F1E6\U0001F1FC"),
    ("Australia", "\U0001F1E6\U0001F1FA"),
    ("Austria", "\U0001F1E6\U0001F1F9"),
    ("Azerbaijan", "\U0001F1E6\U0001F1FF"),
    ("Bahamas", "\U0001F1E7\U0001F1F8"),
    ("Bahrain", "\U0001F1E7\U0001F1ED"),
    ("Bangladesh", "\U0001F1E7\U0001F1E9"),
    ("Barbados", "\U0001F1E7\U0001F1E7"),
    ("Belarus", "\U0001F1E7\U0001F1FE"),
    ("Belgium", "\U0001F1E7\U0001F1EA"),
    ("Belize", "\U0001F1E7\U0001F1FF"),
    ("Benin", "\U0001F1E7\U0001F1EF"),
    ("Bermuda", "\U0001F1E7\U0001F1F2"),
    ("Bhutan", "\U0001F1E7\U0001F1F9"),
    ("Bolivia", "\U0001F1E7\U0001F1F4"),
    ("Bosnia and Herzegovina", "\U0001F1E7\U0001F1E6"),
    ("Botswana", "\U0001F1E7\U0001F1FC"),
    ("Bouvet Island", "\U0001F1E7\U0001F1FB"),
    ("Brazil", "\U0001F1E7\U0001F1F7"),
    ("Brunei Darussalam", "\U0001F1E7\U0001F1F3"),
    ("Bulgaria", "\U0001F1E7\U0001F1EC"),
    ("Burkina Faso", "\U0001F1E7\U0001F1EB"),
    ("Burundi", "\U0001F1E7\U0001F1EE"),
    ("Cabo Verde", "\U0001F1E8\U0001F1FB"),
    ("Cambodia", "\U0001F1F0\U0001F1ED"),
    ("Cameroon", "\U0001F1E8\U0001F1F2"),
    ("Canada", "\U0001F1E8\U0001F1E6"),
    ("Cayman Islands", "\U0001F1F0\U0001F1FE"),
    ("Central African Republic", "\U0001F1E8\U0001F1EB"),
    ("Chad", "\U0001F1F9\U0001F1E9"),
    ("Chile", "\U0001F1E8\U0001F1F1"),
    ("China", "\U0001F1E8\U0001F1F3"),
    ("Christmas Island", "\U0001F1E8\U0001F1FD"),
    ("Cocos (Keeling) Islands", "\U0001F1E8\U0001F1E8"),
    ("Colombia", "\U0001F1E8\U0001F1F4"),
    ("Comoros", "\U0001F1F0\U0001F1F2"),
    ("Congo", "\U0001F1E8\U0001F1EC"),
    ("Congo, The Democratic Republic of the", "\U0001F1E8\U0001F1E9"),
    ("Cook Islands", "\U0001F1E8\U0001F1F0"),
    ("Costa Rica", "\U0001F1E8\U0001F1F7"),
    ("Croatia", "\U0001F1ED\U0001F1F7"),
    ("Cuba", "\U0001F1E8\U0001F1FA"),
    ("Curaçao", "\U0001F1E8\U0001F1FC"),
    ("Cyprus", "\U0001F1E8\U0001F1FE"),
    ("Czechia", "\U0001F1E8\U0001F1FF"),
    ("Côte d'Ivoire", "\U0001F1E8\U0001F1EE"),
    ("Denmark", "\U0001F1E9\U0001F1F0"),
    ("Djibouti", "\U0001F1E9\U0001F1EF"),
    ("Dominica", "\U0001F1E9\U0001F1F2"),
    ("Dominican Republic", "\U0001F1E9\U0001F1F4"),
    ("Ecuador", "\U0001F1EA\U0001F1E8"),
    ("Egypt", "\U0001F1EA\U0001F1EC"),
    ("El Salvador", "\U0001F1F8\U0001F1FB"),
    ("Equatorial Guinea", "\U0001F1EC\U0001F1F6"),
    ("Eritrea", "\U0001F1EA\U0001F1F7"),
    ("Estonia", "\U0001F1EA\U0001F1EA"),
    ("Eswatini", "\U0001F1F8\U0001F1FF"),
    ("Ethiopia", "\U0001F1EA\U0001F1F9"),
    ("Fiji", "\U0001F1EB\U0001F1EF"),
    ("Finland", "\U0001F1EB\U0001F1EE"),
    ("France", "\U0001F1EB\U0001F1F7"),
    ("French Guiana", "\U0001F1EC\U0001F1EB"),
    ("French Polynesia", "\U0001F1F5\U0001F1EB"),
    ("Gabon", "\U0001F1EC\U0001F1E6"),
    ("Gambia", "\U0001F1EC\U0001F1F2"),
    ("Georgia", "\U0001F1EC\U0001F1EA"),
    ("Germany", "\U0001F1E9\U0001F1EA"),
    ("Ghana", "\U0001F1EC\U0001F1ED"),
    ("Gibraltar", "\U0001F1EC\U0001F1EE"),
    ("Greece", "\U0001F1EC\U0001F1F7"),
    ("Greenland", "\U0001F1EC\U0001F1F1"),
    ("Grenada", "\U0001F1EC\U0001F1E9"),
    ("Guadeloupe", "\U0001F1EC\U0001F1F5"),
    ("Guam", "\U0001F1EC\U0001F1FA"),
    ("Guatemala", "\U0001F1EC\U0001F1F9"),
    ("Guernsey", "\U0001F1EC\U0001F1EC"),
    ("Guinea", "\U0001F1EC\U0001F1F3"),
    ("Guinea-Bissau", "\U0001F1EC\U0001F1FC"),
    ("Guyana", "\U0001F1EC\U0001F1FE"),
    ("Haiti", "\U0001F1ED\U0001F1F9"),
    ("Honduras", "\U0001F1ED\U0001F1F3"),
    ("Hong Kong", "\U0001F1ED\U0001F1F0"),
    ("Hungary", "\U0001F1ED\U0001F1FA"),
    ("Iceland", "\U0001F1EE\U0001F1F8"),
    ("India", "\U0001F1EE\U0001F1F3"),
    ("Indonesia", "\U0001F1EE\U0001F1E9"),
    ("Iran", "\U0001F1EE\U0001F1F7"),
    ("Iraq", "\U0001F1EE\U0001F1F6"),
    ("Ireland", "\U0001F1EE\U0001F1EA"),
    ("Isle of Man", "\U0001F1EE\U0001F1F2"),
    ("Israel", "\U0001F1EE\U0001F1F1"),
    ("Italy", "\U0001F1EE\U0001F1F9"),
    ("Jamaica", "\U0001F1EF\U0001F1F2"),
    ("Japan", "\U0001F1EF\U0001F1F5"),
    ("Jersey", "\U0001F1EF\U0001F1EA"),
    ("Jordan", "\U0001F1EF\U0001F1F4"),
    ("Kazakhstan", "\U0001F1F0\U0001F1FF"),
    ("Kenya", "\U0001F1F0\U0001F1EA"),
    ("Kiribati", "\U0001F1F0\U0001F1EE"),
    ("Korea, Democratic People's Republic of", "\U0001F1F0\U0001F1F5"),
    ("Korea, Republic of", "\U0001F1F0\U0001F1F7"),
    ("Kuwait", "\U0001F1F0\U0001F1FC"),
    ("Kyrgyzstan", "\U0001F1F0\U0001F1EC"),
    ("Latvia", "\U0001F1F1\U0001F1FB"),
    ("Lebanon", "\U0001F1F1\U0001F1E7"),
    ("Lesotho", "\U0001F1F1\U0001F1F8"),
    ("Liberia", "\U0001F1F1\U0001F1F7"),
    ("Libya", "\U0001F1F1\U0001F1FE"),
    ("Liechtenstein", "\U0001F1F1\U0001F1EE"),
    ("Lithuania", "\U0001F1F1\U0001F1F9"),
    ("Luxembourg", "\U0001F1F1\U0001F1FA"),
    ("Macao", "\U0001F1F2\U0001F1F4"),
    ("Madagascar", "\U0001F1F2\U0001F1EC"),
    ("Malawi", "\U0001F1F2\U0001F1FC"),
    ("Malaysia", "\U0001F1F2\U0001F1FE"),
    ("Maldives", "\U0001F1F2\U0001F1FB"),
    ("Mali", "\U0001F1F2\U0001F1F1"),
    ("Malta", "\U0001F1F2\U0001F1F9"),
    ("Marshall Islands", "\U0001F1F2\U0001F1ED"),
    ("Martinique", "\U0001F1F2\U0001F1F6"),
    ("Mauritania", "\U0001F1F2\U0001F1F7"),
    ("Mauritius", "\U0001F1F2\U0001F1FA"),
    ("Mayotte", "\U0001F1FE\U0001F1F9"),
    ("Mexico", "\U0001F1F2\U0001F1FD"),
    ("Micronesia", "\U0001F1EB\U0001F1F2"),
    ("Moldova", "\U0001F1F2\U0001F1E9"),
    ("Monaco", "\U0001F1F2\U0001F1E8"),
    ("Mongolia", "\U0001F1F2\U0001F1F3"),
    ("Montenegro", "\U0001F1F2\U0001F1EA"),
    ("Montserrat", "\U0001F1F2\U0001F1F8"),
    ("Morocco", "\U0001F1F2\U0001F1E6"),
    ("Mozambique", "\U0001F1F2\U0001F1FF"),
    ("Myanmar", "\U0001F1F2\U0001F1F2"),
    ("Namibia", "\U0001F1F3\U0001F1E6"),
    ("Nauru", "\U0001F1F3\U0001F1F7"),
    ("Nepal", "\U0001F1F3\U0001F1F5"),
    ("Netherlands", "\U0001F1F3\U0001F1F1"),
    ("New Caledonia", "\U0001F1F3\U0001F1E8"),
    ("New Zealand", "\U0001F1F3\U0001F1FF"),
    ("Nicaragua", "\U0001F1F3\U0001F1EE"),
    ("Niger", "\U0001F1F3\U0001F1EA"),
    ("Nigeria", "\U0001F1F3\U0001F1EC"),
    ("Niue", "\U0001F1F3\U0001F1FA"),
    ("Norfolk Island", "\U0001F1F3\U0001F1EB"),
    ("North Macedonia", "\U0001F1F2\U0001F1F0"),
    ("Northern Mariana Islands", "\U0001F1F2\U0001F1F5"),
    ("Norway", "\U0001F1F3\U0001F1F4"),
    ("Oman", "\U0001F1F4\U0001F1F2"),
    ("Pakistan", "\U0001F1F5\U0001F1F0"),
    ("Palau", "\U0001F1F5\U0001F1FC"),
    ("Palestine", "\U0001F1F5\U0001F1F8"),
    ("Panama", "\U0001F1F5\U0001F1E6"),
    ("Papua New Guinea", "\U0001F1F5\U0001F1EC"),
    ("Paraguay", "\U0001F1F5\U0001F1FE"),
    ("Peru", "\U0001F1F5\U0001F1EA"),
    ("Philippines", "\U0001F1F5\U0001F1ED"),
    ("Pitcairn", "\U0001F1F5\U0001F1F3"),
    ("Poland", "\U0001F1F5\U0001F1F1"),
    ("Portugal", "\U0001F1F5\U0001F1F9"),
    ("Puerto Rico", "\U0001F1F5\U0001F1F7"),
    ("Qatar", "\U0001F1F6\U0001F1E6"),
    ("Romania", "\U0001F1F7\U0001F1F4"),
    ("Russia", "\U0001F1F7\U0001F1FA"),
    ("Rwanda", "\U0001F1F7\U0001F1FC"),
    ("Saint Kitts and Nevis", "\U0001F1F0\U0001F1F3"),
    ("Saint Lucia", "\U0001F1F1\U0001F1E8"),
    ("Saint Vincent and the Grenadines", "\U0001F1FB\U0001F1E8"),
    ("Samoa", "\U0001F1FC\U0001F1F8"),
    ("San Marino", "\U0001F1F8\U0001F1F2"),
    ("Sao Tome and Principe", "\U0001F1F8\U0001F1F9"),
    ("Saudi Arabia", "\U0001F1F8\U0001F1E6"),
    ("Senegal", "\U0001F1F8\U0001F1F3"),
    ("Serbia", "\U0001F1F7\U0001F1F8"),
    ("Seychelles", "\U0001F1F8\U0001F1E8"),
    ("Sierra Leone", "\U0001F1F8\U0001F1F1"),
    ("Singapore", "\U0001F1F8\U0001F1EC"),
    ("Slovakia", "\U0001F1F8\U0001F1F0"),
    ("Slovenia", "\U0001F1F8\U0001F1EE"),
    ("Solomon Islands", "\U0001F1F8\U0001F1E7"),
    ("Somalia", "\U0001F1F8\U0001F1F4"),
    ("South Africa", "\U0001F1FF\U0001F1E6"),
    ("South Sudan", "\U0001F1F8\U0001F1F8"),
    ("Spain", "\U0001F1EA\U0001F1F8"),
    ("Sri Lanka", "\U0001F1F1\U0001F1F0"),
    ("Sudan", "\U0001F1F8\U0001F1E9"),
    ("Suriname", "\U0001F1F8\U0001F1F7"),
    ("Sweden", "\U0001F1F8\U0001F1EA"),
    ("Switzerland", "\U0001F1E8\U0001F1ED"),
    ("Syrian Arab Republic", "\U0001F1F8\U0001F1FE"),
    ("Taiwan", "\U0001F1F9\U0001F1FC"),
    ("Tajikistan", "\U0001F1F9\U0001F1EF"),
    ("Tanzania", "\U0001F1F9\U0001F1FF"),
    ("Thailand", "\U0001F1F9\U0001F1ED"),
    ("Timor-Leste", "\U0001F1F9\U0001F1F1"),
    ("Togo", "\U0001F1F9\U0001F1EC"),
    ("Tokelau", "\U0001F1F9\U0001F1F0"),
    ("Tonga", "\U0001F1F9\U0001F1F4"),
    ("Trinidad and Tobago", "\U0001F1F9\U0001F1F9"),
    ("Tunisia", "\U0001F1F9\U0001F1F3"),
    ("Turkmenistan", "\U0001F1F9\U0001F1F2"),
    ("Tuvalu", "\U0001F1F9\U0001F1FB"),
    ("Türkiye", "\U0001F1F9\U0001F1F7"),
    ("Uganda", "\U0001F1FA\U0001F1EC"),
    ("Ukraine", "\U0001F1FA\U0001F1E6"),
    ("United Arab Emirates", "\U0001F1E6\U0001F1EA"),
    ("United Kingdom", "\U0001F1EC\U0001F1E7"),
    ("United States", "\U0001F1FA\U0001F1F8"),
    ("Uruguay", "\U0001F1FA\U0001F1FE"),
    ("Uzbekistan", "\U0001F1FA\U0001F1FF"),
    ("Vanuatu", "\U0001F1FB\U0001F1FA"),
    ("Venezuela", "\U0001F1FB\U0001F1EA"),
    ("Viet Nam", "\U0001F1FB\U0001F1F3"),
    ("Virgin Islands, British", "\U0001F1FB\U0001F1EC"),
    ("Virgin Islands, U.S.", "\U0001F1FB\U0001F1EE"),
    ("Yemen", "\U0001F1FE\U0001F1EA"),
    ("Zambia", "\U0001F1FF\U0001F1F2"),
    ("Zimbabwe", "\U0001F1FF\U0001F1FC"),
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
