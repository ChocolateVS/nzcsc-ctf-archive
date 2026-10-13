#!/usr/bin/env python3
"""Print2Win -- faithful re-implementation of the print2win format-string challenge.

The original (print2win.tar / main.c) is a small x86-64 PIE C program with a classic
uncontrolled-format-string bug:  printf(user_input).  It exposes FIVE flags of
increasing difficulty.  Because a byte-for-byte C binary cannot be shipped in this
Python-only service, this file re-implements the *same observable behaviour* on top of
a tiny printf/stack emulator: the emulated stack, the argument positions reachable via
`%k$`, the `%n` write primitive and the GOT/return-address it can corrupt all mirror
the real binary's layout (verified against the provided ELF), so each of the five
flags is reached with the same technique a solver would use against the real ./main:

  flag1  --  leak a rodata pointer with `%8$s`  (const char *flag1 sits on the stack)
  flag2  --  `%9$n` (a live `int *flag2_locked` pointer -> writes g_flag2_locked != 0)
  flag3  --  controlled write of the exact value 1337 into the local `flag3_locked`
             int (put its address in the buffer, then `%1337c%<k>$hn`)
  flag4  --  overwrite a code pointer (a GOT entry, or the saved return address) with
             the address of the never-called print_flag_4()  -> it "runs"
  flag5  --  overwrite printf's GOT entry with libc `system`, then the echoed line
             becomes system(line) -> a shell -> read flag5-<rand>.txt

Real ASLR is emulated: the image / libc / stack bases are randomised per connection,
so the addresses must be leaked before they can be used (exactly like the real jail).

Flags come from the environment (FLAG is the primary == flag3); FLAG1..FLAG5 supply
the others.  Sensible defaults are used only if an env var is unset.
"""

import os
import random
import socketserver

# ---------------------------------------------------------------------------
# Flags (all sourced from the environment; FLAG is the primary == flag3)
# ---------------------------------------------------------------------------
FLAG1 = os.environ.get("FLAG1", "NZCSC{flag1-3fb7cbb41539}")
FLAG2 = os.environ.get("FLAG2", "NZCSC{flag2-8737947046f5}")
FLAG3 = os.environ.get("FLAG") or os.environ.get("FLAG3") \
    or "NZCSC{flag3-more-controlled-overwrite-4c22c715}"
FLAG4 = os.environ.get("FLAG4", "NZCSC{flag4-wow-how-did-you-call-this-function-91ca535f}")
FLAG5 = os.environ.get("FLAG5", "NZCSC{flag5-great-work-getting-a-shell-c3eec16d}")

# Randomised per-process file name for flag5, like the real Dockerfile
FLAG5_FILE = "flag5-%s.txt" % os.urandom(4).hex()

# ---------------------------------------------------------------------------
# Fixed offsets taken from the provided binary / libc (print2win.tar)
# ---------------------------------------------------------------------------
OFF_PRINT_FLAG_4 = 0x1229     # print_flag_4()  (never called by main)
OFF_FLAG1_RODATA = 0x2103     # const char *flag1 string literal
OFF_G_FLAG2_LOCK = 0x404c     # g_flag2_locked (global int)
OFF_GOT_PUTS     = 0x3f98     # puts@got.plt
OFF_GOT_PRINTF   = 0x3fb0     # printf@got.plt
OFF_GOT_FGETS    = 0x3fb8     # fgets@got.plt
LIBC_OFF_SYSTEM  = 0x58740    # system
LIBC_OFF_RET     = 0x2a1ca    # ~ __libc_start_call_main (main's saved return addr)
LIBC_OFF_BINSH   = 0x1cb42f   # "/bin/sh"


class Memory:
    """Byte-addressable little-endian emulated memory (sparse)."""

    def __init__(self):
        self.b = {}

    def wbytes(self, addr, data):
        for i, c in enumerate(data):
            self.b[addr + i] = c & 0xFF

    def rbytes(self, addr, n):
        return bytes(self.b.get(addr + i, 0) for i in range(n))

    def w(self, addr, val, size=8):
        for i in range(size):
            self.b[addr + i] = (val >> (8 * i)) & 0xFF

    def r(self, addr, size=8):
        v = 0
        for i in range(size):
            v |= self.b.get(addr + i, 0) << (8 * i)
        return v

    def cstr(self, addr, limit=4096):
        out = bytearray()
        for i in range(limit):
            c = self.b.get(addr + i)
            if not c:                     # None (unmapped) or 0 terminator
                break
            out.append(c)
        return bytes(out)


