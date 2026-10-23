import React from 'react';
import {AbsoluteFill, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Video} from '@remotion/media';
import {card, easeIn, easeOut, fonts, Kicker, useBrand} from './brand';
import type {Edit, Overlay} from './types';

const IN = 12; // ≈400 ms entrance (brand: 300–500 ms)
const OUT = 8;

// 4-phase cycle shared by every overlay: open → build → hold → exit
const usePhase = (dur: number) => {
  const f = useCurrentFrame();
  const open = easeOut(interpolate(f, [0, IN], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  const exit = easeIn(interpolate(f, [dur - OUT, dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  return {f, open, exit, v: open * (1 - exit)};
};

const Title: React.FC<{o: Extract<Overlay, {type: 'title'}>; dur: number; edit: Edit}> = ({o, dur, edit}) => {
  const {pal} = useBrand();
  const {open, exit, v} = usePhase(dur);
  const short = edit.format === 'short';
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: edit.width * 0.08}}>
      <div style={{...card(pal), padding: short ? '44px 52px' : '36px 56px', opacity: v, transform: `translateY(${(1 - open) * 60 - exit * 30}px)`, maxWidth: short ? '92%' : '70%'}}>
        {o.kicker && <Kicker size={short ? 28 : 22}>{o.kicker}</Kicker>}
        <div style={{fontFamily: fonts.ui, fontWeight: 700, fontSize: short ? 92 : 76, lineHeight: 1.02, letterSpacing: '-0.02em', color: pal.foreground, marginTop: o.kicker ? 14 : 0}}>
          {o.text}
        </div>
        <div style={{height: 6, width: `${open * 120}px`, background: pal.accent, borderRadius: 3, marginTop: 24}} />
      </div>
    </AbsoluteFill>
  );
};

const LowerThird: React.FC<{o: Extract<Overlay, {type: 'lowerThird'}>; dur: number; edit: Edit}> = ({o, dur, edit}) => {
  const {pal} = useBrand();
  const {open, exit, v} = usePhase(dur);
  const short = edit.format === 'short';
  return (
    <div
      style={{
        position: 'absolute',
        left: edit.width * 0.06,
        // y (0–1, top of the card) overrides the default spot: vlogs put the place tag up top, off the face
        top: o.y !== undefined ? edit.height * o.y : short ? edit.height * 0.56 : undefined,
        bottom: o.y !== undefined || short ? undefined : edit.height * 0.08,
        ...card(pal),
        padding: '20px 30px 20px 24px',
        display: 'flex',
        gap: 20,
        alignItems: 'center',
        opacity: v,
        transform: `translateX(${(1 - open) * -80 + exit * -40}px)`,
      }}
    >
      <div style={{width: 6, alignSelf: 'stretch', background: pal.accent, borderRadius: 3}} />
      <div>
        <div style={{fontFamily: fonts.ui, fontWeight: 700, fontSize: short ? 50 : 40, color: pal.foreground, letterSpacing: '-0.01em'}}>{o.name}</div>
        {o.role && <Kicker size={short ? 24 : 20}>{o.role}</Kicker>}
      </div>
    </div>
  );
};

const Emphasis: React.FC<{o: Extract<Overlay, {type: 'emphasis'}>; dur: number; edit: Edit}> = ({o, dur, edit}) => {
  const {pal} = useBrand();
  const {fps} = useVideoConfig();
  const {f, exit} = usePhase(dur);
  // key reveal: the one place a small overshoot is allowed
  const s = spring({frame: f, fps, config: {damping: 13, stiffness: 170, mass: 0.8}});
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: `${(o.y ?? 0.38) * 100}%`, textAlign: 'center', transform: `translateY(-50%) scale(${0.7 + 0.3 * s})`, opacity: Math.min(1, s * 1.5) * (1 - exit)}}>
      <span style={{fontFamily: fonts.ui, fontWeight: 700, fontSize: edit.format === 'short' ? 150 : 120, letterSpacing: '-0.03em', color: pal.onAccent, background: pal.accent, borderRadius: 28, padding: '6px 34px', boxShadow: '0 24px 60px rgba(0,0,0,0.45)'}}>
        {o.text}
      </span>
    </div>
  );
};

