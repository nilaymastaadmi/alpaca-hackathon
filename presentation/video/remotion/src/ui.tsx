import React from 'react';
import {Audio, Easing, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import type {Beat, Caption} from './types';

export const BG = '#0b0f14';
export const FG = '#f2f4f7';
export const DIM = '#8b95a5';
export const AMBER = '#f5b942';
export const GREEN = '#3ddc84';
export const RED = '#ff5c5c';
export const PANEL = '#121822';
export const LINE = '#243042';
export const SANS = '"Segoe UI", Inter, Roboto, Helvetica, Arial, sans-serif';
export const MONO = '"Cascadia Mono", Consolas, "Courier New", monospace';

export const fadeIn = (frame: number, at: number, dur = 10): number =>
  interpolate(frame, [at, at + dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

export const rise = (frame: number, at: number, dur = 12, px = 24): number =>
  interpolate(frame, [at, at + dur], [px, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

export const typed = (text: string, frame: number, start: number, cps: number, fps: number): string => {
  const n = Math.floor(Math.max(0, frame - start) * (cps / fps));
  return text.slice(0, n);
};

export const Captions: React.FC<{captions: Caption[]}> = ({captions}) => {
  const frame = useCurrentFrame();
  const c = captions.find((x) => frame >= x.start && frame < x.end);
  if (!c) return null;
  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: 0,
        height: 150,
        background: 'rgba(4, 6, 10, 0.80)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 110px',
      }}
    >
      <div
        style={{
          color: FG,
          fontFamily: SANS,
          fontSize: 42,
          lineHeight: 1.25,
          textAlign: 'center',
          textShadow: '0 2px 8px rgba(0,0,0,0.8)',
        }}
      >
        {c.text}
      </div>
    </div>
  );
};

export const Kicker: React.FC<{text: string}> = ({text}) => (
  <div
    style={{
      position: 'absolute',
      left: 80,
      top: 26,
      color: AMBER,
      fontFamily: SANS,
      fontSize: 24,
      letterSpacing: 6,
      textTransform: 'uppercase',
      opacity: 0.95,
      background: 'rgba(11, 15, 20, 0.86)',
      padding: '8px 16px 8px 18px',
      borderRadius: 8,
      border: `1px solid ${LINE}`,
    }}
  >
    {text}
  </div>
);

export const NumberCard: React.FC<{
  big: string;
  sub?: string;
  at: number;
  color?: string;
  right?: number;
  left?: number;
  top?: number;
  size?: number;
  backdrop?: boolean;
}> = ({big, sub, at, color = AMBER, right, left, top = 40, size = 128, backdrop = true}) => {
  const frame = useCurrentFrame();
  const o = fadeIn(frame, at, 12);
  const y = rise(frame, at, 14, 30);
  const alignRight = left === undefined;
  return (
    <div
      style={{
        position: 'absolute',
        right: alignRight ? (right ?? 80) : undefined,
        left: alignRight ? undefined : left,
        top,
        opacity: o,
        transform: `translateY(${y}px)`,
        textAlign: alignRight ? 'right' : 'left',
        fontFamily: SANS,
        background: backdrop ? 'rgba(11, 15, 20, 0.86)' : 'transparent',
        border: backdrop ? `1px solid ${LINE}` : 'none',
        borderRadius: 16,
        padding: backdrop ? '14px 26px 18px' : 0,
      }}
    >
      <div style={{color, fontSize: size, fontWeight: 700, lineHeight: 1, letterSpacing: -2, textShadow: '0 4px 24px rgba(0,0,0,0.6)'}}>
        {big}
      </div>
      {sub ? <div style={{color: FG, fontSize: 30, marginTop: 10, opacity: 0.9}}>{sub}</div> : null}
    </div>
  );
};

export const Terminal: React.FC<{title: string; children: React.ReactNode; style?: React.CSSProperties; fontSize?: number}> = ({
  title,
  children,
  style,
  fontSize = 30,
}) => (
  <div
    style={{
      position: 'absolute',
      background: '#0d1117',
      border: `1px solid ${LINE}`,
      borderRadius: 14,
      boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
      overflow: 'hidden',
      ...style,
    }}
  >
    <div style={{height: 46, background: '#161b22', borderBottom: `1px solid ${LINE}`, display: 'flex', alignItems: 'center', padding: '0 18px', gap: 10}}>
      <span style={{width: 14, height: 14, borderRadius: 7, background: '#ff5f57'}} />
      <span style={{width: 14, height: 14, borderRadius: 7, background: '#febc2e'}} />
      <span style={{width: 14, height: 14, borderRadius: 7, background: '#28c840'}} />
      <span style={{marginLeft: 16, color: DIM, fontFamily: MONO, fontSize: 20}}>{title}</span>
    </div>
    <div style={{padding: '26px 34px', color: FG, fontFamily: MONO, fontSize, lineHeight: 1.55, whiteSpace: 'pre-wrap', wordBreak: 'break-word'}}>
      {children}
    </div>
  </div>
);

export const Cursor: React.FC<{visible?: boolean}> = ({visible = true}) => {
  const frame = useCurrentFrame();
  const on = Math.floor(frame / 15) % 2 === 0;
  return <span style={{opacity: visible && on ? 1 : 0, color: FG}}>{'▌'}</span>;
};

export const BeatAudio: React.FC<{beat: Beat}> = ({beat}) => {
  if (!beat.audio) return null;
  return (
    <Sequence from={beat.lead} layout="none">
      <Audio src={staticFile(beat.audio)} />
    </Sequence>
  );
};
