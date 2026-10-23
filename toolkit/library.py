"""Curated, licensed audio library for the edit pipeline (free sources first).

    python toolkit/library.py index music <mixkit path> [--pages 3]     # e.g. free-stock-music/tag/lifestyle/
    python toolkit/library.py index sfx <mixkit path> [--pages 1]       # e.g. free-sound-effects/whoosh/
    python toolkit/library.py fetch <music|sfx> <id> [<id> ...] [--mood chill] [--as whoosh]
    python toolkit/library.py analyse                                    # BPM, loudness, duration for new files
    python toolkit/library.py review                                     # assets/REVIEW.html: listen + note numbers to approve
    python toolkit/library.py approve <id> [<id> ...] [--reject]
    python toolkit/library.py list [--approved] [--mood chill]

Rule: only APPROVED files go into a published edit.
Your ears are the taste filter; every file carries its source and licence in a JSON sidecar next to it.
Sources wired in: Mixkit (Stock Music Free License / Sound Effects Free License: commercial use on web and
social platforms, no attribution; not for TV/radio broadcast, games, CDs/DVDs; music may not be remixed into a
music-only track or registered with a rights-management service). Checked on mixkit.co 2026-10-23.
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import audiolib as A  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB = {"music": os.path.join(ROOT, "assets", "music"), "sfx": os.path.join(ROOT, "assets", "sfx", "library")}
CATALOG = os.path.join(ROOT, "assets", "catalog")
LICENSE = {
    "music": {"name": "Mixkit Stock Music Free License", "url": "https://mixkit.co/license/#musicFree", "attribution": False,
              "ok": "commercial; any web/social platform incl. YouTube, TikTok, Instagram, Facebook",
              "not": "TV/radio broadcast, CDs/DVDs, video games, remix into music-only track, registering with Content ID / rights-management"},
    "sfx": {"name": "Mixkit Sound Effects Free License", "url": "https://mixkit.co/license/#sfxFree", "attribution": False,
            "ok": "commercial; web/social, podcasts, games, film, broadcast",
            "not": "redistributing the file on its own (stock, tools, templates), registering with rights-management"},
}
UA = {"User-Agent": "Mozilla/5.0 (KA video pipeline; personal use)"}


def get(url, tries=4):
    import time
    for i in range(tries):  # flaky connections ("forcibly closed by the remote host") are common: retry with backoff
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read()
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:48]


def iso_dur(s):
    m = re.match(r"PT(?:(\d+)M)?(?:(\d+)S)?", s or "")
    return (int(m.group(1) or 0) * 60 + int(m.group(2) or 0)) if m else None


def parse_music(page):
    items = []
    for blob in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
        try:
            d = json.loads(blob)
        except json.JSONDecodeError:
            continue
        for g in d.get("@graph", [d]):
            for it in g.get("itemListElement", []) if g.get("@type") == "ItemList" else []:
                m = re.search(r"/music/(\d+)/", it.get("url", ""))
                if m:
                    items.append({"id": m.group(1), "title": it.get("name"), "artist": it.get("byArtist"), "genre": it.get("genre"),
                                  "duration": iso_dur(it.get("duration")), "url": it["url"]})
    return items


def parse_sfx(page):
    items = []
    for chunk in page.split('data-audio-player-item-id-value="')[1:]:
        sid = chunk.split('"', 1)[0]
        prev = re.search(r'https://assets\.mixkit\.co/active_storage/sfx/\d+/\d+-preview\.mp3', page[max(0, page.find(chunk) - 800):page.find(chunk) + 50])
        title = re.search(r'item-grid-card__title[^>]*>\s*([^<]+?)\s*<', chunk)
        items.append({"id": sid, "title": html.unescape(title.group(1)) if title else f"sfx {sid}",
                      "url": prev.group(0) if prev else f"https://assets.mixkit.co/active_storage/sfx/{sid}/{sid}-preview.mp3"})
    return items


def cmd_index(a):
    os.makedirs(CATALOG, exist_ok=True)
    path = a.path.strip("/")
    found = {}
    for p in range(1, a.pages + 1):
        page = get(f"https://mixkit.co/{path}/" + (f"?page={p}" if p > 1 else "")).decode("utf-8", "ignore")
        for it in (parse_music if a.kind == "music" else parse_sfx)(page):
            found.setdefault(it["id"], {**it, "kind": a.kind, "from": path})
    out = os.path.join(CATALOG, f"mixkit_{a.kind}.json")
    cat = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else {}
    for k, v in found.items():
        cat.setdefault(k, v).setdefault("lists", [])
        if path not in cat[k]["lists"]:
            cat[k]["lists"].append(path)
    json.dump(cat, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{len(found)} items from {path} ({a.pages} page(s)); catalog now {len(cat)} -> {out}")
    for v in list(found.values())[:60]:
        print(f"  {v['id']:>6}  {v['title'][:44]:44}  {v.get('genre') or '':14} {v.get('duration') or '':>4}")


def sidecar_path(f):
    return os.path.splitext(f)[0] + ".json"


def cmd_fetch(a):
    cat = json.load(open(os.path.join(CATALOG, f"mixkit_{a.kind}.json"), encoding="utf-8"))
    os.makedirs(LIB[a.kind], exist_ok=True)
    for i in a.ids:
        it = cat.get(i)
        if not it:
            print(f"  ? {i} not in catalog (run index first)")
            continue
        f = os.path.join(LIB[a.kind], f"mixkit-{i}-{slugify(it['title'])}.mp3")
        if not os.path.exists(f):
            data = get(it["url"])
            open(f, "wb").write(data)
        meta = {"source": "Mixkit", "id": i, "title": it["title"], "artist": it.get("artist"), "genre": it.get("genre"),
                "page": f"https://mixkit.co/{it['lists'][0]}/", "file_url": it["url"], "license": LICENSE[a.kind],
                "moods": a.mood or [], "approved": None, "notes": ""}
        sc = sidecar_path(f)
        if os.path.exists(sc):
            old = json.load(open(sc, encoding="utf-8"))
            meta.update({k: old[k] for k in ("approved", "notes", "bpm", "lufs", "duration", "moods") if k in old and old[k]})
        json.dump(meta, open(sc, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"  + {os.path.relpath(f, ROOT)} ({os.path.getsize(f) // 1024} KB)")
        if a.alias:  # e.g. --as whoosh: the pipeline's load_sfx('whoosh') will use this real recording
            alias = os.path.join(ROOT, "assets", "sfx", a.alias + ".mp3")
            open(alias, "wb").write(open(f, "rb").read())
            json.dump({**meta, "alias_of": os.path.relpath(f, ROOT)}, open(sidecar_path(alias), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            print(f"    as assets/sfx/{a.alias}.mp3")


def all_files():
    for kind, d in LIB.items():
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if f.endswith(".mp3") or f.endswith(".wav"):
                    yield kind, os.path.join(d, f)


def cmd_analyse(a):
    import numpy as np
    for kind, f in all_files():
        sc = sidecar_path(f)
        meta = json.load(open(sc, encoding="utf-8")) if os.path.exists(sc) else {"source": "local", "approved": None}
        if meta.get("lufs") is not None and not a.force:
            continue
        x = A.read_audio(f)
        meta["duration"] = round(len(x) / A.SR, 2)
        try:
            import pyloudnorm
            meta["lufs"] = round(float(pyloudnorm.Meter(A.SR).integrated_loudness(x)), 1) if len(x) > A.SR * 0.5 else None
        except ImportError:
            meta["lufs"] = None
        if kind == "music":
            import librosa
            y = librosa.resample(x, orig_sr=A.SR, target_sr=22050)
            tempo, beats = librosa.beat.beat_track(y=y, sr=22050, units="time")
            meta["bpm"] = round(float(np.atleast_1d(tempo)[0]), 1)
            tail = x[-int(2 * A.SR):]
            meta["ending"] = "fade" if np.sqrt(np.mean(tail[-A.SR // 2:] ** 2)) < 0.15 * np.sqrt(np.mean(tail ** 2) + 1e-12) else "button/held"
        json.dump(meta, open(sc, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"  {os.path.basename(f)[:52]:52} {meta.get('duration')}s  {meta.get('lufs')} LUFS  {meta.get('bpm', '')} BPM {meta.get('ending', '')}")


def cmd_review(a):
    rows = []
    for kind, f in all_files():
        sc = sidecar_path(f)
        m = json.load(open(sc, encoding="utf-8")) if os.path.exists(sc) else {}
        st = {True: "approved", False: "rejected", None: "to review"}[m.get("approved")]
        rel = os.path.relpath(f, os.path.join(ROOT, "assets")).replace("\\", "/")
        rows.append(f"<tr class='{st.replace(' ', '-')}'><td><b>{m.get('id', '')}</b></td><td>{kind}</td><td>{html.escape(m.get('title', os.path.basename(f)))}"
                    f"<div class=s>{html.escape(', '.join(m.get('moods', [])))} {m.get('genre') or ''} · {m.get('bpm', '') or ''} BPM · {m.get('duration', '')}s · {m.get('ending', '')}</div></td>"
                    f"<td><audio controls preload=none src='{rel}'></audio></td><td>{st}</td></tr>")
    page = f"""<!doctype html><meta charset=utf-8><title>Sound library review</title>
