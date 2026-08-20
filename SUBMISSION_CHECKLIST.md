# SUBMISSION CHECKLIST

Deadline: **Friday 4 September 2026, 20:30 IST** (15:00 UTC / 11:00 ET).

Submit Thursday night or Friday early, not at the deadline. Deadline servers die
at 23:58, and Friday morning is meant to be rehearsal and buffer.

"Submitted" is a claim that needs evidence. Verify the submission actually landed
before closing the laptop.

---

## Blocking, will invalidate or damage the submission if missed

- [ ] **Flip the GitHub repo to PUBLIC.** The rules require a public repository.
      Currently PRIVATE by decision (see below). One click:
      `gh repo edit nilaymastaadmi/alpaca-hackathon --visibility public`
      Changing visibility does NOT break the Streamlit deployment or its URL.
- [ ] **Create a BRAND NEW Alpaca paper account** for the submission, around
      26-27 Aug. "Projects run on an existing or reused account will not be
      eligible for judging." The practice account is `PA308NOY3X36` and is
      **disqualified**. Keys go in a separate env file, never mixed.
- [ ] **Submit the FRESH account ID**, not the practice one. Judges pull P&L
      directly from whatever ID is submitted.
- [ ] **Disambiguate the practice account inside the repo before going public.**
      `HANDOFF.md` names `PA308NOY3X36`. A judge skimming could mistake it for
      the submission account and conclude a reused account was used. Label it
      unmistakably or remove it.
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

## Ask the organisers at kickoff, 28 Aug

- [ ] **Is Social Engagement a separate prize podium?** The precursor Kraken
      hackathon ran it as its own podium with 3 winners. Alpaca's page lists it
      both as a judging criterion and as an "extra challenge", which is ambiguous.
      If separate, that is 3 more prize slots most technical entrants ignore.
- [ ] **Any restriction on pre-kickoff work?** The rulebook contains no clause
      about when code may be written, and the event page explicitly says to "get a
      head start on your project" and to "use any paper account you like during
      development". A general lablab guidance article (not the rulebook) mentioned
      core AI functionality being built in-window. Cheap to confirm, expensive to
      assume.
- [ ] Were technology partners announced? They were "to be announced" and may add
      partner prize surfaces.

## Standing decisions, do not relitigate

- Track 2, Volatility and Event. Locked 19 Aug with full reasoning in `STRATEGY.md`.
- Solo, by choice, despite teams being allowed up to 6.
- Repo PRIVATE until submission, so competitors cannot read `STRATEGY.md` and the
  8 research documents during the build week. Public at submission.
- Live sizing is 5 concurrent at 3% each (15% concurrent), a deliberate deviation
  from the 1% research sizing, recorded in `research/DEPLOYMENT_DECISIONS.md`.
