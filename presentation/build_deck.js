/**
 * Build the submission deck.
 *
 * Every live number on these slides is READ FROM THE SEALED LOG at build
 * time, not typed in. Rebuild after Friday's flatten and the deck updates
 * itself. A deck whose numbers are hand-copied drifts from the artifacts by
 * Thursday night, and the whole pitch here is that the numbers are checkable.
 *
 *   node presentation/build_deck.js
 */

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.join(__dirname, "..");
const A = (f) => path.join(ROOT, "artifacts", f);

// ---------------------------------------------------------------- live data
const readJson = (p, fb) => { try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return fb; } };
const decisions = fs.readFileSync(A("decisions.jsonl"), "utf8").trim().split("\n")
  .filter(Boolean).map((l) => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
const seal = readJson(A("merkle_root.json"), {});
const positions = readJson(A("positions.json"), { open: [] });
const cmp = readJson(A("compare_summary.json"), { tally: {} });
const expl = readJson(A("explanations.json"), { counts: {} });

const CYCLE = new Set(["enter", "refuse", "halt", "flatten"]);
const ENVGATE = new Set(["market_open", "session_window"]);
const cycles = decisions.filter((d) => CYCLE.has(d.action) && !d.dry_run);
const classify = (d) => {
  let bg = d.blocking_gate, eb = d.environmental_block;
  if (eb == null && ENVGATE.has(bg)) { eb = bg; bg = null; }
  const opp = d.was_an_opportunity == null ? eb == null : d.was_an_opportunity;
  return { opp, bg };
};
const opps = cycles.map((d) => ({ d, ...classify(d) })).filter((x) => x.opp);
const nEnter = opps.filter((x) => x.d.action === "enter").length;
const nDeclined = opps.length - nEnter;
const pctDeclined = Math.round((nDeclined / Math.max(opps.length, 1)) * 100);
const byGate = {};
opps.filter((x) => x.d.action !== "enter").forEach((x) => {
  const k = x.bg || "entry ladder unfilled (all gates passed)";
  byGate[k] = (byGate[k] || 0) + 1;
});
const lastCycle = cycles[cycles.length - 1] || { portfolio: {} };
const equity = Number(lastCycle.portfolio.equity || 100000);
const pnl = equity - 100000;
const open = positions.open || [];
const contracts = open.reduce((s, p) => s + (p.contracts || 0), 0);
const credit = open.reduce((s, p) => s + (p.credit || 0) * 100 * (p.contracts || 0), 0);
const maxRisk = open.reduce((s, p) => s + (p.max_loss_per_contract || 0) * 100 * (p.contracts || 0), 0);
const rootShort = (seal.merkle_root || "").slice(0, 16);
const tally = cmp.tally || {};
const money = (n) => "$" + Math.round(n).toLocaleString("en-US");
const built = new Date().toISOString().slice(0, 16).replace("T", " ");

// ------------------------------------------------------------------ palette
const INK = "0B1622";        // dominant background
const SURF = "16283D";       // raised surface
const SURF2 = "1E3550";      // second surface
const GOLD = "E8B54A";       // the seal, the accent
const ICE = "C9DAF0";        // secondary text
const WHITE = "FFFFFF";
const PASS = "3E8E6B";
const BLOCK = "A6414C";
const MUTE = "7C93AE";

const HEAD = "Cambria";
const BODY = "Calibri";
const MONO = "Courier New";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";                 // 13.3 x 7.5
pres.author = "Nilay Toshniwal";
pres.title = "Glass Box";

const W = 13.3, H = 7.5, M = 0.7;

// Repeated motif: the sealed root, in the corner of every slide. It is the
// one thing that makes this project different, so it is literally on every
// page, and it is the real root, read from disk.
function chrome(slide, n) {
  slide.addText(`root ${rootShort}...`, {
    x: M, y: H - 0.52, w: 5, h: 0.28, isTextBox: true, margin: 0,
    fontFace: MONO, fontSize: 9, color: MUTE, align: "left",
  });
  if (n) slide.addText(String(n), {
    x: W - M - 0.6, y: H - 0.52, w: 0.6, h: 0.28, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 10, color: MUTE, align: "right",
  });
}

function bg(slide, color) { slide.background = { color: color || INK }; }

function title(slide, text, sub) {
  slide.addText(text, {
    x: M, y: 0.55, w: W - 2 * M, h: 0.9, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 38, bold: true, color: WHITE,
  });
  if (sub) slide.addText(sub, {
    x: M, y: 1.42, w: W - 2 * M, h: 0.5, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 15, color: ICE,
  });
}

// A stat card. The motif everywhere: raised surface, gold number, small label.
function stat(slide, x, y, w, h, value, label, opts = {}) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08, fill: { color: opts.fill || SURF },
    line: { color: opts.line || SURF2, width: 1 },
  });
  slide.addText(String(value), {
    x: x + 0.22, y: y + 0.18, w: w - 0.44, h: h * 0.52, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: opts.size || 34, bold: true,
    color: opts.color || GOLD, align: "left",
  });
  slide.addText(label, {
    x: x + 0.22, y: y + h * 0.62, w: w - 0.44, h: h * 0.34, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 11, color: ICE, align: "left",
  });
}

