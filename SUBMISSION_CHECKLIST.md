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
- [x] **Commit artifacts during the live week** so the deployed dashboard is not
      stale. Working: the live agent publishes every cycle (13 auto-commits on
      31 Aug alone), and the dashboard's Merkle badge verifies in production.
      Keep confirming daily that the 18:50 IST task actually fired.

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
- [x] ~~Up to 5 social post links~~ **DECLINED by Nilay, 2026-08-30.** No
      social posts for this submission. Submit with this field empty;
      forfeits the Social Engagement axis and both $500 slots. Do not
      re-raise.

## Live week operations, 31 Aug to 4 Sep

- [x] Agent live and trading at **Mon 31 Aug 09:30 ET**: first fill 09:45 ET,
      4 condors filled through MCP. Three of the four were a ledger-parsing
      incident, since fixed and adopted (`RISK_REGISTER.md` 4.7, 4.8). The
      watchdog was killed at cycle 13 of 85 by a console close; the task now
      self-restarts. **Do not close the console window it opens at 18:50 IST.**
- [ ] Visit the Streamlit app daily. Community Cloud apps sleep after roughly 12
      hours without traffic and take about 30 seconds to wake. A judge should not
      be the one waking it.
- [ ] Capture screenshots and logs **as they happen**, not reconstructed later.
- [ ] **Thu 3 Sep and Fri 4 Sep: gate 8 refuses all NEW entries** (NFP lands
      Fri 08:30 ET, within its 1-day window). What fires is a refusal
      artifact, not a position reduction; `event_derisk_fraction` was never
      wired and stays that way (RISK_REGISTER 4.6). Capture the refusal
      artifacts, they are the event-awareness demo.
- [x] **Flat at submission: DECIDED 2026-09-01 by Nilay, trade the maximum
      cycles.** Positions ride through the NFP print and the deadline flatten
      closes everything Fri 09:30-11:00 ET, before the 11:00 ET deadline.
      Accepts the NFP gap on the open book as a conscious trade-off. Capture
      the flatten artifacts Friday morning.
- [ ] `make seal` and confirm `make verify` passes before submitting.

## Resolved by the official kickoff email (28 Aug) and the live hackathon page (29 Aug)

- [x] **Is Social Engagement a separate prize podium? YES, confirmed.** 2 teams
      x $500 plus a month of Algo Trader Plus per member, distinct from the
      1st/2nd/3rd podium. Fewer slots than the precursor Kraken event's 3, but
      real and worth the up-to-5 social posts.
- [x] **Total prize pool is $6,000**, not the $5,000 this repo assumed
      everywhere until now: 1st $2,500 + $300 Featherless credits, 2nd $1,500,
      3rd $1,000, Social Engagement 2 x $500 (+ Algo Trader Plus).
- [x] **One-page write-up covering AI logic, risk gates, and Alpaca
      infrastructure**: drafted at `presentation/WRITEUP.md`, corrected
      2026-09-01 (gate count, hedge reality, dev bar 0.791, the live
      incident). One final-numbers pass on Thursday before submitting.
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
