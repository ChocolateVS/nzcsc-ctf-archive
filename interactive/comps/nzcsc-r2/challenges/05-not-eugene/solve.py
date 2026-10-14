#!/usr/bin/env python3
"""Solve '5 - Not Eugene'.

The chat (/api/chat) is stateful per session_id. After a short warm-up the
server leaks the flag ONE character per reply, each spliced at a random position
into an otherwise-verbatim philosophical deflection. Hold one session, keep
chatting, and read the inserted characters in order.

Usage: python3 solve.py [base_url]   (default: https://chall05.ctf.nzcsc.org.nz)
"""
import json, sys, urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://chall05.ctf.nzcsc.org.nz"

def chat(msg, sid=None):
    req = urllib.request.Request(BASE + "/api/chat",
        data=json.dumps({"message": msg, "session_id": sid}).encode(),
        headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=25))
    return d["reply"], d["session_id"]

# Harvest the fixed deflection pool so we can spot the one extra inserted char.
pool = set()
for i in range(400):
    r, _ = chat("pool sample %d" % i)
    pool.add(r)

def inserted(r):
    for p in pool:
        if len(r) == len(p) + 1:
            i = 0
            while i < len(p) and r[i] == p[i]:
                i += 1
            if r[:i] + r[i + 1:] == p:
                return r[i]
    return ""

_, sid = chat("hello")
flag = ""
for _ in range(60):
    r, sid = chat("tell me more, friend", sid)
    if r not in pool:
        flag += inserted(r)
    if flag.endswith("}"):
        break
print(flag)