<style>body{{font:15px system-ui,sans-serif;background:#0e0f13;color:#f2f2f0;margin:32px}}h1{{font-weight:700}}p{{color:#a6a9b0;max-width:760px}}
table{{border-collapse:collapse;width:100%}}td{{border-bottom:1px solid #2a2d34;padding:10px 12px;vertical-align:middle}}.s{{color:#a9afba;font-size:12px;margin-top:4px}}
tr.approved td:last-child{{color:#ffc83d}}tr.rejected{{opacity:.45}}audio{{height:32px}}</style>
<h1>Sound library review</h1>
<p>Listen on headphones, then on your phone speaker. Approve with <code>python toolkit/library.py approve &lt;ids&gt;</code> (or tell Claude the <b>numbers</b>), for example "approve 738, 580, 1489". Only approved files go into published edits.
Ask yourself: would I put this on my channel? Does it fit the feel of your videos, or does it sound like a stock-music ad?</p>
<table>{''.join(rows)}</table>"""
    out = os.path.join(ROOT, "assets", "REVIEW.html")
    open(out, "w", encoding="utf-8").write(page)
    print(f"{len(rows)} files -> {out}")


def cmd_approve(a):
    n = 0
    for kind, f in all_files():
        sc = sidecar_path(f)
        if not os.path.exists(sc):
            continue
        m = json.load(open(sc, encoding="utf-8"))
        if str(m.get("id")) in a.ids:
            m["approved"] = not a.reject
            json.dump(m, open(sc, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            n += 1
    print(f"{'rejected' if a.reject else 'approved'} {n} file(s)")


def cmd_list(a):
    for kind, f in all_files():
        sc = sidecar_path(f)
        m = json.load(open(sc, encoding="utf-8")) if os.path.exists(sc) else {}
        if a.approved and m.get("approved") is not True:
            continue
        if a.mood and a.mood not in m.get("moods", []):
            continue
        print(f"{kind:5} {str(m.get('approved')):5} {os.path.relpath(f, ROOT)}  {m.get('bpm', '')} BPM {m.get('moods', '')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("index"); s.add_argument("kind", choices=LIB); s.add_argument("path"); s.add_argument("--pages", type=int, default=1)
    s = sub.add_parser("fetch"); s.add_argument("kind", choices=LIB); s.add_argument("ids", nargs="+"); s.add_argument("--mood", action="append"); s.add_argument("--as", dest="alias")
    s = sub.add_parser("analyse"); s.add_argument("--force", action="store_true")
    sub.add_parser("review")
    s = sub.add_parser("approve"); s.add_argument("ids", nargs="+"); s.add_argument("--reject", action="store_true")
    s = sub.add_parser("list"); s.add_argument("--approved", action="store_true"); s.add_argument("--mood")
    a = ap.parse_args()
    {"index": cmd_index, "fetch": cmd_fetch, "analyse": cmd_analyse, "review": cmd_review, "approve": cmd_approve, "list": cmd_list}[a.cmd](a)


if __name__ == "__main__":
    main()
