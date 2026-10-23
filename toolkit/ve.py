"""better-post: a local, AI-driven video edit pipeline (run it yourself or let Claude Code drive it).

    python toolkit/ve.py new <slug> [files or a folder]   # start a project (a folder is ordered START, 2, 3 ... ENDING)
    python toolkit/ve.py prep <slug>             # normalise (HDR fix, grade), transcribe, cut dead air, draft edit.json
    python toolkit/ve.py sound <slug>            # music fitted on the beat, ducked under the voice, mastered for the platform
    python toolkit/ve.py render <slug> [--preview]
    python toolkit/ve.py review <slug>           # contact sheet of the render (look at it!)
    python toolkit/ve.py conform <slug> <files>  # bring b-roll in, Remotion-safe
    python toolkit/ve.py all <slug>              # prep, sound, render, review
    prep options: --ranges "a-b,..." (manual cut)  --reuse  --renormalise  --grade cinematic  --model small  --no-cut  --force-plan

Everything runs locally: ffmpeg, faster-whisper, numpy, librosa, pyloudnorm and Remotion. No API credits.
Created by Kurt Axcel (@povniaxcel). See NOTICE. Playbook: PLAYBOOK.md.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import audiolib as A  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FPS = 30
MEDIA = (".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi", ".mts", ".mp3", ".wav", ".m4a", ".aac", ".flac")
FILLERS = {"um", "uh", "uhm", "umm", "erm", "er", "ah", "hmm", "mm", "eh"}
FORMATS = {"short": (1080, 1920), "landscape": (1920, 1080), "square": (1080, 1080)}
# Remotion's frame extractor fails ("No frame found at position") on x264 B-frames; every video it reads goes through this
REMOTION_SAFE = ["-c:v", "libx264", "-crf", "17", "-preset", "fast", "-bf", "0", "-g", str(FPS), "-pix_fmt", "yuv420p", "-movflags", "+faststart"]


def P(slug, *parts):
    return os.path.join(ROOT, "projects", slug, *parts)


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd)[:220])
    return subprocess.run(cmd, check=True, **kw)


def jload(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def jsave(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate,color_transfer:stream_side_data_list",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    v = next((s for s in d.get("streams", []) if s["codec_type"] == "video"), None)
    a = any(s["codec_type"] == "audio" for s in d.get("streams", []))
    w, h = (v["width"], v["height"]) if v else (0, 0)
    rot = 0
    for sd in (v or {}).get("side_data_list", []) or []:
        if "rotation" in sd:  # phones: display matrix entry among DOVI/HDR side data
            rot = int(sd["rotation"])
    if abs(rot) in (90, 270):
        w, h = h, w
    hdr = (v or {}).get("color_transfer") in ("arib-std-b67", "smpte2084")  # iPhone HLG / HDR10 → needs tone mapping
    return {"path": path, "duration": float(d["format"]["duration"]), "video": bool(v), "audio": a, "width": w, "height": h, "hdr": hdr}


# ---------------------------------------------------------------- new
def ordered_clips(folder):
    """Naming convention (contents/README.md): START first, then numbered clips ascending, then other named clips
    (instructions like "COVER THE MONEY", "B-ROLL ..."), ENDING last."""
    clips = [f for f in os.listdir(folder) if f.lower().endswith(MEDIA)]
    def key(f):
        n = os.path.splitext(f)[0].strip().upper()
        if n.startswith("START"):
            return (0, 0, n)
        if n.startswith("ENDING") or n.startswith("END "):
            return (3, 0, n)
        m = re.match(r"(\d+)", n)
        return (1, int(m.group(1)), n) if m else (2, 0, n)
    out = [os.path.join(folder, f) for f in sorted(clips, key=key)]
    print("  order: " + " | ".join(os.path.basename(f) for f in out))
    return out



def cmd_new(args):
    proj = P(args.slug)
    os.makedirs(os.path.join(proj, "out"), exist_ok=True)
    files = args.files or [os.path.join(ROOT, "contents")]
    expanded = []
    for f in files:  # a folder (e.g. contents/MY VLOG) is ordered by the naming convention in contents/README.md
        expanded += ordered_clips(f) if os.path.isdir(f) else [f]
    files = [os.path.abspath(f) for f in expanded]
    if not files:
        sys.exit("No media found. Put footage in contents/ or pass file paths.")
    info = [probe(f) for f in files]
    fmt = args.format or ("short" if info[0]["height"] > info[0]["width"] else "landscape")
    jsave(os.path.join(proj, "project.json"), {"slug": args.slug, "format": fmt, "sources": info})
    print(f"Project {args.slug}: {len(files)} source(s), format {fmt}")
    for i in info:
        print(f"  {os.path.basename(i['path'])}: {i['duration']:.1f}s {i['width']}x{i['height']} audio={i['audio']}")


# ---------------------------------------------------------------- prep
GRADES = {
    "none": "",
    "natural": "eq=contrast=1.04:saturation=1.06,",
    "warm": "eq=contrast=1.05:saturation=1.08,colorbalance=rs=0.03:gs=0.01:bs=-0.03,",
    "cool": "eq=contrast=1.05:saturation=1.04,colorbalance=rs=-0.02:bs=0.03,",
    "punchy": "eq=contrast=1.10:saturation=1.15:gamma=0.98,unsharp=5:5:0.4,",
    # vlog / lifestyle look: soft S-curve, lifted blacks, cool shadows + warm highlights, a touch less saturation, vignette
    "cinematic": "curves=master='0/0.035 0.25/0.21 0.5/0.5 0.75/0.79 1/0.965',colorbalance=rs=-0.04:gs=-0.005:bs=0.05:rh=0.05:gh=0.01:bh=-0.035,eq=saturation=0.93,vignette=angle=PI/5,",
}


# HDR (iPhone HLG / HDR10) → SDR BT.709. Hable: natural skin, keeps bright highlights
# (mobius blew out highlights; no tone map left skin grey). Runs after the downscale so it's cheap.
TONEMAP = "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,"


def normalise(proj, project, grade):
    """All sources -> one constant-30fps master.mp4 (video) + master.wav (48k mono). Fixes phone VFR drift."""
    srcs = project["sources"]
    # canvas = the target format (not the first clip: a landscape intro once squeezed 9 portrait clips into 16:9)
    W, H = FORMATS[project["format"]]
    cmd = ["ffmpeg", "-y", "-v", "error", "-stats"]
    for s in srcs:
        cmd += ["-i", s["path"]]
    parts = []
    for i, s in enumerate(srcs):
        d = s["duration"]
        if s["video"]:
            tm = TONEMAP if s.get("hdr") else ""
            pre = f"[{i}:v]fps={FPS},scale={W}:{H}:force_original_aspect_ratio=decrease,{tm}{GRADES[grade]}"
            same = abs((s["width"] / s["height"]) / (W / H) - 1) < 0.06
            if same:  # same shape: fill the canvas exactly
                parts.append(f"{pre}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,format=yuv420p,trim=0:{d:.3f},setpts=PTS-STARTPTS[v{i}]")
            else:  # other shape (landscape in a vertical edit): square-crop the centre (2 people still fit) so it reads big,
                # over a dark, heavily blurred fill of itself (a light blur looked like coloured blobs: "AI slop")
                sq = min(W, H)
                pre = f"[{i}:v]fps={FPS},crop='min(iw,ih)':'min(iw,ih)',scale={sq}:{sq},{tm}{GRADES[grade]}"
                parts.append(f"{pre}split[f{i}][b{i}]")
                parts.append(f"[b{i}]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=60,eq=brightness=-0.32:saturation=0.55[bb{i}]")
                parts.append(f"[bb{i}][f{i}]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p,trim=0:{d:.3f},setpts=PTS-STARTPTS[v{i}]")
        else:
            parts.append(f"color=c=0x0b0d10:s={W}x{H}:r={FPS}:d={d:.3f},format=yuv420p[v{i}]")
        if s["audio"]:
            parts.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono,atrim=0:{d:.3f},asetpts=PTS-STARTPTS,apad=whole_dur={d:.3f}[a{i}]")
        else:
            parts.append(f"anullsrc=r=48000:cl=mono,atrim=0:{d:.3f}[a{i}]")
    joined = "".join(f"[v{i}][a{i}]" for i in range(len(srcs)))
    parts.append(f"{joined}concat=n={len(srcs)}:v=1:a=1[v][a]")
    script = os.path.join(proj, "normalise.ffgraph")
    with open(script, "w") as f:
        f.write(";\n".join(parts))
    cmd += ["-filter_complex_script", script, "-map", "[v]", "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-an", os.path.join(proj, "master.mp4"),
            "-map", "[a]", "-c:a", "pcm_s16le", os.path.join(proj, "master.wav")]
    run(cmd)
    # source boundaries on the master timeline (for transitions between clips)
    bounds, t = [], 0.0
    for s in srcs[:-1]:
        t += s["duration"]
        bounds.append(round(t, 3))
    return bounds


def transcribe(wav_path, model_name, language):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segs, info = model.transcribe(wav_path, word_timestamps=True, beam_size=5, language=language, vad_filter=False)
    words = []
    for seg in segs:
        for w in seg.words or []:
            words.append({"text": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3), "p": round(w.probability, 3)})
    return words, info.language


def keep_ranges(words, duration, max_gap, pad_in, pad_out, drop_fillers):
    kept = [w for w in words if not (drop_fillers and w["text"].lower().strip(".,!?") in FILLERS)]
    if not kept:
        return [(0.0, duration)]
    ranges = []
    for w in kept:
        a, b = max(0.0, w["start"] - pad_in), min(duration, w["end"] + pad_out)
        if ranges and a - ranges[-1][1] <= max_gap:
            ranges[-1][1] = max(ranges[-1][1], b)
        else:
            ranges.append([a, b])
    # snap to the frame grid so audio and video cut on identical boundaries
    snapped = []
    for a, b in ranges:
        fa, fb = math.floor(a * FPS), math.ceil(b * FPS)
        if snapped and fa <= snapped[-1][1]:
            snapped[-1][1] = fb
        elif fb - fa >= 3:
            snapped.append([fa, fb])
    return [(fa / FPS, fb / FPS) for fa, fb in snapped]


def read_wav(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768


def cut(proj, ranges):
    """Single-pass frame-accurate video select + numpy audio cut with 30 ms fades at every join."""
    sel = "+".join(f"between(n,{round(a * FPS)},{round(b * FPS) - 1})" for a, b in ranges)
    script = os.path.join(proj, "cut.ffgraph")
    with open(script, "w") as f:
        f.write(f"[0:v]select='{sel}',setpts=N/{FPS}/TB[v]")
    run(["ffmpeg", "-y", "-v", "error", "-stats", "-i", os.path.join(proj, "master.mp4"), "-filter_complex_script", script, "-map", "[v]",
         "-r", str(FPS), *REMOTION_SAFE, os.path.join(proj, "cut.mp4")])
    audio = read_wav(os.path.join(proj, "master.wav"))
    fade = int(0.03 * A.SR)
    pieces = []
    for a, b in ranges:
        seg = audio[int(a * A.SR): int(b * A.SR)].copy()
        if len(seg) > 2 * fade:
            seg[:fade] *= np.linspace(0, 1, fade)
            seg[-fade:] *= np.linspace(1, 0, fade)
        pieces.append(seg)
    A.write_wav(os.path.join(proj, "dialogue.wav"), np.concatenate(pieces), stereo=False)


def remap(words, ranges):
    out, t = [], 0.0
    for a, b in ranges:
        for w in words:
            if w["start"] >= a - 1e-3 and w["end"] <= b + 1e-3:
                out.append({**w, "start": round(w["start"] - a + t, 3), "end": round(w["end"] - a + t, 3)})
        t += b - a
    return out, [(round(sum(bb - aa for aa, bb in ranges[:i]), 3), round(sum(bb - aa for aa, bb in ranges[: i + 1]), 3)) for i in range(len(ranges))]


def cmd_prep(args):
    proj = P(args.slug)
    project = jload(os.path.join(proj, "project.json"))
    reuse = args.reuse and os.path.exists(os.path.join(proj, "transcript.json"))
    if reuse:  # re-cut / re-plan only: keep master + transcript
        print("1-2/4 reuse master + transcript")
        if args.renormalise:  # rebuild the video master only (e.g. after a canvas/grade fix); transcript stays
            normalise(proj, project, args.grade)
        t = jload(os.path.join(proj, "transcript.json"))
        dur, words, lang = t["duration"], t["words"], t["language"]
        bounds = t.get("sourceBounds", [])
    else:
        print("1/4 normalise + join sources")
        bounds = normalise(proj, project, args.grade)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", os.path.join(proj, "master.wav")],
                                   capture_output=True, text=True, check=True).stdout)
        print(f"2/4 transcribe ({args.model}) — local, no credits")
        words, lang = transcribe(os.path.join(proj, "master.wav"), args.model, args.lang)
        jsave(os.path.join(proj, "transcript.json"), {"language": lang, "duration": dur, "words": words, "sourceBounds": bounds, "grade": args.grade})
    print(f"   {len(words)} words, language {lang}")
    print("3/4 cut dead air" + (" + fillers" if not args.keep_fillers else ""))
    if args.ranges:  # creative override, e.g. "0.9-6.9,8.2-10" (seconds on the source timeline), snapped to frames
        ranges = [(round(float(a) * FPS) / FPS, round(float(b) * FPS) / FPS) for a, b in (r.split("-") for r in args.ranges.split(","))]
    else:
        ranges = [(0.0, dur)] if args.no_cut else keep_ranges(words, dur, args.gap, 0.08, 0.14, not args.keep_fillers)
    cut(proj, ranges)
    cut_words, dst = remap(words, ranges)
    cut_dur = dst[-1][1]
    # where each source boundary lands after the cut
    src_bounds = []
    for bt in bounds:
        for (a, b), (da, db) in zip(ranges, dst):
            if a <= bt <= b or bt < a:
                src_bounds.append(round(da + max(0.0, bt - a), 3))
                break
    jsave(os.path.join(proj, "cut.json"), {"ranges": ranges, "timeline": dst, "duration": cut_dur, "removed": round(dur - cut_dur, 2),
                                            "sourceBounds": src_bounds, "words": cut_words})
    print(f"   {dur:.1f}s -> {cut_dur:.1f}s ({len(ranges)} segments, removed {dur - cut_dur:.1f}s)")
    print("4/4 draft edit.json")
    if os.path.exists(os.path.join(proj, "edit.json")) and not args.force_plan:
        print("   edit.json kept (use --force-plan to redraft; re-check overlay times after a re-cut)")
    else:
        plan(proj, project, args.format or project["format"])
    shutil.copy(os.path.join(ROOT, "brand", "brand.json"), os.path.join(proj, "brand.json"))


def default_track():
    """Your go-to: the first APPROVED track in assets/music (library.py approve), else None (pick one in edit.json)."""
    d = os.path.join(ROOT, "assets", "music")
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if f.endswith(".json"):
            m = jload(os.path.join(d, f))
            if m.get("approved") is True:
                return "assets/music/" + f[:-5] + ".mp3"
    return None


def plan(proj, project, fmt):
    c = jload(os.path.join(proj, "cut.json"))
    brand = jload(os.path.join(ROOT, "brand", "brand.json"))
    W, H = FORMATS[fmt]
    talking = len(c["words"]) / max(c["duration"], 1) > 1.0  # speech-led footage
    # Vlog defaults: clean cuts between clips, punch-in alternates only on
    # jump cuts inside the same clip, a slow 3% push everywhere else. No auto whips at clip changes.
    bounds = [0.0]
    for s_ in project["sources"]:
        bounds.append(bounds[-1] + s_["duration"])
    src_of = lambda t: next((i for i in range(len(bounds) - 1) if bounds[i] <= t < bounds[i + 1]), len(bounds) - 2)
    segments, prev, k = [], None, 0
    for (a, b), (da, db) in zip(c["ranges"], c["timeline"]):
        src = src_of(a)
        k = k + 1 if src == prev else 0
        prev = src
        segments.append({"start": da, "end": db, "zoom": [1.0, 1.1][k % 2], "push": 0.03})
    transitions = []
    end_card = 2.0
    edit = {
        "format": fmt, "width": W, "height": H, "fps": FPS,
        "video": "cut.mp4", "audio": "mix.wav",
        "source": {k: probe(os.path.join(proj, "cut.mp4"))[k] for k in ("width", "height")},
        "contentDuration": c["duration"],
        "durationInFrames": math.ceil((c["duration"] + end_card) * FPS),
        "theme": brand["video"]["defaultTheme"],
        "reframe": {"mode": "cover" if fmt == "short" else "fit", "focusX": 0.5, "focusY": 0.42},
        "segments": segments,
        "transitions": transitions,
        "captions": {"enabled": talking, "maxWords": brand["video"]["captions"]["maxWordsShort"] if fmt == "short" else 6,
                     "y": 0.70 if fmt == "short" else 0.84, "accent": [], "words": c["words"]},
        "overlays": [],
        "branding": {"kicker": True, "endCard": end_card, "handle": brand["handles"]["youtube"] if fmt == "landscape" else brand["handles"]["tiktok"], "progressBar": False, "watermark": brand["handles"].get("tiktok")},  # moving anti-reupload watermark
        "grain": 0.06,
        # music: pick an APPROVED library track (python toolkit/library.py list --approved); "generate" = synth draft only
        "music": {"mode": "library", "file": default_track(), "silences": [], "trimDb": 0},
        "style": "cinematic",
        "sfx": [],
        "autoSfx": False,  # cinematic: designed SFX only where Claude places them (camera moves), max 3 per short
        "notes": "Draft from ve.py plan. Claude: set captions.accent, add overlays (title, lowerThird, emphasis, callout, counter, image, broll), music silences before big moments, then ve.py sound + render.",
    }
    jsave(os.path.join(proj, "edit.json"), edit)
    print(f"   {len(segments)} segments, {len(transitions)} transitions, captions={'on' if talking else 'off'}")


# ---------------------------------------------------------------- sound
# Mixing priority: voice > location sound > music > designed SFX.
# Cinematic/lifestyle: most cuts get NO added sound; designed SFX only on camera energy, budgeted, never on a word onset.
SFX_FOR = {"whip": "whoosh", "zoom": "whoosh", "flash": "impact"}
SFX_FOR_EXPLAINER = {**SFX_FOR, "slide": "swish", "title": "whoosh", "lowerThird": "swish", "emphasis": "pop", "callout": "tick", "counter": "click"}
SFX_BUDGET = {"cinematic": 3, "explainer": 12}
TARGET_LUFS = {"short": -12.0, "square": -12.0, "landscape": -14.0}  # shorts: phone speakers; YouTube normalises to -14
MUSIC_UNDER_SPEECH_DB = -18.0  # music 15-20 dB under the voice while talking
MUSIC_IN_GAPS_DB = -8.0        # rises in pauses longer than 1 s


def auto_cues(edit):
    style = edit.get("style", "cinematic")
    table = SFX_FOR if style == "cinematic" else SFX_FOR_EXPLAINER
    cues = [[t["at"], table[t["type"]], 0.35] for t in edit["transitions"] if t["type"] in table]
    if style != "cinematic":
        cues += [[o["start"], o.get("sfx") or table[o["type"]], 0.3] for o in edit["overlays"] if o.get("sfx") or table.get(o["type"])]
    onsets = [w["start"] for w in edit["captions"]["words"]]
    cues = [c for c in cues if all(abs(c[0] - o) >= 0.3 for o in onsets)]  # an SFX on a word masks the word
    return cues[: SFX_BUDGET.get(style, 3)]


def place(N, cues, sfx_dir, guard_words=()):
    out, cache = np.zeros(N), {}
    for t, name, gain in cues:
        if any(abs(t - o) < 0.3 for o in guard_words):
            print(f"  ! sfx '{name}' at {t:.2f}s sits on a spoken word (kept: it was placed by hand)")
        if name not in cache:
            cache[name] = A.load_sfx(name, sfx_dir)
        snd, peak = cache[name]
        i = int((t - peak) * A.SR)
        if i < 0:
            snd, i = snd[-i:], 0
        out[i: i + len(snd)] += snd[: max(0, N - i)] * gain
    return out


def beat_times(x):
    try:
        import librosa
        y = librosa.resample(x, orig_sr=A.SR, target_sr=22050)
        _, b = librosa.beat.beat_track(y=y, sr=22050, units="time")
        return np.asarray(b, dtype=float)
    except ImportError:  # no librosa: 0.5 s grid (avoids random cuts, not beat-exact)
        return np.arange(0, len(x) / A.SR, 0.5)


def fit_music(path, need, total, start_at=None):
    """Library track -> exactly `need` s, cut on a beat, reverb tail on the final hit only (never looped mid-phrase)."""
    x = A.read_audio(path)
    beats = beat_times(x)
    t0 = start_at if start_at is not None else (float(beats[0]) if len(beats) else 0.0)
    rel = beats[beats > t0 + 1.0] - t0
    cut = float(rel[np.argmin(np.abs(rel - need))]) if len(rel) else need
    seg = x[int(t0 * A.SR): int((t0 + cut) * A.SR)].copy()
    fi, fo = int(0.25 * A.SR), int(0.08 * A.SR)
    seg[:fi] *= np.linspace(0, 1, fi)
    seg[-fo:] *= np.linspace(1, 0, fo)
    last = int(1.0 * A.SR)
    tail = A.convolve(np.concatenate([seg[-last:], np.zeros(3 * A.SR)]), A.impulse_response(3.0, 0.8, 5000))[last:]
    N = int(total * A.SR) + A.SR
    out = np.zeros(N)
    out[: min(len(seg), N)] = seg[:N]
    j = len(seg)
    if j < N:  # tail starts at the level of the final bar and decays (never louder than the music itself)
        ref = np.sqrt(np.mean(seg[-last:] ** 2)) + 1e-9
        tail *= 0.7 * ref / (np.sqrt(np.mean(tail[: int(0.3 * A.SR)] ** 2)) + 1e-9)
        out[j: j + len(tail)] += tail[: N - j]
    bpm = 60 / np.median(np.diff(beats)) if len(beats) > 2 else 0
    print(f"  music: {os.path.basename(path)} from {t0:.2f}s, cut on a beat at {cut:.2f}s (~{bpm:.0f} BPM) + reverb tail")
    return out


def lufs(x):
    try:
        import pyloudnorm
        return pyloudnorm.Meter(A.SR).integrated_loudness(x)
    except Exception:  # fallback: RMS dBFS (fine for relative levels)
        return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


def duck_envelope(N, words, silences):
    """Gain curve from the transcript's word timings: down ~250 ms before each word, back up only in pauses > 1 s."""
    db = np.full(N, MUSIC_IN_GAPS_DB)
    spans = []
    for w in words:
        a, b = w["start"] - 0.25, w["end"] + 0.6
        if spans and a - spans[-1][1] < 1.0:
            spans[-1][1] = b
        else:
            spans.append([a, b])
    for a, b in spans:
        db[max(0, int(a * A.SR)): int(b * A.SR)] = MUSIC_UNDER_SPEECH_DB
    for a, b in silences:  # strategic silence before a reveal; ambience stays (it lives in the dialogue track)
        db[int(a * A.SR): int(b * A.SR)] = -90
    k = int(0.25 * A.SR)  # smooth moves, no pumping
    db = np.convolve(db, np.ones(k) / k, mode="same")
    return 10 ** (db / 20)


