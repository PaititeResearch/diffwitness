# Alpha stabilization — consolidated candidate (2026-10-24)

Status: **MACHINE qualification in progress · HUMAN NOT RUN · not merged · not released · not ALPHA READY.**
Registry: PaititeResearch/diffwitness#74. This dossier is append-only: later results are added as dated
entries in §10; earlier entries, failures and incidents are never rewritten.

Companion files: `STABILIZATION_ALPHA_20261024.json` (machine-readable manifest),
`STABILIZATION_ALPHA_HUMAN_RECIPE_20261024.md` (human acceptance recipe).

## 1. Starting point (verified on GitHub before any change)

| Candidate | PR | Head verified | State |
|---|---|---|---|
| Core project understanding | diffwitness#133 | `0933d5caebc087b4f2321e283879dd2a83d54d17` | draft, open, not merged |
| IdleProof project understanding | idleproof#37 | `6f06cb3291ac56bd38fbd761d40ff54827a708e0` | draft, open |
| IdleProof unified Atlas | idleproof#52 | `d227e8ebcc0eb68048c5cb3dacf5379b7ebc7672` | draft, open (base #46) |
| IdleProof native Proof status | idleproof#54 | `7c8ffee00273fd153c7d4490ba238dff61222e15` | draft, open (base #52) |
| Portal project understanding | idleproof-portal#50 | `198215fb8a2dcc16d6f381fba13603821306b8f6` | draft, open |

`main` of the three products: Core `61dbf48c`, IdleProof `77250573`, Portal `459cb7bf`. #54 contains
#37 entirely (merge base = #37 head) and #52, so it is the IdleProof line to build on. The
`snapshots/alpha-20261024-before-claude/*` restore branches were not touched. No `main`, no candidate
branch and no recipe data were modified; the work is on `claude/diffwitness-idleproof-alpha-d0lv1f`
in each repository (the branch name this session is bound to), one commit series per lot.

## 2. Consolidated candidate manifest

| Product | Branch | Base (unchanged) | Code head | Draft PR | Package version |
|---|---|---|---|---|---|
| Core | `claude/diffwitness-idleproof-alpha-d0lv1f` | #133 `0933d5c` | see §10 (latest entry) | diffwitness#137 | `diffwitness 0.4.0a1` (unchanged) |
| IdleProof Local | `claude/diffwitness-idleproof-alpha-d0lv1f` | #54 `7c8ffee` | see §10 | idleproof#55 | `idleproof 0.10.0` (unchanged) |
| Portal | `claude/diffwitness-idleproof-alpha-d0lv1f` | #50 `198215f` | see §10 | idleproof-portal#56 | `0.1.0-alpha.1` (unchanged) |

Version numbers are unchanged, so **identical versions do not mean identical code**: identify every
installed component by its commit (IdleProof tarball SHA-256, Core wheel built from the pinned commit,
Portal `build.revision`). Interproduct contracts used and kept: `change-envelope-1` (Core → Local
binding), `dwchg_` identity (identical computation verified across Core and Local, §6),
`idleproof.portal-snapshot.v1` (unchanged), Stop hook protocol fields (unchanged). New optional
configuration: `[diffwitness] python_env` / `DIFFWITNESS_PYTHON_ENV`. Migrations: **none** in any
product. Portal CI integrated jobs pin the consolidated Core and IdleProof heads (legacy pins unchanged).

## 3. Lot journal

### L1 — Native Proof status bound to the exact change (idleproof#53, #54)