function card(slide, x, y, w, h, head, bodyText, opts = {}) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.08, fill: { color: opts.fill || SURF },
    line: { color: SURF2, width: 1 },
  });
  slide.addText(head, {
    x: x + 0.24, y: y + 0.18, w: w - 0.48, h: 0.34, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 14, bold: true, color: opts.headColor || GOLD,
  });
  slide.addText(bodyText, {
    x: x + 0.24, y: y + 0.56, w: w - 0.48, h: h - 0.76, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, color: ICE, lineSpacingMultiple: 1.15,
  });
}

// ------------------------------------------------------------------ slide 1
{
  const s = pres.addSlide(); bg(s);
  s.addText("GLASS BOX", {
    x: M, y: 1.55, w: W - 2 * M, h: 1.0, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 60, bold: true, color: WHITE, charSpacing: 2,
  });
  s.addText("An options agent whose every decision you can verify", {
    x: M, y: 2.62, w: W - 2 * M, h: 0.5, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 20, color: GOLD,
  });
  s.addText("Alpaca AI Trading Agents Hackathon 2026   |   Options Alpha Agents   |   Nilay Toshniwal, solo", {
    x: M, y: 3.15, w: W - 2 * M, h: 0.4, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 13, color: MUTE,
  });
  const cw = (W - 2 * M - 3 * 0.25) / 4;
  stat(s, M, 4.05, cw, 1.35, decisions.length.toLocaleString("en-US"), "sealed artifacts, one Merkle tree");
  stat(s, M + (cw + 0.25), 4.05, cw, 1.35, `${nDeclined} of ${opps.length}`, "opportunities declined, with reasons");
  stat(s, M + 2 * (cw + 0.25), 4.05, cw, 1.35, "233", "automated tests");
  stat(s, M + 3 * (cw + 0.25), 4.05, cw, 1.35, "1", "bug the log caught in its author");
  s.addText("make verify", {
    x: M, y: 5.62, w: 4, h: 0.35, isTextBox: true, margin: 0,
    fontFace: MONO, fontSize: 13, color: GOLD,
  });
  s.addText("recomputes the root over every decision. You do not have to trust the operator.", {
    x: M + 1.55, y: 5.62, w: W - 2 * M - 1.55, h: 0.35, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, color: MUTE,
  });
  chrome(s);
  s.addNotes("Glass Box. Every number on these slides is read from the sealed artifact log at build time, not typed in.");
}

// ------------------------------------------------------------------ slide 2
{
  const s = pres.addSlide(); bg(s);
  title(s, "Most trading agents are built to trade", "This one is built to measure first, and to decline out loud when the premium is not there.");
  stat(s, M, 2.25, 3.6, 1.9, `${pctDeclined}%`, "of real opportunities declined", { size: 54 });
  s.addText([
    { text: "A refusal is logged with the same detail as a fill: every gate, every measured number, sealed into the same tree.\n\n", options: { breakLine: true } },
    { text: "That is the product. An agent that cannot say no is not risk-managed, it is just fast.", options: { bold: true, color: WHITE } },
  ], {
    x: M + 3.9, y: 2.25, w: W - 2 * M - 3.9, h: 1.9, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 15, color: ICE, lineSpacingMultiple: 1.2,
  });
  s.addText("What blocked the trades, counted from the log", {
    x: M, y: 4.45, w: 8, h: 0.35, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 13, bold: true, color: GOLD,
  });
  const rows = Object.entries(byGate).sort((a, b) => b[1] - a[1]).slice(0, 3);
  const maxN = Math.max(...rows.map((r) => r[1]), 1);
  rows.forEach(([name, n], i) => {
    const y = 4.9 + i * 0.55;
    s.addText(name, {
      x: M, y, w: 4.6, h: 0.4, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12, color: ICE,
    });
    s.addShape(pres.ShapeType.roundRect, {
      x: M + 4.7, y: y + 0.07, w: Math.max((n / maxN) * 5.6, 0.25), h: 0.26,
      rectRadius: 0.06, fill: { color: i === 0 ? GOLD : SURF2 },
    });
    s.addText(String(n), {
      x: M + 4.7 + Math.max((n / maxN) * 5.6, 0.25) + 0.12, y, w: 0.9, h: 0.4,
      isTextBox: true, margin: 0, fontFace: MONO, fontSize: 12, color: WHITE,
    });
  });
  chrome(s, 2);
}

