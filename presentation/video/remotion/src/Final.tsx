import React from 'react';
import {AbsoluteFill} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import type {Beat, Timeline} from './types';
import {BEATS} from './beats';
import {BeatAudio, Captions, INK, MONO, MUTED_I, MUTED_C} from './ui';

const CREAM_BEATS = new Set(['b02', 'b04', 'b07', 'b09']);

const BeatView: React.FC<{beat: Beat; tl: Timeline}> = ({beat, tl}) => {
  const Visual = BEATS[beat.id];
  const onCream = CREAM_BEATS.has(beat.id);
  return (
    <AbsoluteFill style={{backgroundColor: INK}}>
      {Visual ? <Visual beat={beat} tl={tl} /> : null}
      <div style={{position: 'absolute', top: 76, right: 80, fontFamily: MONO, fontSize: 15, letterSpacing: 3, textTransform: 'uppercase', color: onCream ? MUTED_C : MUTED_I}}>
        {tl.strip}
      </div>
      {tl.subtitles ? <Captions captions={beat.captions} /> : null}
      <BeatAudio beat={beat} />
    </AbsoluteFill>
  );
};

export const totalFrames = (tl: Timeline): number =>
  tl.beats.reduce((s, b) => s + b.durationInFrames, 0) - (tl.beats.length - 1) * tl.transition;

export const Final: React.FC<Timeline> = (tl) => {
  const children: React.ReactNode[] = [];
  tl.beats.forEach((b, i) => {
    if (i > 0) {
      children.push(
        <TransitionSeries.Transition key={`t-${b.id}`} presentation={fade()} timing={linearTiming({durationInFrames: tl.transition})} />,
      );
    }
    children.push(
      <TransitionSeries.Sequence key={b.id} durationInFrames={b.durationInFrames}>
        <BeatView beat={b} tl={tl} />
      </TransitionSeries.Sequence>,
    );
  });
  return (
    <AbsoluteFill style={{backgroundColor: INK}}>
      <TransitionSeries>{children}</TransitionSeries>
    </AbsoluteFill>
  );
};
