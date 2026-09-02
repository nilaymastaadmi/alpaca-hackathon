import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Beat, Timeline} from './types';
import {AMBER, BG, Cursor, DIM, FG, GREEN, LINE, MONO, NumberCard, PANEL, RED, SANS, Terminal, fadeIn, rise, typed} from './ui';

type P = {beat: Beat; tl: Timeline};

// ---------------------------------------------------------------- beat 1
export const Beat01: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const a = beat.anchors;
  const scale = interpolate(frame, [0, beat.durationInFrames], [1.0, 1.18], {extrapolateRight: 'clamp'});
  const hl = fadeIn(frame, a.n81, 10);
  const hlW = interpolate(frame, [a.n81, a.n81 + 18], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{backgroundColor: BG, overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, transform: `scale(${scale})`, transformOrigin: '26% 39%'}}>
        <Img src={staticFile('assets/b01_dashboard.png')} style={{width: 1920, height: 1080, display: 'block'}} />
        <div
          style={{
            position: 'absolute',
            left: 72,
            top: 401,
            width: 826 * hlW,
            height: 34,
            border: `3px solid ${AMBER}`,
            borderRadius: 6,
            boxShadow: `0 0 26px ${AMBER}80`,
            opacity: hl,
          }}
        />
      </div>
      <NumberCard big={`${tl.facts.LIVE_PCT}%`} sub={`declined, of ${tl.facts.LIVE_N} real opportunities`} at={a.declined} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- beat 2
