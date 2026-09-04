import React, {createContext, useContext} from 'react';
import {AbsoluteFill, Audio, Easing, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {loadFont as loadArchivo} from '@remotion/google-fonts/ArchivoBlack';
import {loadFont as loadGrotesk} from '@remotion/google-fonts/SpaceGrotesk';
import {loadFont as loadMono} from '@remotion/google-fonts/JetBrainsMono';
import type {Beat, Caption, Clip} from './types';

const archivo = loadArchivo('normal', {weights: ['400'], subsets: ['latin']});
const grotesk = loadGrotesk('normal', {weights: ['500', '700'], subsets: ['latin']});
const jet = loadMono('normal', {weights: ['400', '700'], subsets: ['latin']});

export const HEAD = `${archivo.fontFamily}, "Segoe UI Black", "Arial Black", sans-serif`;
export const BODY = `${grotesk.fontFamily}, "Segoe UI", Arial, sans-serif`;
export const MONO = `${jet.fontFamily}, "Cascadia Mono", Consolas, monospace`;

export const CREAM = '#f3efe3';
export const INK = '#0a1621';        // matches presentation/slides.pdf
export const INK2 = '#16283c';       // deck panel navy
export const PAPER = '#fbfaf6';
export const TEXT_C = '#14161a';
export const TEXT_I = '#f4f1ea';
export const RED = '#e5322d';
export const RED_I = '#ff5a52';
export const YELLOW = '#ffe234';
export const GREEN = '#35d07f';
export const MUTED_C = '#6b6f76';
export const MUTED_I = '#9aa0a8';
export const LINE_C = '#d9d4c5';
export const LINE_I = '#2a2f38';

export type Tone = 'cream' | 'ink';
const ToneCtx = createContext<Tone>('cream');
export const useTone = () => useContext(ToneCtx);
export const palette = (tone: Tone) => ({
  bg: tone === 'cream' ? CREAM : INK,
  text: tone === 'cream' ? TEXT_C : TEXT_I,
  muted: tone === 'cream' ? MUTED_C : MUTED_I,
  line: tone === 'cream' ? LINE_C : LINE_I,
  red: tone === 'cream' ? RED : RED_I,
  card: tone === 'cream' ? PAPER : INK2,
});

// ------------------------------------------------------------------ motion helpers
export const fadeIn = (frame: number, at: number, dur = 10): number =>
  interpolate(frame, [at, at + dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

export const rise = (frame: number, at: number, dur = 12, px = 24): number =>
  interpolate(frame, [at, at + dur], [px, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});

export const pop = (frame: number, at: number, dur = 10): number =>
  interpolate(frame, [at, at + dur], [0.92, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.back(1.4))});

export const grow = (frame: number, at: number, dur = 9): number =>
  interpolate(frame, [at, at + dur], [0, 100], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});

export const typed = (text: string, frame: number, start: number, cps: number, fps: number): string => {
  const n = Math.floor(Math.max(0, frame - start) * (cps / fps));
  return text.slice(0, n);
};

// ------------------------------------------------------------------ layout
export const Section: React.FC<{tone: Tone; children: React.ReactNode}> = ({tone, children}) => (
  <ToneCtx.Provider value={tone}>
    <AbsoluteFill style={{backgroundColor: palette(tone).bg, fontFamily: BODY, color: palette(tone).text}}>{children}</AbsoluteFill>
  </ToneCtx.Provider>
);

export const Label: React.FC<{text: string; at?: number; top?: number; left?: number}> = ({text, at = 0, top = 72, left = 80}) => {
  const frame = useCurrentFrame();
  const p = palette(useTone());
  return (
    <div style={{position: 'absolute', top, left, fontFamily: MONO, fontSize: 19, letterSpacing: 5, textTransform: 'uppercase', color: p.red, opacity: fadeIn(frame, at, 8)}}>
      {text}
    </div>
  );
};

export const Strip: React.FC<{text: string}> = ({text}) => {
  const p = palette(useTone());
  return (
    <div style={{position: 'absolute', top: 74, right: 80, fontFamily: MONO, fontSize: 16, letterSpacing: 3, textTransform: 'uppercase', color: p.muted}}>
      {text}
    </div>
  );
};

// ------------------------------------------------------------------ typography
export type Seg = {t: string; hi?: 'yellow' | 'green'; strike?: boolean; dim?: boolean};

/** Word-by-word headline. Highlighted words get a marker swipe; strike segments get a red line at strikeAt. */
export const Headline: React.FC<{
  segs: Seg[];
  at: number;
  perWord?: number;
  size?: number;
  width?: number;
  top?: number;
  left?: number;
  lineHeight?: number;
  strikeAt?: number;
  hiAt?: number;
}> = ({segs, at, perWord = 4, size = 84, width = 1400, top = 150, left = 80, lineHeight = 1.12, strikeAt, hiAt}) => {
  const frame = useCurrentFrame();
  const p = palette(useTone());
  let idx = 0;
  return (
    <div style={{position: 'absolute', top, left, width, fontFamily: HEAD, fontSize: size, lineHeight, color: p.text, letterSpacing: -1}}>
      {segs.map((s, si) => {
        const words = s.t.split(/(\s+)/).filter((w) => w.length);
        const segStart = at + idx * perWord;
        const nWords = words.filter((w) => !/^\s+$/.test(w)).length;
        const hiStart = s.hi ? (hiAt !== undefined ? Math.max(hiAt, segStart + 3) : segStart + (nWords - 1) * perWord + 3) : 0;
        const inkOnMarker = s.hi && frame >= hiStart + 4;
        const rendered = words.map((w, wi) => {
          if (/^\s+$/.test(w)) return <span key={`${si}-${wi}`}>{w}</span>;
          const my = at + idx * perWord;
          idx += 1;
          const o = fadeIn(frame, my, 6);
          const y = rise(frame, my, 8, 14);
          return (
            <span key={`${si}-${wi}`} style={{display: 'inline-block', opacity: o, transform: `translateY(${y}px)`, color: inkOnMarker ? TEXT_C : s.dim ? p.muted : p.text}}>
              {w}
            </span>
          );
        });
        if (s.hi) {
          const hiPct = grow(frame, hiStart, 10);
          const hiColor = s.hi === 'green' ? GREEN : YELLOW;
          return (
            <span
              key={si}
              style={{
                backgroundImage: `linear-gradient(${hiColor}, ${hiColor})`,
                backgroundRepeat: 'no-repeat',
                backgroundSize: `${hiPct}% 86%`,
                backgroundPosition: '0 62%',
                padding: '0 12px',
                margin: '0 -6px',
                boxDecorationBreak: 'clone',
                WebkitBoxDecorationBreak: 'clone',
              }}
            >
              {rendered}
            </span>
          );
        }
        if (!s.strike) return <React.Fragment key={si}>{rendered}</React.Fragment>;
        const sAt = strikeAt ?? segStart + words.length * perWord + 12;
        const w = grow(frame, sAt, 12);
        return (
          <span key={si} style={{position: 'relative', display: 'inline'}}>
            {rendered}
            <span style={{position: 'absolute', left: 0, top: '52%', height: Math.max(6, size * 0.09), width: `${w}%`, background: RED, borderRadius: 3, transform: 'rotate(-1.2deg)'}} />
          </span>
        );
      })}
    </div>
  );
};

export const Sub: React.FC<{text: string; at: number; top: number; left?: number; size?: number; width?: number; mono?: boolean; until?: number}> = ({text, at, top, left = 80, size = 30, width = 1300, mono, until}) => {
  const frame = useCurrentFrame();
  const p = palette(useTone());
  const o = until !== undefined && frame >= until ? interpolate(frame, [until, until + 8], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : fadeIn(frame, at, 10);
  return (
    <div style={{position: 'absolute', top, left, width, fontFamily: mono ? MONO : BODY, fontWeight: 500, fontSize: size, lineHeight: 1.35, color: p.muted, opacity: o, transform: `translateY(${rise(frame, at, 10, 12)}px)`}}>
      {text}
    </div>
  );
};

/** A sticker caption: black box with the numbers in yellow, or a yellow box with black text. */
export const Sticker: React.FC<{text: string; at: number; x: number; y: number; tone?: 'black' | 'yellow' | 'cream'; size?: number; until?: number; maxWidth?: number}> = ({
  text, at, x, y, tone = 'black', size = 34, until, maxWidth = 1100,
}) => {
  const frame = useCurrentFrame();
  const o = until !== undefined && frame >= until ? interpolate(frame, [until, until + 6], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : fadeIn(frame, at, 7);
  const s = pop(frame, at, 10);
  const bg = tone === 'black' ? INK : tone === 'yellow' ? YELLOW : CREAM;
  const fg = tone === 'black' ? TEXT_I : TEXT_C;
  const tokens = text.split(/(\s+)/);
  return (
    <div style={{position: 'absolute', left: x, top: y, opacity: o, transform: `scale(${s})`, transformOrigin: 'left center', background: bg, color: fg, fontFamily: BODY, fontWeight: 700, fontSize: size, lineHeight: 1.2, padding: '12px 20px', maxWidth, boxShadow: '0 10px 30px rgba(0,0,0,0.35)'}}>
      {tokens.map((t, i) => {
        const hot = tone === 'black' && /[\d$%]/.test(t);
        return (
          <span key={i} style={hot ? {color: YELLOW} : undefined}>{t}</span>
        );
      })}
    </div>
  );
};

export const BigStat: React.FC<{value: string; label: string; at: number; x: number; y: number; size?: number; color?: string; strike?: boolean; strikeAt?: number; width?: number}> = ({
  value, label, at, x, y, size = 150, color, strike, strikeAt, width,
}) => {
  const frame = useCurrentFrame();
  const p = palette(useTone());
  const w = strike ? grow(frame, strikeAt ?? at + 20, 12) : 0;
  return (
    <div style={{position: 'absolute', left: x, top: y, width, opacity: fadeIn(frame, at, 8), transform: `translateY(${rise(frame, at, 12, 20)}px)`}}>
      <div style={{position: 'relative', display: 'inline-block', fontFamily: HEAD, fontSize: size, lineHeight: 1, letterSpacing: -3, color: color ?? p.text}}>
        {value}
        {strike ? <div style={{position: 'absolute', left: -6, top: '50%', height: Math.max(8, size * 0.09), width: `${w}%`, background: RED, borderRadius: 4, transform: 'rotate(-2deg)'}} /> : null}
      </div>
      <div style={{fontFamily: MONO, fontSize: 21, letterSpacing: 2, color: p.muted, marginTop: 14, textTransform: 'uppercase'}}>{label}</div>
    </div>
  );
};

export const Card: React.FC<{title: string; sub?: string; icon?: 'check' | 'cross' | 'none'; at: number; x: number; y: number; width?: number; hot?: boolean; hotAt?: number; size?: number}> = ({
  title, sub, icon = 'none', at, x, y, width = 900, hot, hotAt, size = 30,
}) => {
  const frame = useCurrentFrame();
  const tone = useTone();
  const p = palette(tone);
  const isHot = hot && frame >= (hotAt ?? at);
  const iconColor = icon === 'check' ? GREEN : RED;
  return (
    <div style={{position: 'absolute', left: x, top: y, width, opacity: fadeIn(frame, at, 8), transform: `translateY(${rise(frame, at, 10, 16)}px)`, background: isHot ? (tone === 'cream' ? '#e9f8ee' : '#112a1c') : p.card, border: `2px solid ${isHot ? GREEN : tone === 'cream' ? TEXT_C : LINE_I}`, boxShadow: tone === 'cream' ? `6px 6px 0 ${TEXT_C}` : 'none', padding: '18px 24px', display: 'flex', gap: 20, alignItems: 'flex-start'}}>
      {icon !== 'none' ? <div style={{fontFamily: MONO, fontSize: 34, lineHeight: 1.1, color: iconColor, width: 34}}>{icon === 'check' ? '✓' : '✗'}</div> : null}
      <div>
        <div style={{fontFamily: BODY, fontWeight: 700, fontSize: size, color: p.text, lineHeight: 1.2}}>{title}</div>
        {sub ? <div style={{fontFamily: BODY, fontWeight: 500, fontSize: Math.round(size * 0.73), color: p.muted, marginTop: 6}}>{sub}</div> : null}
      </div>
    </div>
  );
};

export const Chip: React.FC<{text: string; at: number; color?: string; size?: number; fill?: boolean}> = ({text, at, color, size = 22, fill}) => {
  const frame = useCurrentFrame();
  const p = palette(useTone());
  const c = color ?? p.text;
  return (
    <span style={{display: 'inline-block', fontFamily: MONO, fontSize: size, color: fill ? TEXT_C : c, background: fill ? YELLOW : 'transparent', border: `1.5px solid ${fill ? TEXT_C : c}`, borderRadius: 4, padding: '6px 12px', marginRight: 12, marginBottom: 12, opacity: fadeIn(frame, at, 6), transform: `scale(${pop(frame, at, 8)})`}}>
      {text}
    </span>
  );
};

export const FlowRow: React.FC<{items: {t: string; s: string; hot?: boolean}[]; at: number; x: number; y: number; step?: number}> = ({items, at, x, y, step = 8}) => {
  const frame = useCurrentFrame();
  const tone = useTone();
  const p = palette(tone);
  return (
    <div style={{position: 'absolute', left: x, top: y, display: 'flex', alignItems: 'center', gap: 14}}>
      {items.map((it, i) => {
        const a = at + i * step;
        return (
          <React.Fragment key={it.t}>
            {i > 0 ? <div style={{width: 46, height: 3, background: YELLOW, opacity: fadeIn(frame, a - 3, 5)}} /> : null}
            <div style={{opacity: fadeIn(frame, a, 6), transform: `translateY(${rise(frame, a, 8, 10)}px)`, background: p.card, border: `2px solid ${it.hot ? YELLOW : tone === 'cream' ? TEXT_C : LINE_I}`, padding: '12px 18px', minWidth: 190}}>
              <div style={{fontFamily: BODY, fontWeight: 700, fontSize: 24, color: p.text}}>{it.t}</div>
              <div style={{fontFamily: MONO, fontSize: 16, color: p.muted, marginTop: 4}}>{it.s}</div>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};

// ------------------------------------------------------------------ frames and media
export const Browser: React.FC<{url: string; at?: number; x: number; y: number; width: number; height: number; children: React.ReactNode}> = ({url, at = 0, x, y, width, height, children}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{position: 'absolute', left: x, top: y, width, height, opacity: fadeIn(frame, at, 10), transform: `translateY(${rise(frame, at, 14, 24)}px)`, background: '#0b0d11', borderRadius: 12, overflow: 'hidden', boxShadow: '0 30px 80px rgba(0,0,0,0.55)', border: `1px solid ${LINE_I}`}}>
      <div style={{height: 44, background: '#1a1e25', display: 'flex', alignItems: 'center', padding: '0 16px', gap: 8}}>
        <span style={{width: 12, height: 12, borderRadius: 6, background: '#ff5f57'}} />
        <span style={{width: 12, height: 12, borderRadius: 6, background: '#febc2e'}} />
        <span style={{width: 12, height: 12, borderRadius: 6, background: '#28c840'}} />
        <div style={{marginLeft: 18, flex: 1, height: 26, background: '#0f1218', borderRadius: 6, display: 'flex', alignItems: 'center', padding: '0 12px', fontFamily: MONO, fontSize: 14, color: MUTED_I}}>
          <span style={{color: GREEN, marginRight: 8}}>{'●'}</span>
          {url}
        </div>
      </div>
      <div style={{position: 'absolute', left: 0, top: 44, right: 0, bottom: 0, overflow: 'hidden'}}>{children}</div>
    </div>
  );
};

/** Real footage: plays the clip, then freezes on its last frame for as long as the beat runs. */
export const Footage: React.FC<{clip: Clip; scale?: number}> = ({clip, scale = 1}) => {
  const frame = useCurrentFrame();
  const style: React.CSSProperties = {width: 1920, height: 1080, transform: `scale(${scale})`, transformOrigin: 'top left', display: 'block'};
  if (frame < clip.frames - 2) {
    return <OffthreadVideo src={staticFile(clip.src)} muted style={style} />;
  }
  return <Img src={staticFile(clip.last)} style={style} />;
};

export const Terminal: React.FC<{title: string; children: React.ReactNode; style?: React.CSSProperties; fontSize?: number; at?: number}> = ({title, children, style, fontSize = 28, at = 0}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{position: 'absolute', background: '#0d1117', border: `1px solid ${LINE_I}`, borderRadius: 12, boxShadow: '0 30px 80px rgba(0,0,0,0.5)', overflow: 'hidden', opacity: fadeIn(frame, at, 10), transform: `translateY(${rise(frame, at, 14, 24)}px)`, ...style}}>
      <div style={{height: 44, background: '#161b22', borderBottom: `1px solid ${LINE_I}`, display: 'flex', alignItems: 'center', padding: '0 16px', gap: 8}}>
        <span style={{width: 12, height: 12, borderRadius: 6, background: '#ff5f57'}} />
        <span style={{width: 12, height: 12, borderRadius: 6, background: '#febc2e'}} />
        <span style={{width: 12, height: 12, borderRadius: 6, background: '#28c840'}} />
        <span style={{marginLeft: 14, color: MUTED_I, fontFamily: MONO, fontSize: 16}}>{title}</span>
      </div>
      <div style={{padding: '24px 30px', color: TEXT_I, fontFamily: MONO, fontSize, lineHeight: 1.55, whiteSpace: 'pre-wrap', wordBreak: 'break-word'}}>{children}</div>
    </div>
  );
};

export const Cursor: React.FC<{visible?: boolean}> = ({visible = true}) => {
  const frame = useCurrentFrame();
  const on = Math.floor(frame / 15) % 2 === 0;
  return <span style={{opacity: visible && on ? 1 : 0, color: TEXT_I}}>{'▌'}</span>;
};

export const Captions: React.FC<{captions: Caption[]}> = ({captions}) => {
  const frame = useCurrentFrame();
  const c = captions.find((x) => frame >= x.start && frame < x.end);
  if (!c) return null;
  return (
    <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 120, background: 'rgba(4, 6, 10, 0.82)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 110px'}}>
      <div style={{color: TEXT_I, fontFamily: BODY, fontWeight: 500, fontSize: 36, lineHeight: 1.25, textAlign: 'center'}}>{c.text}</div>
    </div>
  );
};

export const BeatAudio: React.FC<{beat: Beat}> = ({beat}) => {
  if (!beat.audio) return null;
  return (
    <Sequence from={beat.lead} layout="none">
      <Audio src={staticFile(beat.audio)} />
    </Sequence>
  );
};

/** The project wordmark, set quietly: small caps, low contrast, out of the way. */
export const Wordmark: React.FC<{text: string; at: number; bottom?: boolean}> = ({text, at, bottom}) => {
  const frame = useCurrentFrame();
  const tone = useTone();
  const p = palette(tone);
  return (
    <div
      style={{
        position: 'absolute',
        left: 80,
        [bottom ? 'bottom' : 'top']: bottom ? 90 : 118,
        fontFamily: HEAD,
        fontSize: 30,
        letterSpacing: 8,
        color: p.text,
        opacity: fadeIn(frame, at, 16) * (tone === 'cream' ? 0.5 : 0.62),
      }}
    >
      {text}
    </div>
  );
};

export const useFps = () => useVideoConfig().fps;