def cmd_sound(args):
    proj = P(args.slug)
    edit = jload(os.path.join(proj, "edit.json"))
    total = edit["durationInFrames"] / FPS
    N = int(total * A.SR) + A.SR
    style = edit.get("style", "cinematic")
    words = edit["captions"]["words"]

    # 1. dialogue: high-pass + gentle EQ/compression. No gate: the location sound IS the vlog's ambience.
    dpath = os.path.join(proj, "dialogue_proc.wav")
    run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(proj, "dialogue.wav"), "-af",
         "highpass=f=90,equalizer=f=200:t=q:w=1:g=1.5,equalizer=f=3200:t=q:w=1.4:g=2,"
         "acompressor=threshold=-26dB:ratio=3:attack=6:release=150:makeup=4,aresample=192000,alimiter=limit=0.5:attack=1:release=50:level=disabled,aresample=48000",
         "-ac", "1", "-ar", str(A.SR), dpath])
    dia = np.zeros(N)
    d = A.read_audio(dpath)
    dia[: min(len(d), N)] = d[:N]
    speech = np.concatenate([dia[int(w["start"] * A.SR): int(w["end"] * A.SR)] for w in words]) if words else dia
    L_dia = lufs(speech) if len(speech) > A.SR * 0.4 else lufs(dia)

    # 2. designed SFX: auto (budgeted, cinematic = camera energy only) + hand-placed; peaks 6 dB under the voice
    sfx_dir = os.path.join(ROOT, "assets", "sfx")
    auto = auto_cues(edit) if edit.get("autoSfx", style != "cinematic") else []
    hand = edit.get("sfx", [])
    sfx = place(N, auto, sfx_dir) + place(N, hand, sfx_dir, guard_words=[w["start"] for w in words])
    sting = edit["branding"].get("sting")
    if edit["branding"].get("endCard") and sting:  # one fixed brand sting, chosen once
        sfx += place(N, [[edit["contentDuration"] + 0.1, sting, 0.6]], sfx_dir)
    if np.any(sfx):
        sfx *= min(1.0, (np.max(np.abs(dia)) * 0.5) / (np.max(np.abs(sfx)) + 1e-9))
    print(f"  sfx: {len(auto)} auto + {len(hand)} hand-placed ({style})")

    # 3. music: approved library track fitted on the beat (the synth bed is a draft placeholder only)
    m = edit["music"]
    music = np.zeros(N)
    need = edit["contentDuration"] + min(1.2, edit["branding"].get("endCard", 0))  # carry ~1 s into the end card
    if m["mode"] in ("library", "file") and not m.get("file"):
        print("  ! no music track chosen: edit.json music.file is empty (python toolkit/library.py list --approved)")
    if m["mode"] in ("library", "file") and m.get("file"):
        cands = [m["file"], os.path.join(ROOT, m["file"]), os.path.join(proj, m["file"])]
        src = next(c for c in cands if os.path.exists(c))
        music = fit_music(src, need, total, m.get("startAt"))
    elif m["mode"] == "generate":
        print("  ! music mode 'generate' is a DRAFT placeholder (synth bed). Use a library track for anything published.")
        music = A.music_bed(total, m.get("mood", "tech"))[:N]
        music[int(need * A.SR):] = 0
    if np.any(music):
        music = A.voice_pocket(music, depth=0.4)
        L_mus = lufs(music[: int(need * A.SR)])
        music *= 10 ** ((L_dia - L_mus) / 20) * duck_envelope(N, words, m.get("silences", [])) * 10 ** (m.get("trimDb", 0) / 20)

    A.write_wav(os.path.join(proj, "music.wav"), music, stereo=False)
    A.write_wav(os.path.join(proj, "sfx.wav"), sfx, stereo=False)
    mixed = dia + music + sfx
    f = int(0.6 * A.SR)
    e = int(total * A.SR)
    mixed[e - f: e] *= np.linspace(1, 0, f)
    pre = os.path.join(proj, "premix.wav")
    A.write_wav(pre, mixed[:e], peak=0.5)  # headroom: never clip before mastering
    master(proj, pre, TARGET_LUFS.get(edit["format"], -14.0))


