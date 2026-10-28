import os
from flask import Flask, render_template, request, abort
from hashlib import sha256
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import re
import traceback


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKS_DIR = os.path.join(BASE_DIR, "tracks")

DRM_KEY = b"6fc7b68334fd280c8a244ef439b57028"

app = Flask(__name__)

TRACKS = [
    {"id": 1, "title": "Electric Silence", "artist": "Elija K", "file": "electric_silence.mp3", "color": "#5f94b7"},
    {"id": 2, "title": "Drive Into Summer", "artist": "Pumpupthemind", "file": "drive_into_summer.mp3", "color": "#cb7033"},
    {"id": 3, "title": "One Chance in a Hundred", "artist": "Pumpupthemind", "file": "one_chance_in_a_hundred.mp3", "color": "#a873be"},
    {"id": 4, "title": "Party Anthem", "artist": "Pumpupthemind", "file": "party_anthem.mp3", "color": "#1d6e3f"},
    {"id": 5, "title": "Rise and Shine", "artist": "Roulet", "file": "rise_and_shine.mp3", "color": "#0f3460"}
]

def xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def drm(data: bytes) -> bytes:
    seed = DRM_KEY[::-1] + b":DRM"
    key = sha256(seed).digest()[:16]
    counter = bytes([0x4e, 0x5a, 0x43, 0x53, 0x43, 0x2d, 0x44, 0x52, 0x4d, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

    cipher = Cipher(algorithms.AES(key),modes.CTR(counter))

    encryptor = cipher.encryptor()
    return encryptor.update(data) + encryptor.finalize()

@app.route("/")
def index():
    return render_template("index.html", tracks=TRACKS)


@app.route("/track")
def track():
    name = request.args.get("name", "")
    if not name:
        abort(400, description="Track name required.")

    sanitised_name = name.lstrip("/")
    
    full_path = os.path.realpath(os.path.join(TRACKS_DIR, sanitised_name))
    base_dir_real = os.path.realpath(BASE_DIR)

    if not (full_path == base_dir_real or full_path.startswith(base_dir_real + os.sep)):
        trace = ''.join(traceback.format_stack(None))
        return f'''\
<html>
    <h1>Forbidden</h1>
    <p>Access is blocked outside of the app directory</p>
    <pre>{trace}</pre>
</html>
''', 403

    if not os.path.isfile(full_path):
        abort(404)

    with open(full_path, "rb") as f:
        data = f.read()

    return drm(data), 200, {"Content-Type": "application/octet-stream"}

# Legacy DRM before we switched to AES -  TODO: remove before deploy
@app.route("/track_legacy_drm")
def track_legacy_drm():
    name = request.args.get("name", "")
    if not name:
        abort(400, description="Track name required.")

    clean = re.sub(r"\.\./", "", name)
    full_path = os.path.join(TRACKS_DIR, clean)

    if not os.path.isfile(full_path):
        abort(404)

    with open(full_path, "rb") as f:
        data = f.read()
    return xor_bytes(data,DRM_KEY), 200, {"Content-Type": "application/octet-stream"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
