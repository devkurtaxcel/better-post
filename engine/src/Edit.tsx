import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {BrandProvider, easeOut, fonts, Kicker, Mark, useBrand} from './brand';
import {Footage} from './Footage';
import {Captions} from './Captions';
import {Overlays} from './Overlays';
import type {Edit as EditT} from './types';

const Grain: React.FC<{amount: number}> = ({amount}) => {
  const frame = useCurrentFrame();
  const seed = Math.floor(frame / 2.5) % 8; // 12 fps texture boil
  if (amount <= 0) return null;
  return (
    <svg width="100%" height="100%" style={{position: 'absolute', inset: 0, pointerEvents: 'none', opacity: amount, mixBlendMode: 'overlay'}}>
      <filter id={`g${seed}`}>
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={seed} />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter={`url(#g${seed})`} />
    </svg>
  );
};

const KickerBadge: React.FC<{edit: EditT}> = ({edit}) => {
  const frame = useCurrentFrame();
  const {brand, pal} = useBrand();
  const v = easeOut(interpolate(frame, [6, 18, 75, 87], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  const top = edit.format === 'short' ? edit.height * 0.075 : edit.height * 0.06;
  return (
    <div style={{position: 'absolute', top, left: edit.width * 0.06, display: 'flex', alignItems: 'center', gap: 16, opacity: v, transform: `translateY(${(1 - v) * -12}px)`}}>
      <Mark size={edit.format === 'short' ? 40 : 32} />
      <div style={{width: 1, height: 28, background: pal.border}} />
      <Kicker size={edit.format === 'short' ? 22 : 18} color={pal.foreground}>{brand.tagline}</Kicker>
    </div>
  );
};

const Progress: React.FC<{edit: EditT}> = ({edit}) => {
  const frame = useCurrentFrame();
  const {pal} = useBrand();
  const p = Math.min(1, frame / (edit.contentDuration * edit.fps));
  return (
    <div style={{position: 'absolute', top: 0, left: 0, right: 0, height: 8, background: 'rgba(255,255,255,0.08)'}}>
      <div style={{height: '100%', width: `${p * 100}%`, background: pal.accent}} />
    </div>
  );
};

const EndCard: React.FC<{edit: EditT}> = ({edit}) => {
  const frame = useCurrentFrame();
  const {brand, pal} = useBrand();
  const v = easeOut(interpolate(frame, [0, 14], [0, 1], {extrapolateRight: 'clamp'}));
  const line = easeOut(interpolate(frame, [8, 26], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  const short = edit.format === 'short';
  return (
    <AbsoluteFill style={{background: pal.background, justifyContent: 'center', alignItems: 'center', opacity: interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'})}}>
      <div style={{transform: `translateY(${(1 - v) * 30}px)`, opacity: v, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 26}}>
        <Mark size={short ? 170 : 140} />
        <div style={{height: 4, width: 220 * line, background: pal.accent, borderRadius: 2}} />
        <Kicker size={short ? 30 : 26} color={pal.foreground}>{brand.tagline}</Kicker>
        <div style={{fontFamily: fonts.ui, fontWeight: 500, fontSize: short ? 40 : 34, color: pal.muted, opacity: line}}>{edit.branding.handle}</div>
      </div>
    </AbsoluteFill>
  );
};

// Anti-reupload watermark: small, subtle, and it MOVES between safe spots every 6 s (a fixed corner is easy to crop or
// cover). Positions avoid the caption band (~0.72) and top titles (0.07-0.15). Set branding.watermark to your handle,
// or null to turn it off.
const SPOTS: [number, number, 'left' | 'right'][] = [[0.07, 0.6, 'left'], [0.93, 0.42, 'right'], [0.07, 0.26, 'left'], [0.93, 0.6, 'right']];
const Watermark: React.FC<{edit: EditT; text: string}> = ({edit, text}) => {
  const frame = useCurrentFrame();
  const {pal} = useBrand();
  const per = 6 * edit.fps;
  const i = Math.floor(frame / per) % SPOTS.length;
  const f = frame % per;
  const o = interpolate(f, [0, 15, per - 15, per], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const [x, y, side] = SPOTS[i];
  const size = edit.format === 'short' ? 34 : 28;
  return (
    <div style={{position: 'absolute', top: edit.height * y, left: side === 'left' ? edit.width * x : undefined, right: side === 'right' ? edit.width * (1 - x) : undefined,
      fontFamily: fonts.ui, fontWeight: 500, fontSize: size, letterSpacing: '0.01em', color: pal.foreground, opacity: 0.32 * o,
      textShadow: '0 1px 8px rgba(0,0,0,0.55)', pointerEvents: 'none', whiteSpace: 'nowrap'}}>
      {text}
    </div>
  );
};

const Inner: React.FC<{edit: EditT}> = ({edit}) => {
  const {pal} = useBrand();
  const content = Math.round(edit.contentDuration * edit.fps);
  return (
    // brand background under everything: the cut into the end card dips to brand dark, never pure black
    <AbsoluteFill style={{backgroundColor: pal.background}}>
      <Sequence durationInFrames={content} name="footage">
        <Footage edit={edit} />
      </Sequence>
      <Sequence durationInFrames={content} name="overlays">
        <Overlays edit={edit} />
      </Sequence>
      {edit.captions.enabled && (
        <Sequence durationInFrames={content} name="captions">
          <Captions edit={edit} />
        </Sequence>
      )}
      {edit.branding.kicker && (
        <Sequence from={Math.round((edit.branding.kickerAt ?? 0) * edit.fps)} durationInFrames={100} name="kicker">
          <KickerBadge edit={edit} />
        </Sequence>
      )}
      {edit.branding.progressBar && (
        <Sequence durationInFrames={content} name="progress">
          <Progress edit={edit} />
        </Sequence>
      )}
      {edit.branding.watermark && (
        <Sequence durationInFrames={content} name="watermark">
          <Watermark edit={edit} text={edit.branding.watermark} />
        </Sequence>
      )}
      {edit.branding.endCard > 0 && (
        <Sequence from={content} name="end card">
          <EndCard edit={edit} />
        </Sequence>
      )}
      <Grain amount={edit.grain} />
      <Audio src={staticFile(edit.audio)} />
    </AbsoluteFill>
  );
};

export const Edit: React.FC<EditT> = (edit) => (
  <BrandProvider theme={edit.theme}>
    <Inner edit={edit} />
  </BrandProvider>
);