- **Problem.** Local said "The code is ready" after a refused Stop (#53). #54 added native Stop states.
- **Defect found in #54 and reproduced.** `classifyNativeStop()` accepted "DiffWitness Proof accepted:
  dw2_…" when the message carried **no** `dwchg_`. Core omits that id when Continuity is degraded
  (`ide_handoff.py`). REPRO test fails on `7c8ffee` (`actual: 'accepted'`).
- **Decision.** Acceptance requires Core's structured `change-envelope-1` for the same `dwchg_`,
  `proof.accepted === true`, an accepted claim and the same `certificate_id`; text can only lower the
  status. Rejected alternatives: requiring `dwchg_` in the text (Core omits it legitimately; text is
  untrusted); new fields in the Stop stdout (provider protocol is strict, the bridge rejects extra
  fields); a new Core status file (the envelope already is the structured contract).
- **Also.** Distinct states (pending, accepted, blocked, inconclusive, terminal, unavailable,
  no-change, not-required, not-configured, unverified) with the Core cause; bounded per-session verdict
  history and verdict on the frozen change record; later acceptance shows earlier refusals; a repeated
  Stop of an accepted tree does not reset to pending; every Core certificate family recognised
  (`dw2_`, `dwac1_`, `dwa1_`, `dwv1_`); envelope located through `git rev-parse --git-path` (the IDE
  assurance reader missed linked worktrees).
- **Tests.** `test/native-stop-status.test.mjs` (16, including the real hook runner with a stand-in
  Core), `test/local-ui-state.test.mjs` (states, labels, no "code is ready").
- **Commits.** idleproof `5946dfb`, `cc77f35`. **Rollback:** stay on `7c8ffee`; added state fields are
  additive, legacy states read as unverified.

### L2 — Evidence runs with the project's Python environment (diffwitness#136)

- **Problem.** E2E-ALPHA-01: 16/16 green in the project `.venv`; native Stop ran `python -m pytest` with
  DiffWitness's own venv and refused three times as bare `stable-fail`.
- **Cause (reproduced, two independent venvs, Core `bin/` first on PATH).** `runner.command_env`
  inherited the caller's PATH; the alpha install guide (Portal `ALPHA_LOCAL_FIRST_USE.md`) put the whole
  Core venv `bin/` (with `python`) on PATH through `~/.bashrc`. That Codex's hook shell re-read it on the
  operator host is consistent with the observation, not proven there.
- **Second defect found while reproducing.** With an editable install (`pip install -e .`, src layout)
  each proof worktree imported the **original source**; the base "passed" with the candidate's code and
  the Stop refused with a misleading `claim is 'preservation'`.
- **Decision.** Explicit evidence environment in the single choke point `command_env` (order: override
  / `python_env`, `.venv`/`venv`, inherited non-Core `VIRTUAL_ENV`, inherited PATH); editable roots
  mapped into the worktree through `PYTHONPATH`; explicit `cause:` line (`test-runner-unavailable`,
  `evidence-command-unavailable`, `missing-module`) without changing classification, causality,
  stability or budgets; static `dw doctor` report. Rejected: stripping Core's venv from PATH (breaks a
  deliberately shared venv); installing dependencies (forbidden); config-only selection (a `.venv`
  project must work as is); rewriting the `python` token to an absolute path (misses `pytest`, scripts,
  nested shells). Contract: `docs/EVIDENCE_ENVIRONMENT.md`.
- **Before → after (real native Stop).** `.venv` project: `stable-fail` → accepted, causal. No project
  environment: bare `stable-fail` → `cause: test-runner-unavailable … (DiffWitness's own runtime …)`.
  Editable src layout: `preservation` refusal → accepted, causal.
- **Commits.** diffwitness `ec01078`, `8ee8ee2` (venv-internal `.pth` paths are not source roots);
  idleproof-portal `1021857` (guide links only `dw`). **Rollback:** stay on #133; `python_env` is new
  and optional.

### L3 — Explain the change the agent made (idleproof#29)

- **Problem.** After `gift_wrap_fee_cents` was added: "Work around test_small_order in
  tests/test_cart.py", `test_small_order` / `apply_discount` as subject, and "This part decides who
  the user is…".
- **Causes (each reproduced on `7c8ffee`, and together in one real Core + hook run).** Handoff subject =
  file touched last (the tests); request tokens kept underscores so `gift_wrap_fee_cents` matched no
  symbol part and the first declaration won; the diff was never used; the "why" used any concept found
  in prompts, commands or tool output ("session" is an auth root) as a fact about the code;
  `from`/`update` in prose became SQL tables.
- **Decision.** Git hunks against the task's baseline tree mark symbols added/modified (parser spans;
  added-line declarations without a parser); handoff subject = changed production file, then changed
  test file; a symbol is the subject only with change or request evidence; unchanged declarations are
  listed as existing context; a concept is explained only when the inspected code supports it; SQL
  tables need a statement shape (shared with the feature model); Portal summary says Adds/Changes only
  from Git; Git reads agent paths literally and only admitted project files. No LLM call. Rejected: LLM
  re-ranking (cost, non-determinism); keeping the first-declaration fallback (it is the defect); a full
  diff per live event (latency).
- **Tests.** `test/context-change-subject.test.mjs` (13 incl. rename, partial edit, similar names,
  several files, tests only, empty diff, no parser, pathspec/outside paths, SQL shapes); 4 existing tests
  that observed the first-declaration fallback now assert the `symbols` list (stronger).
- **Commits.** idleproof `bc1e085`, `a805bdd`, `53715cf`, and the pathspec hardening commit (§10).

### L4 — One exact status per change in the Portal timeline (idleproof-portal#55)

- **Problem.** Several observed receipts of `dwchg_580694c6a3bf2a0a2b692b39` showed "PROVE: not attached
  yet" around the post-proof receipt with `dw2_510e50ee0bed56a15eaa`; the reconciliation existed only
  for the latest change and only in Guided.
- **Decision.** Group page receipts by exact validated id; one synthesis per change from two bounded,
  project-scoped, RLS-protected reads for all changes of the page (no N+1, no migration, pagination
  unchanged); newest explicit Proof and Debt (same rule as readiness); counts, freshness, partial reads
  and failures explicit; original receipt cards unchanged below. Rejected: a DB view/migration (would
  touch retained stacks); hiding observed receipts (forbidden); prefix grouping (forbidden).
- **Tests.** `src/lib/change-synthesis.test.ts` (the exact #55 scenario, prefix collision, out-of-order
  receipt, newer rejection, partial reads, query shape), `src/components/ChangeSummary.test.ts`.
