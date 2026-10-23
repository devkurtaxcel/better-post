import React from 'react';
import {Composition} from 'remotion';
import {Edit} from './Edit';
import type {Edit as EditT} from './types';

// Props come from projects/<slug>/edit.json (--props); the project folder is the public dir.
const sample: EditT = {
  format: 'short', width: 1080, height: 1920, fps: 30, video: 'cut.mp4', audio: 'mix.wav',
  contentDuration: 5, durationInFrames: 225, theme: 'dark',
  reframe: {mode: 'cover', focusX: 0.5, focusY: 0.42},
  segments: [], transitions: [],
  captions: {enabled: false, maxWords: 3, y: 0.7, accent: [], words: []},
  overlays: [], branding: {kicker: true, endCard: 2.5, handle: '@yourhandle', progressBar: false}, grain: 0.04,
};

export const Root: React.FC = () => (
  <Composition
    id="Edit"
    component={Edit}
    defaultProps={sample}
    durationInFrames={sample.durationInFrames}
    fps={30}
    width={1080}
    height={1920}
    calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames, width: props.width, height: props.height, fps: props.fps})}
  />
);
