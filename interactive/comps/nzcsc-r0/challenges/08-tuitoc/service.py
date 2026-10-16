#!/usr/bin/env python3
"""8 - Tuitoc - a line-based TCP re-implementation of the original tuitoc.py.

The original is a menu-driven CLI that "sends bird songs" by running
`echo "TODO: implement sending a bird song to {host}"` through `subprocess.run(...,
shell=True)` in a background worker thread. The intended bug is a TOCTOU race:
`bird_song_host` is written to shared state *before* it is validated, and the worker
rebuilds its shell command from that shared value on *every* loop iteration. Start a
long, valid job, then submit a second host containing shell metacharacters - it fails
the whitelist so no new worker starts, but the poisoned value is already live and the
still-running worker executes it via shell=True.

Flag comes from the FLAG env var (never hard-coded). It is written to ./flag.txt in the
service's working directory so the writeup's `;cat flag.txt;` injection works, exactly
like the original challenge shipped flag.txt in its jail cwd.
"""
import os
import queue
import socketserver
import subprocess
import tempfile
import time
from threading import Thread

FLAG = os.environ.get("FLAG", "NZCSC{placeholder_set_the_real_flag_in_flags.env}")

ALLOWED = "abcdefghijklmnopqrstuvwxyz0123456789."


def _install_flag():
    """Materialize FLAG as ./flag.txt in a writable cwd so `cat flag.txt` works."""
    candidates = [os.getcwd(), os.path.expanduser("~"), tempfile.gettempdir()]
    for d in candidates:
        try:
            path = os.path.join(d, "flag.txt")
            with open(path, "w") as f:
                f.write(FLAG + "\n")
            os.chdir(d)
            return
        except OSError:
            continue


class Handler(socketserver.StreamRequestHandler):
    timeout = 120

    # --- line I/O helpers (mimic print()/input() over the socket) ---
    def send(self, text):
        self.wfile.write(text.encode())

    def println(self, text=""):
        self.send(text + "\n")

    def ask(self, prompt):
        """Write a prompt without a trailing newline, then read one stripped line."""
        self.send(prompt)
        line = self.rfile.readline()
        if not line:
            raise EOFError
        return line.decode(errors="replace").strip()

    # --- per-connection state (was module-global in the original) ---
    def setup(self):
        super().setup()
        self.bird_song_host = ""
        self.number_of_songs = 0
        self.bird_song_results = queue.Queue()
        self.worker = None

    def worker_bird_run(self):
        try:
            for i in range(self.number_of_songs):
                # NOTE: command is rebuilt from the shared attribute EACH iteration -
                # this is the TOCTOU sink.
                command = f'echo "TODO: implement sending a bird song to {self.bird_song_host}"'

                self.bird_song_results.put(
                    f"Sending song {i} - running command '{command}'..."
                )
                running_task = subprocess.run(
                    command, shell=True, capture_output=True, text=True, check=False
                )

                if running_task.stdout:
                    self.bird_song_results.put(running_task.stdout)
                if running_task.stderr:
                    self.bird_song_results.put(running_task.stderr)
                self.bird_song_results.put("Done!")
                time.sleep(1)
        except Exception as e:  # noqa: BLE001
            self.bird_song_results.put(str(e))

        self.bird_song_results.put("Bird song finished")

    def hatch_bird(self):
        # Shared value written BEFORE validation - and NOT reverted on the failure path.
        self.bird_song_host = self.ask(
            "Please enter the hostname of the host you want to send a bird song too (e.g. google.com) > "
        )
        for c in self.bird_song_host:
            if c not in ALLOWED:
                self.println(f"'{c}' is not allowed - naughty naughty")
                return

        try:
            self.number_of_songs = int(
                self.ask("How many times would you like to send them a bird song (1-10) > ")
            )
        except Exception as e:  # noqa: BLE001
            self.println(f"Not valid {e}")
            return

        if self.number_of_songs > 10 or self.number_of_songs < 1:
            self.println(f"{self.number_of_songs} is too high/low")
            return

        self.worker = Thread(target=self.worker_bird_run, daemon=True)
        self.worker.start()
        self.println(f"Started worker bird: {self.worker}")

    def print_bird_song_status(self):
        self.println("Getting results...")
        while True:
            try:
                result = self.bird_song_results.get(block=False)
                self.println(result.rstrip("\n"))
            except queue.Empty:
                self.println("No more bird songs results for now")
                return

    def handle(self):
        try:
            while True:
                self.println("=== MAIN MENU ===")
                self.println("1. Send a bird song to someone")
                self.println("2. Check the status of your bird songs")
                self.println("3. Quit")

                try:
                    choice = int(self.ask("> "))
                except ValueError:
                    continue

                if choice == 1:
                    self.hatch_bird()

                if choice == 2:
                    self.print_bird_song_status()
                elif choice == 3:
                    self.println("Thanks!")
                    break
        except (EOFError, ConnectionError, OSError):
            return


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    _install_flag()
    Server(("0.0.0.0", 1337), Handler).serve_forever()
