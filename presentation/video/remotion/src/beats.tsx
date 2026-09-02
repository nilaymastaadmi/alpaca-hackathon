import React from 'react';
import {Img, staticFile, useCurrentFrame} from 'remotion';
import type {Beat, Timeline} from './types';
import {
  BigStat, Browser, Card, Chip, Cursor, FlowRow, Footage, GREEN, Headline, Label, MONO, MUTED_I, RED, RED_I, Section, Sticker, Sub, TEXT_I, Terminal, YELLOW, fadeIn, typed, useFps,
} from './ui';

type P = {beat: Beat; tl: Timeline};
const DASH_URL = 'alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app';

// ---------------------------------------------------------------- 01 hook: real dashboard footage
export const Beat01: React.FC<P> = ({beat, tl}) => {
  const a = beat.anchors;
  const c = beat.copy;
  return (
    <Section tone="ink">
      <Label text={beat.label} at={beat.lead} />
      <Browser url={DASH_URL} at={2} x={120} y={130} width={1680} height={800}>
        <Footage clip={tl.clips.top} scale={1680 / 1920} />
      </Browser>
      <Sticker text={c.s1} at={a.trade} x={120} y={950} tone="yellow" until={a.refuse} />
      <Sticker text={c.s2} at={a.refuse} x={120} y={950} tone="black" until={a.n81} />
      <Sticker text={c.s3} at={a.n81} x={120} y={950} tone="yellow" until={a.signed} />
      <Sticker text={c.s4} at={a.signed} x={120} y={950} tone="black" until={a.point} />
      <Sticker text={c.s5} at={a.point} x={120} y={950} tone="yellow" />
    </Section>
  );
};

// ---------------------------------------------------------------- 02 thesis, then the git proof
export const Beat02: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const fps = useFps();
  const a = beat.anchors;
  const c = beat.copy;
  const cmd = 'git log --diff-filter=A --reverse --date=iso -- research/PREREGISTRATION_R1.md backtest/';
  const cmdAt = a.pre + 14;
  const cmdDone = cmdAt + Math.ceil((cmd.length * fps) / 50);
  const linesAt = cmdDone + 8;
  const stampAt = Math.max(a.git, linesAt + 40);
  return (
    <Section tone="cream">
      <Label text={beat.label} at={beat.lead} />
      <Headline segs={[{t: 'Options are priced richer than the move that '}, {t: 'follows.', hi: 'yellow'}]} at={beat.lead + 4} size={80} top={140} width={1560} />
      <Sub text={c.sub} at={beat.lead + 44} top={352} size={30} width={1400} until={a.pre} />
      <Sticker text={c.s1} at={a.pre} x={80} y={345} tone="black" size={32} />
      <Terminal title="alpaca-hackathon (main)" at={a.pre + 4} style={{left: 80, top: 440, width: 1760, height: 520}} fontSize={24}>
        <span style={{color: GREEN}}>$ </span>
        {typed(cmd, frame, cmdAt, 50, fps)}
        <Cursor visible={frame < cmdDone} />
        {'\n'}
        {tl.gitlog.map((l, i) => {
          const at = linesAt + i * 8;
          const hot = l.highlight && frame >= Math.max(a.git, at + 12);
          return (
            <div key={l.hash} style={{opacity: fadeIn(frame, at, 4), marginTop: 10, lineHeight: 1.4}}>
              <span style={{color: YELLOW}}>{l.hash}</span>{' '}
              <span style={{color: hot ? '#14161a' : MUTED_I, background: hot ? YELLOW : 'transparent', padding: hot ? '0 6px' : 0, fontWeight: hot ? 700 : 400}}>{l.time}</span>
              {'  '}
              <span style={{color: l.highlight ? TEXT_I : MUTED_I}}>{l.subject}</span>
            </div>
          );
        })}
        <div style={{marginTop: 22, opacity: fadeIn(frame, stampAt + 10, 10), borderTop: '1px solid #2a2f38', paddingTop: 14, color: TEXT_I}}>
          <span style={{color: YELLOW, fontWeight: 700}}>19:57</span> pre-registered.{'   '}
          <span style={{color: YELLOW, fontWeight: 700}}>20:01</span> first backtest commit.{'   '}
          <span style={{color: MUTED_I}}>Four minutes, in the right order.</span>
        </div>
      </Terminal>
    </Section>
  );
};

