---
name: project-council
description: Run a big or important project through a council of AI agents with different viewpoints — independent proposals and test cases, evidence-based debate until measured agreement, one builder scored on a sealed holdout it never sees, multi-seat review of the real result, verified fixes and re-review loops until a quality gate passes. Use when the user calls a project big, important or critical, wants it done right, or asks agents to argue, debate, cross-check or review each other — even when they give only a one-line goal.
---

# Project council

The user gives a simple goal; you turn it into a charter, seat 3–6 specialist subagents with different mandates, let each propose independently **and write test cases from its angle**, debate the plan with evidence until agreement is measured (not felt), have **one builder agent** build it while you hold back most of the council's cases as a sealed holdout, then have every seat review the real artifact and write fresh cases, verify their findings, fix, and loop until `council.py gate` passes. `$SKILL` = this skill's folder; `C="python3 $SKILL/scripts/council.py"`, run from the project root (state lives in `.council/`).

**Use it** for work worth 20–30 agent calls: a product feature, a system, a launch plan, a document that matters. **Don't** for small or exploratory tasks — just do those. Measured trade-off: on a clear, well-specified coding task a careful single agent got within a few points, and the council's edge showed on the hardest inputs (about +4 points on unseen hard cases) at roughly 6× the cost. So use `lite` for clear code, and `standard`/`critical` when inputs are messy, the domain is unfamiliar or mistakes are expensive. It needs the Agent tool (subagents); without it, tell the user the council can't run here and do a careful single-agent version with an explicit self-review.

## Why it's built this way (keep these in mind when you improvise)
- **Independence first.** Seats propose before seeing each other, so the council doesn't anchor on the first idea. Risks raised by several seats independently are the strongest signal (the digest ranks them).
- **Measure generalisation, not effort.** A single agent with a self-review already gets the obvious cases right; where councils win is the inputs nobody thought of. So every seat writes realistic cases with exact expected results; `cases split` seals ~60% of them. The builder never sees the sealed set, so its score is an honest estimate of how the work handles unseen inputs. Reviewers write fresh cases before testing, which measures it again after the fixes.
- **Debate surfaces objections; evidence decides them.** Plain back-and-forth mostly averages opinions — it doesn't make the group more correct. So objections need evidence to count, a seat may only change its mind by naming what convinced it, and agreement is never the goal. One debate round is the default; more rounds rarely pay for themselves.
- **Suspicious unanimity gets a red team.** If everyone accepts everything on the first pass, the skeptic attacks the riskiest assumption before you trust it.
- **One builder, and it isn't you.** Shared-context work degrades when several agents edit it, and you hold the sealed cases, so a single builder agent does the work and every fix. You chair, score, verify and decide.
- **Review the real thing, verify before fixing.** Reviewers run it and must give reproducible evidence; you reproduce every blocker/major before acting, because confident-sounding false findings are common.
- **Safety bought with refusals is still a miss.** An empty or "needs review" answer where a correct one was possible counts as wrong in the scores. Fixes must not trade wrong answers for blank ones unless the charter says blank is right.
- **Mechanics, not vibes.** `council.py` computes convergence (≥ 2/3 support on every decision, no open blockers, no new majors), the scores and the ship gate. Rounds are capped; a stalemate ends in a recorded chair ruling with the dissent kept.

## Workflow — make a task for each step
1. **Charter.** `$C init "<the goal in the user's words>" --type code|product|content|business|research|general --stakes lite|standard|critical`. Look at the workspace first (existing code, data, examples), then fill `.council/charter.md`: objective, deliverables, a **checkable definition of done** (AT1, AT2… with concrete values), the **case format** (what one input is, what the expected result looks like, the target sealed score), constraints, users and their real inputs, assumptions, out of scope. Stakes: lite = 3 seats/1 debate round/1 review pass; standard (default for "important") = 5/1/2; critical (money, health, production, public launch) = 6/2/3. User present and something genuinely ambiguous → one AskUserQuestion; otherwise record the assumption and go.
2. **Seats.** `$C seats --suggest`, then `$C seats --set skeptic,user,builder,domain:"<concrete field>",quality`. Always name the domain precisely ("hospital pharmacy inventory", not "healthcare"). Add `security` when money or personal data is involved. If you can pick subagent models, put one or two seats on a different model for diversity.
3. **Independent proposals + cases.** For each seat, `$C brief <seat> --phase propose` and spawn a subagent with that text verbatim — **all seats in one message, in the foreground** (`run_in_background: false`) so they run in parallel and you get their results before moving on. Then `$C record <seat> --phase propose` for each (it checks the cases too); if a record fails, send the errors back to that agent (SendMessage) and record again. `$C digest --phase propose`, then `$C cases split`. Skim the sealed cases once for wrong expectations (`$C cases drop C# --note` for a case that is actually wrong — not for one that is merely hard).
4. **Plan.** Read `.council/digest_propose1.md`. Write `.council/plan_v1.md`: 5–12 numbered decisions as lines `D1: …`, each high-signal risk handled by a decision (or rejected with a reason), the merged acceptance tests, the build order. `$C plan`. See [references/protocol.md](references/protocol.md) for decision granularity.
5. **Debate.** `$C brief <seat> --phase debate --round 2` → spawn all seats in parallel → record each → `$C digest --phase debate --round 2`. Follow the verdict:
   - CONTINUE: write `plan_v2.md` answering every objection (change the decision, or say why not), `$C resolve O# --how "…"` for each, `$C plan`, next round (`--round 3`).
   - RED_TEAM: `$C brief skeptic --phase redteam --round N` (plus one more seat), record, digest with `--phase redteam`.
   - STALEMATE (round limit hit): you are the chair — `$C decide --note "ruling + whose dissent"`.
   - CONVERGED: `$C report` → `.council/DECISIONS.md`.
