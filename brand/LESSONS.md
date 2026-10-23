# Lessons: pitfalls and the rule that prevents each

**Read before every edit; add your own** (mistake → cause → rule). These come from real edits.

| # | Pitfall | Cause | Rule |
|---|---|---|---|
| 1 | iPhone video looks grey and washed out | HDR (HLG / Dolby Vision) converted without tone mapping | `prep` tone-maps HDR automatically (Hable). Check `probe()` shows `hdr: True` for phone clips |
| 2 | Portrait phone clip treated as landscape | Rotation stored in side data | `probe()` reads the rotation; check the reported width × height |
| 3 | Vertical clips squeezed into a 16:9 frame | Canvas taken from the first (landscape) clip | Canvas = target format (`--format short` = 1080×1920); check `master.mp4` |
| 4 | Landscape clip in a vertical video looks blotchy | A light blur fill looks like coloured blobs | Square-crop the centre over a dark, heavily blurred fill (built in) |
| 5 | Audio and video drift apart after cutting | Phones record variable frame rate | Everything is converted to constant 30 fps before cutting (built in) |
| 6 | Render crashes: "No frame found at position" | B-frames + low RAM | Every video Remotion reads is no-B-frame H.264 (`conform` for b-roll); `--concurrency=2` |
| 7 | Render opens the wrong page | Port 3000 used by another dev server | Renders use `--port=3917` |
| 8 | Video sounds cheap / "annoying" | Sound effect on every caption, title and cut | Lifestyle vlogs: keep the real ambience; at most ~3 designed sounds per short, on real camera moves |
| 9 | Sound effect hides a word | Placed on a word onset | Keep effects ≥ 0.3 s away from spoken words |
| 10 | Video too quiet after mastering | Clipped pre-mix or a loud music tail | Pre-mix with headroom; check per-stem peaks if loudness misses the target |
| 11 | Captions over a face or a cropped frame | One fixed caption height | `captions.yAt: [[start, end, y]]` moves them for specific shots |
| 12 | Wrong words in captions | Speech-to-text mishears names and slang | Proofread every caption; ask the creator about unclear words; keep words the transcript heard with high confidence |
| 13 | Private info went public | Nobody checked the frames | Check every render for addresses, plates, money, IDs, screens and people's details before posting |
| 14 | Edits lost after re-cutting | Overlay times were tied to the old cut | Re-check overlay and caption times after every `--ranges` change |