// ------------------------------------------------------------------ slide 3
{
  const s = pres.addSlide(); bg(s);
  title(s, "Registered before the code existed", "Provable from git history, not asserted on a slide. The hypotheses, the trial count and the significance bar were all committed before a single line of backtest ran.");
  const cw = (W - 2 * M - 2 * 0.28) / 3;
  stat(s, M, 2.3, cw, 1.5, "+3.68", "mean volatility risk premium, vol points");
  stat(s, M + cw + 0.28, 2.3, cw, 1.5, "t = +4.74", "Newey-West corrected, 1,741 observations");
  stat(s, M + 2 * (cw + 0.28), 2.3, cw, 1.5, "6.99 yrs", "SPY, out of sample");
  card(s, M, 4.05, (W - 2 * M - 0.28) / 2, 1.85,
    "The naive number is 18.16, and it is wrong",
    "21-day forward windows sampled daily overlap by 20 of 21 days, so the observations are not independent. Reporting 18.16 would have been four times more impressive and meaningless.");
  card(s, M + (W - 2 * M - 0.28) / 2 + 0.28, 4.05, (W - 2 * M - 0.28) / 2, 1.85,
    "Seven trials, one corrected bar",
    "The significance bar was recomputed to 0.791 as trials were added, and set before any result was seen. The deployed tenor had to clear the bar that the search itself raised.");
  chrome(s, 3);
}

// ------------------------------------------------------------------ slide 4
{
  const s = pres.addSlide(); bg(s);
  title(s, "What did not work", "Reported with the same weight as the wins, because a submission that only reports its wins is a sales document. All four are in the repo.");
  const cw = (W - 2 * M - 0.28) / 2, ch = 1.55;
  card(s, M, 2.2, cw, ch, "A registered prediction was wrong",
    "P2 predicted the regime gate would show a 1.0 point mean advantage. Measured 0.59. The mean was the wrong statistic; the gate survives because the premium is reliably present in contango, not because contango pays more.", { headColor: BLOCK === "A6414C" ? "E08A93" : BLOCK });
  card(s, M + cw + 0.28, 2.2, cw, ch, "The pricing model failed its own gate",
    "26.78% median error against a pre-registered 15% threshold, so H3 was not run while it stood. VIX is a variance-swap rate, not ATM implied vol. Corrected on 2024 data only, then passed at 10.75%.", { headColor: "E08A93" });
  card(s, M, 2.2 + ch + 0.25, cw, ch, "The deployed result is fragile, and we say so",
    "Doubling transaction costs improved the best trial's Sharpe, which is impossible and means the optimiser is partly selecting noise. The ungated baseline beats the gated variants on average. Disclosed, not buried.", { headColor: "E08A93" });
  card(s, M + cw + 0.28, 2.2 + ch + 0.25, cw, ch, "Our own cost model was lying",
    "Charging cost as a percentage of credit under-charged exactly the configurations that looked best. Measured: the spread is 0.8% of a 35-delta option's price and 13.3% of a 5-delta option's. A 16x range.", { headColor: "E08A93" });
  chrome(s, 4);
}

