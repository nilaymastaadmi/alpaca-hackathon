export type Caption = {start: number; end: number; text: string};

export type Beat = {
  id: string;
  label: string;
  durationInFrames: number;
  lead: number;
  speech: number;
  audio: string | null;
  captions: Caption[];
  anchors: Record<string, number>;
  copy: Record<string, string>;
};

export type GitLine = {hash: string; time: string; subject: string; highlight: boolean};

export type Tenor = {id: string; dte: string; cycles: string; days: string; deployed: boolean};

export type Gate = {n: number; name: string; breaker: boolean};

export type Clip = {src: string; last: string; frames: number};

export type Timeline = {
  fps: number;
  width: number;
  height: number;
  transition: number;
  subtitles: boolean;
  strip: string;
  beats: Beat[];
  facts: Record<string, string | number>;
  verify: {command: string; output: string; count: string; steps: [string, string][]};
  gitlog: GitLine[];
  seq30: {header: string; gate5: string[]; positions: string[]; reconcile: string[]};
  fills: string[];
  record: string[];
  race: {title: string; tenors: Tenor[]};
  gates: Gate[];
  live: {pnl: string; pnlSub: string; book: string; flatten: string; noise: string; hedge: string; hedgeSub: string;
    explain: {model: string; explained: number; rejected: number; label: string}};
  close: {line: string; commands: string; url: string; tests: string; wordmark: string};
  clips: {top: Clip; explain: Clip; positions: Clip};
};