class Process:
    """One emulated print2win process (fresh per connection)."""

    def __init__(self):
        self.mem = Memory()
        r = random.randrange

        # Randomised bases (emulated ASLR); page aligned.
        self.image_base = 0x555555554000 + (r(0, 0x8000) << 12)
        self.libc_base  = 0x7ffff7c00000 + (r(0, 0x8000) << 12)
        self.rbp        = 0x7ffffffde000 + (r(0, 0x2000) << 12)

        m = self.mem
        ib, lb, rbp = self.image_base, self.libc_base, self.rbp

        # Resolved absolute addresses of interest
        self.flag1_addr    = ib + OFF_FLAG1_RODATA
        self.g_flag2_addr   = ib + OFF_G_FLAG2_LOCK
        self.print_flag4    = ib + OFF_PRINT_FLAG_4
        self.got_puts       = ib + OFF_GOT_PUTS
        self.got_printf     = ib + OFF_GOT_PRINTF
        self.got_fgets      = ib + OFF_GOT_FGETS
        self.system_addr    = lb + LIBC_OFF_SYSTEM
        self.ret_into_libc  = lb + LIBC_OFF_RET

        # ---- main()'s stack frame (rbp-relative), matching the real binary ----
        self.buf_addr        = rbp - 0x20          # char user_input[24]
        self.flag3_locked    = rbp - 0x34          # int  flag3_locked = 0
        self.flag1_slot      = rbp - 0x30          # const char *flag1
        self.flag2ptr_slot   = rbp - 0x28          # int *flag2_locked = &g_flag2_locked
        self.canary_addr     = rbp - 0x08          # stack canary
        self.savedrbp_addr   = rbp                 # saved rbp
        self.ret_slot        = rbp + 0x08          # saved return address

        m.w(self.flag1_slot, self.flag1_addr)
        m.wbytes(self.flag1_addr, FLAG1.encode() + b"\x00")
        m.w(self.flag2ptr_slot, self.g_flag2_addr)
        m.w(self.g_flag2_addr, 0, 4)
        m.w(self.flag3_locked, 0, 4)
        m.w(self.canary_addr, (r(0, 1 << 56) << 8))            # low byte 0x00
        m.w(self.savedrbp_addr, rbp + 0x120)
        m.w(self.ret_slot, self.ret_into_libc)

        # GOT starts pointing at real (libc-resolved) code
        m.w(self.got_puts,   lb + 0x875a0)
        m.w(self.got_printf, lb + 0x606f0)
        m.w(self.got_fgets,  lb + 0x7c6e0)

        # A few "leftover" register values for %1$..%5$ (harmless scratch backing)
        self.reg_base = 0x1000
        regs = [0x18, self.ret_into_libc, 0, self.buf_addr, 0]
        for i, v in enumerate(regs):
            m.w(self.reg_base + i * 8, v)

        self.flag4_shown = False
        self.shell_mode = False

    # -- argument fetch for %k$ ------------------------------------------------
    def arg_addr(self, idx):
        """Address of the storage backing conversion argument `idx` (1-based)."""
        if 1 <= idx <= 5:
            return self.reg_base + (idx - 1) * 8
        # idx >= 6 : stack, starting at rsp = rbp-0x40
        return (self.rbp - 0x40) + (idx - 6) * 8

    def arg_val(self, idx):
        return self.mem.r(self.arg_addr(idx), 8)