6. **Build.** Spawn ONE builder agent in the foreground (`run_in_background: false` — everything after depends on it, and a background agent dies with a headless session) with `$C brief build` verbatim (charter + DECISIONS.md + dev cases; it writes the acceptance tests first, works in stages and returns an eval command). After each stage reply, continue the same agent with SendMessage until it reports done. Then `$C cases score --set sealed --run "<eval command with {cases}>"` and `--set dev`. Below target: tell the builder (SendMessage, same agent) the miss counts by field and by author seat and the *patterns* in your own words — never the sealed inputs — and score again; at most 3 rounds. Record runnable checks with `$C accept --run "<command>" --name AT1` (manual checks: `--result pass --evidence "…"`).
7. **Review.** `$C brief <seat> --phase review --round 1` for every seat, in parallel in one message, foreground. Record each, `$C findings merge --pass 1`, then **before any fix** `$C cases score --set fresh-1 --run "…"` — that number is the honest one.
8. **Verify, then fix.** For every open blocker/major: reproduce it from its evidence (run the command/input). `$C findings set F# verified --note "…"` or `dismissed --note "why it isn't real"`. Send the verified ones (and cheap minors) to the builder in one message; when it's done, re-score dev and sealed (no regressions), re-run the acceptance checks, then `$C findings set F# fixed --note "what changed + how verified"`.
9. **Gate and loop.** `$C gate` (needs: review done, no open verified blocker/major, acceptance passing, sealed score ≥ target or a recorded waiver, re-review after major fixes while passes remain). If it asks for a re-review, run another pass (the seats whose findings were fixed plus one fresh seat), score its fresh cases first, merge, verify, fix, gate again. At the pass limit, stop and ship with the remaining risks named.
10. **Deliver.** `$C report`, then give the user the work and a short account: the decisions that shaped it, the scores (sealed, each fresh pass), what the council caught and fixed (top 3–5 findings), acceptance results, recorded dissent and residual risks. Point to `.council/` for the full trail. Don't paste raw JSON.

## Commands
| command | does |
|---|---|
| `$C init "<goal>" --type T --stakes S` | creates `.council/` and the charter template |
| `$C seats --suggest` / `--set a,b,domain:"…"` | recommends / fixes the seats |
| `$C brief <seat> --phase propose\|debate\|redteam\|review --round N` | prints the exact subagent prompt (role card, rules, output schema, output path) |
| `$C brief build` | the builder agent's prompt (dev cases only, eval-command contract) |
| `$C record <seat> --phase P --round N` | validates the seat's JSON (schema, evidence and case rules) and files it |
| `$C digest --phase propose\|debate\|redteam --round N` | anonymised digest, vote tally, objection ledger, convergence verdict |
| `$C cases split` · `score --set sealed\|dev\|fresh-K --run "cmd {cases}"` · `list` · `drop C# --note` · `target 0.95` · `waive --note` | seal a holdout, score the work on any set (non-code: `--results judged.json` from a judge agent), track the trend |
| `$C plan` · `$C resolve O# --how` · `$C decide --note` | register a plan version · answer an objection · chair ruling |
| `$C status` | where things stand and the next step |
| `$C findings merge --pass K` · `list --open` · `set F# <status> --note` | review findings: dedupe, triage, track (merge also collects fresh cases) |
| `$C accept --run "<cmd>" --name AT#` | runs and records an acceptance check |
| `$C gate` · `$C report` | ship gate (exit 0 = ready) · DECISIONS.md + REPORT.md |

## Non-code work
Cases still apply: an input is a scenario or question, the expected result is what a good answer must contain or decide ("~mentions the refund window"). Score with a judge subagent that sees only the cases and the work, writes `[{"id", "pass", "note"}]`, and `$C cases score --set sealed --results that.json`.

## Cost and pacing
A standard run is about 5 seats × (1 proposal + 1 debate + 2 reviews) + 1 builder ≈ 21–25 subagent calls; tell the user before starting a critical-stakes council on a big codebase. Keep the user posted at each milestone (charter, plan converged, build scored, each review pass) in one line each — the task list carries the detail.

## Files
| path | read when |
|---|---|
| [references/protocol.md](references/protocol.md) | writing the charter and case format, choosing seats, writing plans, judging objections and findings, worked example |
| `scripts/council.py` | the ledger (run it; no args prints usage) |
