# Proposal: readability of DiffWitness Core human output

Status: **PROPOSAL — no output is changed by this document.** It accompanies the
IdleProof Local / DiffWitness Portal UI redesign and applies the same rules to the
terminal and Markdown text people read. Every "after" example below is illustrative
and must be implemented and re-qualified separately.

Evidence: real captures from candidate `7f043a3`, produced in a disposable repository
with an empty `HOME` (no network, no paid API). File and line references are to that
commit.

## 1. What must not change

These are contracts (class **A**). A readability change may not alter them, in any
view (`guided`/`technical`) or language (`en`/`fr`):

- commands, subcommands, options and their meaning; exit codes;
- every JSON document and schema (`diffwitness.project-status.v1`,
  `diffwitness.doctor.v1`, certificates, debt reports, ledger JSON, continuity JSON);
- identifiers and citations: certificate ids (`dw2_…`, `dwa1_…`), change ids
  (`dwchg_…`), event ids and hashes, ledger ids (`DW-…`), commit SHAs;
- status tokens read by scripts, skills and docs: `WITNESSED`, `UNWITNESSED`,
  `INCONCLUSIVE`, `PROOF ACCEPTED`, `strong surplus candidate`, Protect decisions;
- `$GITHUB_OUTPUT` keys, `::warning`/`::error` workflow commands, `action.yml` inputs
  and outputs, the evidence artifact name;
- native hook protocol keys (`decision`, `reason`, `systemMessage`,
  `hookSpecificOutput`, …) and the single-JSON-document rule on Stop;
- `docs/LANGUAGE_CONTRACT.md`: enums, codes, evidence and JSON are never translated.

## 2. Who reads the human text today

| Surface | Entry point | Consumers that depend on wording | Class |
| --- | --- | --- | --- |
| `dw --help` (guided/technical, en/fr) | `public_help.py:4,109,133` | `tests/test_ht001_guided_first_run.py:65-114`, `test_view_mode.py:75-85`, `test_language.py:135`, `test_release_metadata.py:46,50` | B |
| `dw status` | `status_cli.py:422,486`; `readiness.py:228-274` | `test_status_cli.py`, `test_language.py:37-69`, `test_doctor_proof_truthfulness.py:71-80`, `scripts/language_acceptance.py` | B (JSON A) |
| `dw doctor` | `doctor.py:78,207,306` | `test_rr007_guided_surface.py:94-106`, `test_ht002_doctor_outside_git.py:77` (exact line) | B (JSON A) |
| `dw explain` | `explain_ui.py:14,38,92` | `test_rr007_guided_surface.py:125-133`, `test_idleproof_freshness.py:62`, `test_stale_proof_end_to_end.py:126` | B (JSON A) |
| `dw protect …` | `protect_ui.py:99,156-210` | `test_rr007_guided_surface.py:168-172`, `test_language.py:41,73` | B (JSON A) |
| `dw setup [status]` | `setup.py:364-482` | `test_ht004_guided_vocabulary.py:79-110`, `test_native_setup_journeys.py:187` | B |
| gate / prove / guard terminal report | `gate.py:398-421,586`, `guard.py:239-375`, `frontend.py:228,287` | `test_cli.py:62`, `test_human_blocker_regressions.py:140`, `scripts/human_acceptance.py`, `alpha_smoke.py`, `recovery_acceptance.py`, `unborn_release_acceptance.py`, `skills/diffwitness/SKILL.md:52-56`, `README.md:357-359` | tokens A, prose B |
| Markdown certificate / step summary | `reporting.py:135`, `validation.py:102`, `assurance.py:172`, `github_actions.py:43` | `test_cli.py:67`; `action.yml:137,186-197` (uploads `diffwitness-evidence.md`) | headings B, body C |
| debt / health / plan / ledger | `debt_cli.py:74-171`, `ledger_cli.py:117-166` | `test_debt_cli.py:42-96`, `recovery_acceptance.py:95` | B (JSON A) |
| native hook messages (agent and IDE) | `ide_plugin.py:190-246`, `ide_handoff.py:31-79,314-327` | `test_native_hook_contracts.py`, `test_ide_handoff_fail_closed.py`, `test_legacy_stop_contract.py`; **IdleProof** `bin/idleproof-hook.mjs:31,36` and `src/cursor-hook-cli.mjs:87` match the message text | B, cross-repository |
| continuity (`ask`, `context`, `state`) | `continuity_context_command.py:17`, `continuity_questions.py:522` | `test_rr007_guided_surface.py:152-154`, memory acceptance scripts | B |

