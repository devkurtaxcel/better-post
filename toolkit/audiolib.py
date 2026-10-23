"""Audio synthesis for the edit pipeline: SFX library, music beds, reverb. numpy only, no credits.

Every SFX is 3 layers (sub / mid texture / high detail) and returns (samples, peak_offset_seconds)
so it can be placed with its transient exactly on the cue frame.
A real file in assets/sfx/<name>.wav (or .mp3) overrides the synthesized one.
"""
import os
import subprocess
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


# ---------- helpers ----------
def T(d):
    return np.arange(int(d * SR)) / SR


def fft_filter(x, gain_fn):
    n = 1 << int(np.ceil(np.log2(len(x) + 1)))
    X = np.fft.rfft(x, n)
    f = np.fft.rfftfreq(n, 1 / SR)
    return np.fft.irfft(X * gain_fn(f), n)[: len(x)]


def band(x, lo, hi):
    return fft_filter(x, lambda f: ((f >= lo) & (f <= hi)).astype(float))


def noise(d):
    return rng.standard_normal(int(d * SR))


def decay(d, tau):
    return np.exp(-T(d) / tau)


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def sweep(f0, f1, d, tau=None):
    t = T(d)
    f = f0 * (f1 / f0) ** (t / d)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return s * (np.exp(-t / tau) if tau else 1)


def fit(*layers):
    out = np.zeros(max(len(l) for l in layers))
    for l in layers:
        out[: len(l)] += l
    return out


def impulse_response(d, tau, bright=6000):
    ir = noise(d) * decay(d, tau)
    ir = fft_filter(ir, lambda f: 1 / (1 + (f / bright) ** 2))
    ir[0] = 0
    return norm(ir, 0.3)


def convolve(x, ir):
    n = 1 << int(np.ceil(np.log2(len(x) + len(ir))))
    return np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[: len(x)]


def read_audio(path, mono=True):
    """Decode any audio/video file to float32 mono 48k via ffmpeg."""
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1" if mono else "2", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768


def write_wav(path, x, peak=None, stereo=True):
    if peak is not None:
        x = norm(x, peak)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    if stereo:
        pcm = np.repeat(pcm[:, None], 2, axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2 if stereo else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------- SFX ----------
def whoosh():
    d = 0.7
    t = T(d)
    bell = np.sin(np.pi * t / d) ** 3
    return norm(fit(band(noise(d), 60, 300) * bell * 1.2, band(noise(d), 400, 3000) * bell * 0.6, band(noise(d), 5000, 11000) * np.sin(np.pi * t / d) ** 8 * 0.4)), 0.35


def swish():  # short, light: text slides, lower thirds
    d = 0.35
    t = T(d)
    bell = np.sin(np.pi * t / d) ** 4
    return norm(fit(band(noise(d), 1500, 9000) * bell, band(noise(d), 200, 800) * bell * 0.4)), 0.17


def pop():
    return norm(fit(sweep(220, 110, 0.08, 0.03) * 0.8, sweep(1100, 650, 0.07, 0.02), band(noise(0.006), 3000, 12000) * 0.6)), 0.0


def tick():
    body = np.sin(2 * np.pi * 2400 * T(0.03)) * decay(0.03, 0.006)
    return norm(fit(body, band(noise(0.004), 4000, 14000) * 0.7, sweep(400, 300, 0.03, 0.01) * 0.4)), 0.0


def click():  # keyboard/spacebar-ish UI click
    d = 0.05
    return norm(fit(band(noise(d), 2000, 8000) * decay(d, 0.006), sweep(180, 120, d, 0.012) * 0.6, band(noise(0.003), 8000, 15000) * 0.5)), 0.0


def pen():
    d = 0.45
    t = T(d)
    am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 17 * t + rng.random() * 3))
    return norm(fit(band(noise(d), 1800, 7000) * am * np.sin(np.pi * t / d), band(noise(d), 300, 1200) * np.sin(np.pi * t / d) * 0.4)), 0.0


def tape():
    d = 0.4
    t = T(d)
    rough = band(noise(d), 800, 5000) * (0.6 + 0.4 * np.sin(2 * np.pi * 40 * t)) * np.minimum(1, t / 0.05) * decay(d, 0.15)
    return norm(fit(rough, band(noise(0.05), 3000, 10000) * 0.5, band(noise(d), 100, 400) * decay(d, 0.08) * 0.5)), 0.02