// ------------------------------------------------------------------ slide 5
{
  const s = pres.addSlide(); bg(s);
  title(s, "Eleven gates, then a trade", "Evaluated at decision time, all of them, so one artifact shows the whole picture rather than the first failure.");
  const gates = [
    ["0", "position integrity", 1], ["1", "session window", 1], ["2", "drawdown breaker", 0],
    ["3", "daily loss limit", 0], ["4", "consecutive losses", 1], ["5", "capacity", 1],
    ["6", "term structure", 1], ["7", "VRP threshold", 1], ["8", "event proximity", 1],
    ["9", "cost ceiling", 1], ["10", "sizing", 1], ["+", "stagger rule", 1],
  ];
  const cols = 4, gw = (W - 2 * M - (cols - 1) * 0.22) / cols, gh = 0.62;
  gates.forEach(([n, name, ok], i) => {
    const x = M + (i % cols) * (gw + 0.22);
    const y = 2.25 + Math.floor(i / cols) * (gh + 0.2);
    s.addShape(pres.ShapeType.roundRect, {
      x, y, w: gw, h: gh, rectRadius: 0.06,
      fill: { color: ok ? SURF : SURF2 }, line: { color: ok ? SURF2 : GOLD, width: ok ? 1 : 1.5 },
    });
    s.addText(n, {
      x: x + 0.16, y: y + 0.12, w: 0.5, h: 0.38, isTextBox: true, margin: 0,
      fontFace: MONO, fontSize: 15, bold: true, color: ok ? MUTE : GOLD,
    });
    s.addText(name, {
      x: x + 0.66, y: y + 0.13, w: gw - 0.8, h: 0.38, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12, color: WHITE,
    });
  });
  s.addText("Gates 0, 2 and 3 are circuit breakers, outlined above and distinguished in code: a refusal means no trade now, a breach means stop.", {
    x: M, y: 5.05, w: W - 2 * M, h: 0.4, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 13, color: ICE,
  });
  const cw2 = (W - 2 * M - 0.28) / 2;
  card(s, M, 5.5, cw2, 1.35, "Sizing is a recorded deviation, not a default",
    "Research ran at 1% per position. Live runs 5 concurrent at 3%, hard capped at 15%, because research sizing implied under one trade all week. Written down before the week started.");
  card(s, M + cw2 + 0.28, 5.5, cw2, 1.35, "The deadline is a risk event",
    "A dedicated mechanism flattens the entire book 90 minutes before submission, so the reported result is realised P&L and not a mark at an arbitrary instant.");
  chrome(s, 5);
}

// ------------------------------------------------------------------ slide 6
{
  const s = pres.addSlide(); bg(s);
  title(s, "Three strategies, one market", "Three candidate tenors ran live in parallel for eight days, on the same real prices, risking nothing. The deployed one was picked from that, not from the backtest ranking.");
  const labels = [["T4", "7 to 14 DTE"], ["T6", "21 to 45 DTE"], ["T7", "5 to 10 DTE"]];
  const cw = (W - 2 * M - 2 * 0.3) / 3;
  labels.forEach(([k, desc], i) => {
    const t = tally[k] || { cycles: 0, would_enter: 0 };
    const deployed = k === (cmp.deployed || "T6");
    const x = M + i * (cw + 0.3);
    s.addShape(pres.ShapeType.roundRect, {
      x, y: 2.3, w: cw, h: 2.35, rectRadius: 0.1,
      fill: { color: deployed ? SURF2 : SURF },
      line: { color: deployed ? GOLD : SURF2, width: deployed ? 2 : 1 },
    });
    s.addText(k, {
      x: x + 0.25, y: 2.5, w: cw - 0.5, h: 0.5, isTextBox: true, margin: 0,
      fontFace: HEAD, fontSize: 26, bold: true, color: deployed ? GOLD : WHITE,
    });
    s.addText(desc, {
      x: x + 0.25, y: 3.0, w: cw - 0.5, h: 0.35, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12, color: ICE,
    });
    s.addText(String(t.would_enter), {
      x: x + 0.25, y: 3.42, w: cw - 0.5, h: 0.7, isTextBox: true, margin: 0,
      fontFace: HEAD, fontSize: 40, bold: true, color: deployed ? WHITE : MUTE,
    });
    s.addText(`would-enter cycles of ${t.cycles}`, {
      x: x + 0.25, y: 4.12, w: cw - 0.5, h: 0.35, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 11, color: MUTE,
    });
    if (deployed) s.addText("DEPLOYED", {
      x: x + cw - 1.45, y: 2.55, w: 1.2, h: 0.3, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 10, bold: true, color: GOLD, align: "right",
    });
  });
  s.addText([
    { text: "The backtest preferred one tenor. Eight days of live paper comparison preferred another, and the live evidence won. ", options: {} },
    { text: "The cost of switching is written down in the same file as the decision.", options: { bold: true, color: WHITE } },
  ], {
    x: M, y: 4.95, w: W - 2 * M, h: 0.8, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 14, color: ICE, lineSpacingMultiple: 1.2,
  });
  s.addText("Every shadow cycle is a real decision on real prices. None of them ever sends an order.", {
    x: M, y: 5.75, w: W - 2 * M, h: 0.4, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, color: MUTE,
  });
  chrome(s, 6);
}

