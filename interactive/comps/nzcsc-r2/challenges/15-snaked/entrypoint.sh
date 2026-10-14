#!/bin/sh
# flag is injected by the challenge host (FLAG env from catalog.json)
if [ -z "$FLAG" ]; then FLAG="NZCSC{placeholder_flag}"; fi
printf '%s\n' "$FLAG" > /flag.txt
chmod 644 /flag.txt
exec /usr/sbin/sshd -D -e
