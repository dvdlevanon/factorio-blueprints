"""List the in-game blueprint library (blueprint-storage-2.dat) as a tree.
Reverse-engineered format; planners (decon/upgrade) are skipped by scanning."""
import struct, sys, re

PATH = sys.argv[1] if len(sys.argv) > 1 else '/home/david/games/factorio/blueprint-storage-2.dat'
d = open(PATH, 'rb').read()
ITEM = {0x40: 'blueprint', 0x41: 'deconstruction-planner', 0x42: 'upgrade-planner', 0x43: 'blueprint-book'}

class R:
    def __init__(s, p): s.p = p
    def u8(s): v = d[s.p]; s.p += 1; return v
    def u16(s): v = struct.unpack_from('<H', d, s.p)[0]; s.p += 2; return v
    def u32(s): v = struct.unpack_from('<I', d, s.p)[0]; s.p += 4; return v
    def size(s):
        v = s.u8()
        return s.u32() if v == 0xff else v
    def str(s): n = s.size(); v = d[s.p:s.p+n].decode('utf8', 'replace'); s.p += n; return v

HDR = re.compile(rb'\x01[\x00-\x03][\x00-\xff]{2}\x00\x00[\x40-\x43]\x00', re.S)

def slot(r, depth, out):
    used = r.u8()
    if used == 0:
        return
    assert used == 1, f'bad used flag {used} at {r.p-1}'
    kind = r.u8(); gen = r.u32(); item = r.u16()
    label = r.str()
    if kind == 0:      # blueprint
        r.str()        # description
        assert r.u8() == 0  # ?
        n = r.size(); r.p += n
        out.append((depth, 'bp', label))
    elif kind == 1:    # book
        desc = r.str()
        icons = r.u8()
        assert icons == 0, f'book icons not handled at {r.p}'
        r.u8()         # ?
        cnt = r.u32()
        out.append((depth, 'book', label))
        for _ in range(cnt):
            try: slot(r, depth + 1, out)
            except Skip: pass
        r.u8(); r.u8()   # trailer (active index? + ?)
    elif kind == 2:    # deconstruction planner (layout inferred from samples)
        r.str()                      # description
        r.p += 4                     # icons/flags (all zero in samples; icons not handled)
        for _ in range(r.u8()):      # entity filter slots: empty 3 bytes, filled 4
            fid = r.u16(); r.p += 1 if fid == 0 else 2
        r.p += 2                     # trees_and_rocks_only + ?
        r.u8(); r.u8()               # tile mode bytes (02 00)
        for _ in range(r.u8()):      # tile filter slots (only empty seen: 2 bytes)
            assert r.u16() == 0, f'filled tile filter not handled at {r.p}'
        out.append((depth, 'deconstruction-planner', label))
    else:              # upgrade planner: unknown layout, skip to next slot header
        out.append((depth, ITEM.get(item, kind), label))
        m = HDR.search(d, r.p)
        r.p = m.start() if m else len(d)
        raise Skip(r.p)

class Skip(Exception): pass

# top level header: find "\x00 gen(u32) timestamp(u32) 0(u32) \x01 count(u32)" after the prototype index
i = d.find(b'nauvis') + 6
r = R(i)
while not (d[r.p] == 1 and d[r.p+1] in (0, 1, 2, 3) and d[r.p+6] in ITEM): r.p += 1
cnt = struct.unpack_from('<I', d, r.p - 4)[0]
out = []
for _ in range(cnt):
    try: slot(r, 1, out)
    except Skip: pass
print(f'# parsed to {r.p}/{len(d)} bytes, {cnt} top-level slots', file=sys.stderr)
print('blueprints')
for depth, k, label in out:
    tag = '' if k in ('bp', 'book') else f' [{k}]'
    print('  ' * depth + ('📘 ' if k == 'book' else '') + (label or '(unnamed)') + tag)