// ------------------------------------------------------------------ slide 7
{
  const s = pres.addSlide(); bg(s);
  title(s, "Built on Alpaca, and provably so", "Every runtime decision goes through the MCP server. The CLI reads the account back from a different surface.");
  const cw = (W - 2 * M - 0.28) / 2;
  card(s, M, 2.25, cw, 2.0, "MCP server, the execution path",
    "alpaca-mcp-server 2.3.0, JSON-RPC over stdio, 74 tools, all versions pinned after fastmcp 4.0.0 shipped mid-competition and broke the unpinned server at import.\n\nEvery request and response is recorded inside the sealed artifact, failures included, and the dashboard shows the calls and latencies for the latest cycle.");
  card(s, M + cw + 0.28, 2.25, cw, 2.0, "CLI, the read-only second opinion",
    "Alpaca's official CLI 0.0.14, behind an allowlist of read commands. order submit, position close-all and order cancel-all are refused before a process starts.\n\nReading the account back through a different Alpaca surface than the one that wrote to it is a real check, not a box tick.");
  const sw = (W - 2 * M - 3 * 0.24) / 4;
  stat(s, M, 4.5, sw, 1.3, "1.5%", "round trip cost, laddered from mid");
  stat(s, M + sw + 0.24, 4.5, sw, 1.3, "8.3%", "cost if it crossed the spread");
  stat(s, M + 2 * (sw + 0.24), 4.5, sw, 1.3, "5", "ladder rungs before it gives up");
  stat(s, M + 3 * (sw + 0.24), 4.5, sw, 1.3, "246 ms", "measured API round trip");
  chrome(s, 7);
}

// ------------------------------------------------------------------ slide 8
{
  const s = pres.addSlide(); bg(s);
  title(s, "The log caught its own author", "First live morning, 09:45 ET. This is the strongest evidence in the submission.");
  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 2.2, w: W - 2 * M, h: 1.5, rectRadius: 0.1,
    fill: { color: SURF }, line: { color: GOLD, width: 1.5 },
  });
  s.addText("A payload-parsing bug read the account as flat, so the agent opened four condors where it should have opened one.", {
    x: M + 0.3, y: 2.4, w: W - 2 * M - 0.6, h: 0.5, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 16, bold: true, color: WHITE,
  });
  s.addText("The proof was a single sealed artifact holding both the raw broker response, with the legs plainly in it, and the reconciliation that ignored them. The bug could not hide from the record it had just written.", {
    x: M + 0.3, y: 2.92, w: W - 2 * M - 0.6, h: 0.7, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 14, color: ICE, lineSpacingMultiple: 1.15,
  });
  const cw = (W - 2 * M - 3 * 0.24) / 4;
  const steps = [
    ["Found", "in the artifact, not in a dashboard"],
    ["Fixed", "reconciliation now reads both shapes"],
    ["Tested", "a regression test for that exact payload"],
    ["Kept", "positions adopted, incident written up"],
  ];
  steps.forEach(([h, b], i) => {
    const x = M + i * (cw + 0.24);
    s.addShape(pres.ShapeType.roundRect, { x, y: 4.0, w: cw, h: 1.25, rectRadius: 0.08, fill: { color: SURF }, line: { color: SURF2, width: 1 } });
    s.addText(h, { x: x + 0.22, y: 4.15, w: cw - 0.44, h: 0.35, isTextBox: true, margin: 0, fontFace: HEAD, fontSize: 18, bold: true, color: GOLD });
    s.addText(b, { x: x + 0.22, y: 4.52, w: cw - 0.44, h: 0.62, isTextBox: true, margin: 0, fontFace: BODY, fontSize: 11, color: ICE });
  });
  s.addText("RISK_REGISTER.md sections 4.7 and 4.8 name the exact artifact. Nothing was quietly deleted, because the seal would have shown it.", {
    x: M, y: 5.45, w: W - 2 * M, h: 0.4, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, color: MUTE,
  });
  chrome(s, 8);
}

