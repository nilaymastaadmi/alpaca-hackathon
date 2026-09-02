import React from 'react';
import {Composition} from 'remotion';
import {Final, totalFrames} from './Final';
import type {Timeline} from './types';
import timeline from '../public/timeline.json';

const defaults = timeline as unknown as Timeline;

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Final"
    component={Final}
    fps={defaults.fps}
    width={defaults.width}
    height={defaults.height}
    durationInFrames={totalFrames(defaults)}
    defaultProps={defaults}
    calculateMetadata={({props}) => ({
      durationInFrames: totalFrames(props as Timeline),
      fps: (props as Timeline).fps,
      width: (props as Timeline).width,
      height: (props as Timeline).height,
    })}
  />
);
