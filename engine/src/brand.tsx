import React from 'react';
import {continueRender, delayRender, Easing, staticFile} from 'remotion';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';
import {loadFont as loadMono} from '@remotion/google-fonts/JetBrainsMono';
import type {Brand, Palette} from './types';

// Fonts: Inter for titles/captions, JetBrains Mono for small kicker labels. Swap here to change your look.
export const fonts = {
  ui: loadInter('normal', {weights: ['500', '700'], subsets: ['latin']}).fontFamily,
  mono: loadMono('normal', {weights: ['400', '700'], subsets: ['latin']}).fontFamily,
};

// brand.video.motion: calm, weighted ease-out entrances
export const easeOut = Easing.bezier(0.22, 1, 0.36, 1);
export const easeIn = Easing.bezier(0.64, 0, 0.78, 0);

type Ctx = {brand: Brand; pal: Palette};
const BrandCtx = React.createContext<Ctx | null>(null);

// brand.json is copied into the project folder (the render's public dir) by ve.py
export const BrandProvider: React.FC<{theme: 'dark' | 'light'; children: React.ReactNode}> = ({theme, children}) => {
  const [brand, setBrand] = React.useState<Brand | null>(null);
  const [handle] = React.useState(() => delayRender('brand.json'));
  React.useEffect(() => {
    fetch(staticFile('brand.json'))
      .then((r) => r.json())
      .then((b: Brand) => {
        setBrand(b);
        continueRender(handle);
      });
  }, [handle]);
  if (!brand) return null;
  return <BrandCtx.Provider value={{brand, pal: brand[theme]}}>{children}</BrandCtx.Provider>;
};

export const useBrand = () => {
  const c = React.useContext(BrandCtx);
  if (!c) throw new Error('useBrand outside BrandProvider');
  return c;
};

// Your mark (brand.json "mark"): bold text with a short accent bar underneath
export const Mark: React.FC<{size: number; color?: string}> = ({size, color}) => {
  const {brand, pal} = useBrand();
  return (
    <div style={{display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: size * 0.12}}>
      <div style={{fontFamily: fonts.ui, fontWeight: 700, fontSize: size, lineHeight: 1, color: color ?? pal.foreground, letterSpacing: '-0.02em'}}>{brand.mark}</div>
      <div style={{width: size * 0.9, height: Math.max(2, size * 0.06), background: pal.accent, borderRadius: 2}} />
    </div>
  );
};

export const Kicker: React.FC<{children: React.ReactNode; color?: string; size?: number}> = ({children, color, size = 26}) => {
  const {pal} = useBrand();
  return (
    <div style={{fontFamily: fonts.mono, fontSize: size, letterSpacing: '0.24em', textTransform: 'uppercase', color: color ?? pal.muted}}>{children}</div>
  );
};

export const card = (pal: Palette): React.CSSProperties => ({
  background: pal.surface,
  border: `1px solid ${pal.border}`,
  borderRadius: 18,
  boxShadow: '0 18px 40px rgba(0,0,0,0.35)',
});
