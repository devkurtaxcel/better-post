# better-post

**Turn raw phone clips into a finished, captioned, music-mixed vertical video, edited by AI on your own computer.**
A local, Claude Code-driven finishing pipeline: phone footage in, a mastered, captioned, watermarked Short out, and it remembers how you like them. No CapCut timeline, and your video files never leave your machine.

Created by **Kurt Axcel**: [Axcel's POV](https://www.facebook.com/POVniAxcel) · [SIDEQUEST](https://www.facebook.com/SIDEQUESTniAxcel/) · TikTok [@povniaxcel](https://www.tiktok.com/@povniaxcel) · [all links](https://links.kurtaxcel.com).
If this helps you, credit `@povniaxcel` in your post.

## Why I made this
I built better-post to solve my own problem. I shoot vlogs on my phone, and every one meant hours of editing: iPhone footage that turned grey and washed out after upload, captions typed by hand, music that drowned out my voice or didn't fit, and a variety of sound effects. I wanted to hand over my clips and get back something I'd actually post, in my own style.

This is the setup that worked for me. I'm sharing it in case you have the same problem. It's not a product or a service, just a tool I use, given away as-is. Take what helps.

**Status: active development, on my own schedule.** I update it when I have time and when I need something for my own videos. There's no roadmap, no promised updates and no guaranteed support, so please don't wait on me for features or fixes. Treat it as a **reference and a starting point**: fork it, take it apart, and build your own version with your own ideas.

---

## What it does
Drop your clips in a folder, then run one command (or just ask [Claude Code](https://claude.com/claude-code) to "edit this"):

- **Fixes iPhone footage automatically:** HDR → normal colour (no more grey, washed-out uploads), rotation, mixed frame rates, landscape clips placed cleanly in a 9:16 frame.
- **Transcribes your voice locally** (English and Taglish/Filipino work), then **cuts dead air and "um/uh"** on exact frames, with smooth audio joins.
- **Word-by-word captions** in your brand style, with one highlighted key word per line.
- **Clean cuts and subtle punch-ins** so jump cuts look intentional, a cinematic colour grade and light film grain.
- **Music that sounds produced:** a free, commercially licensed track fitted to your video's length and cut on the beat, automatically lowered under your voice, mastered to the right loudness for TikTok/Reels/Shorts or YouTube.
- **A moving watermark** with your handle (harder to crop off than a corner logo) and a branded end card.
- **A review sheet** of frames from the render, so you (or the AI) can check it before posting.

The video work runs **locally**: ffmpeg, faster-whisper, numpy, librosa and [Remotion](https://www.remotion.dev). No extra API keys or paid credits.
**Privacy note:** your video files stay on your computer, but Claude Code is an AI service. The text it works with (transcripts, captions, your prompts) and any frames it looks at while reviewing are sent to Anthropic. Don't use it on footage you can't share with an AI provider.

## Why better-post
Plenty of open-source AI editors cut and caption. better-post is about the **finishing** that makes a phone video postable:
- **Phone-footage ready:** iPhone HDR tone-mapped to normal colour, rotation and variable frame rates fixed, landscape clips placed cleanly in 9:16.
- **Music you're allowed to post:** free, commercially licensed tracks, each saved with its licence file, approved by ear by you.
- **Music that fits:** trimmed to your video's length on a beat, with a clean ending instead of a hard cut.
- **Your voice stays on top:** music ducks under every word, using the transcript's word timings.
- **Platform-ready loudness:** mastered to about −12 LUFS for Shorts/Reels/TikTok or −14 for YouTube, peaks kept under −1 dB.
- **Harder to steal:** a moving watermark with your handle, not a corner logo someone can crop.
- **Taglish-friendly:** multilingual transcription, so Filipino and English mixed in one sentence work.
- **It learns your taste:** feedback becomes rules in `brand/TASTE.md` and `brand/LESSONS.md`, so the next edit lands closer.

**When to use something else:** for long talking-head videos or a GUI timeline, a general-purpose editor or a heavier agent editor may suit you better. better-post is built for short phone vlogs.

## Requirements
- **A Claude Code subscription** for the AI editing workflow (a paid Claude plan such as Pro or Max, or Anthropic API billing). See [claude.com/claude-code](https://claude.com/claude-code). Without it you can still run every step yourself with the commands below; Claude Code is what turns it into "just tell it what you want".
- Windows, macOS or Linux
- **Python 3.11** (with [uv](https://docs.astral.sh/uv/) recommended)
- **Node.js 20+**
- **ffmpeg** with the `zscale` filter (most full builds have it, e.g. `winget install Gyan.FFmpeg` / `brew install ffmpeg`)
- About 3 GB free disk space; 8 GB RAM recommended

## Setup (one time)
```bash
git clone https://github.com/devkurtaxcel/better-post
cd better-post
uv venv .venv --python 3.11
uv pip install --python .venv -r requirements.txt
cd engine && npm install && cd ..
```
Then set **your** brand in `brand/brand.json` (name, mark, tagline, handles, accent colour).

## Edit your first video
1. Put your clips in `contents/MY VLOG/` and name them in order: `START`, `2`, `3`, … `ENDING` (see [contents/README.md](contents/README.md)).
2. Get a music track (free, licensed for social media):
   ```bash
   .venv/Scripts/python.exe toolkit/library.py index music free-stock-music/mood/relaxed --pages 1
   .venv/Scripts/python.exe toolkit/library.py fetch music <id> --mood chill
   .venv/Scripts/python.exe toolkit/library.py approve <id>
   ```
   (macOS/Linux: use `.venv/bin/python`.)
3. Run the pipeline:
   ```bash
   .venv/Scripts/python.exe toolkit/ve.py new myvlog "contents/MY VLOG" --format short
   .venv/Scripts/python.exe toolkit/ve.py all myvlog --model small --grade cinematic
   ```
4. Open `projects/myvlog/out/contact.png` to check it, and post `projects/myvlog/out/final_share.mp4`.

### With Claude Code (the fun way)
*Requires a Claude Code subscription (see Requirements).* Open this folder in Claude Code and say:
> Edit `contents/MY VLOG` for TikTok. It's about ___.

Claude follows [PLAYBOOK.md](PLAYBOOK.md): it reads your taste file, cuts the story, writes the captions, mixes, renders, reviews the frames, and asks you only what it can't figure out. Every time you give feedback, it writes it into `brand/TASTE.md`, so your next video comes out closer to how you like it.

## Make it yours
| File | What to change |
|---|---|
| `brand/brand.json` | Colours, mark, tagline, handles |
| `brand/TASTE.md` | Your likes and dislikes. The AI reads this before every edit |
| `brand/LESSONS.md` | Known pitfalls and their fixes (add your own) |
| `projects/<name>/edit.json` | Fine-tune one video: captions, highlighted words, titles, music level |

## Music and licences
- `toolkit/library.py` pulls from **Mixkit** (free; commercial use on web and social platforms; no attribution required; not for TV/radio broadcast; don't re-upload the files on their own). Always re-check the source's licence before you publish.
- Approve tracks by ear (`assets/REVIEW.html`): you're the taste filter.
- Remotion has its own licence: free for individuals and small teams; companies above its threshold need a company licence. See [remotion.dev/license](https://www.remotion.dev/license).

## Responsible use
Check every video for private information before posting: addresses, house numbers, plates, IDs, money, screens, and other people's details. Blur or cut what shouldn't be public, and ask people before you name them.

## Credits and licence
Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). The NOTICE file (credit to the creator) must be kept in copies and forks.
Made by [Kurt Axcel](https://links.kurtaxcel.com) · building in public · [kurtaxcel.com](https://kurtaxcel.com) · [blog](https://blog.kurtaxcel.com/) · [YouTube](https://www.youtube.com/@cloudwithkurtaxcel) · [Instagram](https://www.instagram.com/povniaxcel/) · [Threads](https://www.threads.com/@povniaxcel) · [X](https://x.com/POVniAxcel).
Questions? Comment on the post where you found this. 🙌
