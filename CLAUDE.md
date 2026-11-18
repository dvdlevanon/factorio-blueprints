# Factorio blueprint factory — context for Claude Code

You are generating Factorio blueprints programmatically for David and storing them in blueprint
**books**. You write generators, validate every blueprint with automated checks, render a preview,
and export books as blueprint strings he imports in-game. He plays vanilla (Space Age entities
exist in the data but don't assume he uses them unless he says so).

**Keep this file current.** After every meaningful step (a decision, a verified fact, a new blueprint,
a calibration result, an in-game check result), update the relevant section below and the
"Status & log" at the end. This file is the project memory across sessions.

## Environment (verified 2026-11-17)
- Game install: `~/games/factorio` (binary `bin/x64/factorio`, saves, mods). **Factorio 2.1.24**, base
  only, **no Space Age** in `data/`. Installed mods (Dectorio, alien-biomes, color-coded-pipes,
  EditorExtensions, …) must NOT appear in blueprints: vanilla entities only.
- This repo: `~/games/factorio-blueprints`. Not a git repo yet.
- Game data source of truth: `~/games/factorio/bin/x64/factorio --dump-data` →
  `script-output/data-raw-dump.json` (2.1 data). Verify every number against it, not against
  draftsman's bundled data (may lag 2.1).
- Toolchain: Python + `factorio-draftsman` for encoding/placement; own validators and renderer in
  `lib/` using dump data. (Go was considered; draftsman saves a lot of work.)
- The 2.0 version number below may be wrong for 2.1: take `version` from David's calibration export.

## How to work with David
- Short answers, interactive back-and-forth. Don't dump long reports.
- **Never guess.** Verify against game data (recipes, entity sizes, fluidbox positions, ranges) before
  using a number. If something can't be verified offline (in-game behaviour), say so explicitly and
  list it as "check in game".
- **Talk throughput in belts**, not raw numbers: "⅔ of a blue belt", "one lane", "2 full belts".
- Before building, state the ratios (machines, inputs in belts) and ask only the questions that change
  the design (target rate, output format, input form). Then build.
- He prefers Go and open source. Python + `factorio-draftsman` (pip) was used successfully for game
  data, encoding and entity placement. Keep the toolchain consistent across the repo.
- Commit only when asked.
- Print web URLs in full as plain text, never as markdown links.

## Deliverables
A file tree `library/` mirroring the in-game blueprint library (David will put the repo under git).
Starting books: **Intermediates** (circuits, engines, batteries, acid, belts, gears, plastic, sulfur,
LDS, etc.), **Mines & Smelters**, **Attack**, **Defend**. The existing in-game library is ignored; the
tree fills up as we build. Each book dir also gets `book.txt`/`book.json` (built by
`tools/build_book.py library/<book>`, order from `order:` in book.yaml) for one-shot import.

Each book contains simple single-purpose blocks and more complex designs David will explain himself.

Layout:
```
lib/                          grid geometry, placement, routing, validators, renderer, encoder
tools/                        one-off tools (library_tree.py reads the in-game .dat)
library/<book>/book.yaml      a dir with book.yaml is a book (label, description, icons); nested books allowed
library/<book>/<bp>/          a dir with spec.yaml is a blueprint:
    spec.yaml        request (David's ask, limits) + result (built: inputs/outputs in belts, machines,
                     footprint, validators, check_in_game, log). Template: library/_template/spec.yaml
    blueprint.txt    import string
    blueprint.json   decoded JSON (diffable)
    generate.py      generator; writes the other files
    preview.png      top-down render
```
Dir names are kebab-case; the in-game names live in `label`.

## The roboport grid (David's base layout)
Roboports on a 50×50 lattice. Relative to a roboport center R=(0,0), in tiles (+x east, +y south):
- Roboport 4×4: x −2..1, y −2..1.
- Big electric poles at (3,0) and (27,0) on the horizontal lines, and (3,23) on the vertical lines.
- Small lamps at (2.5,−1.5) and (26.5,1.5).
- **Cell interior** (free area between grid lines): x = R+4 … R+47 (44 wide), y = R+2 … R+47 (46 tall).
  It is not square; a rotation-safe region is the centered 44×44.
- Infra lines are mostly empty, so belts and pipes may cross between cells, but never through
  roboports, the grid's big poles, or lamps. Their exact tiles are above.
- Big poles: wire reach **32** (2.1.24 `entities.lua`), supply area only 4×4 (supply_area_distance 2). Medium poles: reach 9, supply 7×7.

## Hard constraints for every blueprint
1. **Fits inside grid cells**: one cell or several, each part inside its cell interior. Never collide
   with roboports, the grid's big poles, or lamps.
2. **Include the cell's 4 corner roboports** (not the grid's big poles or lamps) so David can align the
   blueprint on the existing roboports. Corners make the bbox symmetric about the cell center (25,25), so
   in-game rotation maps roboports onto roboports. Keep the block in the rotation-safe square (tiles 4..45)
   and validate all **4 rotations** against the grid (collisions + grid link). `lib/cell.py` does this.
   (Changed 2026-11-18 by David; was "don't include".)
