import os
import random
import secrets
from pathlib import Path

from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

HERE = Path(__file__).resolve().parent
INDEX = HERE / "templates" / "index.html"

GAMES_PER_RUN = 3
GROUPS_PER_GAME = 4
WORDS_PER_GROUP = 4


def read_flag() -> str:
    env = os.environ.get("FLAG")
    if env:
        return env.strip()
    try:
        return (HERE / "flag.txt").read_text().strip()
    except OSError:
        return "NZCSC{missing_flag}"


# 25 categories, each with its official name and word pool.
# Recovered from the live site: each game picks 4 categories and samples 4
# words from each pool; a run is 3 games, win all three in a row for the flag.
CATEGORIES = [
    ("Types of Malware", ["Adware", "Botnet", "Keylogger", "Ransomware", "Rootkit", "Spyware", "Trojan", "Worm"]),
    ("Social Engineering", ["Phishing", "Pretexting", "Quishing", "Smishing", "Vishing", "Watering Hole", "Whaling"]),
    ("Famous Vulnerabilities", ["Dirty Pipe", "EternalBlue", "Heartbleed", "Log4Shell", "POODLE", "RedSun", "Regresshion", "Shellshock", "Zerologon"]),
    ("Encryption Algorithms", ["AES", "Blowfish", "ChaCha20", "DES", "ECC", "RSA", "Serpent", "Twofish"]),
    ("Linux Distros", ["Alpine", "Arch", "Debian", "Fedora", "Gentoo", "Kali", "Mint", "Ubuntu"]),
    ("APTs/Hacking Groups", ["Anonymous", "Cozy Bear", "Equation Group", "Fancy Bear", "Lazarus", "LulzSec", "Sandworm", "Scattered Spider"]),
    ("OWASP Top 10", ["Broken Access Control", "Cryptographic Failures", "Injection", "Insecure Design", "Logging Failures", "Security Misconfiguration", "Software Supply Chain Failures", "Vulnerable Components"]),
    ("Classic Web Attacks", ["CSRF", "Clickjacking", "Deserialization", "Open Redirect", "Path Traversal", "SQLi", "XSS", "XXE"]),
    ("Databases", ["Cassandra", "MariaDB", "MongoDB", "MySQL", "Oracle DB", "PostgreSQL", "Redis", "SQLite"]),
    ("Firewall Brands", ["Check Point", "Cisco", "Fortinet", "Juniper", "Palo Alto", "SonicWall", "WatchGuard", "pfSense"]),
    ("C2 Frameworks", ["Cobalt Strike", "Covenant", "Havoc", "Merlin", "Metasploit", "Mythic", "Nighthawk", "Sliver"]),
    ("MITRE ATT&CK Tactics", ["Defense Evasion", "Discovery", "Execution", "Exfiltration", "Impact", "Lateral Movement", "Persistence", "Reconnaissance"]),
    ("SIEM Platforms", ["Elastic", "Graylog", "LogRhythm", "QRadar", "Sentinel", "Splunk", "Sumo Logic", "Wazuh"]),
    ("Auth Protocols & Standards", ["FIDO2", "Kerberos", "LDAP", "OAuth", "OpenID", "RADIUS", "SAML", "TACACS+"]),
    ("Programming Languages", ["Go", "Java", "Kotlin", "Perl", "Python", "Ruby", "Rust", "Swift"]),
    ("Assembly Instructions", ["ADD", "MOV", "POP", "PUSH", "RET", "SYSCALL", "XOR"]),
    ("Hashing Algorithms", ["Argon2", "MD5", "NTLM", "RIPEMD", "SHA-1", "SHA-256", "bcrypt"]),
    ("Security Conferences/Events", ["BSides", "Black Hat", "DEF CON", "Kawaiicon", "NZCSC", "Pwn2Own", "SANS Open-Source Intelligence Summit"]),
    ("Reverse Engineering Tools", ["Binary Ninja", "DotPeek", "GDB", "Ghidra", "ObjDump", "Strings", "WinDbg"]),
    ("EDR / Antivirus", ["Carbon Black", "CrowdStrike", "Defender", "McAfee", "SentinelOne", "Sophos", "Symantec"]),
    ("Notorious Malware", ["Conficker", "Emotet", "ILOVEYOU", "NotPetya", "Stuxnet", "Wannacry", "Zeus"]),
    ("Linux Commands", ["cat", "curl", "find", "ipconfig", "man", "wget", "whoami"]),
    ("Authentication Attack Tools", ["Aircrack-ng", "CeWL", "Hashcat", "Hydra", "John the Ripper", "Ncrack"]),
    ("Web Pentesting Tools", ["Burp Suite", "Dirbuster", "Ffuf", "Nikto", "Postman", "SQLmap"]),
    ("Physical Pentesting", ["Impersonation", "Keycard Cloning", "Lockpicking", "Nearest Neighbour Attack", "Tailgating", "USB Drop"]),
]

