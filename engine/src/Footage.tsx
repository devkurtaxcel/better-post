import React from 'react';
import {AbsoluteFill, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Video} from '@remotion/media';
import {easeIn, easeOut, useBrand} from './brand';
import type {Edit, Transition} from './types';

const HALF = 5; // transition half-length in frames (≈0.17 s each side of the join)

// Offset/scale/blur/opacity contributed by transitions around the current frame
const transitionFx = (frame: number, fps: number, list: Transition[], W: number) => {
  let x = 0, scale = 1, blur = 0, flash = 0, dip = 0;
  for (const t of list) {
    const at = t.at * fps;
    const d = frame - at;
    if (Math.abs(d) > HALF) continue;
    const dir = t.dir ?? 1;
    // out-going half accelerates in, incoming half settles out: it reads as one continuous move
    const k = d < 0 ? easeIn(1 + d / HALF) : 1 - easeOut(d / HALF);
    if (t.type === 'whip' || t.type === 'slide') {
      const dist = t.type === 'whip' ? 0.35 : 0.12;
      x += (d < 0 ? -1 : 1) * dir * k * W * dist * (d < 0 ? 1 : 1);
      if (t.type === 'whip') blur += k * 28;
    } else if (t.type === 'zoom') {
      scale *= 1 + 0.35 * k;
      blur += k * 14;
    } else if (t.type === 'flash') {
      flash = Math.max(flash, 1 - Math.abs(d) / HALF);
    } else if (t.type === 'dip') {
      dip = Math.max(dip, 1 - Math.abs(d) / HALF);
    }
  }
  return {x, scale, blur, flash, dip};
};

export const Footage: React.FC<{edit: Edit}> = ({edit}) => {
  const frame = useCurrentFrame();
  const {pal} = useBrand();
  const t = frame / edit.fps;
  const seg = edit.segments.find((s) => t >= s.start && t < s.end) ?? edit.segments[edit.segments.length - 1];
  const p = seg ? interpolate(t, [seg.start, seg.end], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
  const segScale = seg ? seg.zoom * (1 + (seg.push ?? 0) * p) : 1;
  const fx = transitionFx(frame, edit.fps, edit.transitions, edit.width);
  const fit = edit.reframe.mode === 'fit' ? 'contain' : edit.reframe.mode === 'cover' ? 'cover' : 'contain';
  const fX = seg?.focusX ?? edit.reframe.focusX;
  const fY = seg?.focusY ?? edit.reframe.focusY;
  const pos = `${fX * 100}% ${fY * 100}%`;
  const src = staticFile(edit.video);
  const style: React.CSSProperties = {width: '100%', height: '100%'};
  // <Video> centres a cover crop; shift it toward the focus point using the source size
  let shiftX = 0, shiftY = 0;
  if (fit === 'cover' && edit.source) {
    const s = Math.max(edit.width / edit.source.width, edit.height / edit.source.height);
    shiftX = (0.5 - fX) * (edit.source.width * s - edit.width);
    shiftY = (0.5 - fY) * (edit.source.height * s - edit.height);
  }

  return (
    <AbsoluteFill style={{backgroundColor: pal.background}}>
      {fit === 'contain' && (
        // blur-fill behind letterboxed footage so a vertical/horizontal mismatch never shows bars
        <AbsoluteFill style={{filter: 'blur(40px) brightness(0.45)', transform: 'scale(1.2)'}}>
          <Video src={src} muted objectFit="cover" style={style} />
        </AbsoluteFill>
      )}
      <AbsoluteFill
        style={{
          transform: `translate(${fx.x}px, 0px) scale(${segScale * fx.scale})`,
          transformOrigin: pos,
          filter: fx.blur > 0.5 ? `blur(${fx.blur}px)` : undefined,
        }}
      >
        <Video src={src} muted objectFit={fit} style={{...style, transform: `translate(${shiftX}px, ${shiftY}px)`}} />
      </AbsoluteFill>
      {fx.flash > 0 && <AbsoluteFill style={{background: pal.foreground, opacity: fx.flash * 0.85}} />}
      {fx.dip > 0 && <AbsoluteFill style={{background: pal.background, opacity: fx.dip}} />}
    </AbsoluteFill>
  );
};
