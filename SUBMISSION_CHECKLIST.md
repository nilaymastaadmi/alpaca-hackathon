# SUBMISSION CHECKLIST

Deadline: **Friday 4 September 2026, 20:30 IST** (15:00 UTC / 11:00 ET).

Submit Thursday night or Friday early, not at the deadline. Deadline servers die
at 23:58, and Friday morning is meant to be rehearsal and buffer.

"Submitted" is a claim that needs evidence. Verify the submission actually landed
before closing the laptop.

---

## Blocking, will invalidate or damage the submission if missed

- [x] **Flip the GitHub repo to PUBLIC.** Done well before this checklist item
      was revisited — repo has been public since early in the build week, by
      deliberate decision ("keep the repo public"), confirmed reachable.
- [x] **Create a BRAND NEW Alpaca paper account** for the submission — done
      2026-08-28. Verified live, not assumed: `PA37R35A5ZGW`, ACTIVE, zero
      orders, zero positions, options level 3 approved, $100,000 equity.
      Keys in `.env.live`, gitignored, never mixed into `.env`.
- [ ] **Submit the FRESH account ID: `PA37R35A5ZGW`**, not the practice one.
      Judges pull P&L directly from whatever ID is submitted.
- [x] **Disambiguate the practice account inside the repo before going public.**
      `HANDOFF.md` already labels it unmistakably: "Practice account (dev-only,
      DO NOT submit): `PA308NOY3X36`".
- [ ] **Commit artifacts during the live week** so the deployed dashboard is not
      stale. It renders whatever is committed; without this a judge opening the
      URL on 3 Sep sees decisions from 20 Aug.

## Mandatory submission fields

- [ ] Project title
- [ ] Short description
- [ ] Long description
- [ ] Technology and category tags
- [ ] **Cover image**, PNG or JPG, **16:9**
- [ ] **Video presentation, MP4** (mandatory, not optional)
- [ ] **Slide presentation, PDF** (mandatory, not optional)
- [ ] **Public GitHub repository** URL
- [ ] **Application URL** (the Streamlit Cloud deployment, for interactive evaluation)
- [ ] **Alpaca paper account ID** (the fresh one)
- [ ] Up to 5 social post links, each dated **during** 28 Aug to 4 Sep

## Live week operations, 31 Aug to 4 Sep

- [ ] Agent live and trading at **Mon 31 Aug 09:30 ET**. A late start loses a
      quarter of the P&L window.
- [ ] Visit the Streamlit app daily. Community Cloud apps sleep after roughly 12
      hours without traffic and take about 30 seconds to wake. A judge should not
      be the one waking it.
- [ ] Capture screenshots and logs **as they happen**, not reconstructed later.
- [ ] **Thu 3 Sep close: the NFP de-risk fires.** Nonfarm payrolls lands Fri 4 Sep
      08:30 ET, inside the window and 2.5 hours before the deadline. This is the
      demo's best moment. Capture it.
- [ ] Consider being **flat at submission**. Open positions get marked at whatever
      the tape says; flat means realised, unambiguous P&L. It also pairs exactly
      with the NFP de-risk, so the risk-correct move and the presentation-correct
      move are the same move.
- [ ] `make seal` and confirm `make verify` passes before submitting.

## Resolved by the official kickoff email (28 Aug) and the live hackathon page (29 Aug)

- [x] **Is Social Engagement a separate prize podium? YES, confirmed.** 2 teams
      x $500 plus a month of Algo Trader Plus per member, distinct from the
      1st/2nd/3rd podium. Fewer slots than the precursor Kraken event's 3, but
      real and worth the up-to-5 social posts.
- [x] **Total prize pool is $6,000**, not the $5,000 this repo assumed
      everywhere until now: 1st $2,500 + $300 Featherless credits, 2nd $1,500,
      3rd $1,000, Social Engagement 2 x $500 (+ Algo Trader Plus).
- [ ] **New requirement from the same email: a one-page write-up covering AI
      logic, risk gates, and Alpaca infrastructure implementation.** Distinct
      from the "long description" field below. Not yet drafted; the source
      material already exists across `STRATEGY.md`, `RISK_REGISTER.md` and
      `HANDOFF.md`, condensing it is the remaining work.
- [x] **"Options Alpha Agents" vs "Track 2: Volatility and Event", resolved.**
      Checked the live hackathon page directly, 29 Aug: there is exactly one
      main challenge, "Options Alpha Agents," no separate tracks exist.
      "Track 2" was this repo's own framing, not an official category. Use
      "Options Alpha Agents" for the submission's category/tag field.
- [ ] **"Demo application platform" field.** The submission form lists this
      separately from "Application URL" — name the platform (Streamlit
      Community Cloud) explicitly, not just the link.
- [ ] **If this places: payment needs a W-9 (US) or W-8BEN (non-US),
      government photo ID, and bank details, filed within 90 days of winner
      notification or the prize is forfeited.** Prizes pay to one individual,
      not a team. Non-US payments face 30% US withholding unless a
      tax-treaty claim is filed on the W-8BEN. Nothing to do now; flagging
      so it isn't a scramble later.
- [ ] **Any restriction on pre-kickoff work?** Still technically unconfirmed
      in writing, though moot now that kickoff has happened. The event page
      always said to "get a head start" and to "use any paper account you
      like during development," which the official email now explicitly
      restates ("While building: use any Alpaca paper account you like.
      Prototype freely.").
- [ ] Were technology partners announced? They were "to be announced" and may add
      partner prize surfaces.

## Standing decisions, do not relitigate

- Track 2, Volatility and Event (see the open naming question above). Locked
  19 Aug with full reasoning in `STRATEGY.md`.
- Solo, by choice, despite teams being allowed up to 6.
- Repo made PUBLIC early, deliberately, superseding the original "stay
  private until submission" plan recorded here. No downside found; see
  `HANDOFF.md`.
- Live sizing is 5 concurrent at 3% each (15% concurrent), a deliberate deviation
  from the 1% research sizing, recorded in `research/DEPLOYMENT_DECISIONS.md`.