def master(proj, pre, target):
    """Measured gain to the platform target, then a 4x-oversampled limiter at -1 dBTP (no level riding)."""
    def measure(path):
        err = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
        tail = err[err.rindex("Summary:"):]
        return float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1)), float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", tail).group(1))
    out = os.path.join(proj, "mix.wav")
    gain0 = gain = target - measure(pre)[0]
    for _ in range(3):  # limiting shaves loudness off: correct, but never push more than 3 dB extra into the limiter
        run(["ffmpeg", "-y", "-v", "error", "-i", pre, "-af",
             f"volume={gain:.2f}dB,aresample=192000,alimiter=limit=0.891:attack=3:release=60:level=disabled,aresample={A.SR}", out])
        I, tp = measure(out)
        if abs(I - target) <= 0.5 or gain - gain0 >= 3.0:
            break
        gain = min(gain + target - I, gain0 + 3.0)
    note = "" if abs(I - target) <= 0.5 else " (stopped short: more would squash the voice's peaks)"
    print(f"  mix.wav: {I:.1f} LUFS (target {target}), true peak {tp:.1f} dBTP{note}")


# ---------------------------------------------------------------- render / review
def cmd_render(args):
    proj = P(args.slug)
    if not os.path.exists(os.path.join(proj, "mix.wav")):
        cmd_sound(args)
    name = "preview.mp4" if args.preview else "final.mp4"
    out = os.path.join(proj, "out", name)
    shutil.copy(os.path.join(ROOT, "brand", "brand.json"), os.path.join(proj, "brand.json"))  # always render with the current brand
    cmd = [shutil.which("npx") or "npx", "remotion", "render", "src/index.ts", "Edit", out, f"--props={os.path.join(proj, 'edit.json')}", f"--public-dir={proj}", "--log=error", "--port=3917", "--concurrency=2"]  # own port: 3000 is often taken by other dev servers
    cmd += ["--scale=0.5", "--crf=26"] if args.preview else ["--crf=16"]
    run(cmd, cwd=os.path.join(ROOT, "engine"))
    print(f"  -> {out}")
    if not args.preview:
        small = os.path.join(proj, "out", "final_share.mp4")
        run(["ffmpeg", "-y", "-v", "error", "-i", out, "-c:v", "libx264", "-crf", "27", "-preset", "slow", "-c:a", "aac", "-b:a", "160k", small])