const Callout: React.FC<{o: Extract<Overlay, {type: 'callout'}>; dur: number}> = ({o, dur}) => {
  const {pal} = useBrand();
  const {open, v} = usePhase(dur);
  return (
    <div style={{position: 'absolute', left: `${o.x * 100}%`, top: `${o.y * 100}%`, transform: `translate(-50%, -100%) translateY(${(1 - open) * 20}px)`, opacity: v, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
      <div style={{...card(pal), background: pal.surfaceRaised, padding: '16px 28px', fontFamily: fonts.ui, fontWeight: 700, fontSize: 54, color: pal.foreground}}>{o.text}</div>
      <div style={{width: 3, height: 60 * open, background: pal.accent}} />
      <div style={{width: 18, height: 18, borderRadius: '50%', background: pal.accent, boxShadow: `0 0 0 ${8 * open}px rgba(34,211,238,0.25)`}} />
    </div>
  );
};

const Counter: React.FC<{o: Extract<Overlay, {type: 'counter'}>; dur: number; edit: Edit}> = ({o, dur, edit}) => {
  const {pal} = useBrand();
  const {f, open, v} = usePhase(dur);
  const n = interpolate(easeOut(interpolate(f, [0, Math.min(dur - OUT, 36)], [0, 1], {extrapolateRight: 'clamp'})), [0, 1], [o.from ?? 0, o.to]);
  const digits = Number.isInteger(o.to) ? 0 : 1;
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <div style={{...card(pal), padding: '30px 54px', textAlign: 'center', opacity: v, transform: `translateY(${(1 - open) * 40}px)`}}>
        <div style={{fontFamily: fonts.ui, fontWeight: 700, fontSize: edit.format === 'short' ? 170 : 140, color: pal.accent, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums'}}>
          {o.prefix ?? ''}
          {n.toLocaleString('en-US', {minimumFractionDigits: digits, maximumFractionDigits: digits})}
          {o.suffix ?? ''}
        </div>
        {o.label && <Kicker size={26}>{o.label}</Kicker>}
      </div>
    </AbsoluteFill>
  );
};

const ImageCard: React.FC<{o: Extract<Overlay, {type: 'image'}>; dur: number; edit: Edit}> = ({o, dur, edit}) => {
  const {pal} = useBrand();
  const {f, open, exit, v} = usePhase(dur);
  const kb = 1 + 0.06 * (f / dur);
  const w = edit.width * (edit.format === 'short' ? 0.84 : 0.56);
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <div style={{...card(pal), padding: 14, width: w, opacity: v, transform: `translateY(${(1 - open) * 70 - exit * 30}px) rotate(${(1 - open) * -2}deg)`}}>
        <div style={{overflow: 'hidden', borderRadius: 10}}>
          <Img src={staticFile(o.src)} style={{width: '100%', display: 'block', transform: `scale(${kb})`}} />
        </div>
        {o.caption && <div style={{padding: '14px 6px 2px'}}><Kicker size={22}>{o.caption}</Kicker></div>}
      </div>
    </AbsoluteFill>
  );
};

const Broll: React.FC<{o: Extract<Overlay, {type: 'broll'}>; dur: number; edit: Edit}> = ({o, dur, edit}) => {
  const {v} = usePhase(dur);
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{opacity: Math.min(1, v * 2)}}>
      <Video src={staticFile(o.src)} muted trimBefore={Math.round((o.trim ?? 0) * fps)} objectFit="cover" style={{width: '100%', height: '100%'}} />
    </AbsoluteFill>
  );
};

// Pre-rendered motion graphic (any MP4 you made elsewhere) full-frame or as a floating card
const Motion: React.FC<{o: Extract<Overlay, {type: 'motion'}>; dur: number; edit: Edit}> = ({o, dur, edit}) => {
  const {pal} = useBrand();
  const {open, v} = usePhase(dur);
  const vid = <Video src={staticFile(o.src)} muted objectFit="cover" style={{width: '100%', height: '100%'}} />;
  if (o.mode === 'card')
    return (
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{...card(pal), overflow: 'hidden', width: edit.width * 0.86, aspectRatio: '16 / 9', opacity: v, transform: `scale(${0.94 + 0.06 * open})`}}>{vid}</div>
      </AbsoluteFill>
    );
  return <AbsoluteFill style={{opacity: Math.min(1, v * 2)}}>{vid}</AbsoluteFill>;
};

export const Overlays: React.FC<{edit: Edit}> = ({edit}) => {
  const {fps} = useVideoConfig();
  // b-roll and motion sit under captions; cards and text above
  const order = (o: Overlay) => (o.type === 'broll' || o.type === 'motion' ? 0 : 1);
  return (
    <>
      {[...edit.overlays].sort((a, b) => order(a) - order(b)).map((o, i) => {
        const from = Math.round(o.start * fps);
        const dur = Math.max(1, Math.round((o.end - o.start) * fps));
        const C = {title: Title, lowerThird: LowerThird, emphasis: Emphasis, callout: Callout, counter: Counter, image: ImageCard, broll: Broll, motion: Motion}[o.type] as React.FC<{o: Overlay; dur: number; edit: Edit}>;
        return (
          <Sequence key={i} from={from} durationInFrames={dur} name={`${o.type} ${o.start}s`} layout="none">
            <AbsoluteFill>
              <C o={o} dur={dur} edit={edit} />
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </>
  );
};
