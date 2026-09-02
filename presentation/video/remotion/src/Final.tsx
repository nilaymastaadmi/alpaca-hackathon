import React from 'react';
import {AbsoluteFill} from 'remotion';
import {TransitionSeries, linearTiming} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import type {Beat, Timeline} from './types';
import {BEATS} from './beats';
import {BG, BeatAudio, Captions, Kicker} from './ui';

const BeatView: React.FC<{beat: Beat; tl: Timeline}> = ({beat, tl}) => {
  const Visual = BEATS[beat.id];
  return (
    <AbsoluteFill style={{backgroundColor: BG}}>
      {Visual ? <Visual beat={beat} tl={tl} /> : null}
      <Kicker text={beat.kicker} />
      <Captions captions={beat.captions} />
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
    <AbsoluteFill style={{backgroundColor: BG}}>
      <TransitionSeries>{children}</TransitionSeries>
    </AbsoluteFill>
  );
};