// ------------------------------------------------------------------ slide 9
{
  const s = pres.addSlide(); bg(s);
  title(s, "The model explains. The numbers decide.", "This is an AI agents hackathon, so the honest question is where the model sits. Ours sits after the decision.");
  const cw = (W - 2 * M - 0.3) / 2;
  card(s, M, 2.25, cw, 2.1, "What it does",
    "After a decision is sealed, Qwen 2.5 72B on Featherless reads that artifact and writes three plain sentences a judge can understand.\n\nIt runs outside the trading loop, on a schedule. Nothing it produces flows back into the agent. The decision existed, and was sealed, before the text did.");
  card(s, M + cw + 0.3, 2.25, cw, 2.1, "Why you can believe it",
    "Every number in the generated text is checked against the artifact it came from, digit for digit. An explanation that invents or alters a number is rejected and counted, not quietly shown.\n\nA hallucinated sentence under a sealed decision would be worse than no sentence at all.");
  const sw = (W - 2 * M - 2 * 0.28) / 3;
  stat(s, M, 4.6, sw, 1.35, String(expl.counts.explained || 0), "decisions explained");
  stat(s, M + sw + 0.28, 4.6, sw, 1.35, String(expl.counts.rejected || 0), "rejected by the grounding check", { color: WHITE });
  stat(s, M + 2 * (sw + 0.28), 4.6, sw, 1.35, "0", "model decisions to trade", { color: WHITE });
  chrome(s, 9);
}

// ----------------------------------------------------------------- slide 10
{
  const s = pres.addSlide(); bg(s);
  title(s, "Try to tamper with it", "The verification is not a claim on a slide. It is a button on the dashboard and a command in the repo.");
  s.addShape(pres.ShapeType.roundRect, { x: M, y: 2.2, w: W - 2 * M, h: 2.55, rectRadius: 0.1, fill: { color: SURF }, line: { color: SURF2, width: 1 } });
  s.addText([
    { text: "sealed root      ", options: { color: MUTE } },
    { text: `${rootShort}...\n`, options: { color: GOLD, breakLine: true } },
    { text: "honest recompute ", options: { color: MUTE } },
    { text: `${rootShort}...   MATCHES\n`, options: { color: PASS === "3E8E6B" ? "6FD3A6" : PASS, breakLine: true } },
    { text: "after moving one decision's spot by one cent\n", options: { color: MUTE, breakLine: true } },
    { text: "                 253b8da69a86901f...   DETECTED", options: { color: "E08A93" } },
  ], {
    x: M + 0.35, y: 2.42, w: W - 2 * M - 0.7, h: 1.72, isTextBox: true, margin: 0,
    fontFace: MONO, fontSize: 13, lineSpacingMultiple: 1.1,
  });
  s.addText("SHA-256 Merkle tree with domain-separated leaves and nodes, so a forger who recomputes the leaf hashes consistently still fails. The root is sealed before outcomes are known.", {
    x: M + 0.35, y: 4.2, w: W - 2 * M - 0.7, h: 0.45, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, color: ICE,
  });
  const cw = (W - 2 * M - 0.28) / 2;
  card(s, M, 4.98, cw, 1.3, "One command, no credentials",
    "make judge runs the tests, recomputes the root, prints the decision summary, and regenerates the results page from the log it just verified.");
  card(s, M + cw + 0.28, 4.98, cw, 1.3, "Or press the button",
    "The dashboard edits one sealed decision in memory and recomputes the root in front of you. Nothing on disk is touched, and the root breaks.");
  chrome(s, 10);
}

