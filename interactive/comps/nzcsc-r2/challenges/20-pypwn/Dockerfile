# Image nsjail:ubuntu-24.04 pinned by sha256
FROM ghcr.io/downunderctf/docker-vendor/nsjail@sha256:a0853d266c92078564ba7d864139c9b19a816ff81b9d10fa63e02d105e420a00

ENV JAIL_CWD=/chal
COPY flag.txt /home/ctf/chal/flag.txt
COPY main.py /home/ctf/chal/main.py
COPY start.sh /home/ctf/chal/pwn