// ---------------------------------------------------------------- 03 the evidence
export const Beat03: React.FC<P> = ({beat}) => {
  const a = beat.anchors;
  const c = beat.copy;
  return (
    <Section tone="ink">
      <Label text={beat.label} at={beat.lead} />
      <BigStat value="+3.68" label="mean VRP, vol points" at={a.vrp} x={80} y={200} size={150} />
      <BigStat value="1,741" label="daily observations, 6.99 years" at={a.obs} x={640} y={200} size={150} />
      <BigStat value="t = +4.74" label="Newey-West corrected" at={a.t} x={1170} y={200} size={150} color={GREEN} />
      <BigStat value="t = +18.16" label="naive, invalid" at={a.naive} x={80} y={560} size={120} color={MUTED_I} strike strikeAt={a.naive + 16} />
      <Sub text={c.sub} at={a.naive + 18} top={575} left={760} size={28} width={1080} />
      <Sticker text={c.s1} at={a.honest} x={80} y={880} tone="yellow" />
    </Section>
  );
};

// ---------------------------------------------------------------- 04 eleven gates
export const Beat04: React.FC<P> = ({beat, tl}) => {
  const a = beat.anchors;
  const c = beat.copy;
  const n = tl.gates.length;
  const gateAt = (i: number) => a.listStart + Math.round(((a.listEnd - a.listStart) * i) / Math.max(1, n - 1));
  return (
    <Section tone="cream">
      <Label text={beat.label} at={beat.lead} />
      <Headline segs={[{t: 'Eleven numbered gates, then a '}, {t: 'stagger rule.', hi: 'yellow'}]} at={beat.lead + 4} size={68} top={140} width={1760} hiAt={a.stagger} />
      <div style={{position: 'absolute', left: 80, top: 330, width: 1760}}>
        {tl.gates.map((g, i) => (
          <Chip key={g.n} text={`${g.n}  ${g.name}`} at={gateAt(i)} color={g.breaker ? RED : undefined} size={24} />
        ))}
        <Chip text="+  stagger rule: one position per expiry" at={a.stagger} fill size={24} />
      </div>
      <Sticker text={c.s1} at={a.listEnd + 12} x={80} y={560} tone="black" size={32} />
      <FlowRow
        at={a.mcp}
        x={80}
        y={700}
        items={[
          {t: 'market data', s: 'via MCP'},
          {t: 'signals', s: 'VRP, term structure'},
          {t: '11 gates', s: 'numbered 0 to 10', hot: true},
          {t: 'execute or refuse', s: 'via MCP'},
          {t: 'Merkle artifact', s: 'make verify'},
        ]}
      />
      <Sub text={c.sub} at={a.mcp + 30} top={880} size={24} mono width={1700} />
    </Section>
  );
};

