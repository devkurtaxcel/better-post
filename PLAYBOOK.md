# Playbook: editing a vlog with better-post

The recipe Claude Code (or you) follows from raw clips to a postable vertical video.
**Read first, every time:** `brand/TASTE.md` (what the creator likes) and `brand/LESSONS.md` (pitfalls). Brand values come from `brand/brand.json` only.
Commands use `PY=.venv/Scripts/python.exe` (macOS/Linux: `.venv/bin/python`).

## 1. Intake
- List `contents/<VLOG>/`. **File names are instructions:** `START` opens, numbers set the order, text in brackets says what a clip is (`6 (PRODUCT DEMO)`), `ENDING` closes.
- Look at a few frames of each clip to understand the story.

## 2. Prep
```bash
$PY toolkit/ve.py new <slug> "contents/<VLOG>" --format short
$PY toolkit/ve.py prep <slug> --format short --model small --grade cinematic --no-cut
```
Automatic: HDR fix, 1080×1920 canvas (landscape clips square-cropped over a dark blur), constant 30 fps, local transcript.
`--no-cut` keeps b-roll intact so you choose the cuts; drop it for talking-head videos to auto-remove pauses and fillers.

## 3. Ask once
Only what you can't infer: names (product, people: OK to name them?), places, words the transcript got wrong. Use the creator's **exact words** in captions; never paraphrase.

## 4. Story and cut
- Write `projects/<slug>/brief.md`: the story in "but / therefore" beats (setup → problem → payoff), not "and then".
- Choose keep-ranges between word timings (source seconds). Keep the lines that carry the story; trim b-roll to 2.5–4.5 s. Aim for **30–60 s**: most viewers decide in the **first second**, and many leave by ~30 s.
- Remove: fillers, dead air, anything private (addresses, plates, IDs, money, screens, other people's details).
```bash
$PY toolkit/ve.py prep <slug> --format short --grade cinematic --reuse --force-plan --ranges "a-b,c-d,..."
```

## 5. Creative pass (edit `projects/<slug>/edit.json`)
| Field | Rule of thumb |
|---|---|
| `captions.words` | Key lines only for vlogs; fix transcription mistakes; max 3 words on screen |
| `captions.accent` | One highlighted word per line (names, numbers, the payoff) |
| `overlays` | `title`, `lowerThird`, `emphasis`, `callout`, `counter`, `image`, `broll`. Keep them away from faces and the caption band |
| `segments[].zoom` | Punch-in (1.1) only on jump cuts inside the same clip |
| `music` | An approved track; `silences: [[a,b]]` drops the music right before a big moment |
| `sfx` | Rare: only on real camera moves. Never on every caption or title (it sounds cheap) |
| `branding.watermark` | Your handle (moving watermark), or `null` |

## 6. Sound, render, review
```bash
$PY toolkit/ve.py sound <slug>              # prints loudness (≈ -12 LUFS shorts / -14 YouTube)
$PY toolkit/ve.py render <slug> --preview
$PY toolkit/ve.py review <slug> --frames 24 # LOOK at out/contact.png
```
Check:
- captions are readable and not over faces;
- no frame looks blotchy or badly cropped;
- nothing private is visible;
- the end card is clean.

Then:
```bash
$PY toolkit/ve.py render <slug>             # out/final.mp4 + out/final_share.mp4
```

## 7. Learn
Add every piece of feedback to `brand/TASTE.md` (quote it, add the date) and every mistake to `brand/LESSONS.md` (mistake → cause → rule). That's how the next edit lands in one shot.