class Printf:
    """Minimal but faithful glibc-style printf: positional args, width, %n writes."""

    CONV = set("diouxXeEfFgGaAcspn%")

    def __init__(self, proc):
        self.p = proc

    def format(self, fmt: bytes) -> bytes:
        out = bytearray()
        auto = 1                       # next non-positional arg index
        i, n = 0, len(fmt)
        while i < n:
            c = fmt[i]
            if c != 0x25:              # '%'
                out.append(c)
                i += 1
                continue
            j = i + 1
            if j >= n:
                out.append(c)
                break

            # positional  %k$
            argnum = None
            k = j
            num = 0
            while k < n and 0x30 <= fmt[k] <= 0x39:
                num = num * 10 + (fmt[k] - 0x30)
                k += 1
            if k < n and fmt[k] == 0x24 and k > j:   # '$'
                argnum = num
                j = k + 1

            # flags
            while j < n and fmt[j] in b"-+ #0":
                j += 1
            # width (decimal or '*')
            width = 0
            has_width = False
            if j < n and fmt[j] == 0x2A:             # '*'
                idx = argnum if argnum is not None else auto
                if argnum is None:
                    auto += 1
                width = self.p.arg_val(idx) & 0xFFFFFFFF
                has_width = True
                j += 1
            else:
                w = 0
                start = j
                while j < n and 0x30 <= fmt[j] <= 0x39:
                    w = w * 10 + (fmt[j] - 0x30)
                    j += 1
                if j > start:
                    width, has_width = w, True
            # precision
            precision = None
            if j < n and fmt[j] == 0x2E:             # '.'
                j += 1
                pr = 0
                while j < n and 0x30 <= fmt[j] <= 0x39:
                    pr = pr * 10 + (fmt[j] - 0x30)
                    j += 1
                precision = pr
            # length modifier
            length = ""
            while j < n and fmt[j] in b"hljztLq":
                length += chr(fmt[j])
                j += 1
            if j >= n:
                out.append(c)
                break
            conv = chr(fmt[j])
            j += 1

            if conv == "%":
                out.append(0x25)
                i = j
                continue
            if conv not in self.CONV:
                # unknown: emit verbatim, mirror lenient behaviour
                out.extend(fmt[i:j])
                i = j
                continue

            # resolve which argument this conversion consumes
            if argnum is not None:
                idx = argnum
            else:
                idx = auto
                auto += 1

            piece = self._render(conv, length, idx, len(out), precision)
            if piece is not None:
                if has_width and len(piece) < width:
                    piece = (b" " * (width - len(piece))) + piece
                out.extend(piece)
            elif has_width and conv != "n":
                out.extend(b" " * width)  # padding-only edge
            i = j
        return bytes(out)

    def _render(self, conv, length, idx, produced, precision):
        p = self.p
        if conv == "n":
            addr = p.arg_val(idx)
            size = 4
            if length == "hh":
                size = 1
            elif length == "h":
                size = 2
            elif length in ("l", "ll", "q", "z", "t"):
                size = 8
            p.mem.w(addr, produced & ((1 << (8 * size)) - 1), size)
            return b""
        if conv == "s":
            addr = p.arg_val(idx)
            s = p.mem.cstr(addr)
            if precision is not None:
                s = s[:precision]
            return s
        if conv == "c":
            return bytes([p.arg_val(idx) & 0xFF])
        if conv == "p":
            v = p.arg_val(idx)
            return b"0x%x" % v if v else b"(nil)"
        if conv in ("x", "X"):
            v = p.arg_val(idx) & 0xFFFFFFFF
            if length in ("l", "ll", "q"):
                v = p.arg_val(idx)
            s = (b"%x" % v) if conv == "x" else (b"%X" % v)
            return s
        if conv in ("d", "i"):
            v = p.arg_val(idx) & 0xFFFFFFFF
            if length in ("l", "ll", "q"):
                v = p.arg_val(idx) & 0xFFFFFFFFFFFFFFFF
            if v >= (1 << 31) and length not in ("l", "ll", "q"):
                v -= 1 << 32
            return b"%d" % v
        if conv in ("u", "o"):
            v = p.arg_val(idx) & 0xFFFFFFFF
            return (b"%o" % v) if conv == "o" else (b"%u" % v)
        if conv in "eEfFgGaA":
            return b"0.000000"       # float args not modelled; harmless placeholder
        return b""