def cmd_review(args):
    proj = P(args.slug)
    src = next((os.path.join(proj, "out", f) for f in ("final.mp4", "preview.mp4") if os.path.exists(os.path.join(proj, "out", f))), None)
    if not src:
        sys.exit("render first")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src], capture_output=True, text=True).stdout)
    n = args.frames
    rdir = os.path.join(proj, "out", "review")
    os.makedirs(rdir, exist_ok=True)
    for i in range(n):
        t = dur * (i + 0.5) / n
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1", "-vf", "scale=360:-1", os.path.join(rdir, f"f{i:02d}.png")])
    cols = 6 if n >= 12 else n
    run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(rdir, "f%02d.png"), "-filter_complex", f"tile={cols}x{math.ceil(n / cols)}", "-frames:v", "1", os.path.join(proj, "out", "contact.png")])
    print(f"  -> {os.path.join(proj, 'out', 'contact.png')} ({n} frames over {dur:.1f}s)")


def cmd_conform(args):
    """Copy a b-roll / motion clip into the project as a Remotion-safe 30 fps file: assets/<name>.mp4."""
    proj = P(args.slug)
    os.makedirs(os.path.join(proj, "assets"), exist_ok=True)
    for f in args.files:
        out = os.path.join(proj, "assets", os.path.splitext(os.path.basename(f))[0] + ".mp4")
        run(["ffmpeg", "-y", "-v", "error", "-i", f, "-vf", f"fps={FPS}", "-an", *REMOTION_SAFE, out])
        print(f"  -> assets/{os.path.basename(out)}")


