# Factorio blueprints

`library/` mirrors the in-game blueprint library: directories are books, leaves are blueprints.

- A dir with `book.yaml` is a **book** (label, description, icons). Subdirs are its contents.
- A dir with `spec.yaml` is a **blueprint**. It contains:
  - `spec.yaml`: request (what was asked) and result (what was built and verified). See `library/_template/`.
  - `blueprint.txt`: the import string. Paste it in game.
  - `blueprint.json`: the same blueprint decoded (readable, diffable).
  - `generate.py`: the generator that produces `blueprint.txt`/`.json`/`preview.png`.
  - `preview.png`: top-down render.

Books are assembled in game by hand; there are no book strings.
