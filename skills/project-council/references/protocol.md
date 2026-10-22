# Council protocol — the craft behind each step

## Contents
1. Turning a one-line goal into a charter
2. Choosing seats
2b. Cases, the sealed holdout and fresh cases
3. Writing the plan (decisions)
4. Judging objections
5. Verifying findings
6. Worked example
7. Research basis

## 1. Turning a one-line goal into a charter
The user's sentence is the start, not the spec. Before writing the charter, look at what exists: the repo, sample data, the user's earlier messages, the context the goal implies (who uses it, where, with what inputs). Then write:
- **Objective** — the outcome for the user, not the activity ("orders reach the courier with a callable phone number", not "write a parser").
- **Definition of done** — 4–10 acceptance tests with concrete values: `AT3: "03/04/26" from a UK supplier → invoice date 2026-04-03`. If a test can't be checked, rewrite it until it can. These drive the build and the gate.
- **Case format** — what one input is and what the expected result looks like, so seven agents write cases the scorer can compare: e.g. input = one raw customer message; expected = `{"phone": "+1…", "city": "~Lyon", "notes": null}` with only the fields that matter (`~` = contains, `null` = must be empty). Set the target sealed pass rate (default 90%).
- **Constraints** — fixed interfaces the user named, stack, no-go areas, deadlines.
- **Users and their real inputs** — the messiest realistic examples you can find or construct. Most failures live here.
- **Assumptions** — every call you made without asking, with the reason. The user can overturn them later.
Good charters are short (one page) and concrete. Seats will add acceptance tests in round 1; merge the good ones into the plan.

## 2. Choosing seats
- Presets by type are a start; pick for the risks of *this* project. Ask: who would catch the mistake that hurts most here?
- **domain** is the highest-value seat when outsiders get things wrong (local formats, regulations, trade conventions). Name it precisely.
- **skeptic** is always on. **user** is on whenever humans touch the result. **quality** for code; **security** for money/personal data; **ops** for running services; **money** for product bets; **audience/editor** for content.
- 5 seats is the sweet spot; more seats add cost faster than insight. Don't seat two copies of one viewpoint.

## 2b. Cases, the sealed holdout and fresh cases
- Good cases are realistic and specific to the seat's angle: the domain seat writes the local formats and conventions outsiders miss, the user seat the messy real inputs, the skeptic the plausible-but-nasty ones. Not impossible inputs, not trick questions with debatable answers.
- Skim the sealed set once after `split`: drop a case only if its expected result is wrong or genuinely ambiguous (two reasonable answers). Hard is fine — hard is the point.
- Telling the builder about sealed misses: counts by field and author seat, plus the pattern in general words ("district names without the governorate", "labels written on one line"). Never quote sealed inputs; once you do, the score stops meaning anything.
- If the builder pushes back that a sealed case must be wrong, you check it (you can read it), and `drop` it with a note or say it stands.
- Fresh cases from reviewers are scored before any fix, then join the dev set. A big gap between the dev score and the fresh score means the work is overfitted to what it has seen — tell the builder to generalise (data tables, rules), not to patch case by case.
- Over-caution: a blank or "please confirm" result where the case has a clear answer is a miss. If the charter wants a needs-review flag, put it in the case's expected result explicitly.

## 3. Writing the plan (decisions)
- 5–12 decisions, each one line starting `D#:` and then the detail underneath. A decision is something a seat could reasonably vote against: "D4: Parse supplier dates with the supplier's country format, never by guessing" — not "D4: Write good code".
- Every risk that several seats raised independently must map to a decision or to an explicit "not doing X because Y".
- Include the merged acceptance tests and a build order (what gets built and checked first).
- On revision (plan_v2…), change the decision text itself; add a short "Changes from v1" list naming the objections each change answers. Don't renumber decisions — seats vote by number.