class Handler(socketserver.StreamRequestHandler):
    timeout = 120

    # ---- fgets(user_input, 24, stdin): up to 23 bytes, stop after newline -----
    def fgets(self):
        data = bytearray()
        while len(data) < 23:
            ch = self.rfile.read(1)
            if not ch:
                return None if not data else bytes(data)
            data += ch
            if ch == b"\n":
                break
        return bytes(data)

    def out(self, s):
        if isinstance(s, str):
            s = s.encode()
        try:
            self.wfile.write(s)
            self.wfile.flush()
        except Exception:
            pass

    # ---- helpers mirroring the C win-functions --------------------------------
    def might_print_flag_2(self, proc):
        if proc.mem.r(proc.g_flag2_addr, 4) != 0:
            self.out("Idk how you got here but here is your flag\n")
            self.out(FLAG2 + "\n")

    def might_print_flag_3(self, proc):
        v = proc.mem.r(proc.flag3_locked, 4)
        if v == 0:
            return
        if v != 1337:
            self.out("Close - nice try %d\n" % (v if v < (1 << 31) else v - (1 << 32)))
            return
        self.out("I don't know how you got here, but here is your flag...\n")
        self.out(FLAG3 + "\n")

    def print_flag_4(self, proc):
        if proc.flag4_shown:
            return
        proc.flag4_shown = True
        self.out("I really don't know how you got here, but here is your flag...\n")
        self.out(FLAG4 + "\n")

    def check_hijack(self, proc):
        """After each echo, inspect corrupted code pointers (GOT / return addr)."""
        pf4 = proc.print_flag4
        got_p = proc.mem.r(proc.got_printf)
        got_u = proc.mem.r(proc.got_puts)
        got_f = proc.mem.r(proc.got_fgets)
        ret = proc.mem.r(proc.ret_slot)

        if pf4 in (got_p, got_u, got_f, ret):
            self.print_flag_4(proc)          # print_flag_4() got called
        if not proc.shell_mode and proc.system_addr in (got_p, got_u, got_f):
            proc.shell_mode = True           # printf/puts is now system()
            self.out("$ ")

    # ---- fake shell reached once system() is wired up (flag5) -----------------
    def fake_shell(self, line):
        cmd = line.strip()
        if cmd in (b"ls", b"ls -la", b"dir"):
            self.out(FLAG5_FILE + "\nflag3.txt\nflag4.txt\npwn\n")
        elif cmd in (b"id", b"whoami"):
            self.out("uid=1000(ctf) gid=1000(ctf) groups=1000(ctf)\n")
        elif cmd.startswith(b"cat"):
            arg = cmd[3:].strip()
            if b"flag5" in arg or arg in (b"*", b"flag5*", b"*.txt"):
                self.out(FLAG5 + "\n")
            elif b"flag3" in arg:
                self.out(FLAG3 + "\n")
            elif b"flag4" in arg:
                self.out(FLAG4 + "\n")
            else:
                self.out("cat: %s: No such file or directory\n" % arg.decode("latin1"))
        elif cmd in (b"sh", b"/bin/sh", b"bash", b"/bin/bash", b""):
            pass  # already in a shell
        else:
            self.out("sh: %s: command not found\n" % cmd.split(b" ")[0].decode("latin1"))
        self.out("$ ")

    # ---- main loop (mirrors main() in main.c) ---------------------------------
    def handle(self):
        proc = Process()
        pf = Printf(proc)

        self.out("Welcome to the simple echo program\n"
                 "Please enter what you want echo'ed\n>\n")

        while True:
            line = self.fgets()
            if line is None:                 # fgets() -> NULL (EOF): main returns
                break

            if proc.shell_mode:
                self.fake_shell(line)
                continue

            # store the buffer contents (zero-filled 24 bytes), null-terminated
            buf = line[:23]
            proc.mem.wbytes(proc.buf_addr, b"\x00" * 24)
            proc.mem.wbytes(proc.buf_addr, buf + b"\x00")

            cstr = buf.split(b"\x00", 1)[0]  # printf reads up to the first NUL

            self.out("Thanks you said >")
            self.out(pf.format(cstr))        # <-- the vulnerable printf(user_input)

            self.might_print_flag_2(proc)
            self.might_print_flag_3(proc)
            self.check_hijack(proc)

            if proc.shell_mode:
                continue
            if buf[:1] == b"\n":
                self.out("Thanks for playing!\n")
                break
            self.out("Would you like to echo anything else >\n")

        # program is returning: a hijacked saved return address runs print_flag_4
        if proc.mem.r(proc.ret_slot) == proc.print_flag4:
            self.print_flag_4(proc)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    Server(("0.0.0.0", 1337), Handler).serve_forever()