export const Beat02: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const a = beat.anchors;
  const drift = interpolate(frame, [0, beat.durationInFrames], [0, -70], {extrapolateRight: 'clamp'});
  const panelX = interpolate(frame, [a.pre, a.pre + 16], [1000, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const shiftX = interpolate(frame, [a.pre, a.pre + 16], [0, -420], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const cmd = 'git log --diff-filter=A --reverse --date=iso -- research/PREREGISTRATION_R1.md backtest/';
  const typedCmd = typed(cmd, frame, a.pre + 18, 46, fps);
  const cmdDone = frame >= a.pre + 18 + Math.ceil((cmd.length * fps) / 46);
  const linesAt = Math.max(a.git, a.pre + 18 + Math.ceil((cmd.length * fps) / 46) + 6);
  return (
    <AbsoluteFill style={{backgroundColor: BG, overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, transform: `translate(${shiftX}px, ${drift}px)`}}>
        <Img src={staticFile('assets/b02_prereg.png')} style={{width: 1920, height: 1080, display: 'block'}} />
      </div>
      <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(90deg, rgba(11,15,20,0) 40%, rgba(11,15,20,0.75) 60%)', opacity: fadeIn(frame, a.pre, 16)}} />
      <div style={{position: 'absolute', inset: 0, transform: `translateX(${panelX}px)`}}>
        <Terminal title="alpaca-hackathon  (main)" style={{left: 960, top: 110, width: 900, height: 740}} fontSize={26}>
          <span style={{color: GREEN}}>$ </span>
          {typedCmd}
          <Cursor visible={!cmdDone} />
          {'\n'}
          {tl.gitlog.map((l, i) => {
            const at = linesAt + i * 9;
            const o = fadeIn(frame, at, 4);
            const hot = l.highlight && frame >= at + 14;
            return (
              <div key={l.hash} style={{opacity: o, marginTop: 14, lineHeight: 1.4}}>
                <span style={{color: AMBER}}>{l.hash}</span>{' '}
                <span style={{color: hot ? FG : DIM, background: hot ? '#3a2d0a' : 'transparent', padding: hot ? '0 6px' : 0, borderRadius: 6, transition: 'none'}}>{l.time}</span>
                {'\n'}
                <span style={{color: l.highlight ? FG : DIM}}>{l.subject}</span>
              </div>
            );
          })}
          <div style={{marginTop: 26, opacity: fadeIn(frame, linesAt + 34, 10), fontFamily: SANS, borderTop: `1px solid ${LINE}`, paddingTop: 18}}>
            <span style={{color: AMBER, fontSize: 56, fontWeight: 700}}>19:57</span>
            <span style={{color: FG, fontSize: 28}}>{'  pre-registered.  '}</span>
            <span style={{color: AMBER, fontSize: 56, fontWeight: 700}}>20:01</span>
            <span style={{color: FG, fontSize: 28}}>{'  first backtest commit.'}</span>
          </div>
        </Terminal>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- beat 3
export const Beat03: React.FC<P> = ({beat}) => {
  const frame = useCurrentFrame();
  const a = beat.anchors;
  const ring = (at: number): React.CSSProperties => ({
    position: 'absolute',
    border: `4px solid ${AMBER}`,
    borderRadius: 14,
    boxShadow: `0 0 30px ${AMBER}66`,
    opacity: fadeIn(frame, at, 8),
    transform: `scale(${interpolate(frame, [at, at + 10], [1.12, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})})`,
  });
  const strikeW = interpolate(frame, [a.naive, a.naive + 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{backgroundColor: '#f5f6f8', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, transform: 'scale(0.86)', transformOrigin: '50% 0%'}}>
        <Img src={staticFile('assets/slide05.png')} style={{width: 1920, height: 1080, display: 'block'}} />
        <div style={{...ring(a.vrp), left: 84, top: 372, width: 270, height: 122}} />
        <div style={{...ring(a.obs), left: 604, top: 372, width: 268, height: 122}} />
        <div style={{...ring(a.t), left: 1122, top: 372, width: 392, height: 122}} />
        <div style={{position: 'absolute', left: 348, top: 918, width: 592 * strikeW, height: 6, background: RED, borderRadius: 3, boxShadow: `0 0 16px ${RED}`}} />
      </div>
      <div style={{position: 'absolute', left: 1062, top: 800, width: 760, color: '#3b4657', fontFamily: SANS, fontSize: 24, lineHeight: 1.35, opacity: fadeIn(frame, a.naive, 10)}}>
        6.99 years of SPY, out of sample. The naive t of +18.16 is invalid: 21-day windows overlap by 20 of 21 days.
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- beat 4
const PIPE = [
  ['market data', 'via MCP'],
  ['signals', 'VRP, term structure'],
  ['11 gates', 'numbered 0 to 10'],
  ['execute or refuse', 'via MCP'],
  ['Merkle artifact', 'make verify'],
];

export const Beat04: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const a = beat.anchors;
  const n = tl.gates.length;
  const gateAt = (i: number) => a.listStart + Math.round(((a.listEnd - a.listStart) * i) / Math.max(1, n - 1));
  return (
    <AbsoluteFill style={{backgroundColor: BG, fontFamily: SANS}}>
      <div style={{position: 'absolute', left: 80, right: 80, top: 215, display: 'flex', alignItems: 'center', gap: 18}}>
        {PIPE.map(([t, s], i) => {
          const at = beat.lead + i * 8;
          return (
            <React.Fragment key={t}>
              {i > 0 ? <div style={{color: DIM, fontSize: 40, opacity: fadeIn(frame, at, 8)}}>{'→'}</div> : null}
              <div style={{flex: 1, opacity: fadeIn(frame, at, 8), transform: `translateY(${rise(frame, at, 10, 16)}px)`, background: PANEL, border: `1px solid ${i === 2 ? AMBER : LINE}`, borderRadius: 14, padding: '18px 22px', textAlign: 'center'}}>
                <div style={{color: FG, fontSize: 32, fontWeight: 600}}>{t}</div>
                <div style={{color: DIM, fontSize: 22, marginTop: 4}}>{s}</div>
              </div>
            </React.Fragment>
          );
        })}
      </div>
      <div style={{position: 'absolute', left: 80, right: 80, top: 385, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16}}>
        {tl.gates.map((g, i) => {
          const at = gateAt(i);
          const lit = frame >= at;
          const o = fadeIn(frame, beat.lead + 20 + i * 2, 6);
          return (
            <div key={g.n} style={{opacity: o, background: lit ? '#1a2231' : PANEL, border: `2px solid ${lit ? (g.breaker ? RED : AMBER) : LINE}`, borderRadius: 12, padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 16, boxShadow: lit ? `0 0 22px ${g.breaker ? RED : AMBER}40` : 'none'}}>
              <div style={{color: lit ? (g.breaker ? RED : AMBER) : DIM, fontFamily: MONO, fontSize: 34, width: 44, textAlign: 'right'}}>{g.n}</div>
              <div>
                <div style={{color: lit ? FG : DIM, fontSize: 27}}>{g.name}</div>
                {g.breaker ? <div style={{color: lit ? RED : DIM, fontSize: 18, letterSpacing: 3, textTransform: 'uppercase'}}>circuit breaker</div> : null}
              </div>
            </div>
          );
        })}
        <div style={{opacity: fadeIn(frame, beat.lead + 44, 6), background: frame >= a.stagger ? '#1a2231' : PANEL, border: `2px solid ${frame >= a.stagger ? AMBER : LINE}`, borderRadius: 12, padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 16}}>
          <div style={{color: frame >= a.stagger ? AMBER : DIM, fontFamily: MONO, fontSize: 34, width: 44, textAlign: 'right'}}>+</div>
          <div style={{color: frame >= a.stagger ? FG : DIM, fontSize: 27}}>stagger rule: one position per expiry</div>
        </div>
      </div>
      <div style={{position: 'absolute', left: 80, right: 80, top: 830, opacity: fadeIn(frame, a.mcp, 12), transform: `translateY(${rise(frame, a.mcp, 12, 16)}px)`, color: FG, fontSize: 30, background: PANEL, border: `1px solid ${LINE}`, borderRadius: 12, padding: '16px 24px', display: 'flex', gap: 24, alignItems: 'center'}}>
        <span style={{color: AMBER, fontFamily: MONO, fontSize: 26}}>MCP</span>
        <span>Alpaca's official MCP server, 74 tools, JSON-RPC over stdio. Every request and response recorded.</span>
      </div>
      <NumberCard big="11" sub="gates, 0 to 10, plus a stagger rule" at={a.eleven} top={30} size={88} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- beat 5
export const Beat05: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const a = beat.anchors;
  const won = frame >= a.won;
  return (
    <AbsoluteFill style={{backgroundColor: BG, fontFamily: SANS}}>
      <div style={{position: 'absolute', left: 80, right: 80, top: 130, color: FG, fontSize: 40, opacity: fadeIn(frame, beat.lead, 10)}}>{tl.race.title}</div>
      <div style={{position: 'absolute', left: 80, right: 80, top: 250, display: 'flex', gap: 28}}>
        {tl.race.tenors.map((t, i) => {
          const at = a.three + i * 8;
          const hot = won && t.deployed;
          const cold = won && !t.deployed;
          return (
            <div key={t.id} style={{flex: 1, opacity: fadeIn(frame, at, 10) * (cold ? 0.45 : 1), transform: `translateY(${rise(frame, at, 12, 20)}px) scale(${hot ? 1.03 : 1})`, background: hot ? '#10251a' : PANEL, border: `3px solid ${hot ? GREEN : LINE}`, borderRadius: 18, padding: '30px 34px', boxShadow: hot ? `0 0 40px ${GREEN}40` : 'none'}}>
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
                <div style={{color: FG, fontSize: 44, fontWeight: 700}}>{t.id}</div>
                <div style={{color: DIM, fontSize: 28}}>{t.dte}</div>
              </div>
              {hot ? <div style={{color: GREEN, fontSize: 22, letterSpacing: 4, textTransform: 'uppercase', marginTop: 6}}>deployed</div> : <div style={{height: 34}} />}
              <div style={{marginTop: 30, color: DIM, fontSize: 24}}>would-enter cycles</div>
              <div style={{color: FG, fontSize: 56, fontFamily: MONO, opacity: fadeIn(frame, a.eight, 8)}}>{t.cycles}</div>
              <div style={{marginTop: 24, color: DIM, fontSize: 24}}>days with an entry</div>
              <div style={{color: hot ? GREEN : FG, fontSize: hot ? 118 : 56, fontFamily: MONO, lineHeight: 1.05, opacity: fadeIn(frame, a.eight + 10, 8)}}>{t.days}</div>
            </div>
          );
        })}
      </div>
      <div style={{position: 'absolute', left: 80, top: 790, color: DIM, fontSize: 26, opacity: fadeIn(frame, a.won, 10)}}>
        Source: research/DEPLOYMENT_DECISIONS.md, decision D3, 2026-08-30. The comparison harness never sent an order.
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- beat 6
export const Beat06: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const a = beat.anchors;
  const c1 = '# artifacts/decisions.jsonl: every decision, fill and refusal is a leaf';
  const c2 = '# SHA-256 Merkle tree, domain-separated leaves and nodes, root sealed before outcomes are known';
  const cmd = tl.verify.command;
  const cmdStart = a.command;
  const cmdDone = cmdStart + Math.ceil((cmd.length * fps) / 14);
  const outAt = cmdDone + 12;
  const out = tl.verify.output;
  const idx = out.indexOf('VERIFIED');
  return (
    <AbsoluteFill style={{backgroundColor: BG}}>
      <Terminal title="alpaca-hackathon  (main)" style={{left: 80, top: 110, width: 1760, height: 760}} fontSize={32}>
        <span style={{color: DIM}}>{typed(c1, frame, beat.lead, 70, fps)}</span>
        {'\n'}
        <span style={{color: DIM}}>{typed(c2, frame, a.sealed, 70, fps)}</span>
        {'\n\n'}
        <span style={{opacity: frame >= cmdStart ? 1 : 0}}>
          <span style={{color: GREEN}}>$ </span>
          {typed(cmd, frame, cmdStart, 14, fps)}
          <Cursor visible={frame < cmdDone} />
        </span>
        {'\n'}
        <span style={{opacity: frame >= outAt ? 1 : 0}}>
          {idx >= 0 ? (
            <>
              <span style={{color: GREEN, fontWeight: 700}}>{out.slice(idx, idx + 8)}</span>
              {out.slice(idx + 8)}
            </>
          ) : (
            out
          )}
        </span>
        {'\n'}
        <span style={{opacity: frame >= outAt + 6 ? 1 : 0}}>
          <span style={{color: GREEN}}>$ </span>
          <Cursor visible={frame >= outAt + 6} />
        </span>
      </Terminal>
      <NumberCard big={tl.verify.count} sub="sealed artifacts, one root, one command" at={outAt + 10} top={600} right={140} size={140} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- beat 7
const Code: React.FC<{lines: string[]; at: number; hot?: boolean; label?: string; frame: number}> = ({lines, at, hot, label, frame}) => {
  const o = fadeIn(frame, at, 8);
  return (
    <div style={{opacity: o, transform: `translateY(${rise(frame, at, 10, 12)}px)`, marginBottom: 26, borderLeft: `6px solid ${hot ? AMBER : LINE}`, paddingLeft: 22, position: 'relative'}}>
      {label ? <div style={{color: AMBER, fontFamily: SANS, fontSize: 22, letterSpacing: 3, textTransform: 'uppercase', marginBottom: 6}}>{label}</div> : null}
      {lines.map((l, i) => (
        <div key={i} style={{color: l.includes('SPY261002C00792000') || l.includes('0/5 positions open') || l.includes('no legs at broker') ? AMBER : FG, fontFamily: MONO, fontSize: 25, lineHeight: 1.45, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere'}}>
          {l}
        </div>
      ))}
    </div>
  );
};

export const Beat07: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const a = beat.anchors;
  const showRecord = frame >= a.record;
  return (
    <AbsoluteFill style={{backgroundColor: BG, fontFamily: SANS}}>
      <div style={{position: 'absolute', left: 80, top: 100, color: DIM, fontFamily: MONO, fontSize: 24, opacity: fadeIn(frame, beat.lead, 8)}}>{tl.seq30.header}</div>
      <div style={{position: 'absolute', left: 80, top: 150, width: 1180, height: 760, overflow: 'hidden'}}>
        <Code frame={frame} at={a.flat} lines={tl.seq30.gate5} label="gate 5, capacity" />
        <Code frame={frame} at={a.raw} lines={tl.seq30.positions} hot label="mcp_calls[1], the raw broker response" />
        <Code frame={frame} at={a.recon} lines={tl.seq30.reconcile} hot label="reconciliation, the same sealed record" />
      </div>
      <div style={{position: 'absolute', left: 1320, top: 150, width: 520}}>
        <div style={{opacity: showRecord ? 0 : 1}}>
          <div style={{opacity: fadeIn(frame, a.morning, 10), marginBottom: 26}}>
            <div style={{color: AMBER, fontSize: 22, letterSpacing: 3, textTransform: 'uppercase'}}>first live morning</div>
            <div style={{color: FG, fontSize: 40, fontWeight: 600}}>Mon 31 Aug 2026</div>
            <div style={{color: DIM, fontSize: 26}}>Alpaca paper account, market open 09:30 ET</div>
          </div>
          {tl.fills.map((f, i) => {
            const at = a.four + i * 7;
            return (
              <div key={f} style={{opacity: fadeIn(frame, at, 6), transform: `translateX(${rise(frame, at, 8, 20)}px)`, display: 'flex', gap: 18, alignItems: 'center', marginBottom: 10}}>
                <div style={{width: 18, height: 18, borderRadius: 9, background: AMBER, boxShadow: `0 0 14px ${AMBER}`}} />
                <div style={{color: FG, fontFamily: MONO, fontSize: 26, whiteSpace: 'nowrap'}}>{f}</div>
              </div>
            );
          })}
          <div style={{marginTop: 24, opacity: fadeIn(frame, a.four + 40, 10)}}>
            <div style={{color: AMBER, fontSize: 130, fontWeight: 700, lineHeight: 1, letterSpacing: -4}}>4</div>
            <div style={{color: FG, fontSize: 32, marginTop: 8}}>condors, 7 contracts each, in 36 minutes.</div>
            <div style={{color: FG, fontSize: 32}}>The design intended 1.</div>
          </div>
        </div>
        <div style={{position: 'absolute', left: 0, top: 0, width: 520, opacity: fadeIn(frame, a.record, 10)}}>
          <div style={{color: AMBER, fontSize: 22, letterSpacing: 3, textTransform: 'uppercase', marginBottom: 18}}>all in the record</div>
          {tl.record.map((r, i) => (
            <div key={r} style={{opacity: fadeIn(frame, a.record + 6 + i * 8, 6), display: 'flex', gap: 16, alignItems: 'flex-start', marginBottom: 18}}>
              <div style={{color: GREEN, fontSize: 30, lineHeight: 1.2}}>{'✓'}</div>
              <div style={{color: FG, fontSize: 28, lineHeight: 1.25}}>{r}</div>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- beat 8
export const Beat08: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const a = beat.anchors;
  const drift = interpolate(frame, [0, beat.durationInFrames], [0, -50], {extrapolateRight: 'clamp'});
  const card = (at: number): React.CSSProperties => ({
    opacity: fadeIn(frame, at, 10),
    transform: `translateY(${rise(frame, at, 12, 18)}px)`,
    background: 'rgba(11, 15, 20, 0.88)',
    border: `1px solid ${LINE}`,
    borderRadius: 14,
    padding: '16px 26px',
    marginBottom: 14,
    color: FG,
    fontSize: 29,
    lineHeight: 1.3,
  });
  return (
    <AbsoluteFill style={{backgroundColor: BG, overflow: 'hidden', fontFamily: SANS}}>
      <div style={{position: 'absolute', inset: 0, transform: `translateY(${-470 + drift}px)`, filter: 'brightness(0.5)'}}>
        <Img src={staticFile('assets/b08_positions.png')} style={{width: 1920, height: 1080, display: 'block'}} />
      </div>
      <div style={{position: 'absolute', left: 80, top: 110, width: 1000}}>
        <div style={{opacity: fadeIn(frame, beat.lead, 10), transform: `translateY(${rise(frame, beat.lead, 14, 24)}px)`, marginBottom: 18, background: 'rgba(11, 15, 20, 0.88)', border: `1px solid ${LINE}`, borderRadius: 16, padding: '18px 26px 22px'}}>
          <div style={{color: AMBER, fontSize: 128, fontWeight: 700, lineHeight: 1, letterSpacing: -4, textShadow: '0 6px 30px rgba(0,0,0,0.7)'}}>{tl.live.pnl}</div>
          <div style={{color: FG, fontSize: 32, marginTop: 10}}>{tl.live.pnlSub}</div>
          <div style={{color: FG, fontSize: 26, marginTop: 6, opacity: 0.85}}>{tl.live.book}</div>
        </div>
        <div style={card(a.friday)}>{tl.live.flatten}</div>
        <div style={card(a.noise)}>{tl.live.noise}</div>
        <div style={{...card(a.hedge), borderColor: AMBER}}>
          <div style={{color: AMBER, fontWeight: 600}}>{tl.live.hedge}</div>
          <div style={{color: FG, fontSize: 26, marginTop: 4}}>{tl.live.hedgeSub}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- beat 9
export const Beat09: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const a = beat.anchors;
  const drift = interpolate(frame, [0, beat.durationInFrames], [0, -40], {extrapolateRight: 'clamp'});
  const dim = interpolate(frame, [a.trust, a.trust + 12], [1, 0.22], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{backgroundColor: BG, overflow: 'hidden', fontFamily: SANS}}>
      <div style={{position: 'absolute', inset: 0, transform: `translate(235px, ${drift}px)`, filter: `brightness(${dim})`}}>
        <Img src={staticFile('assets/b09_readme.png')} style={{width: 1920, height: 1080, display: 'block'}} />
      </div>
      <div style={{position: 'absolute', left: 240, right: 240, top: 250, bottom: 250, borderRadius: 24, background: 'rgba(11, 15, 20, 0.62)', opacity: fadeIn(frame, a.trust, 12)}} />
      <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingBottom: 120, opacity: fadeIn(frame, a.trust, 12), transform: `translateY(${rise(frame, a.trust, 14, 24)}px)`}}>
        <div style={{color: FG, fontSize: 84, fontWeight: 700, textAlign: 'center', textShadow: '0 6px 30px rgba(0,0,0,0.8)'}}>{tl.close.line}</div>
        <div style={{color: AMBER, fontFamily: MONO, fontSize: 40, marginTop: 34, opacity: fadeIn(frame, a.trust + 10, 10)}}>{tl.close.commands}</div>
        <div style={{color: FG, fontSize: 34, marginTop: 30, opacity: fadeIn(frame, a.trust + 18, 10)}}>{tl.close.url}</div>
        <div style={{color: DIM, fontSize: 28, marginTop: 14, opacity: fadeIn(frame, a.trust + 24, 10)}}>{tl.close.tests}</div>
      </div>
    </AbsoluteFill>
  );
};

export const BEATS: Record<string, React.FC<P>> = {
  b01: Beat01,
  b02: Beat02,
  b03: Beat03,
  b04: Beat04,
  b05: Beat05,
  b06: Beat06,
  b07: Beat07,
  b08: Beat08,
  b09: Beat09,
};
