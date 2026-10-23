// edit.json schema. ve.py drafts it; Claude refines it; this engine renders it.
export type Word = {text: string; start: number; end: number};

export type Segment = {start: number; end: number; zoom: number; push?: number; focusX?: number; focusY?: number};

export type TransitionType = 'whip' | 'zoom' | 'flash' | 'dip' | 'slide';
export type Transition = {at: number; type: TransitionType; dir?: 1 | -1};

type Base = {start: number; end: number; sfx?: string | null};
export type Overlay =
  | (Base & {type: 'title'; text: string; kicker?: string})
  | (Base & {type: 'lowerThird'; name: string; role?: string; y?: number})
  | (Base & {type: 'emphasis'; text: string; y?: number})
  | (Base & {type: 'callout'; text: string; x: number; y: number})
  | (Base & {type: 'counter'; from?: number; to: number; prefix?: string; suffix?: string; label?: string})
  | (Base & {type: 'image'; src: string; caption?: string})
  | (Base & {type: 'broll'; src: string; trim?: number})
  | (Base & {type: 'motion'; src: string; mode?: 'full' | 'card'});

export type Edit = {
  format: 'short' | 'landscape' | 'square';
  width: number;
  height: number;
  fps: number;
  video: string;
  audio: string;
  source?: {width: number; height: number};
  contentDuration: number;
  durationInFrames: number;
  theme: 'dark' | 'light';
  reframe: {mode: 'cover' | 'fit' | 'none'; focusX: number; focusY: number};
  segments: Segment[];
  transitions: Transition[];
  captions: {enabled: boolean; maxWords: number; y: number; accent: string[]; words: Word[]; yAt?: [number, number, number][]};
  overlays: Overlay[];
  branding: {kicker: boolean; kickerAt?: number; endCard: number; handle: string; progressBar: boolean; watermark?: string | null};
  grain: number;
};

export type Brand = {
  name: string;
  mark: string;
  tagline: string;
  handles: Record<string, string>;
  dark: Palette;
  light: Palette;
  video: {captions: {text: string; highlight: string; highlightText: string; stroke: string}};
};

export type Palette = {
  background: string;
  surface: string;
  surfaceRaised: string;
  foreground: string;
  muted: string;
  border: string;
  accent: string;
  accentSoft: string;
  onAccent: string;
};
