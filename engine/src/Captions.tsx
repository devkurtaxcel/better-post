import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {easeOut, fonts, useBrand} from './brand';
import type {Edit, Word} from './types';

const clean = (t: string) => t.replace(/^[\s"'“]+|[\s"'”]+$/g, '');
const key = (t: string) => clean(t).toLowerCase().replace(/[.,!?;:]/g, '');

// Pages of up to maxWords, breaking after sentence punctuation
const paginate = (words: Word[], max: number) => {
  const pages: Word[][] = [];
  let cur: Word[] = [];
  for (const w of words) {
    cur.push(w);
    if (cur.length >= max || /[.!?,;:]$/.test(w.text)) {
      pages.push(cur);
      cur = [];
    }
  }
  if (cur.length) pages.push(cur);
  return pages;
};

// Word-by-word captions in the brand caption style: light text with a dark stroke,
// accent words on a pill in the brand accent colour (one key word per line reads best).
export const Captions: React.FC<{edit: Edit}> = ({edit}) => {
  const frame = useCurrentFrame();
  const {brand} = useBrand();
  const cs = brand.video.captions;
  const {captions: c, fps, width, format} = edit;
  const pages = React.useMemo(() => paginate(c.words, c.maxWords), [c.words, c.maxWords]);
  const accent = React.useMemo(() => new Set(c.accent.map(key)), [c.accent]);
  const t = frame / fps;
  const idx = pages.findIndex((p, i) => {
    const next = pages[i + 1];
    const until = Math.min(next ? next[0].start : Infinity, p[p.length - 1].end + 0.6);
    return t >= p[0].start && t < until;
  });
  if (idx < 0) return null;
  const page = pages[idx];
  const size = format === 'short' ? 92 : format === 'square' ? 70 : 60;

  return (
    <div
      style={{
        position: 'absolute',
        // yAt: [start, end, y] overrides, e.g. drop captions below a square-cropped landscape shot
        top: `${(c.yAt?.find(([a, b]) => page[0].start >= a && page[0].start < b)?.[2] ?? c.y) * 100}%`,
        left: width * 0.07,
        right: width * 0.07,
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        gap: `${size * 0.18}px ${size * 0.26}px`,
        transform: 'translateY(-50%)',
      }}
    >
      {page
        .filter((w) => w.start <= t + 0.02)
        .map((w, i) => {
          const f = frame - w.start * fps;
          const inP = easeOut(interpolate(f, [0, 7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
          const isAccent = accent.has(key(w.text));
          const text = clean(w.text);
          return (
            <span
              key={`${w.start}-${i}`}
              style={{
                fontFamily: fonts.ui,
                fontWeight: 700,
                fontSize: size,
                lineHeight: 1.08,
                letterSpacing: '-0.02em',
                color: isAccent ? cs.highlightText : cs.text,
                background: isAccent ? cs.highlight : 'transparent',
                borderRadius: size * 0.22,
                padding: isAccent ? `${size * 0.04}px ${size * 0.2}px` : 0,
                WebkitTextStroke: isAccent ? undefined : `${size * 0.1}px ${cs.stroke}`,
                paintOrder: 'stroke fill',
                textShadow: isAccent ? undefined : '0 4px 18px rgba(0,0,0,0.45)',
                opacity: inP,
                transform: `translateY(${(1 - inP) * size * 0.35}px) scale(${0.92 + 0.08 * inP})`,
                display: 'inline-block',
              }}
            >
              {text}
            </span>
          );
        })}
    </div>
  );
};