Text consumers outside this repository, found by search:

- IdleProof matches Stop `systemMessage` text with `/not armed|session state is invalid/i`
  and displays Core's message verbatim (`bin/idleproof-hook.mjs:31,36`).
- IdleProof matches `/restart/i` and `/unrecognized arguments/i` on the stderr of
  `dw state events` (`src/portal-memory-sync.mjs:200-201`), without `--language en`.
- IdleProof requires `/dw debt/` in `dw debt --help` and keys a cache on `dw --version`
  (`src/auto-debt.mjs:122-124,436-439`).
- DiffWitness Portal reads snapshot fields only and writes its own wording.

Rule for any implementation: class **B** text changes only together with the tests,
scripts, docs and IdleProof matchers listed above, in the same reviewed change.
Class **C** text can change freely.

## 3. Principles (same as the Local and Portal design system)

1. **Verdict first.** The first line answers "is the current change verified?". Banners,
   versions and paths come after.
2. **One vocabulary across products.** Use the words people see in Local and Portal.
   Verified, accepted, observed, inferred, declared and unknown keep their meaning. A
   finding's *confidence* is never printed as "verified" next to a risk.
3. **Machine tokens belong to the technical view.** The guided view never prints
   `key=True`, raw codes or 64-character hashes; the technical view keeps all of them.
4. **One stream discipline.** With `--json`, stdout is exactly one JSON document.
   Prose and errors go to stderr.
5. **Width and structure.** Lines of 100 columns or less; aligned label columns; the
   same section order in guided and technical (verdict, state, next step, details).
6. **Language completeness.** French output contains no English sentence fragments.
   Codes stay untranslated, as the language contract requires.
7. **Absence is explicit.** "Not measured", "not run" and "unknown" are never shown as
   zero, success or readiness.

## 4. Before / after examples

### 4.1 `dw status` (guided, clean change)

Before (capture `101-status-after-guard-guided.txt`, abridged):

```text
DIFFWITNESS · GUIDED

The current change is verified
The current code exactly matches the latest change accepted by DiffWitness.

Project state
Current Proof: fresh · current tree verified=True
The current exact code is covered by the latest accepted Proof.
Native integration not configured (optional).
• Live protection is off (optional).
✓ Verification can be started.
✓ The currently visible change is covered by the latest accepted Proof.
⚠ 1 known issue(s) still need review.
✓ A DiffWitness change history exists.

Next step
1. Current change is already verified
   The current worktree exactly matches the latest accepted DiffWitness candidate. …
   Command: git status --short
2. Review the highest-value debt repayment work
   …
```

After (illustrative; same facts):

```text
DiffWitness · current change verified
The code in your working tree matches the change DiffWitness last accepted.

  Proof        verified for this exact code   (edit anything and it becomes stale)
  Debt         1 known issue to review        → dw plan
  Protection   off (optional)                 → dw protect enable
  Agent        native integration not set up (optional)

Next: review the open issue with `dw plan`.
Details: dw status --view technical
```

- Removed from guided: `current tree verified=True`, and the step that suggested
  `git status --short` as an action for a change that is already verified.
- Kept as is: the technical view and every JSON field.

### 4.2 `dw explain` (guided)

Before (capture `44-explain-after-guard-guided.txt`):

```text
Things to know
- Shell execution added (verified)
```

After:

```text
Things to know
- Shell execution added — finding confidence: verified by a deterministic rule.
  Review it; Proof does not say this code is safe.
```

The finding's `confidence` field is unchanged. Only its label in prose changes, so that
"verified" does not read as "verified safe".

### 4.3 `dw health`

Before (capture `74-health-with-debt.txt`):

```text
DIFFWITNESS
Project health / debt ledger
Debt                     5
--------------------------------
security                     5
auto-replayable               5

Current project scan: 13 point(s), 2 signal(s)
```