- **Commit.** idleproof-portal `fcb6226`.

### L5 — Human mastery is never 0 % without answered checks (idleproof-portal#48)

- **Remaining surfaces after #50.** Stored explanation of every receipt (also sent to the managed-AI
  context) said "0% understanding coverage"; readiness printed missing knowledge debt as 0; the Technical
  workspace listing showed an absent legacy coverage as "0%". Fixed on all three; Local already showed
  "Not assessed". **Commit** `43b3ccf`.

### L6 — Restart after reboot without sudo (idleproof-portal#46, H12)

- **Evidence (Supabase CLI 2.115.0 source, read-only shallow clone).** `functions serve` stages
  `supabase/.temp/start-secrets/supabase_edge_runtime_<project>/{env,multiline-env,main}` (0700), mounts
  `main/index.ts` with `docker run -v`, removes the directory before each serve (the H12 message is that
  `rm`), sets no restart policy, and documents that the bind sources must exist whenever the container
  can be re-attached. A Docker daemon starting/re-attaching a container whose `-v` source is missing
  recreates it root:root 0755. H12's directory was root-owned, non-empty (else the user could have
  removed it) and had no `env/` (passed with `--env-file`, never bind-mounted): **consistent** with that
  mechanism. **Not established:** which component re-attached the container on the operator host.
- **Decision.** Diagnose read-only before `supabase start` (owner, mode, times, entry names, container
  state, boot time; never contents); after serve and container are stopped, move an unwritable staging
  path aside **unchanged** inside its own writable parent (no sudo/chown/chmod/delete/secret read),
  report it and the manual removal command; idempotent; `.temp`/`start-secrets` problems still fail.
  Added `supabase/.gitignore` (`.temp`, `.branches`): the staging secrets were untracked and not ignored,
  so the launcher's build revision read them and `git add -A` could commit them. Rejected: automatic
  sudo/chown (forbidden); deleting the directory (needs root, destructive); running Supabase as root;
  upgrading the CLI without a disposable-stack qualification.
- **Tests.** `alpha-local-temp-permissions.test.ts` reproduces H12 faithfully when run as root
  (`setpriv` → `nobody` facing a root-owned directory) and with mode 0555 otherwise; nothing is skipped.
- **Commit.** idleproof-portal `48a5490`. **Human:** real Windows reboots remain required.

## 4. Root-cause summary

| Issue | Status | Evidence level |
|---|---|---|
| idleproof#54 fail-open without `dwchg_` | **CONFIRMED** and fixed | REPRO test on `7c8ffee` |
| diffwitness#136 wrong interpreter | **CONFIRMED** mechanism, fixed | deterministic two-venv native Stop; PATH reordering under Codex on the operator host INFERRED |
| Editable install imports original source | **CONFIRMED** (new), fixed | native Stop before/after |
| idleproof#29 wrong subject / invented role | **CONFIRMED** (5 causes), fixed | REPRO on `7c8ffee` and real Core + hook run |
| idleproof-portal#55 per-receipt status | **CONFIRMED** presentation defect, fixed | code reading + tests |
| idleproof-portal#48 0 % without checks | **CONFIRMED** on 3 remaining surfaces, fixed | code reading + tests |
| idleproof-portal#46 root-owned staging dir | mechanism **INFERRED** (source-backed), recovery fixed; trigger on host **UNKNOWN** | CLI source, faithful local reproduction of the state |
| Staging secrets not git-ignored | **CONFIRMED** (new), fixed | `git check-ignore` |

## 5. Non-regression matrix (historical human qualifications)

A historical PASS stays evidence for its own version and scope; it is not transferred.