## 4. Judging objections (you are the chair)
- **Blocker** = the definition of done can't be met, or real harm (money lost, data leaked, users locked out). **Major** = likely to bite. **Minor** = worth doing. The script refuses blocker/major objections without evidence.
- Answer each one in the next plan: accept (change the decision), partially accept, or reject with a reason that addresses the evidence. "We disagree" is not a reason.
- A seat withdrawing must say what convinced it — if it just caved, keep the objection open yourself.
- Use `decide` only at the round limit or when two good options are genuinely tied. Record whose view you overrode and why; that dissent goes in the report.

## 5. Verifying findings
- Reproduce every blocker/major from its evidence before touching code: run the command, feed the input, read the line. If it doesn't reproduce, `dismissed` with what you saw.
- Duplicate findings from several seats are merged by the script — independent duplicates raise confidence.
- Fix the root cause, then re-run the acceptance checks and the failing input; note both in `fixed --note`.
- A fix to a blocker/major needs another review pass if any are left (the gate enforces this). Choose reviewers who can judge the fix plus one fresh seat for regressions.
- Nits: fix in bulk only if trivial; never let them crowd out majors.

## 6. Worked example (abridged)
Goal: "Make a dedupe tool for our CRM CSV exports — it's important, our sales team relies on it."
- Charter ATs: `AT1 Ana@X.com / ana@x.com → 1 row`, `AT2 "+1 (555) 010-2000" / "5550102000" → 1 row`, `AT3 empty file → empty output, exit 0`, `AT4 1M rows < 60s`.
- Seats: skeptic, user (sales ops), builder, domain:"CRM data hygiene", quality.
- Round 1: all five independently flagged phone formats (strongest signal); the domain seat added "two people can share a company switchboard number — phone alone must not merge".
- Plan v1 D2 "keep the most recent row" → skeptic blocker O1 with evidence "row 12: newer row has blank phone; merge would drop the number" → plan v2 D2 "merge field-wise; newest non-empty wins" → O1 withdrawn ("field-wise merge keeps the data").
- Review pass 1: F1 crash on empty file (2 seats, reproduced, fixed, AT3 re-run), F3 "Turkish dotted İ breaks lowercasing" (reproduced, fixed with casefold), F5 claimed slowness (didn't reproduce at 1M rows: 21s → dismissed).
- Cases: 52 written by seats, 31 sealed. Build round 1 scored sealed 81% (misses: phone 4, name 2 — "extensions and shared switchboards"); after one feedback round 94%. Review pass 1 fresh cases: 88% before fixes (two seats found accented names merged wrongly) → fixed → fresh-2 in pass 2: 100%.
- Pass 2 (skeptic + quality + fresh user seat): no blockers/majors → gate READY.

## 7. Research basis
- Multi-agent debate improves reasoning and factuality over a single model (Du et al., 2023), but gains are largely explained by ensembling/majority voting and debate alone doesn't raise expected correctness unless belief updates are biased toward correction ("Debate or Vote", NeurIPS 2025) → independent proposals + votes, evidence-gated changes of mind.
- Agents conform to majorities and drop correct answers; consensus-free, anti-conformity prompting and scoring across all rounds helps (Free-MAD, 2025) → agreement isn't the goal, objections persist until answered, dissent is recorded.
- Distinct, well-specified roles matter; identical roles degrade debate (ChatEval) → a roster with mandates and must-checks.
- Orchestrator–worker systems need detailed briefs (objective, output format, boundaries), parallel workers, outputs written to files, effort scaled to the task, and end-state evaluation; they fit shared-context coding poorly (Anthropic, "How we built our multi-agent research system", 2025) → generated briefs, JSON files, one builder, an executable gate.
- Holdout evaluation is the standard defence against overfitting: a builder that sees the test set will fit it. Sealing the council's cases from the builder, and scoring reviewers' fresh cases before fixes, keeps the score an honest estimate of unseen-input quality.
- Existing council skills (Claude Council: opinions → anonymised peer review → chairman; The Roast Room: positions → rebuttals → vote, unanimity treated as a warning) informed the anonymised digest and the red-team trigger; this skill adds the build, review, verification and gate loop around the debate.
