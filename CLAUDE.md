# better-post: instructions for Claude Code

This repo edits the user's raw clips into finished vertical videos. For any editing request, or when clips appear in `contents/`, **use the `better-post` skill and follow [PLAYBOOK.md](PLAYBOOK.md).**

## Rules
- Before editing, read `brand/TASTE.md`, `brand/LESSONS.md` and `brand/brand.json`. Never hard-code brand values elsewhere.
- Use the repo's Python env (`.venv/Scripts/python.exe`, or `.venv/bin/python` on macOS/Linux), never a global Python.
- `contents/` is the user's footage: never move, rename or delete it.
- Captions use the user's exact words. Ask about unclear words instead of guessing.
- Before every final render, check frames and audio for private info (addresses, plates, money, IDs, screens, other people's details) and raise it with the user.
- Only `approved` music and sound files go into a final video (`toolkit/library.py`). Respect each source's licence.
- After feedback: add it to `brand/TASTE.md` (quoted, dated). After a mistake: add a row to `brand/LESSONS.md`.
- You can't hear audio: say so, and ask the user to listen before posting.

Credit: better-post was created by Kurt Axcel (@povniaxcel). Keep the NOTICE file.