// ---------------------------------------------------------------- 05 raced live
export const Beat05: React.FC<P> = ({beat, tl}) => {
  const a = beat.anchors;
  const c = beat.copy;
  const t = tl.race.tenors;
  return (
    <Section tone="ink">
      <Label text={beat.label} at={beat.lead} />
      <Headline segs={[{t: 'Three tenors raced on the real market. The one that traded '}, {t: 'won.', hi: 'green'}]} at={beat.lead + 4} size={70} top={140} width={1560} hiAt={a.won} />
      <Card icon="cross" title={`${t[0].id}, ${t[0].dte}`} sub={`${t[0].cycles} cycles would enter, ${t[0].days} days`} at={a.three} x={80} y={400} width={880} />
      <Card icon="cross" title={`${t[2].id}, ${t[2].dte}`} sub={`${t[2].cycles} cycles would enter, ${t[2].days} days`} at={a.three + 10} x={80} y={540} width={880} />
      <Card icon="check" title={`${t[1].id}, ${t[1].dte}: deployed`} sub={`${t[1].cycles} cycles would enter, ${t[1].days} days`} at={a.three + 20} x={80} y={680} width={880} hot hotAt={a.won} />
      <Sticker text={c.s1} at={a.won + 8} x={1040} y={690} tone="yellow" />
      <Sub text={c.sub} at={a.eight} top={890} size={22} mono width={1700} />
    </Section>
  );
};

// ---------------------------------------------------------------- 06 one command
export const Beat06: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const fps = useFps();
  const a = beat.anchors;
  const c = beat.copy;
  const c1 = '# artifacts/decisions.jsonl: every decision, fill and refusal is a leaf';
  const c2 = '# SHA-256 Merkle tree, domain-separated leaves and nodes, root sealed before outcomes are known';
  const cmd = tl.verify.command;
  const cmdDone = a.command + Math.ceil((cmd.length * fps) / 14);
  const outAt = cmdDone + 12;
  const out = tl.verify.output;
  const idx = out.indexOf('VERIFIED');
  return (
    <Section tone="ink">
      <Label text={beat.label} at={beat.lead} />
      <Terminal title="alpaca-hackathon (main)" style={{left: 80, top: 140, width: 1760, height: 580}} fontSize={30}>
        <span style={{color: MUTED_I}}>{typed(c1, frame, beat.lead, 70, fps)}</span>
        {'\n'}
        <span style={{color: MUTED_I}}>{typed(c2, frame, a.sealed, 70, fps)}</span>
        {'\n\n'}
        <span style={{opacity: frame >= a.command ? 1 : 0}}>
          <span style={{color: GREEN}}>$ </span>
          {typed(cmd, frame, a.command, 14, fps)}
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
      <Sticker text={c.s1} at={outAt + 14} x={80} y={800} tone="yellow" />
      <Sticker text={`${tl.verify.count} sealed artifacts, one root.`} at={outAt + 34} x={1180} y={800} tone="cream" />
    </Section>
  );
};

