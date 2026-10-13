#!/usr/bin/env python3
"""PyCraft — a Minecraft-in-Python TCP "nc" service on 0.0.0.0:1337.

Faithful replica of the NZCSC round-0 "15 - PyCraft" challenge. It generates a
300x300 world from Python's Mersenne-Twister PRNG, lets the player walk around and
observe blocks, then asks for the coordinates of every diamond_ore. Listing them
all correctly grants one eval()'d "admin command" that is guarded by a (subtly
broken) character-class regex.

Intended solve (see writeup):
  1. Observe 624 words worth of blocks -> recover MT19937 state -> predict every
     diamond_ore coordinate (block value <-> byte is a clean bijection over 256).
  2. Escape the eval sandbox: the regex `[\[\]+-_a-zA-Z0-9 \.]+` has a range bug
     (`+-_`), but still bans ()/quotes; the escape mutates
     __builtins__.__loader__.__class_getitem__ via for-loop assignment targets to
     get a call-without-parens gadget and reads flag.txt.

The real game runs on stdin/stdout (as the original did behind nsjail); here each
connection gets its own thread with sys.stdin/sys.stdout routed to its socket via a
thread-local proxy, and its own PRNG instance so concurrent players don't interfere.
The flag is read from the FLAG env var (never hard-coded) and written to a flag.txt
in a private working directory that the intended escape's open("flag.txt") reaches.
"""
import os
import re
import sys
import random
import threading
import tempfile
import socketserver
from time import sleep

FLAG = os.environ.get("FLAG", "NZCSC{placeholder_set_the_real_flag_in_flags.env}")

# Make the flag reachable ONLY through the intended escape (open("flag.txt")).
# Written from the env var into a private, writable CWD -- never hard-coded.
_workdir = tempfile.mkdtemp(prefix="pycraft_")
with open(os.path.join(_workdir, "flag.txt"), "w") as _f:
    _f.write(FLAG)
os.chdir(_workdir)

# --- per-connection stdio routing -------------------------------------------
# The original service used plain input()/print() (one OS process per connection
# behind nsjail). We keep that logic verbatim but route the module-level
# sys.stdin/sys.stdout through a thread-local so each connection's builtins talk
# to its own socket. print()'s stdout is thus "directly wired to the socket",
# exactly as the intended eval escape relies on.
_tls = threading.local()


class _SockOut:
    def write(self, s):
        f = getattr(_tls, "wfile", None)
        if f is None:
            return 0
        if isinstance(s, str):
            s = s.encode("utf-8", "replace")
        try:
            f.write(s)
        except OSError:
            return 0
        return len(s)

    def flush(self):
        f = getattr(_tls, "wfile", None)
        if f is not None:
            try:
                f.flush()
            except OSError:
                pass


class _SockIn:
    def readline(self, *args):
        f = getattr(_tls, "rfile", None)
        if f is None:
            return ""
        line = f.readline()
        if isinstance(line, bytes):
            line = line.decode("utf-8", "replace")
        return line

    def read(self, *args):
        return self.readline()


sys.stdout = _SockOut()
sys.stdin = _SockIn()


def _make_get_block(rng, pregen):
    def get_block():
        if not pregen:
            randu32 = rng.getrandbits(32)
            for _ in range(4):
                pregen.append(randu32 & 0xff)
                randu32 >>= 8
        return BLOCKS[pregen.pop()]
    return get_block


