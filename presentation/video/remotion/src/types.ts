export type Caption = {start: number; end: number; text: string};

export type Beat = {
  id: string;
  kicker: string;
  durationInFrames: number;
  lead: number;
  speech: number;
  audio: string | null;
  captions: Caption[];
  anchors: Record<string, number>;
};

export type GitLine = {hash: string; time: string; subject: string; highlight: boolean};

export type Tenor = {id: string; dte: string; cycles: string; days: string; deployed: boolean};

export type Gate = {n: number; name: string; breaker: boolean};

export type Timeline = {
  fps: number;
  width: number;
  height: number;
  transition: number;
  beats: Beat[];
  facts: Record<string, string | number>;
  verify: {command: string; output: string; count: string};
  gitlog: GitLine[];
  seq30: {header: string; gate5: string[]; positions: string[]; reconcile: string[]};
  fills: string[];
  record: string[];
  race: {title: string; tenors: Tenor[]};
  gates: Gate[];
  live: {pnl: string; pnlSub: string; book: string; flatten: string; noise: string; hedge: string; hedgeSub: string};
  close: {line: string; commands: string; url: string; tests: string};
};
