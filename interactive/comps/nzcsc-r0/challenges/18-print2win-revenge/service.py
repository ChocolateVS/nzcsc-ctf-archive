#!/usr/bin/env python3
"""18 - Print2Win Revenge  (nc / tcp)

Faithful self-hosted replica of the NZCSC "Print2Win Revenge" pwn challenge.

The original is a tiny C binary:

    char user_input[24] = {0};
    puts("Welcome to the simple echo program");
    for (uint8_t i = 0; i < 2; i++) {
        puts("Please enter what you want echo'ed\n> ");
        if (!fgets(user_input, sizeof(user_input), stdin)) break;
        printf("Thanks you said > ");
        printf(user_input);          // <-- format-string bug
    }
    puts("Thanks for playing!");
    exit(0);

built with PIE / Full RELRO / NX / no canary / Intel CET (SHSTK+IBT).  There is
no win() and no GOT to overwrite, so the intended path (see writeup 18.md) is a
pure format-string exploit:

  * `%12$p` / `%13$p` leak the saved rbp and a __libc_start_call_main return
    address (stack + libc leaks),
  * the loop counter is a uint8_t sitting one byte *below* user_input, so a
    `%hhn` write of 0xFF into it makes `i++` wrap 0xFF->0x00 and the `i <= 1`
    test stays true forever  -> the "2 shots" become unlimited shots,
  * with unlimited shots you perform FSOP on the real _IO_2_1_stdout_ object
    (repoint the wide-data vtable to a fake one inside the same struct, plant
    system() in its __doallocate slot, then flip stdout's own vtable from
    _IO_file_jumps to the real _IO_wfile_jumps), and the next use of stdout
    reaches system(&stdout) through a legitimate indirect *call* (CET-safe),
    with the command string spelled out in stdout's dead leading bytes.

Reproducing real glibc byte-for-byte in Python is impossible, so this replica
emulates a small printf() over a simulated stack + glibc memory model that is
self-consistent with the exact offsets used in the writeup's exploit script.
When a solver drives the documented FSOP write sequence to completion, the
service execs a real /bin/sh (the reconstructed command string) in a directory
holding flag.txt -- i.e. the player pops a genuine shell and `cat flag.txt`,
exactly as on the real challenge.

The flag is read from the FLAG environment variable and is never hard-coded.
"""
import os
import re
import struct
import socketserver
import subprocess
import tempfile
import shutil

FLAG = os.environ.get("FLAG", "NZCSC{placeholder_set_the_real_flag_in_flags.env}")

# --- simulated address space (self-consistent with writeup 18.md offsets) -----
LIBC_BASE = 0x00007F1234500000            # chosen so all addrs fit in 48 bits
STACK_RBP = 0x00007FFDEA1B2C00            # value leaked at %12$p ([rbp])

# offsets copied verbatim from the writeup's exploit script
LIBC_START_CALL_MAIN_RET_OFF = 0x2A1CA
POS12_TO_COUNTER_OFF = 0xC1
IO_2_1_STDOUT_OFF = 0x2045C0
IO_WFILE_JUMPS_OFF = 0x202228
SYSTEM_OFF = 0x58740
WIDE_DATA_OFF = 0x2037E0

RET_ADDR = LIBC_BASE + LIBC_START_CALL_MAIN_RET_OFF          # leaked at %13$p
COUNTER = STACK_RBP - POS12_TO_COUNTER_OFF                   # the uint8_t i
STDOUT = LIBC_BASE + IO_2_1_STDOUT_OFF
WFILE_JUMPS = LIBC_BASE + IO_WFILE_JUMPS_OFF
SYSTEM = LIBC_BASE + SYSTEM_OFF
WIDE_DATA = LIBC_BASE + WIDE_DATA_OFF
# stdout starts pointing at _IO_file_jumps, which shares its top 48 bits with
# _IO_wfile_jumps and differs only in the low 16 -> a single %hn flips it.
FILE_JUMPS = (WFILE_JUMPS & ~0xFFFF) | 0x1600

# one conversion specifier:  %[pos$][flags][width][length]conv
_SPEC = re.compile(rb"%(?:(\d+)\$)?([#0\- +]*)(\d+)?(hh|h|ll|l)?([diouxXpcsn%])")


class _GotShell(Exception):
    """Raised to unwind out of the request loop once a shell has been spawned."""