def play():
    # Each connection gets its own PRNG (auto-seeded from os.urandom, like the
    # original per-process module RNG) and its own pregen buffer.
    rng = random.Random()
    pregen = []
    get_block = _make_get_block(rng, pregen)

    # 300x300 grid
    DIM = 300
    world = [['' for _ in range(DIM)] for _ in range(DIM)]

    print('[+] Generating world')
    sleep(1)
    for x in range(DIM):
        print(f' - ({x+1} / {DIM})')
        sleep(0.01)
        for y in range(DIM):
            world[x][y] = get_block()

    print('[+] Rendering world')
    sleep(1)

    print('[+] Use wasd to walk around and look at blocks')
    x = rng.randint(0, DIM-1)
    y = rng.randint(0, DIM-1)
    print(f'[+] Spawning in at {x},{y}')

    directions = input('Enter your movements> ')
    if len(directions) > 3000:
        print('[-] You walked too fair and ran out of hunger')
        return

    found_blocks = []
    for dir in directions:
        if dir == 'a':
            x -= 1
        elif dir == 'd':
            x += 1
        elif dir == 'w':
            y += 1
        elif dir == 's':
            y -= 1
        else:
            print('[-] Bad command')
            return
        if max(x, y) >= DIM or min(x, y) < 0:
            print('[-] You died on the world border')
            return
        found_blocks.append(world[x][y])
    print(f'[+] Here is what you saw: {",".join(found_blocks)}')

    num_diamonds = sum(x == 'diamond_ore' for row in world for x in row)
    print(f'[+] There are {num_diamonds} diamond ore in the world, can you list there coordinates?')

    coordinates_str = input('Enter coordinates eg: 1,2 3,4 4,5 > ')
    coordinates = set()
    try:
        for cord_str in coordinates_str.strip().split(' '):
            x, y = cord_str.split(',')
            coordinates.add((int(x), int(y)))
    except:
        print('[-] Error parsing coordinates')
        return

    if len(coordinates) > num_diamonds:
        print('[-] No cheating!')
        return

    num_found_diamonds = 0
    for x, y in coordinates:
        try:
            if world[x][y] == 'diamond_ore':
                num_found_diamonds += 1
        except:
            pass

    print(f'[+] You found {num_found_diamonds} diamonds')

    if num_found_diamonds == num_diamonds:
        print('[+] Wow nice work! Since you found all the diamonds you get one free server admin command')
        command = input('Command >')
        if not re.fullmatch(r'[\[\]+-_a-zA-Z0-9 \.]+', command):
            print('[-] Whoa thats a dangerous command')
            return
        eval(command, {}, {})