After:

```text
DiffWitness · project debt
  Recorded in the Debt Ledger   5 points   (security 5 · auto-replayable 5)
  Seen by today's scan         13 points   2 signals, not yet recorded
  Trend (30 days)              +5          introduced 1 · resolved 0 · reopened 0
```

This explains why the two numbers differ, and aligns the columns.

### 4.4 GitHub step summary (`--report` / `$GITHUB_STEP_SUMMARY`)

Before (capture `122-gate-unwitnessed-gha-step-summary.md`), the rejected gate starts
with:

```markdown
# DiffWitness evidence certificate

**Certificate:** `dw2_6cf9f6f9a6aba886e81d`
**Contrast:** `base-fail_candidate-pass`
```

The strict-policy rejection summary (capture 121) is indistinguishable from the
acceptance summary (capture 120).

After:

```markdown
# DiffWitness · rejected under balanced policy

1 of 2 changed hunks has no causal witness (strong surplus candidate).

**Certificate:** `dw2_6cf9f6f9a6aba886e81d`
**Contrast:** `base-fail_candidate-pass`
```

The existing sections follow unchanged. Adding a first heading changes a class B
heading consumed by `test_cli.py:67`; that test would be updated in the same change.
The artifact name and `$GITHUB_OUTPUT` keys stay the same.

### 4.5 Gate terminal report ordering

Before, the verdict line prints before the banner, and an acceptance goes to stdout while
a rejection goes to stderr (`gate.py:403` vs `:405`). The proposal changes only the
order on stdout: banner, then the hunk table, then the verdict. Every line keeps its
current stream, because CI scripts read both.

## 5. Anomalies found while inventorying (not fixed here)

These are behaviour issues, not wording. They are listed so they can be decided
separately:

1. **Text match that no longer matches.** IdleProof's
   `/session state is invalid/i` (`bin/idleproof-hook.mjs:31`,
   `src/cursor-hook-cli.mjs:87`) cannot match Core's current wording "DiffWitness
   SessionStart state is invalid" (`ide_handoff.py:191`, `proof_cli.py:548`). The
   `not armed` branch still matches. Prefer a machine field over text matching.
2. **Prose after JSON on stdout.** `entry/__init__.py:133` prints "Project continuity: N
   Debt Ledger lifecycle event(s) projected" after the JSON of `ledger … --json` and
   `recheck --json`. This was reproduced after a ledger event had been recorded through
   an internal path (capture 182); whether ordinary CLI use can reach it needs
   confirmation.
3. **Prose instead of JSON.** `doctor --json` and `explain --json` print prose errors on
   stdout (`doctor.py:386`, `explain_ui.py:107-109`). The doctor case is pinned by
   `test_ht002_doctor_outside_git.py:77`.
4. **Uncaught traceback.** `dw status --repo <non-git>` and `dw explain --repo
   <non-git>` print a Python traceback and exit 1 (`status_cli.py:556`,
   `explain_ui.py:105`).
5. **Ready without an agent.** `dw setup status` with nothing installed prints
   "⚠ Integration configured: your configured coding agent" and exits 0
   (`setup.py:413,298`).
6. **Logic tied to wording.** The Protect status mark depends on matching the French
   word "approbation" (`protect_ui.py:122`).
7. **Rejection summary omits the verdict.** See 4.4. There is also no verdict key in
   `$GITHUB_OUTPUT`.
8. **Misleading hunk labels.** Labels use Git's hunk-header context, so an added
   `square()` can be labelled with the preceding function's name.

## 6. Suggested sequence

1. Fix the class C text and the anomalies that need no wording change (4, 5) behind
   their own tests.
2. Change one class B surface at a time (`status`, then `explain`, `doctor`, `health`,
   the Markdown summary), each with its tests, acceptance scripts, docs and IdleProof
   matchers in the same change, in both languages, and re-run
   `scripts/language_acceptance.py`.
3. Replace IdleProof's text matching of Stop messages with a machine field before any
   change to hook wording.
4. Re-qualify humanly with both views and both languages. The terminal and Markdown
   captures are the acceptance artifacts.