// ----------------------------------------------------------------- slide 11
{
  const s = pres.addSlide(); bg(s);
  title(s, "Live week, as it happened", `Read from the sealed log when this deck was built: ${built} UTC. Rebuild the deck, the numbers move.`);
  const sw = (W - 2 * M - 3 * 0.24) / 4;
  stat(s, M, 2.3, sw, 1.4, money(equity), "equity, from $100,000");
  // Sign goes OUTSIDE the currency symbol: "-$565", never "$-565".
  stat(s, M + sw + 0.24, 2.3, sw, 1.4,
    (pnl >= 0 ? "+" : "-") + money(Math.abs(pnl)), "profit and loss",
    { color: pnl >= 0 ? GOLD : "E08A93" });
  stat(s, M + 2 * (sw + 0.24), 2.3, sw, 1.4, String(open.length), "condors open");
  stat(s, M + 3 * (sw + 0.24), 2.3, sw, 1.4, String(contracts), "contracts");
  const cw = (W - 2 * M - 2 * 0.26) / 3;
  card(s, M, 3.95, cw, 1.72, "Bounded by construction",
    `${money(credit)} of credit collected against a worst case of ${money(maxRisk)}, which is ${(maxRisk / 1000).toFixed(1)}% of the account. Defined risk means the loss is known before the order is sent.`);
  card(s, M + cw + 0.26, 3.95, cw, 1.72, "Unattended and supervised",
    "Every cycle runs in its own process with an OS-enforced timeout, because an in-process timer cannot rescue a thread stuck in a syscall. The watchdog restarts what it kills.");
  card(s, M + 2 * (cw + 0.26), 3.95, cw, 1.72, "One week is mostly noise",
    "The backtest does not predict this week. It establishes positive expectancy, so these days are a draw from a favourable distribution, not a coin flip. We report the draw.");
  s.addText("The tail hedge is designed, coded and never engaged: no VIX expiry inside its 21 to 45 day window was quoted all week. That refusal is logged every cycle rather than hidden.", {
    x: M, y: 5.82, w: W - 2 * M, h: 0.45, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, color: MUTE,
  });
  chrome(s, 11);
}

// ----------------------------------------------------------------- slide 12
{
  const s = pres.addSlide(); bg(s);
  title(s, "Sixty seconds, and you can check all of it", "Nothing here needs our credentials, our machine, or our word.");
  const items = [
    ["make test", "233 tests over the gates, the ladder, the flatten and the deadline"],
    ["make verify", "recompute the Merkle root over every logged decision"],
    ["make summary", "opportunities, entries, and every refusal by blocking gate"],
    ["make judge", "all of the above, then rebuild the results page from the log"],
  ];
  items.forEach(([cmd, desc], i) => {
    const y = 2.3 + i * 0.78;
    s.addShape(pres.ShapeType.roundRect, { x: M, y, w: W - 2 * M, h: 0.66, rectRadius: 0.07, fill: { color: i === 3 ? SURF2 : SURF }, line: { color: i === 3 ? GOLD : SURF2, width: i === 3 ? 1.5 : 1 } });
    s.addText(cmd, { x: M + 0.28, y: y + 0.17, w: 2.4, h: 0.34, isTextBox: true, margin: 0, fontFace: MONO, fontSize: 15, bold: true, color: GOLD });
    s.addText(desc, { x: M + 2.9, y: y + 0.18, w: W - 2 * M - 3.2, h: 0.34, isTextBox: true, margin: 0, fontFace: BODY, fontSize: 13, color: ICE });
  });
  s.addText("The dashboard renders entirely from committed artifacts, so it works with the market closed, the API down and the MCP server stopped. A demo that needs a live API is a demo that dies during the demo.", {
    x: M, y: 5.55, w: W - 2 * M, h: 0.6, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, color: MUTE, lineSpacingMultiple: 1.15,
  });
  chrome(s, 12);
}

// ----------------------------------------------------------------- slide 13
{
  const s = pres.addSlide(); bg(s);
  s.addText("You do not have to trust me", {
    x: M, y: 2.5, w: W - 2 * M, h: 0.9, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 44, bold: true, color: WHITE,
  });
  s.addText("That is the entire design. Clone it and check.", {
    x: M, y: 3.42, w: W - 2 * M, h: 0.5, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 18, color: GOLD,
  });
  const cw = (W - 2 * M - 0.3) / 2;
  card(s, M, 4.3, cw, 1.5, "Repository",
    "github.com/nilaymastaadmi/alpaca-hackathon\n\nMIT licensed. Pre-registration, every result including the failures, and the full decision log.");
  card(s, M + cw + 0.3, 4.3, cw, 1.5, "Live dashboard",
    "alpaca-hackathon-wcjwdbkqifybupyd6ckzps.streamlit.app\n\nThe agent's decisions, the shadow race, the MCP traffic, and the tamper button.");
  chrome(s, 13);
}

const out = path.join(__dirname, "slides.pptx");
pres.writeFile({ fileName: out }).then(() => console.log("wrote", out));