BLOCKS = [
    'air',
    'stone',
    'grass',
    'dirt',
    'cobblestone',
    'planks',
    'sapling',
    'bedrock',
    'flowing_water',
    'water',
    'flowing_lava',
    'lava',
    'sand',
    'gravel',
    'gold_ore',
    'iron_ore',
    'coal_ore',
    'log',
    'leaves',
    'sponge',
    'glass',
    'lapis_ore',
    'lapis_block',
    'dispenser',
    'sandstone',
    'noteblock',
    'bed',
    'golden_rail',
    'detector_rail',
    'sticky_piston',
    'web',
    'tallgrass',
    'deadbush',
    'piston',
    'pistonArmCollision',
    'wool',
    'element_0',
    'yellow_flower',
    'red_flower',
    'brown_mushroom',
    'red_mushroom',
    'gold_block',
    'iron_block',
    'double_stone_slab',
    'stone_slab',
    'brick_block',
    'tnt',
    'bookshelf',
    'mossy_cobblestone',
    'obsidian',
    'torch',
    'fire',
    'mob_spawner',
    'oak_stairs',
    'chest',
    'redstone_wire',
    'diamond_ore',
    'diamond_block',
    'crafting_table',
    'wheat',
    'farmland',
    'furnace',
    'lit_furnace',
    'standing_sign',
    'wooden_door',
    'ladder',
    'rail',
    'stone_stairs',
    'wall_sign',
    'lever',
    'stone_pressure_plate',
    'iron_door',
    'wooden_pressure_plate',
    'redstone_ore',
    'lit_redstone_ore',
    'unlit_redstone_torch',
    'redstone_torch',
    'stone_button',
    'snow_layer',
    'ice',
    'snow',
    'cactus',
    'clay',
    'reeds',
    'jukebox',
    'fence',
    'pumpkin',
    'netherrack',
    'soul_sand',
    'glowstone',
    'portal',
    'lit_pumpkin',
    'cake',
    'unpowered_repeater',
    'powered_repeater',
    'invisibleBedrock',
    'trapdoor',
    'monster_egg',
    'stonebrick',
    'brown_mushroom_block',
    'red_mushroom_block',
    'iron_bars',
    'glass_pane',
    'melon_block',
    'pumpkin_stem',
    'melon_stem',
    'vine',
    'fence_gate',
    'brick_stairs',
    'stone_brick_stairs',
    'mycelium',
    'waterlily',
    'nether_brick',
    'nether_brick_fence',
    'nether_brick_stairs',
    'nether_wart',
    'enchanting_table',
    'brewing_stand',
    'cauldron',
    'end_portal',
    'end_portal_frame',
    'end_stone',
    'dragon_egg',
    'redstone_lamp',
    'lit_redstone_lamp',
    'dropper',
    'activator_rail',
    'cocoa',
    'sandstone_stairs',
    'emerald_ore',
    'ender_chest',
    'tripwire_hook',
    'tripWire',
    'emerald_block',
    'spruce_stairs',
    'birch_stairs',
    'jungle_stairs',
    'command_block',
    'beacon',
    'cobblestone_wall',
    'flower_pot',
    'carrots',
    'potatoes',
    'wooden_button',
    'skull',
    'anvil',
    'trapped_chest',
    'light_weighted_pressure_plate',
    'heavy_weighted_pressure_plate',
    'unpowered_comparator',
    'powered_comparator',
    'daylight_detector',
    'redstone_block',
    'quartz_ore',
    'hopper',
    'quartz_block',
    'quartz_stairs',
    'double_wooden_slab',
    'wooden_slab',
    'stained_hardened_clay',
    'stained_glass_pane',
    'leaves2',
    'log2',
    'acacia_stairs',
    'dark_oak_stairs',
    'slime',
    'iron_trapdoor',
    'prismarine',
    'seaLantern',
    'hay_block',
    'carpet',
    'hardened_clay',
    'coal_block',
    'packed_ice',
    'double_plant',
    'standing_banner',
    'wall_banner',
    'daylight_detector_inverted',
    'red_sandstone',
    'red_sandstone_stairs',
    'double_stone_slab2',
    'stone_slab2',
    'spruce_fence_gate',
    'birch_fence_gate',
    'jungle_fence_gate',
    'dark_oak_fence_gate',
    'acacia_fence_gate',
    'repeating_command_block',
    'chain_command_block',
    'hard_glass_pane',
    'hard_stained_glass_pane',
    'chemical_heat',
    'spruce_door',
    'birch_door',
    'jungle_door',
    'acacia_door',
    'dark_oak_door',
    'grass_path',
    'frame',
    'chorus_flower',
    'purpur_block',
    'colored_torch_rg',
    'purpur_stairs',
    'colored_torch_bp',
    'undyed_shulker_box',
    'end_bricks',
    'frosted_ice',
    'end_rod',
    'end_gateway',
    'allow',
    'deny',
    'border_block',
    'magma',
    'nether_wart_block',
    'red_nether_brick',
    'bone_block',
    'structure_void',
    'shulker_box',
    'purple_glazed_terracotta',
    'white_glazed_terracotta',
    'orange_glazed_terracotta',
    'magenta_glazed_terracotta',
    'light_blue_glazed_terracotta',
    'yellow_glazed_terracotta',
    'lime_glazed_terracotta',
    'pink_glazed_terracotta',
    'gray_glazed_terracotta',
    'silver_glazed_terracotta',
    'cyan_glazed_terracotta',
    'blue_glazed_terracotta',
    'brown_glazed_terracotta',
    'green_glazed_terracotta',
    'red_glazed_terracotta',
    'black_glazed_terracotta',
    'concrete',
    'concretePowder',
    'chemistry_table',
    'underwater_torch',
    'chorus_plant',
    'stained_glass',
    'camera',
    'podzol',
    'beetroot',
    'stonecutter',
    'glowingobsidian',
    'netherreactor',
    'info_update',
    'info_update2',
    'movingBlock',
    'observer',
    'structure_block',
    'hard_glass',
    'hard_stained_glass',
    'reserved6',
    'prismarine_stairs',
    'dark_prismarine_stairs',
]


class Handler(socketserver.StreamRequestHandler):
    timeout = 300

    def handle(self):
        _tls.wfile = self.wfile
        _tls.rfile = self.rfile
        try:
            play()
        except (EOFError, ConnectionError, OSError):
            pass
        finally:
            try:
                self.wfile.flush()
            except OSError:
                pass
            _tls.wfile = None
            _tls.rfile = None


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    Server(("0.0.0.0", 1337), Handler).serve_forever()
