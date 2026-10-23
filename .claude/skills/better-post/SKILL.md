---
name: better-post
description: Edit the user's raw clips into a finished vertical (or landscape) video with better-post (cuts, captions, punch-ins, titles, music fitted on the beat, mix, watermark, end card), following PLAYBOOK.md. Use when clips appear in contents/ or the user asks to edit, cut, caption or add music to a video.
---

# better-post

Follow [PLAYBOOK.md](../../../PLAYBOOK.md) step by step. Read `brand/TASTE.md`, `brand/LESSONS.md` and `brand/brand.json` first.

**Pipeline:** `toolkit/ve.py`
- `new <slug> "contents/<FOLDER>"`: orders clips START → 2, 3 … → ENDING.
- `prep`: HDR fix, 1080×1920 canvas, CFR 30, local transcript, cut, draft `edit.json`.
- `sound`: approved track fitted on the beat, voice-keyed ducking, mastered to −12 LUFS shorts / −14 YouTube.
- `render [--preview]`, then `review` (read `out/contact.png`).

**Music:** `toolkit/library.py` (index/fetch/analyse/review/approve). **Engine:** `engine/` (Remotion) renders `edit.json` with the brand.

## edit.json quick reference
- `captions`: `words` (text/start/end in seconds), `accent` (highlighted words), `maxWords`, `y`, `yAt`
- `segments`: `start`, `end`, `zoom`, `push`, `focusX`, `focusY`
- `transitions`: `at` + `whip|zoom|flash|dip|slide`. Use sparingly
- `overlays`: `title`, `lowerThird`, `emphasis`, `callout{x,y}`, `counter{to,prefix,suffix,label}`, `image{src}`, `broll{src,trim}`, `motion{src,mode}`
- `music`: `mode: "library"`, `file`, `silences`, `trimDb`
- `sfx`: `[time, name, gain]` (a file in `assets/sfx/<name>.mp3`)
- `branding`: `kicker`, `endCard`, `handle`, `watermark`, `progressBar`
- `style`: `cinematic` (sparse sound) or `explainer`

## Gotchas
- Every video Remotion reads must be no-B-frame H.264 (`ve.py conform` for b-roll).
- Renders use port 3917 and concurrency 2.
- Proofread captions. Speech-to-text mishears names and slang.
- You can't hear the mix: tell the user to listen before posting.