def cmd_all(args):
    for f in (cmd_prep, cmd_sound, cmd_render, cmd_review):
        f(args)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("new"); s.add_argument("slug"); s.add_argument("files", nargs="*"); s.add_argument("--format", choices=FORMATS)
    for name in ("prep", "all"):
        s = sub.add_parser(name); s.add_argument("slug")
        s.add_argument("--format", choices=FORMATS); s.add_argument("--model", default="small.en", help="faster-whisper model (small for non-English)")
        s.add_argument("--lang", default=None); s.add_argument("--gap", type=float, default=0.35, help="longest pause kept inside a segment (s)")
        s.add_argument("--keep-fillers", action="store_true"); s.add_argument("--no-cut", action="store_true")
        s.add_argument("--grade", choices=GRADES, default="natural"); s.add_argument("--force-plan", action="store_true")
        s.add_argument("--ranges", help='manual keep ranges in source seconds, "a-b,c-d" (overrides the auto cut)')
        s.add_argument("--reuse", action="store_true", help="skip normalise + transcribe, re-cut from the existing master")
        s.add_argument("--renormalise", action="store_true", help="with --reuse: rebuild master.mp4 (canvas/grade) but keep the transcript")
        s.add_argument("--preview", action="store_true"); s.add_argument("--frames", type=int, default=12)
    s = sub.add_parser("sound"); s.add_argument("slug")
    s = sub.add_parser("render"); s.add_argument("slug"); s.add_argument("--preview", action="store_true")
    s = sub.add_parser("review"); s.add_argument("slug"); s.add_argument("--frames", type=int, default=12)
    s = sub.add_parser("conform"); s.add_argument("slug"); s.add_argument("files", nargs="+")
    args = ap.parse_args()
    {"new": cmd_new, "prep": cmd_prep, "sound": cmd_sound, "render": cmd_render, "review": cmd_review, "conform": cmd_conform, "all": cmd_all}[args.cmd](args)


if __name__ == "__main__":
    main()