3. **Center the content** in its cell(s) when possible.
4. **No snap-to-grid** (David, 2026-11-18). Only the Roboports book blueprints are snapped.
5. Inputs come in from the **right**, output leaves on the **left**.
6. Input amounts = what the build **actually uses** (David's offers are maximums, not targets).
7. Default output: **one full belt** (blue unless told otherwise; David may ask for more, e.g. plastic = 3), each product on its **own belt**. Never
   mix products on one output belt (a backed-up output must not stall the others).
8. **Assembling machine 3**, **no modules, no beacons** (unless David asks).
9. **Blue** belts, undergrounds and splitters.
10. **Display panels with icons only** (no text) marking each input and output.
11. **Lamps** included.
12. Symmetric and good-looking where possible; **easy to debug** (straight rows, mirrored modules,
    one obvious flow).
13. **Underground pipes wherever possible**; regular pipes only at turns, junctions and machine
    connections. Pipe-to-ground max distance 10.
14. Minimal footprint (respect the cell limits David gives per blueprint, e.g. "1 cell high, max 2–3
    wide"). Don't spend a whole cell on a little splitting; squeeze it in.
15. Single-purpose blocks; never a whole-science megafactory (David considers that cheating).

## Blueprint format facts (verified for 2.0; re-check against 2.1 calibration export)
- `version`: 562954249961473 (2.0). Book wrapper:
  `{"blueprint_book":{"item":"blueprint-book","label":…,"blueprints":[{"index":i,"blueprint":{…}}],"active_index":0,"version":…}}`.
- Strings: "0" + base64(zlib level 9 of JSON). The game also accepts raw JSON.
- Directions are 16-way: N=0, E=4, S=8, W=12.
- **Inserter direction = pickup side** (direction N picks from the north and drops to the south).
  Fast inserter ≈2.3 items/s, long-handed ≈1.2 items/s at hand size 1. Assume no capacity research
  unless told.
- Copper wires: blueprint-level `"wires": [[entA, 5, entB, 5], …]` (5 = pole copper connector).
  Build a minimum spanning tree over poles with reach = min(reach of both ends).
- Splitter filter: `"filter": {"type":"item","name":…}, "output_priority": "left"|"right"`. For a
  west-facing splitter, "right" = north.
- Underground belt: `"type": "input"|"output"`. Express underground max span 9.
- Pipe-to-ground `direction` = its above-ground connection side; it links underground to the nearest
  pipe-to-ground on the opposite side facing back.
- Display panel: `"icon": {"type":"item"|"fluid","name":…}`.
- Assembler 3 fluid input: middle of the machine's "north" edge (rotates with direction); output is
  the opposite middle.
- Chemical plant: inputs at north edge x−1 and x+1, outputs at south edge x−1 and x+1 (rotate with
  direction).

## Validators (run on every blueprint; report failures, never ship a failing one)
- **Collisions**: entity footprints, plus the grid stamped in all 4 rotations.
- **Power**: every powered entity inside some pole's supply area, and all poles in one wired network.
  Because the grid's big poles aren't in the blueprint, wires to them can't be stored. Check in game
  whether bot-built poles auto-connect; until then, put a medium pole within 9 tiles of a grid big pole.
- **Inserters**: compute each one's pickup and drop tile and assert the expected source and target
  (correct belt row or machine, correct recipe).
- **Belts**: list every junction (curve or sideload) and every dead end. Each must be intended. No
  belt may accidentally feed into another or into a pipe column.
- **Undergrounds**: every belt and pipe underground has a partner within range.
- **Fluids**: flood-fill each pipe network. Every machine intake must sit on the right network, the
  networks must never mix, and there must be no unconnected intakes.
- **Ratios**: recompute throughput from recipe data, inserter rates, lane capacities and machine
  counts. Show the bottleneck in belts.

## Design patterns that worked (reuse them)
- **Mirrored row pairs** sharing belts in the middle: `[out | asm | ins | A | B | ins | asm | out]`.
  Near belt picked with fast inserters, far belt with long-handed ones. Two rows dropping onto a shared
  belt from opposite sides fill both lanes.
- **Two-ingredient belt**: one ingredient per lane, built by side-loading into a belt's start from the
  north and the south. To get a single lane from one side only, put a 1-tile dummy belt behind the
  start tile.
- **Direct insertion chains** for high-volume intermediates: cable→green, Y→R→B belts,
  sulfur→acid→sulfur, gear assemblers beside consumers.
- **Product belts pass their consumers before leaving**: e.g. the yellow belt runs past the red
  assemblers, then exits. A stalled output still feeds downstream consumers.
- **Output merge**: half-belts side-loaded from opposite sides onto the final belt give two full lanes.
- **Wide distribution**: a trunk with chained splitters into rows (back-pressure balances it). Splitters
  preserve lanes, so a mixed-lane trunk feeds mixed-lane rows.
- **Crossings**: use undergrounds. Short hops under trunks; vertical pipe-to-ground under belt rows.
- **Chemical plant fluid side is uncertain** for single-fluid recipes (acid, battery): feed both
  intakes and join both outputs. For two-fluid recipes (sulfur: assumed water on the left, petroleum
  on the right), use **separate inlet pipes** so David can swap them if alt-mode shows them reversed.
- Don't trust "exactly 100%" ratios. Leave slack (extra machines), and note when a lane is exactly full.

## Process for each new blueprint
1. Confirm the target, inputs and footprint limits with David (short).
2. Verify the recipes and entity data, compute the ratios, and report them in belts.
3. Generate → run all validators → render the preview → fix → repeat until clean.
4. Write its dir under `library/`, fill `spec.yaml` result, and summarize in 2–4 lines plus "check in game" items.

## Check in game (open items)
- Do bot-built poles auto-connect to the grid's big poles?

## Status & log
- 2026-11-17: Repo dir created, this file written. Nothing built yet.
- 2026-11-17: Calibration export saved in `calibration.txt` (not decoded yet). `tools/library_tree.py`
  reads the in-game library `~/games/factorio/blueprint-storage-2.dat` (reverse-engineered binary:
  blueprints are length-prefixed, books = slot count + 2-byte trailer, decon planners parsed from samples,
  upgrade planners/book icons not handled). Full file parses (19 top-level slots). Writing the .dat is
  NOT done: the game holds it while running; deliver via import strings instead.
- 2026-11-17: Created `library/` skeleton (4 books, spec template), README, .gitignore. Book strings
  dropped: David manages books in game.
- 2026-11-17: Calibration = David's "Roboport Huge" (5x5 lattice). Verified: `version` 562954249961473
  (unchanged in 2.1), `"snap-to-grid":{x:50,y:50}`, `"absolute-snapping":true`,
  `"position-relative-to-grid":{x:192,y:185}` with first roboport at (2,2). Lattice pattern in
  `lib/roboport_lattice.py`.
- 2026-11-17: Built book **Roboports** (`library/roboports/`): 50x50 … 250x250 (1x1 … 5x5 roboports).
  250x250 matches the calibration exactly. Added 500x500, 1000x1000, 2000x2000 (10x10, 20x20, 40x40).
- 2026-11-17: Book **Electricity** (`library/electricity/`): `huge-solar` = David's Huge Solar
  (import/huge-solar.txt) with 4 roboports instead of 16 (exhaustive search: lone-field construction
  coverage + logistic chaining when tiled). Awaiting in-game test. David's source strings go in `import/`.
- 2026-11-17: Added `sea-supply-base` (snapped, 1 cell, requesters -> 7 yellow belts W) and
  `sea-supply-site` (standalone: belts -> filtered storage chests, robots -> roboport, 4 fish chests).
  Shared code: `lib/build.py` (builder, MST wiring, validators incl. belt trace), `lib/sea_supply.py`.
  Snapped blueprints: entities normalised so bbox top-left = (0,0), offset = (192,185) + bbox top-left in
  the calibration frame (roboport R at (2,2)). Unverified until David places one.
  Return lane (8th belt, row 11, flows east): site open storage chest -> base open storage chest, for
  fish and anything else bots store at the site (replaced the 4 fish chests).
  David's workflow: solar at sea in its own network, fed by one belt per product from base requesters.
- 2026-11-17: Roboports book now has 3 rows: squares, horizontal lines 100x50..2000x50, vertical lines
  50x100..50x2000 (temporary corridors into a build site; `roboport_lattice.build(nx, label, ny=)`).
  `build_book.py` supports `rows:` in book.yaml (sparse indices, row r starts at r*row_width, default 10).
  Check in game: book GUI is 10 slots wide and keeps the gaps.
- 2026-11-18: No more snapping except Roboports; blocks include the cell's 4 corner roboports
  (`cell.finish`). sea-supply-base converted. Plastic is now 3 stacked modules = 3 blue belts (cell was
  mostly empty; David OK'd 3 belts).
  Coal on 2 blue belts -> 2 splitters (`b.splitter`) -> 3 modules (middle one fed by both, sideloaded).
- 2026-11-18: **Intermediates/plastic** (first version, 1 module): 24 chem plants, 2 mirrored rows of 12 around a shared coal belt,
  fast out / long-handed in, petroleum pipes on the outer edges, 41x13 in one cell. New shared code:
  `lib/cell.py` (center in cell, 4-rotation grid check incl. grid link, snap fields), `lib/build.py` now has
  blue belts (`b.belt_name`), pipes/pipe-to-ground, chemical plants, long-handed, `fluid_networks()`.
  Verified data: chem plant inputs north edge (-1,-1),(1,-1), outputs south; pipe-to-ground max 10;
  long-handed pickup 2 (rotation 0.02), fast rotation 0.04; express belt 45/s, express underground max 9.
  David works one blueprint at a time; don't ask what defaults already answer.
- 2026-11-18: **Intermediates/green-circuit**: 2 cells side by side, 4 rows of 3 direct-insertion units
  (C G C G C, bulk inserters), mixed copper/iron row belts formed by sideloads, 2 Cu + 1 Fe belt in.
  Verified: AM3 speed 1.25, cable/circuit 0.5 s, bulk-inserter tech = +1 bulk hand (2). Multi-cell:
  `cell.check_fixed(b, cw, ch)` + `finish(..., corner_list=corners(cw, ch))`; `build.reach()` = belt BFS.
  Grid pole at (53,23) sits mid-line between side-by-side cells: keep a free row band at y22-23.
- 2026-11-18: Sea supply reworked: one chest per product on each end, every chest 1 slot (`bar: 1`),
  base requests one stack with the section OFF (`active: false`; David toggles at bootstrap). No landfill
  buffer. All belts ~2.3/s (landfill ~85 min per Huge Solar field) - David accepts slower builds.
  Return lane kept (row 9). `bar`/`active` JSON from draftsman, unverified in game.
- 2026-11-18: Imported David's Automation designs (`import/{red-circuit,engine,electric-engine,blue-circuit,
  sulfuric-acid}.txt`, grid-embedded). `lib/adapt.py`: strip grid big poles/lamps (keep corner roboports),
  rewire poles as spanning tree, yellow->blue, re-validate (grid collision, power incl. grid poles, pole
  groups near grid, inserter targets, undergrounds, fluid inputs incl. AM3 port (0,-1)N). Built
  intermediates red-circuit (5 cells; cable caps it at 30/s, label says 45), engine (10 cells),
  electric-engine (4 cells), blue-circuit + acid (acid cell right of top-right cell, 80/s acid).
  Flying robot frame: rate not decided (45/s would need 720 AM3).
- 2026-11-18: Red fix: David's cable belts got cable on ONE lane (all cable asms on one side; inserters drop on
  the far lane) -> red was 22.5/s. Added 4 blocks x 5 cable asms sideloading the empty lanes -> 45/s.
  Lesson: inserters fill only the far lane; one-sided feeding = half a belt.
- 2026-11-18: Flying robot frame: 1 yellow belt (David). 264 AM3, 1x4 cells; two mixed snakes (A engine|battery,
  B green|steel) with halfway lane top-ups; outputs via two collectors merging into one yellow belt.
- 2026-11-18: Built sulfur (24 plants, 1 cell, rotation-safe; water/petroleum on separate pipes, petroleum port
  = ptg diving under the water line; assumed fluid box 1 = water), explosives (96 plants, 1 cell, 45 tall so
  not rotation-safe), batteries (192 plants, 2x1 cells, two mixed iron|copper trunks since 45/s > one lane),
  LDS (David: 15/s yellow; 184 AM3, 2x2 cells, 8 copper + 4 plastic + 4 steel input belts). Shared code
  `lib/chem_rows.py` (chem modules with 2 item ingredients + 1 fluid; single or dual trunk; plant gap for grid poles).
  Verified: chem plant speed 1, fluid box order left (-1,-1) then right (1,-1); LDS 15 s; battery 4 s;
  explosives 4 s -> 2; sulfur 30 water + 30 petroleum -> 2 in 1 s.
- 2026-11-18: Scope (David): Intermediates = only what the science-pack blueprints share. Each SP gets its own
  blueprint that takes intermediates and makes the pack-specific parts itself (gears, inserters, belts, ammo,
  grenades, walls, furnaces, modules, rails; rocket fuel and rocket parts live in the white SP blueprint).
  Sulfuric acid and lubricant come from David's oil setup (no blocks needed). Intermediates is complete.
- 2026-11-18: Green circuit now 2 blue belts in the same 2x1 cells: 3 pairs x 2 rows x 3 units (18 units, 54 C +
  36 G), 3 copper + 2 iron in, all exactly full (copper lane caps a row at 3 units). Splitter as lane-preserving
  merger (one output left empty) combines pair 1/3 with half of pair 2.
- 2026-11-18: Flying robot frame re-laid horizontally (4x1): 3 pairs x 2 rows x 44, each pair its own A/B mixed
  belts; inputs split 3 ways by splitter taps on 4 vertical columns, feeds underground under the columns.
  Input panels sit between an underground pair on the entry row (dense entry rows).
- 2026-11-18: New book **Science** (`library/science/`): one block per pack, 1 full blue belt, built red -> space.
  Input belt colour = need (yellow <= 15, red <= 30, blue <= 45; `sp_rows.tier`). Shared code `lib/sp_rows.py`
  (frame layout generalised: pairs of rows, 1 or 2 mixed belts, column taps, collectors). Red science: 192
  packs + 20 gear machines (vertical block, bulk inserters), 3x1 cells. Verified: underground max 5/7/9; pack
  recipes (red 5 s, green 6 s, military 10 s -> 2, blue 24 s -> 2, purple 21 s -> 3, yellow 21 s -> 3).
- 2026-11-18: Added David's **Oil Megablock** to Intermediates as is (`import/oil-megapack.txt`, generate.py only
  copies + renders; constraints not applied). It makes the acid/lubricant/solid fuel the other blocks take.
- 2026-11-18: Roboports book trimmed to 6 sizes per row (100..1000; 50x50 and the 2000 sizes removed), row_width 6:
  row 1 squares, row 2 horizontal lines, row 3 vertical lines.
- 2026-11-18: New book **Mall** (`library/mall/`). David's 5 mall designs saved in `import/mall-*.txt`. Decisions:
  belts block -> 8 filtered storage chests per tier (24); solar + accumulators -> ONE blueprint; artillery -> 60/min;
  all-in-one -> full compact redesign on the grid (David chose it over "fit as is"). Done: belts (adapted 1 cell,
  sorting splitters + chest rows replace the exits); solar+accumulators (1x2 cells, own sulfur/acid/battery);
  artillery 60/min (2x1, radars exactly 1/s). Outputs leave on belts, no buffers (David). All-in-one: kept as is (no redesign) but shifted to the only collision-free grid offset + 24 corner roboports.
  Pitfall caught by the inserter validator: input rows must not end next to an output merge column.
- 2026-11-18: Electricity/steam-power: rebuilt after David: ALL inputs grouped on one side (12 water ptg, two tiles
  apart, + 2 blue coal belts). 150 boilers / 300 engines / 270 MW, 1x4 cells; one separate water line per boiler row,
  fanned out underground in nested columns (no crossings except ptg over ptg); coal trunks on the right grid line.
  Lesson: inputs must be grouped at one place; check totals when grouping (75 coal/s needs blue). Verified: boiler 1.8 MW/60 steam, engine 30 steam/s, offshore pump 1200/s, coal 4 MJ.
  Non-square entities (boiler 3x2, steam engine 3x5) handled by a BP subclass in the generator.
- Next: (2) Run `--dump-data`, set up Python
  venv + draftsman, scaffold `lib/`. (3) David picks the first blueprint + target rate + footprint.