# In-memory per-session store (keyed by the `sid` cookie). Requires a single
# worker so the dict is shared across requests (see Dockerfile: --workers 1).
SESSIONS = {}


def build_game():
    """Pick 4 distinct categories, sample 4 words from each."""
    cats = random.sample(CATEGORIES, GROUPS_PER_GAME)
    groups = []
    for name, pool in cats:
        groups.append({"name": name, "words": random.sample(pool, WORDS_PER_GROUP)})
    return groups


def build_run():
    """A run is 3 games using 12 distinct categories (4 per game)."""
    cats = random.sample(CATEGORIES, GROUPS_PER_GAME * GAMES_PER_RUN)
    games = []
    for gi in range(GAMES_PER_RUN):
        chunk = cats[gi * GROUPS_PER_GAME:(gi + 1) * GROUPS_PER_GAME]
        groups = [{"name": n, "words": random.sample(p, WORDS_PER_GROUP)} for n, p in chunk]
        games.append(groups)
    return {"games": games, "idx": 0, "solved": []}


def current_words(run):
    """All still-unsolved words for the current game, shuffled."""
    groups = run["games"][run["idx"]]
    solved_names = {s["name"] for s in run["solved"]}
    words = []
    for g in groups:
        if g["name"] not in solved_names:
            words.extend(g["words"])
    random.shuffle(words)
    return words


def state_dict(run):
    return {
        "game": run["idx"] + 1,
        "total": GAMES_PER_RUN,
        "solved": run["solved"],
        "words": current_words(run),
    }


def get_sid():
    sid = request.cookies.get("sid")
    if not sid or sid not in SESSIONS:
        return None
    return sid


def new_run_response(payload):
    sid = secrets.token_hex(16)
    SESSIONS[sid] = build_run()
    resp = jsonify(payload(SESSIONS[sid]))
    resp.set_cookie("sid", sid, httponly=True, samesite="Strict")
    return resp


@app.route("/")
def index():
    return send_file(INDEX)


@app.route("/api/game")
def api_game():
    sid = get_sid()
    if sid is None:
        return new_run_response(state_dict)
    return jsonify(state_dict(SESSIONS[sid]))


@app.route("/api/new", methods=["POST"])
def api_new():
    return new_run_response(state_dict)


@app.route("/api/next", methods=["POST"])
def api_next():
    sid = get_sid()
    if sid is None:
        return new_run_response(state_dict)
    run = SESSIONS[sid]
    if run["idx"] < GAMES_PER_RUN - 1:
        run["idx"] += 1
        run["solved"] = []
    return jsonify(state_dict(run))


@app.route("/api/guess", methods=["POST"])
def api_guess():
    sid = get_sid()
    if sid is None:
        return new_run_response(state_dict)
    run = SESSIONS[sid]
    data = request.get_json(silent=True) or {}
    guess = data.get("words")

    groups = run["games"][run["idx"]]
    solved_names = {s["name"] for s in run["solved"]}
    board = set(current_words(run))

    # Validate: exactly 4 distinct words, all currently on the board.
    if (not isinstance(guess, list) or len(guess) != WORDS_PER_GROUP
            or len(set(guess)) != WORDS_PER_GROUP or not set(guess).issubset(board)):
        return jsonify({"error": "invalid guess"})

    guess_set = set(guess)
    for g in groups:
        if g["name"] in solved_names:
            continue
        if set(g["words"]) == guess_set:
            run["solved"].append({"name": g["name"], "words": g["words"]})
            if len(run["solved"]) < GROUPS_PER_GAME:
                return jsonify({"status": "correct", "state": state_dict(run)})
            # Game complete.
            solved = run["solved"]
            if run["idx"] >= GAMES_PER_RUN - 1:
                return jsonify({"status": "won", "flag": read_flag(), "solved": solved})
            return jsonify({"status": "game_complete", "solved": solved})

    # Valid board words but wrong grouping -> the whole run fails and resets.
    SESSIONS[sid] = build_run()
    resp = jsonify({"status": "failed"})
    resp.set_cookie("sid", sid, httponly=True, samesite="Strict")
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