def stamp():
    return norm(fit(sweep(110, 45, 0.35, 0.09), band(noise(0.08), 150, 1500) * decay(0.08, 0.02) * 0.8, band(noise(0.02), 3000, 10000) * decay(0.02, 0.004) * 0.4)), 0.0


def impact():
    return norm(fit(sweep(70, 32, 1.6, 0.45) * 1.2, band(noise(0.5), 90, 900) * decay(0.5, 0.09) * 0.7, band(noise(0.06), 2500, 12000) * decay(0.06, 0.012) * 0.5)), 0.0


def slap():
    return norm(fit(band(noise(0.12), 500, 6000) * decay(0.12, 0.025), sweep(140, 70, 0.2, 0.05) * 0.8, band(noise(0.25), 6000, 12000) * decay(0.25, 0.05) * 0.3)), 0.0


def riser():
    d = 1.3
    t = T(d)
    rise = (t / d) ** 3
    rev = impact()[0][: int(d * SR)][::-1] * 0.6
    return norm(fit(band(noise(d), 2000, 9000) * rise, sweep(180, 720, d) * rise * 0.5, np.pad(rev, (int(d * SR) - len(rev), 0)))), d


def stop():
    return norm(fit(sweep(300, 40, 0.5, 0.18), band(noise(0.1), 80, 600) * decay(0.1, 0.03), band(noise(0.01), 3000, 9000) * 0.3)), 0.0


def glitch_free_shimmer():  # brand sting: airy cyan "shine" for logo / end card
    d = 1.6
    t = T(d)
    tones = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * k) for f, k in [(1318.5, 2.2), (1975.5, 2.8), (2637, 3.5), (659.3, 1.6)])
    air = band(noise(d), 6000, 14000) * np.exp(-t * 3) * 0.3
    sub = sweep(90, 55, 0.6, 0.25) * 0.5
    return norm(fit(tones * np.minimum(1, t / 0.01), air, sub)), 0.0


SYNTH = dict(whoosh=whoosh, swish=swish, pop=pop, tick=tick, click=click, pen=pen, tape=tape, stamp=stamp,
             impact=impact, slap=slap, riser=riser, stop=stop, shimmer=glitch_free_shimmer)


def load_sfx(name, sfx_dir):
    """User file in assets/sfx wins over the synthesized version. Peak offset 0 for files (riser: end)."""
    for ext in (".wav", ".mp3", ".ogg", ".flac"):
        p = os.path.join(sfx_dir, name + ext)
        if os.path.exists(p):
            x = read_audio(p)
            if name.startswith("riser"):
                return norm(x), len(x) / SR
            env = np.convolve(np.abs(x), np.ones(480) / 480, mode="same")  # real files: align the loudest moment to the cue
            return norm(x), float(np.argmax(env)) / SR
    if name not in SYNTH:
        raise KeyError(f"unknown sfx '{name}'. Known: {sorted(SYNTH)} or add assets/sfx/{name}.wav")
    return SYNTH[name]()


# ---------- music ----------
hz = lambda n: 440 * 2 ** ((n - 69) / 12)

MOODS = {
    # brand default: modern, minimal, curious. A minor pulse, airy plucks
    "tech": dict(bpm=104, root=45, pattern=[57, 64, 60, 64, 57, 64, 62, 64], bass=[33, 33, 29, 31], hats=True, drone=0.10),
    "tense": dict(bpm=100, root=38, pattern=[50, 57, 53, 57, 50, 57, 55, 57], bass=[26, 26, 22, 24], hats=False, drone=0.14),
    "upbeat": dict(bpm=120, root=48, pattern=[60, 67, 64, 67, 62, 67, 65, 67], bass=[36, 36, 41, 43], hats=True, drone=0.06),
    "chill": dict(bpm=84, root=43, pattern=[55, 62, 59, 62, 57, 64, 60, 64], bass=[31, 31, 28, 26], hats=False, drone=0.08),
}


def pluck(note, d=0.55, bright=5):
    t = T(d)
    s = sum(np.sin(2 * np.pi * hz(note) * h * t) / h ** 1.5 for h in range(1, bright + 1))
    return s * np.exp(-t * 7) * np.minimum(1, t / 0.004)