class Handler(socketserver.StreamRequestHandler):
    timeout = 60
    rbufsize = 0          # unbuffered read: don't steal bytes meant for the shell
    wbufsize = 0

    # ---- simulated memory -------------------------------------------------
    def mem_write(self, addr, val, size):
        for k in range(size):
            self.mem[addr + k] = (val >> (8 * k)) & 0xFF

    def mem_read_q(self, addr):
        v = 0
        for k in range(8):
            v |= self.mem.get(addr + k, 0) << (8 * k)
        return v

    def arg(self, pos, buf24):
        n = int(pos) if pos is not None else 0
        if n == 8:
            return int.from_bytes(buf24[0:8], "little")
        if n == 9:
            return int.from_bytes(buf24[8:16], "little")
        if n == 10:
            return int.from_bytes(buf24[16:24], "little")
        if n == 12:
            return STACK_RBP
        if n == 13:
            return RET_ADDR
        return 0

    # ---- a small printf() over the simulated stack ------------------------
    def do_printf(self, raw):
        # fgets stores the raw bytes; printf stops at the first NUL, but the
        # vararg slots are read from memory (buf) regardless of that NUL.
        buf24 = (raw + b"\x00" * 24)[:24]
        fmt = raw.split(b"\x00", 1)[0]

        out = bytearray()
        i = 0
        while i < len(fmt):
            if fmt[i:i + 1] != b"%":
                out += fmt[i:i + 1]
                i += 1
                continue
            m = _SPEC.match(fmt, i)
            if not m:
                out += b"%"
                i += 1
                continue
            pos, _flags, width, length, conv = m.groups()
            i = m.end()
            width = int(width) if width else 0

            if conv == b"%":
                out += b"%"
            elif conv == b"n":
                addr = self.arg(pos, buf24)
                val = len(out)
                if length == b"hh":
                    self.mem_write(addr, val & 0xFF, 1)
                elif length == b"h":
                    self.mem_write(addr, val & 0xFFFF, 2)
                elif length in (b"l", b"ll"):
                    self.mem_write(addr, val & ((1 << 64) - 1), 8)
                else:
                    self.mem_write(addr, val & 0xFFFFFFFF, 4)
            elif conv == b"p":
                val = self.arg(pos, buf24)
                out += (b"0x%x" % val) if val else b"(nil)"
            elif conv in (b"x", b"X", b"o", b"u", b"d", b"i"):
                val = self.arg(pos, buf24)
                val &= ((1 << 64) - 1) if length in (b"l", b"ll") else 0xFFFFFFFF
                s = (b"%x" % val) if conv in (b"x", b"X") else (b"%d" % val)
                if width and len(s) < width:
                    s = b" " * (width - len(s)) + s
                out += s
            elif conv == b"c":
                n = width if width else 1
                out += b" " * (n - 1) + b"A"
            elif conv == b"s":
                out += b"(str)"
        return bytes(out)

    # ---- FSOP win condition ----------------------------------------------
    def fsop_ready(self):
        wide_vtable = self.mem_read_q(WIDE_DATA + 0xE0)
        doallocate = self.mem_read_q(wide_vtable + 0x68)
        stdout_vtable = self.mem_read_q(STDOUT + 0xD8)
        return doallocate == SYSTEM and stdout_vtable == WFILE_JUMPS

    def emit(self, data):
        # every use of stdout first checks whether the FILE object has been
        # hijacked -- if so, _IO_wfile_overflow() -> __doallocate == system.
        if self.fsop_ready():
            self.spawn_shell()
            raise _GotShell()
        self.wfile.write(data)

    def spawn_shell(self):
        # system(&_IO_2_1_stdout_): the command string is stdout's leading
        # bytes up to the first NUL (what the solver wrote into _flags/padding).
        cmd = bytearray()
        a = STDOUT
        while self.mem.get(a, 0) != 0 and len(cmd) < 256:
            cmd.append(self.mem.get(a, 0))
            a += 1
        cmd = bytes(cmd)

        workdir = tempfile.mkdtemp(prefix="chal-")
        try:
            with open(os.path.join(workdir, "flag.txt"), "w") as f:
                f.write(FLAG + "\n")
            try:
                self.wfile.flush()
            except Exception:
                pass
            sock = self.connection
            if cmd:
                proc = subprocess.Popen(
                    cmd, shell=True, cwd=workdir,
                    stdin=sock, stdout=sock, stderr=sock,
                )
            else:
                proc = subprocess.Popen(
                    ["/bin/sh"], cwd=workdir,
                    stdin=sock, stdout=sock, stderr=sock,
                )
            proc.wait()
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    # ---- fgets(user_input, 24, stdin) ------------------------------------
    def fgets(self, n):
        out = bytearray()
        while len(out) < n - 1:
            b = self.rfile.read(1)
            if not b:
                return bytes(out) if out else None
            out += b
            if b == b"\n":
                break
        return bytes(out)

    # ---- main() ----------------------------------------------------------
    def handle(self):
        self.mem = {}
        self.mem_write(STDOUT + 0xD8, FILE_JUMPS, 8)     # stdout vtable
        self.mem_write(STDOUT + 0x0, 0xFBAD2887, 4)      # _flags (magic 0xfbad)
        self.mem_write(WIDE_DATA + 0xE0, WFILE_JUMPS, 8)  # _wide_vtable
        self.mem_write(COUNTER, 0, 1)                     # uint8_t i = 0

        try:
            self.emit(b"Welcome to the simple echo program\n")
            while True:
                self.emit(b"Please enter what you want echo'ed\n> \n")
                line = self.fgets(24)
                if line is None:
                    break
                self.emit(b"Thanks you said > ")
                self.emit(self.do_printf(line))
                # i++ (read back from memory: a %hhn write to COUNTER lands here)
                i = (self.mem.get(COUNTER, 0) + 1) & 0xFF
                self.mem_write(COUNTER, i, 1)
                if i > 1:
                    break
            self.emit(b"Thanks for playing!\n")
        except _GotShell:
            return
        except (BrokenPipeError, ConnectionResetError, OSError):
            return


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    Server(("0.0.0.0", 1337), Handler).serve_forever()
