#!/usr/bin/env python3
"""Template TCP/nc challenge — a line-based service on 0.0.0.0:1337.

Recreate the real service's logic from its provided source. Read the flag from FLAG
(never hard-code it). This threads one handler per connection so many players can
connect at once."""
import os, socketserver

FLAG = os.environ.get("FLAG", "NZCSC{placeholder_set_the_real_flag_in_flags.env}")


class Handler(socketserver.StreamRequestHandler):
    timeout = 60

    def handle(self):
        self.wfile.write(b"Welcome. Recreate the challenge's real prompt/logic here.\n> ")
        try:
            line = self.rfile.readline().strip()
        except Exception:
            return
        # EXAMPLE ONLY — replace with the challenge's actual logic.
        if line == b"give me the flag please":
            self.wfile.write(FLAG.encode() + b"\n")
        else:
            self.wfile.write(b"no\n")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    Server(("0.0.0.0", 1337), Handler).serve_forever()
