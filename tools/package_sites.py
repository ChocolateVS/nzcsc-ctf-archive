#!/usr/bin/env python3
# Package recovered 2024/2025 web-challenge mirrors into (a) clean self-contained
# trees for live static hosting and (b) downloadable zips to attach in CTFd.
# Decompresses any gzip'd files (Wayback saved several raw-gzip).
import os, sys, gzip, shutil, zipfile

HERE  = os.path.dirname(os.path.abspath(__file__))
M24   = os.path.join(HERE, "mirrors/mirror2024/r0.nzcsc.org.nz")
MOTH  = os.path.join(HERE, "mirrors/mirror_other/ctf.nzcsc.org.nz")
OUT   = os.path.join(HERE, "packaged")
LIVE  = os.path.join(OUT, "live")
FILES = os.path.join(OUT, "files")

def is_gzip(p):
    with open(p, "rb") as f:
        return f.read(2) == b"\x1f\x8b"

def copy_tree_decompress(src, dst, rename=None):
    """Copy src tree -> dst, gunzipping gzip'd members. rename: {relpath: newrelpath}."""
    rename = rename or {}
    for root, _, fnames in os.walk(src):
        for fn in fnames:
            sp = os.path.join(root, fn)
            rel = os.path.relpath(sp, src)
            rel = rename.get(rel, rel)
            dp = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(dp), exist_ok=True)
            if is_gzip(sp):
                with gzip.open(sp, "rb") as g, open(dp, "wb") as o:
                    o.write(g.read())
            else:
                shutil.copy2(sp, dp)

def zipdir(tree, zippath):
    os.makedirs(os.path.dirname(zippath), exist_ok=True)
    with zipfile.ZipFile(zippath, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, fnames in os.walk(tree):
            for fn in fnames:
                ap = os.path.join(root, fn)
                z.write(ap, os.path.relpath(ap, os.path.dirname(tree)))
    return zippath

if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(LIVE); os.makedirs(FILES)

# --- 2024 web challenges -> live tree + zip ---
C24 = {
    "challenge1": ("2024-c1-robots", None),
    "challenge3": ("2024-c3-traversal", {
        "index.html__file=.._.._.._.._flag.txt": "traversal_result_flag.txt",
        "index.html__file=instructions.txt": "instructions.txt",
    }),
    "challenge5": ("2024-c5-interjection", None),
    "challenge6": ("2024-c6-behind-the-scenes", None),
    "challenge8": ("2024-c8-flag-trader", None),
}
for folder, (slug, rn) in C24.items():
    src = os.path.join(M24, folder)
    live_tree = os.path.join(LIVE, "2024", folder)
    copy_tree_decompress(src, live_tree, rn)
    zipdir(live_tree, os.path.join(FILES, slug + ".zip"))

# 2024 ch4 "Hidden Flag" is a single stego text file -> attach directly
shutil.copy2(os.path.join(M24, "challenge4/ctf.txt"), os.path.join(FILES, "2024-c4-hidden-flag.txt"))

# --- 2025 web challenges ---
C25 = {
    "challenge2":  ("2025-c2-fun-facts", None),
    "challenge16": ("2025-c16-cyber-space", None),
}
for folder, (slug, rn) in C25.items():
    src = os.path.join(MOTH, folder)
    live_tree = os.path.join(LIVE, "2025", folder)
    copy_tree_decompress(src, live_tree, rn)
    zipdir(live_tree, os.path.join(FILES, slug + ".zip"))

# 2025 ch15 "Secure Login" is a single (gzip'd) php page -> decompress, attach + live
src15 = os.path.join(MOTH, "challenge15/securelogin.php")
live15 = os.path.join(LIVE, "2025", "challenge15")
os.makedirs(live15, exist_ok=True)
with gzip.open(src15, "rb") as g:
    data = g.read()
open(os.path.join(live15, "securelogin.php"), "wb").write(data)
open(os.path.join(FILES, "2025-c15-secure-login.html"), "wb").write(data)  # .html so it opens in a browser

print("=== packaged files (to attach) ===")
for fn in sorted(os.listdir(FILES)):
    print(f"  {os.path.getsize(os.path.join(FILES, fn)):>9} {fn}")
print("=== live trees ===")
for yr in sorted(os.listdir(LIVE)):
    for ch in sorted(os.listdir(os.path.join(LIVE, yr))):
        n = sum(len(f) for _,_,f in os.walk(os.path.join(LIVE, yr, ch)))
        print(f"  live/{yr}/{ch}  ({n} files)")