| Historical result (version) | Invariant | Touched by this candidate | Automated coverage now | Human requalification |
|---|---|---|---|---|
| H7/H9 Proof accepted exact tree (Core `61dbf48`) | accepted only for the exact tree | L2 (runner env) | native Stop e2e, ProofBench | **Yes** — recipe S1 |
| H7 explanation FAIL (#29) | no invented role | L3 | context-change-subject | **Yes** — S1 step 4 |
| H8 debt delivered, 0/0 budget pass | debt measured, never assumed 0 | L1 (auto-debt gating unchanged), L4 display | change-synthesis, native-stop | **Yes** — S1 |
| H10 `DEC-1` DECLARED | DECLARED never becomes VERIFIED | not touched | existing memory tests | Spot check — S1 step 9 |
| H11 stop/start, no orphan (Portal `49e48a7`) | no orphaned PID/port/container | L6 (`repair` call) | launcher tests | **Yes** — C3 |
| H12 reboot PARTIAL | restart without manual repair | **L6** | faithful reproduction test | **Yes** — C4, real reboots ×2 |
| H13/H14 backup/restore | data preserved | not touched (no migration) | existing gates | Backup before C4 only |
| H15 identity/assurance idempotence | same receipt id, no duplicate | not touched (ingest unchanged) | existing tests | Not required |
| ATLAS-UNIFIED-01..03 (#51/#52 pilot) | Atlas V1 notes persist, Deep on demand | not touched (Atlas files), cockpit `app.js` touched | full IdleProof suite incl. Atlas tests; Atlas CI workflows | **Yes, light** — C2 |
| PORTAL-UI-02 PASS / UI-01 PARTIAL | Guided/Technical distinct | L4/L5 | component + source tests | **Yes** — S1 step 8 |
| PORTAL-E2E-01 PASS | post-proof receipt visible, exact ids | **L4** | change-synthesis | **Yes** — S1 step 8 |
| E2E-ALPHA-01 Stop PASS (with PATH prefix) | native Stop accepted | **L1, L2** | real Core + hook run | **Yes, without any PATH prefix** — S1 |

## 6. Machine results

Local runs: Linux, Python 3.12 (Core), Node 22.22.0, project venvs on Python 3.13. Hosted CI results are
recorded in §10 as they arrive; a job not run, cancelled or skipped is not counted as passed.

| Check | Baseline | Candidate |
|---|---|---|
| Core unittest | 867 OK, 53 skips, 254 s | see §10 |
| Core ruff F821/F822/F823 + compileall | — | OK |
| ProofBench | 4/4 (2.49 s) | 4/4, identical classifications (2.56 s) |
| ContinuityBench 10k | PASS (append 1.43 s, verify 0.55 s, rebuild 1.02 s) | PASS (1.26 / 0.56 / 1.03 s) |
| IdleProof `npm test` | 902 tests, 894 pass, 0 fail, 8 skip | see §10 |
| ExplainBench | 30/30 exact paths, 2 safe fallbacks | 30/30, 2 safe fallbacks |
| IdleProof perf-gate (alternating runs, medians) | hook p95 13.0 ms, Stop 90.6 ms | 18.4 ms, 99.2 ms (budgets 150 / 750) |
| Portal vitest | 425, 424 pass, 1 environment failure (root) | 446/446 |
| Portal typecheck, build, 4 gates | OK | OK |
| Portal client bundle | 480 128 B, largest chunk 192 484 B | 487 403 B (+1.5 %), largest unchanged |
| Real interproduct run (hook runner → Core) | `.venv` project: `stable-fail`; Local blocked/stable-fail; subject `tests/test_cart.py`/`test_small_order` | accepted causal; Local accepted bound by envelope; **same `dwchg_` in Local and Core**; subject `src/cart.py`/`gift_wrap_fee_cents`; without `.venv`: blocked/`test-runner-unavailable`, no certificate |

## 7. Security, performance and cost review

- **Trust boundaries.** Evidence may now run the project's `.venv` interpreter: the same trust as the
  `node_modules/.bin` evidence already used (the user's own toolchain, untracked); a configured
  `python_env` is a tracked, reviewable change. Counterfactual acceptance rules are unchanged. Editable
  mapping is limited to paths inside the source repository and outside the environment. Diagnostics
  print the interpreter path and the missing module name, never test output. Local: envelope read
  bounded (1 MiB), Git invoked without a shell, agent paths literal and limited to admitted project
  files. Portal: synthesis reads are project-scoped under existing RLS; no new endpoint, grant or
  migration. Launcher: no sudo/chown/chmod/delete, no secret read; staging secrets now git-ignored.
  No secret is logged by any change.
- **Performance.** Core: ~3 ms per evidence command for environment resolution. IdleProof: one Git
  process per live hook event, two at handoff (+≈5 ms p95, +≈9 ms Stop). Portal: +2 bounded queries per
  timeline page, +1.5 % client bundle. ProofBench/ContinuityBench unchanged.
- **AI cost.** No new LLM call, no paid request, no change to OpenRouter or managed-AI budgets. The
  managed-AI context receives null coverage when no check was answered (fewer misleading facts, no
  extra tokens of note).

## 8. Local deployment and rollback (non-destructive)

Install into an **isolated** location first (recipe §0). Never `git reset --hard`, `git clean -fdx`,
force-push, `supabase db reset`, volume deletion or restore over retained data. Before using the
candidate Portal launcher on a retained stack: `scripts/alpha-local.sh backup FILE` and keep FILE.
Rollback = check out the previous commits recorded in the manifest and restart (no migration to undo);
any staging directory moved aside by L6 stays in place for inspection. Draft PRs are not merged.

## 9. Qualification decision (at writing time)

**PARTIAL.** All six lots are implemented with reproduction tests and pass locally; hosted CI is
pending (§10); HUMAN acceptance is NOT RUN. Known residuals outside this candidate: idleproof#30
(`source=manual` vs `ide` provenance), hosted Windows/macOS behaviour of L2 until CI, the host-side
trigger of H12. The candidate may move to **READY FOR HUMAN ALPHA ACCEPTANCE** only once hosted CI is
green on the exact heads; **ALPHA READY** requires the operator's human acceptance.

## 10. Append-only results journal

- 2026-10-24 — dossier created; local results as in §6; draft PRs diffwitness#137, idleproof#55,
  idleproof-portal#56 opened; Portal `prealpha-pr-gates` dispatched on the stabilization branch.
- 2026-10-24 — **incident (test code, sandbox only).** A first version of the L6 test's cleanup walked
  the fixture recursively and followed the fixture's symlink to the system temporary directory, setting
  mode 0755 on files under `/tmp` of the disposable agent container (no deletion: `rmSync` does not
  follow symlinks; no repository, user data or file outside `/tmp` affected). Tracked file modes of the
  scratch worktrees were restored from their Git index. The test now never walks recursively and links
  only inside its fixture; a re-run confirmed no change outside the fixtures.
- 2026-10-24 — **final local heads.** Core `8ee8ee29a5fcc0557b968d9033485251ad80a8e2`: unittest 888 OK,
  53 skips (262 s), ruff F821/F822/F823 and compileall OK, run from a fresh venv of that commit (so the
  subprocesses import the commit under test). IdleProof `cd59df2c6d4b9e74c5ae6224079e1db8b443e088`: `npm
  test` 924 tests, 916 pass, 0 fail, 8 skipped; perf-gate PASS ×3 (hook p95 10.6–11.8 ms, Stop
  73.6–75.8 ms; budgets 150 / 750 ms); ExplainBench 30/30, 2 safe fallbacks. Portal
  `87d92ef06f908856faf1bf0793d659e6250b64f9` pins these two heads in the integrated CI jobs (legacy pins
  unchanged); the earlier dispatched `prealpha-pr-gates` run 40051713551 on the superseded pins was
  cancelled and the workflow re-dispatched on the new head. The cancelled run counts as **not run**.
- 2026-10-24 — **recipe dry run (exact artefacts, isolated prefix, simulated agent events).** Core wheel
  built from `8ee8ee2` into its own venv, IdleProof `npm pack` of `cd59df2` installed with `--prefix`,
  only `dw` and `idleproof` linked on `PATH`; recipe §1 project. `dw setup --agent codex
  --idleproof-command "$(command -v idleproof)"` wrote 9 Codex hooks running the npm hook runner and
  `.idleproof/diffwitness.json` with the absolute Core `dw`. Events fed through those exact hook
  commands: S1 Stop **accepted** (`dw2_9c0a4c64c0eb86563309`, causal, `dwchg_960ad681beab0741fc09e35f`),
  Local `accepted` bound by `core-change-envelope` with the same change and certificate, handoff subject
  `src/cart.py` / `gift_wrap_fee_cents` ("The change adds `gift_wrap_fee_cents`"), no auth/SQL wording;
  S2 Stop **blocked** `stable-fail`, Local `blocked`, the refused change keeps its verdict after the revert
  (`no-change` for the reverted tree); S2.7 without `.venv`: `cause: test-runner-unavailable (`python -m
  pytest -q`: No module named pytest)`. A first S2 attempt that skipped SessionStart was refused
  fail-closed as `not-armed` (simulation error, correct product behaviour). IdleProof tarball SHA-256
  `eca434f137e89dc9333205422588a413470eebfcf15acae67190d1e7940fdeda` (Node 22.22.0, npm 10.9.4).
  **Finding (not changed, recorded as residual):** without `--idleproof-command`, `dw setup` arms the
  `idleproof` console script bundled in the Core wheel; Proof runs but the npm IdleProof Local cockpit
  sees no session. The same wheel script also explains how a Core venv `bin/` on `PATH` can shadow the
  npm `idleproof`. The human recipe uses the explicit form. Not simulated here: a real Codex/Claude
  process, hook trust, the Local and Portal UIs, Windows/WSL.
- 2026-10-24 — **hosted CI on `8ee8ee2` (PaititeResearch/diffwitness#137, run 40052268436): two real
  findings.**
  1. *Release package preflight* — **regression introduced by L2, CONFIRMED and fixed.** The
     source-distribution smoke runs the suite from a venv without pytest that is first on `PATH`; L2's
     readiness then reports, correctly, that `python -m pytest` would run in DiffWitness's own runtime
     without pytest, and three `test_status_cli` fixtures that implicitly assumed the host interpreter has
     pytest failed. Reproduced locally (sdist smoke: 888 tests, 3 failures; same three with the Core venv
     first on `PATH`); the base `0933d5c` passes under the same condition. Fix `8d7ae4d` (tests only): the
     fixture project gets its own `.venv` providing its runner, as a real project does. Product behaviour
     unchanged; no assertion weakened.
  2. *Installed wheel commercial-alpha journeys* (ubuntu, macOS) — **not caused by this candidate.**
     `python -m pipx install --pip-args=--no-index <wheel>` fails inside pipx's own "upgrading shared
     libraries" step (`No matching distribution found for pip>=26.1`) before the wheel is touched.
     Reproduced locally (pipx 1.18.4, a Python whose bundled pip is 25.0.1, `uv` off `PATH`): the base
     `0933d5c` wheel fails identically; `pipx<1.18` (1.17.14) and `PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE=1`
     both pass. pipx is unpinned in `test.yml` (1.18.0 published 2026-10-15); the workflow and the
     acceptance script are byte-identical to the base, which passed on 2026-10-10. Proposed fix (not
     applied, outside this candidate's scope): pin `pipx<1.18`, or set the variable in the script's pipx
     environment. Recorded as **red, not this PR's**; it is not counted as passed.
  3. *Coverage hidden by finding 2.* In that job the failing pipx step is followed by five **skipped**
     steps: `alpha_smoke.py` (Guard + Debt + change envelope), `engine_artifact_smoke.py`,
     `human_acceptance.py`, `idleproof_release_acceptance.py`, `recovery_acceptance.py`. They were run
     locally as in CI (fresh Python 3.12 venv, exact wheel of `8d7ae4d` installed `--no-deps`, its `bin/`
     first on `PATH`, no pytest): **all five PASS** (`dw2_c1eb07171556f55b4d1f`, 6 human journeys, IdleProof
     release boundaries, fail-closed recovery). Linux only; on macOS and Windows these five remain **not
     run** until the pipx step is fixed. Every other job of the run is green: the 12 `test` jobs (Linux,
     macOS, Windows × Python 3.11–3.14; on Windows the evidence-environment tests use real
     `Scripts\python.exe` venvs), standalone binaries ×3, optional syntax providers ×3, composite Action,
     static checks, causal semantics benchmark, native Understand → Prove → Owe → Continuity,
     ContinuityBench.
- 2026-10-24 — **hosted CI on IdleProof `cd59df2` (PaititeResearch/idleproof#55, run 40052171223):
  regression introduced by L3, CONFIRMED and fixed.** Every other job is green (Node 20/22/24 × three
  OS, ExplainBench + perf budgets, installed journeys ×3, paged memory export, first-extraction phases,
  Atlas, Deep, project understanding, contracts, browser). *Real Core context consumer* (6 jobs: three
  OS × two Core refs) failed at `scripts/structure-core-smoke.mjs`: three CI smokes outside `npm test`
  (`structure-core`, `structure-languages`, `structure-all-providers`) asked "Inspect invented" (a decoy
  in a string) and expected the file's **first real declaration** as the subject — the fallback L3
  removes. The whole job was replayed locally, in order, with and without the optional grammars,
  against this candidate's Core: base `7c8ffee` 12/12; `cd59df2` 9/12 (those three); fix `d3b9ed5`
  (scripts only, shipped code unchanged) 12/12. The adapted smokes assert a null subject, exactly the
  AST declarations (never the decoy) and run their cache-invalidation checks on the declarations.
- 2026-10-24 — **Portal gates on `87d92ef` (run 40052300295): regression introduced by L4, CONFIRMED
  and fixed.** Green: replay from zero, app node22/node24, edge, memory card, continuity producers ×2,
  auto-debt real stack, **alpha-local launcher real stack L1–L6** (exercises L6), project understanding
  with real Core/Local/Chromium. Red: *longitudinal memory / real stack recipe* — phase first-project
  P3 (`app.py` not visible) and P9 (per-receipt debt texts not visible after signing in again) — and the
  G1–G12 aggregation that refuses incomplete evidence. Cause: L4 folded each change's receipts in a
  closed `<details>` in Guided, and the recipe reads the visible text (`innerText`): information shown
  before the candidate was hidden by default, contrary to L4's own rule. Fix `5c4b98c`: the group is
  open by default in both views (still foldable); the route test pins it. Local `ci:app` (build,
  typecheck, 446/446, four gates, bundle budget) green; gates re-dispatched on `5c4b98c`.
- 2026-10-24 — **hosted CI after the fixes.**
  - Core `3f33162` (`test` run 40054367942): 21/24 jobs green — including *release package preflight*
    (sdist suite) and the 12 `test` jobs — plus `proofbench`, `continuitybench` and
    `integrated-product-smoke` green. Red: the three *installed wheel commercial-alpha journeys* jobs, at
    the pipx step only (finding 2 above; identical on the base; fix proposed on
    PaititeResearch/diffwitness#137, not applied without the owner's decision). Their five later steps
    are **not run** on macOS/Windows (5/5 PASS locally on Linux).
  - IdleProof `d3b9ed5` (run 40054713702 and the Atlas / Deep / project-understanding workflows): **all
    green**, including the six *real Core context consumer* jobs.
  - Portal `5c4b98c` (`prealpha-pr-gates` run 40054815816, producers pinned to Core `8ee8ee2` and IdleProof
    `cd59df2`, code-identical to the branch heads): **all green**, including the longitudinal
    memory real-stack recipe, the alpha-local launcher real stack (L1–L6), auto-debt on the real stack
    and the G1–G12 aggregation.
- 2026-10-24 — **decision at the end of this session: PARTIAL.** Every lot is implemented, reproduced and
  machine-qualified; three regressions introduced by the candidate were found by hosted CI and fixed
  (`8d7ae4d`, `d3b9ed5`, `5c4b98c`). The candidate becomes **READY FOR HUMAN ALPHA ACCEPTANCE** once the
  only remaining red check — the Core pipx tooling step, outside this candidate — is fixed (one line,
  verified locally) or explicitly waived by the owner, and the Core CI is re-run. **HUMAN NOT RUN.** Not
  merged, not released, **not ALPHA READY**.
- 2026-10-24 — **owner decision on the pipx step** (comment on PaititeResearch/diffwitness#137): neither a
  lasting red exception nor a `pipx<1.18` pin. Classification: orchestration problem of the offline
  consumer scenario (pipx 1.18.4 upgrades its shared pip to `pip>=26.1` under `--no-index`), **not a
  demonstrated Core regression**. Fix authored by the owner in draft PaititeResearch/diffwitness#138
  (`92994a4`): `PIPX_DISABLE_SHARED_LIBS_AUTO_UPGRADE=1` in the disposable `pipx_env` of
  `scripts/installation_resolution_acceptance.py` only; `--no-index`, the real wheel install, the
  executable and hook checks unchanged; no `continue-on-error`, no skip. This supersedes the `pipx<1.18`
  alternative proposed in the 2026-10-24 entry above. #138 CI on `92994a4`: 27/27 green, including the
  three journeys jobs and, for the first time on macOS and Windows, the five steps after pipx.
- 2026-10-24 — **integration into the Core candidate (owner's go-ahead).** Verified before the operation:
  #137 head `24cd6d51e7bfa665ea9f326096a9283ea123de60` (local = remote); `92994a4d87b6df61e988f9da6a53142a9059ad67`
  has parent `24cd6d5` and touches only `scripts/installation_resolution_acceptance.py`. Cherry-picked
  with `-x` → `e289c915565096807c76104a05b06e0e05b608d0` (author kept; tree byte-identical to `92994a4`;
  diff vs `24cd6d5`: that one file, +7/−1); fast-forward push. Backup and reference refs recorded before
  and checked unchanged after: `snapshots/alpha-20261024-before-claude/*` (Core `main`/`pr133`,
  IdleProof `main`/`pr37`/`pr52-atlas`/`pr54-stabilization`, Portal `main`/`pr50`), the three `main`
  (`61dbf48`, `7725057`, `459cb7b`) and the historical candidate branches. Nothing merged, no release.
- 2026-10-24 — **hosted CI on `e289c91`:** **27/27 green** — `test` run 40085568577: 24/24 (12 `test` jobs Linux/macOS/Windows × Python 3.11–3.14, release package preflight, standalone binaries ×3, optional syntax providers ×3, composite Action, fatal static checks, installed wheel commercial-alpha journeys ×3), plus `proofbench` (causal semantics benchmark), `continuitybench` and `integrated-product-smoke` (Native Understand → Prove → Owe → Continuity). In each of the three journeys jobs the pipx step and the five later steps (Guard + Debt + change envelope, private engine + adaptive Gate, human acceptance journeys, IdleProof release boundaries, fail-closed recovery) pass on Linux, macOS and Windows. Refs re-read after the push: only `claude/diffwitness-idleproof-alpha-d0lv1f` moved (`24cd6d5` → `e289c91`).
- 2026-10-24 — **consolidated manifest and inter-product contracts (machine check on the exact heads).**
  Heads: Core `e289c91` (shipped code `8ee8ee2`; later commits change tests, CI scripts and docs only),
  IdleProof `d3b9ed5` (shipped code `cd59df2`), Portal `5c4b98c`. `git diff 8ee8ee2 e289c91 -- src
  pyproject.toml` and `git diff cd59df2 d3b9ed5 -- src bin public package.json` are empty. The ten
  producer pins of Portal `prealpha-pr-gates` are exactly those shipped-code commits (5 × Core `8ee8ee2`,
  5 × IdleProof `cd59df2`); their run 40054815816 on `5c4b98c` is fully green. Migrations: none versus
  the Portal base `198215f` and versus Portal `main`. Contracts: on the producer side no envelope,
  snapshot or integration-config writer changed (Core diff limited to the evidence environment,
  analysis/readiness/doctor/config/autodetect/runner; Portal `supabase/functions` unchanged); identifier
  occurrences at base → head: `change-envelope-1` Core 8 → 8, IdleProof 3 → 5 (new readers);
  `idleproof.portal-snapshot.v1` 1/1/3 → 1/1/3; `diffwitness.integration-config.v1` 1/1 → 1/1;
  `dwchg_` Core 10 → 10, IdleProof 16 → 17, Portal 28 → 36 (new exact-id consumers). In
  `portal-snapshot.mjs` only the text of the bounded summary field changes ("Adds"/"Changes" from Git
  evidence; same key, same 300-character bound). Identical `dwchg_` in Local and in the Core envelope was
  shown on the shipped-code artefacts (recipe dry run). **Machine verdict: consistent.** The owner's
  review of this manifest is still required.
- 2026-10-24 — **status:** Core lot **MACHINE PASS** on `e289c915565096807c76104a05b06e0e05b608d0` (owner's criterion: CI entirely green). Global candidate **NOT ALPHA READY**; not yet
  READY FOR HUMAN ALPHA ACCEPTANCE — owner's conditions: review of the consolidated manifest Core +
  Local + Portal, of the inter-product contracts, and confirmation of the local WSL/Portal backup (recipe
  §0.2b). No human recipe and no migration on the reference installation before that backup is
  confirmed. Recipe updated: backup gate §0.2b (read-only checks, repeated before C4).
- 2026-10-24 — **what remains to qualify (at this entry).**
  1. *Owner gates before READY FOR HUMAN ALPHA ACCEPTANCE:* review of the consolidated manifest
     (`STABILIZATION_ALPHA_20261024.json`, `consolidationCheck`) and of the contracts above; confirmation of
     the local backup (recipe §0.2b: Portal data backup of today, `idleproof-portal-alpha-backup/1` header,
     data rows present; local producer state archived; previous tools recorded; WSL export before C4).
  2. *Human recipe, never run on this candidate:* S1 (Codex/Claude on WSL, **no `PATH` prefix**, Proof
     accepted, explanation of the real change, debt, continuity, Portal Guided/Technical, DEC-S1 DECLARED,
     persistence), S2 (refusal everywhere, recovery, history kept, optional missing-runner cause), C2
     (Atlas note persists, no paid call; `public/app.js` changed), C3 (stop/start, no orphan), C4 (two
     real Windows reboots, Portal running then stopped, no sudo, no manual repair). HUMAN PASS only if every
     non-optional row passes.
  3. *Not covered by any machine evidence:* WSL itself (CI is Linux/macOS/Windows-native; the real Supabase
     stack runs on Linux CI only); provider hook trust and real Codex/Claude processes; the host-side
     trigger of H12 (L6 recovery proven on the Linux real-stack launcher job L1–L6 and by the faithful
     reproduction only); the `PATH` reordering under Codex for #136 (inferred); the visual reading of the
     Guided/Technical timeline and of the Local Native Proof labels.
  4. *Known residuals outside the candidate:* PaititeResearch/idleproof#30 (`source=manual` vs `ide`);
     `dw setup` without `--idleproof-command` arms the `idleproof` script bundled in the Core wheel
     (documented, product decision pending); PaititeResearch/diffwitness#138 is now contained in #137
     (`e289c91`, same tree) and can be closed by its author.
  5. *After HUMAN PASS only:* merge plan of the three drafts onto their bases, then towards `main`, and a
     release with recorded artefact digests — each needs the owner's explicit approval.
- 2026-10-24 — **owner's technical review of the consolidated manifest and contracts**
  (PaititeResearch/diffwitness#74, comment 6383703423; PaititeResearch/diffwitness#137, comment
  6383713859). Verdict: manifest and inter-product contracts consistent with the code heads Core `8ee8ee2`,
  IdleProof `cd59df2`, Portal `5c4b98c` and the exact Portal CI pins; **no blocking divergence for entering
  the human recipe**. CI recorded at review time: Core `dadf874` 27/27 (docs only after `e289c91`, itself
  27/27), IdleProof `d3b9ed5` 32/32, Portal `5c4b98c` 12/12. Reserves handled in this entry's commit: (a)
  the JSON named `e289c91` as the last machine head — `products[core].lastVerifiedBranchHead`
  (`dadf874`, runs 40087320497 / 40087320490 / 40087320492 / 40087320528) and `hostedCi.coreBranchHeads`
  are added, the `e289c91` records are kept, and `branchHeadPolicy` states that a commit cannot name
  itself (later docs-only heads are recorded here and on #74); (b) recipe §0.3 now starts from a new empty
  directory, checks the three checked-out SHAs and **exactly one wheel and one tarball** before computing
  digests and installing by exact file name. Residual recorded: Portal gates still check out the producers
  as `TFourniax/tooltest` / `TFourniax/tooltest-2` (pre-transfer names, working by redirect) — to clear
  before a public release. Status: **MACHINE PASS + REVIEW COMPLETED / LOCAL BACKUP PENDING (§0.2b not
  attested) / HUMAN NOT RUN / NOT ALPHA READY.** No installation, Portal stop, migration or reboot on the
  reference installation before the backup is attested; backup files (SQL dump, archives) hold secrets
  and are never uploaded.

- 2026-10-24 — **Owner correction: retained WSL/Portal/IdleProof data may be reused; no reset
  has been performed.** Earlier mandatory backup gate §0.2b had never been completed: no
  Portal SQL dump, IdleProof archive or WSL export was made. The GitHub snapshot branches protect
  code refs only. The owner did **not** designate existing data disposable and does **not** want
  to repeat the initial onboarding unnecessarily. Recipe §0.2 now requires a read-only check of
  the existing Portal/IdleProof state, code versions, schema and process ownership, followed by
  a compatible non-destructive reuse of the retained Docker volumes. The fixed Supabase project
  name/port means a new checkout is not a database sandbox. No deletion, reset, SQL restore or
  automated backup is performed by this document; a small SQL backup is optional, but absence
  of one is an acknowledged recovery risk. Obtain operator approval before stopping the live
  Portal and before each Windows reboot. This dated decision supersedes only the old
  mandatory-backup *gate*, never earlier evidence of its noncompletion. The next human acceptance
  is still NOT RUN and no new candidate is ALPHA READY.
