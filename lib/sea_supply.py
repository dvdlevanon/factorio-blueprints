"""Sea supply line: base side (one requester per product -> its own yellow belt, leaving WEST) and
site side (belts -> one filtered storage chest per product, robots -> roboport) plus a return lane.

Every chest holds ONE slot (bar = 1) and the base requests one stack, so at most 2 stacks per product
(one per end) plus the belt are left over when the build is done. Requests are OFF by default: David
switches them on at bootstrap and off again.

Base, local frame (x east, y south), product k = 0..6 (landfill first):
  requester (k, 0), fast inserter (k, 1) picks N, belt column x=k going S from y=2, turns W at row 2+k,
  runs W to x=-1; underground in x=-2, display panel x=-3, underground out x=-4 (staircase, no crossings).
  Return lane row 9 arrives from the WEST: underground pair x=-4/-2, belt E to x=6, inserter (7,9) ->
  unfiltered storage chest (8,9).
Site: the same picture mirrored in x, flows reversed; robots go into a roboport instead of a chest.
"""
from .build import BP, N, E, S, W, trace, panels_on, tile_of

STACK = {'landfill': 100, 'solar-panel': 50, 'accumulator': 50, 'medium-electric-pole': 50,
         'big-electric-pole': 50, 'roboport': 10, 'construction-robot': 50}   # stack sizes (item data 2.1)
PRODUCTS = list(STACK)                    # belt order, top row first
ROWS = {p: 2 + k for k, p in enumerate(PRODUCTS)}
RETURN_ROW = 2 + len(PRODUCTS)            # 9
RETURN_ICON = 'storage-chest'             # panel marking the return lane


def base_block() -> BP:
    b = BP()
    for k, item in enumerate(PRODUCTS):
        b.requester(k, 0, item, STACK[item], active=False, bar=1); b.inserter(k, 1, N)
        for y in range(2, 2 + k): b.belt(k, y, S)
        for x in range(k, -2, -1): b.belt(x, 2 + k, W)
        b.ug(-2, 2 + k, W, 'input'); b.panel(-3, 2 + k, item); b.ug(-4, 2 + k, W, 'output')
    r = RETURN_ROW                                                      # return lane arrives from the WEST
    b.ug(-4, r, E, 'input'); b.panel(-3, r, RETURN_ICON); b.ug(-2, r, E, 'output')
    for x in range(-1, 7): b.belt(x, r, E)
    b.inserter(7, r, W); b.storage(8, r, bar=1)                         # unfiltered: base bots take it
    b.add('medium-electric-pole', 3, -1); b.add('medium-electric-pole', 7, 7)
    b.add('small-lamp', 2, -1); b.add('small-lamp', 4, -1)
    return b


def site_block() -> BP:
    b = BP()
    for k, item in enumerate(PRODUCTS):
        row = 2 + k
        b.ug(4, row, W, 'input'); b.panel(3, row, item); b.ug(2, row, W, 'output')
        for x in range(1, -k, -1): b.belt(x, row, W)
        for y in range(2, row + 1): b.belt(-k, y, N)                    # column up to the inserter
        b.inserter(-k, 1, S)
        if item == 'construction-robot':
            b.add('roboport', -k - 3, -3, request_filters={'sections': [{'index': 1}]})   # tiles x-3..x, rows -3..0
        else:
            b.storage(-k, 0, item, bar=1)
    r = RETURN_ROW                                                      # return lane leaves EAST
    b.storage(-8, r, bar=1); b.inserter(-7, r, W)                       # unfiltered: fish and anything else
    for x in range(-6, 2): b.belt(x, r, E)
    b.ug(2, r, E, 'input'); b.panel(3, r, RETURN_ICON); b.ug(4, r, E, 'output')
    b.add('medium-electric-pole', -3, -1); b.add('medium-electric-pole', -7, 7)
    b.add('small-lamp', -2, -1); b.add('small-lamp', -4, -1)
    b.add('big-electric-pole', 2, 0)                                    # connect your pole line here
    return b


def make_base_rules(bp):
    """Requester -> belt reaching the output marked with the requester's item; return lane -> open chest."""
    ret = return_path(bp, E)
    def rules(ins, src, dst):
        if src and src['name'] == 'transport-belt':                     # return lane end
            if tile_of(src) not in ret: return 'picks from a belt that is not the return lane'
            if not dst or dst['name'] != 'storage-chest' or 'request_filters' in dst: return 'return must go into an unfiltered storage chest'
            return None
        if not src or src['name'] != 'requester-chest': return f'picks from {src and src["name"]}'
        if not dst or dst['name'] != 'transport-belt': return f'drops on {dst and dst["name"]}'
        item = src['request_filters']['sections'][0]['filters'][0]['name']
        _, jumped = trace(bp, tile_of(dst))
        marks = panels_on(bp, jumped)
        if marks != [item]: return f'{item} reaches output marked {marks}'
    return rules


def make_site_rules(bp):
    """Belt -> chest filtered for the item marked at that belt's input (robots -> roboport); open chest -> return."""
    ins_t = {}
    for e in bp.ents:
        if e['name'] == 'underground-belt' and e['type'] == 'input' and e['direction'] == W:
            path, jumped = trace(bp, tile_of(e))
            for t in path: ins_t[t] = panels_on(bp, jumped)
    def rules(ins, src, dst):
        if src and src['name'] == 'storage-chest':                      # return lane start
            if 'request_filters' in src: return 'return must pick from an unfiltered chest'
            if not dst or dst['name'] != 'transport-belt': return 'return must drop on a belt'
            _, jumped = trace(bp, tile_of(dst))
            marks = panels_on(bp, jumped)
            return None if marks == [RETURN_ICON] else f'return belt reaches output marked {marks}'
        if not src or src['name'] != 'transport-belt': return f'picks from {src and src["name"]}'
        if not dst or dst['name'] not in ('storage-chest', 'roboport'): return f'drops into {dst and dst["name"]}'
        marks = ins_t.get(tile_of(src))
        if not marks or len(marks) != 1: return f'belt not traced from a marked input ({marks})'
        want = marks[0]
        if want == 'construction-robot':
            return None if dst['name'] == 'roboport' else 'robots must go into the roboport'
        if dst['name'] != 'storage-chest' or 'request_filters' not in dst: return 'unfiltered target'
        got = dst['request_filters']['sections'][0]['filters'][0]['name']
        if got != want: return f'belt of {want} feeds chest filtered {got}'
    return rules


def return_path(bp, d):
    """Belt tiles downstream of the underground entrance (flowing d) marked RETURN_ICON."""
    for e in bp.ents:
        if e['name'] == 'underground-belt' and e['type'] == 'input' and e['direction'] == d:
            path, jumped = trace(bp, tile_of(e))
            if panels_on(bp, jumped) == [RETURN_ICON]: return set(path)
    raise AssertionError('no return lane')