def rhodes(notes, d, vel=1.0):
    """Electric-piano-ish chord: sine + bell partial, soft attack, slow decay, gentle tremolo."""
    t = T(d)
    env = np.minimum(1, t / 0.015) * np.exp(-t * 0.9)
    trem = 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)
    s = sum(np.sin(2 * np.pi * hz(n) * t) + 0.25 * np.sin(2 * np.pi * hz(n) * 2 * t) * np.exp(-t * 4) + 0.12 * np.sin(2 * np.pi * hz(n) * 3.98 * t) * np.exp(-t * 7) for n in notes)
    return s * env * trem * vel / len(notes)


def vlog_bed(duration):
    """'vlog' mood: warm cinematic lifestyle bed. Fmaj7 – Am7 – Dm9 – Bbmaj7 at 88 BPM, soft kick/rim/brush, low-passed."""
    bpm = 88
    beat = 60 / bpm
    bar = beat * 4
    N = int(duration * SR) + SR
    out = np.zeros(N)

    def put(x, at, g=1.0):
        i = int(at * SR)
        if 0 <= i < N:
            out[i: i + len(x)] += x[: N - i] * g

    chords = [[53, 57, 60, 64], [57, 60, 64, 67], [50, 53, 57, 60, 64], [46, 50, 53, 57]]
    roots = [41, 45, 38, 46]
    kick = sweep(95, 45, 0.35, 0.09)
    rim = band(noise(0.06), 1200, 5000) * decay(0.06, 0.012)
    brush = band(noise(0.12), 5000, 11000) * decay(0.12, 0.035)
    t0, k = 0.0, 0
    while t0 < duration:
        c = k % 4
        put(rhodes(chords[c], bar + 1.0), t0, 0.55)
        bt = T(bar)
        put(np.sin(2 * np.pi * hz(roots[c] - 12) * bt) * np.minimum(1, bt / 0.03) * np.exp(-bt * 0.5), t0, 0.35)
        for b in range(4):
            tb = t0 + b * beat
            if b in (0, 2):
                put(kick, tb, 0.55)
            else:
                put(rim, tb, 0.18)
            put(brush, tb + beat / 2, 0.10)
        put(pluck(chords[c][-1] + 12, 0.8, 3), t0 + beat * 2.5, 0.10)  # small top-line sparkle
        t0 += bar
        k += 1
    out = fft_filter(out, lambda f: 1 / (1 + (f / 7000) ** 4))  # lo-fi warmth
    return out


def music_bed(duration, mood="tech", hats_from=0.0):
    if mood == "vlog":
        return vlog_bed(duration)
    m = MOODS[mood]
    N = int(duration * SR) + SR
    out = np.zeros(N)

    def put(x, at):
        i = int(at * SR)
        if 0 <= i < N:
            out[i: i + len(x)] += x[: N - i]

    beat = 60 / m["bpm"]
    kick = sweep(120, 42, 0.4, 0.11)
    hat = band(noise(0.05), 7000, 14000) * decay(0.05, 0.012)
    t0, k = 0.0, 0
    while t0 < duration:
        put(kick * 0.9, t0)
        if m["hats"] and t0 >= hats_from:
            put(hat * 0.25, t0 + beat / 2)
        put(pluck(m["pattern"][k % 8]) * 0.35, t0)
        put(pluck(m["pattern"][(k + 1) % 8] + 12, 0.4) * 0.12, t0 + beat / 2)
        if k % 4 == 0:
            bt = T(beat * 4)
            put(np.sin(2 * np.pi * hz(m["bass"][(k // 4) % 4]) * bt) * np.minimum(1, bt / 0.05) * np.exp(-bt * 0.6) * 0.45, t0)
        t0 += beat
        k += 1
    td = np.arange(N) / SR
    out += (np.sin(2 * np.pi * hz(m["root"] - 7) * td) + 0.5 * np.sin(2 * np.pi * hz(m["root"]) * td * 1.002)) * m["drone"] * np.minimum(1, td / 4)
    return out


def voice_pocket(x, depth=0.55):
    """Bell cut centred ~1.7 kHz (1–3 kHz) so the voice sits on top of the music. depth 0.4 ≈ -4.4 dB, 0.55 ≈ -7 dB."""
    return fft_filter(x, lambda f: 1 - depth * np.exp(-((np.log2(np.maximum(f, 1) / 1730)) ** 2) / 0.35))


def sting(note_root=33):
    st = T(4)
    low = (np.sin(2 * np.pi * hz(note_root) * st) + 0.6 * np.sin(2 * np.pi * hz(note_root + 12) * st)) * np.exp(-st * 0.9) * 0.5
    return fit(low, pluck(note_root + 36, 3) * 0.4)