// ---------------------------------------------------------------- 07 the incident
const CodeBlock: React.FC<{lines: string[]; at: number; label: string; frame: number; hot?: boolean}> = ({lines, at, label, frame, hot}) => (
  <div style={{opacity: fadeIn(frame, at, 8), marginBottom: 18, borderLeft: `5px solid ${hot ? YELLOW : '#2a2f38'}`, paddingLeft: 18}}>
    <div style={{color: RED_I, fontFamily: MONO, fontSize: 15, letterSpacing: 3, textTransform: 'uppercase', marginBottom: 4}}>{label}</div>
    {lines.map((l, i) => (
      <div key={i} style={{color: l.includes('SPY261002C00792000') || l.includes('0/5 positions open') || l.includes('no legs at broker') ? YELLOW : TEXT_I, fontFamily: MONO, fontSize: 21, lineHeight: 1.45, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere'}}>
        {l}
      </div>
    ))}
  </div>
);

export const Beat07: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const a = beat.anchors;
  const c = beat.copy;
  return (
    <Section tone="cream">
      <Label text={beat.label} at={beat.lead} />
      <Headline segs={[{t: 'On the first live morning it stacked '}, {t: 'four', hi: 'yellow'}, {t: ' condors instead of one.'}]} at={a.morning} size={70} top={140} width={1600} hiAt={a.four} />
      <Sub text={c.sub} at={a.four + 8} top={330} size={24} mono width={1760} />
      <Terminal title={tl.seq30.header} at={a.flat} style={{left: 80, top: 400, width: 1120, height: 500}} fontSize={21}>
        <CodeBlock frame={frame} at={a.flat + 6} lines={tl.seq30.gate5} label="gate 5, capacity: the agent believed it was flat" />
        <CodeBlock frame={frame} at={a.raw} lines={tl.seq30.positions} label="mcp_calls[1]: the broker had already answered with the legs" hot />
        <CodeBlock frame={frame} at={a.recon} lines={tl.seq30.reconcile} label="reconciliation: the same record ignored them" hot />
      </Terminal>
      <Sticker text={c.s1} at={a.recon + 8} x={1240} y={400} tone="black" size={30} maxWidth={600} />
      {[c.r1, c.r2, c.r3, c.r4].map((r, i) => (
        <Card key={r} icon="check" title={r} at={a.record + i * 8} x={1240} y={520 + i * 118} width={600} size={26} />
      ))}
    </Section>
  );
};

// ---------------------------------------------------------------- 08 live, so far
export const Beat08: React.FC<P> = ({beat, tl}) => {
  const a = beat.anchors;
  const c = beat.copy;
  return (
    <Section tone="ink">
      <Label text={beat.label} at={beat.lead} />
      <Browser url={DASH_URL} at={beat.lead + 6} x={940} y={130} width={900} height={780}>
        <Footage clip={tl.clips.positions} scale={0.68} />
      </Browser>
      <BigStat value={tl.facts.LIVE_PNL_TEXT as string} label="so far, on a $100,000 paper account" at={beat.lead + 4} x={80} y={170} size={150} width={820} />
      <Sub text={tl.live.book} at={beat.lead + 30} top={380} size={22} mono width={820} />
      <Sticker text={c.s1} at={a.friday} x={80} y={470} tone="yellow" size={30} maxWidth={820} />
      <Sticker text={c.s2} at={a.noise} x={80} y={590} tone="black" size={30} maxWidth={820} />
      <Card icon="check" title={tl.live.hedge} at={a.hedge} x={80} y={700} width={820} />
      <Card icon="cross" title={c.hedgeNo} sub={tl.live.hedgeSub} at={a.hedge + 14} x={80} y={810} width={820} />
    </Section>
  );
};

// ---------------------------------------------------------------- 09 close
export const Beat09: React.FC<P> = ({beat, tl}) => {
  const frame = useCurrentFrame();
  const fps = useFps();
  const a = beat.anchors;
  const c = beat.copy;
  const cmds = ['git clone github.com/nilaymastaadmi/alpaca-hackathon', 'make test', 'make verify', 'make summary'];
  return (
    <Section tone="cream">
      <Label text={beat.label} at={beat.lead} />
      <Browser url="github.com/nilaymastaadmi/alpaca-hackathon" at={beat.lead + 4} x={1000} y={130} width={840} height={880}>
        <Img src={staticFile('assets/b09_readme.png')} style={{width: 1920, height: 1080, transform: 'translateX(-31px) scale(0.62)', transformOrigin: 'top left', display: 'block'}} />
      </Browser>
      <div style={{position: 'absolute', left: 80, top: 150, fontFamily: MONO, fontSize: 26, color: '#14161a', lineHeight: 1.7}}>
        {cmds.map((k, i) => {
          const at = a.clone + i * 14;
          return (
            <div key={k} style={{opacity: frame >= at ? 1 : 0}}>
              <span style={{color: RED}}>$ </span>
              {typed(k, frame, at, 60, fps)}
            </div>
          );
        })}
      </div>
      <Headline segs={[{t: 'You do not have to '}, {t: 'trust me.', hi: 'yellow'}]} at={a.trust} perWord={5} size={80} top={420} width={880} />
      <Sub text={c.sub} at={a.trust + 40} top={660} size={30} width={880} />
      <Sub text={tl.close.tests} at={a.trust + 52} top={900} size={20} mono width={880} />
    </Section>
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
