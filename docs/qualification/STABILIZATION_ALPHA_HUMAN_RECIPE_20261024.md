# Human acceptance recipe — Alpha stabilization candidate (2026-10-24)

Dossier: `STABILIZATION_ALPHA_20261024.md` · Manifest: `STABILIZATION_ALPHA_20261024.json` ·
Registry: PaititeResearch/diffwitness#74.

This recipe is the only route to **HUMAN PASS** for the candidate below. A historical PASS
(H7–H15, PORTAL-E2E-01, ATLAS-UNIFIED-01..03, E2E-ALPHA-01) is not transferred to this version. Run
everything inside one WSL2 Ubuntu distribution, as in Portal `docs/ALPHA_LOCAL_FIRST_USE.md`; only the
browser runs on Windows. Write every observed value on the result sheet (§R), including failures.
Estimated time: 75–100 min, plus two reboots.

**Exact versions under test** (machine-qualified heads; version numbers are unchanged, so the commit is
the identity):

| Product | Repository | Commit |
|---|---|---|
| Core | PaititeResearch/diffwitness | `8ee8ee29a5fcc0557b968d9033485251ad80a8e2` (later branch commits: tests and docs only) |
| IdleProof Local | PaititeResearch/idleproof | `cd59df2c6d4b9e74c5ae6224079e1db8b443e088` |
| Portal | PaititeResearch/idleproof-portal | `5c4b98ccfb21b4ba1929f94ab4bd7a4eb4a7e548` |

**Rules for the operator.** Do not merge anything. Do not run `supabase db reset`, `docker volume rm`,
`git reset --hard`, `git clean -fdx` or `restore` unless §8 says so. Do not paste a token on a command
line. If a step fails, write what you saw, stop that scenario and continue with the next one: a FAIL is
a valid result.

## 0. Preparation (once, ≈20 min)

**0.1 Record what is installed now** (needed for rollback):

```bash
dw --version; command -v dw; npm ls -g idleproof; command -v idleproof
grep -n 'diffwitness' ~/.bashrc ~/.profile 2>/dev/null     # keep any line as it is: the fix must work with it
```

**0.2 Read-only preservation check — reuse the EXISTING WSL, Portal and IdleProof data.**

**Owner decision (2026-10-24):** the previously proposed snapshot scripts were **not run**.
No Portal SQL backup, IdleProof state archive or WSL distribution export exists as part of this
qualification. The owner explicitly wants to **preserve and reuse the current environment**;
the data are NOT declared disposable. This correction removes a disproportionate
mandatory-backup gate, **not** the obligation to protect existing data.

Do not run `supabase db reset`, `docker volume rm`, `git reset --hard`, `git clean -fdx`,
or `scripts/alpha-local.sh restore` on any existing installation. A GitHub snapshot branch
preserves code only, never SQL, credentials, private notes or local WSL files.

**Before any stop/start or candidate install, inspect the existing setup in read-only mode:**

```bash
echo '=== Current WSL projects (read-only) ==='
for p in "$HOME/code/dw-human-test" "$HOME/alpha/portal" "$HOME/atlas-unified-pr52-trial/outil"; do
  if [ -d "$p" ]; then
    echo "$p"
    if git -C "$p" rev-parse --is-inside-work-tree >/dev/null 2>&1; then git -C "$p" rev-parse HEAD; fi
  fi
done
echo '=== State presence; never print secrets ==='
test -f "$HOME/code/dw-human-test/.idleproof/state.json" && echo 'IdleProof state present' || echo 'IdleProof state not found here'
docker ps -a --filter label=com.supabase.cli.project=idleproof-portal --format '{{.Names}} {{.Status}}' || true
ss -H -ltn '( sport = :3000 )' || true
```

Confirm that existing accounts/projects/receipts are visible in Portal before proceeding;
record the current Portal checkout path, running process owner, source commit and schema.
Do not assume the state is healthy solely because GitHub CI is green.

**Crucial isolation limit:** the Portal launcher uses the fixed Docker/Supabase project
`idleproof-portal`, its retained volumes, a shared state directory and port 3000. A new
`~/alpha-stab/portal` Git checkout does **not** create a separate database. The intended
test can reuse the existing database without resetting it, only if the operator has verified
that the schema/credentials are compatible and no unrecognised Portal processes are running.
Existing Portal #56 introduces no new migration relative to the referenced main/base;
this does not guarantee that an arbitrary local stack has the same migrations installed.

Stopping the known existing Portal with **its own** `scripts/alpha-local.sh stop` preserves
Supabase Docker volumes. Obtain operator approval before any live-service interruption.
A new candidate Portal can then start against the retained stack (same project name),
subject to ownership and migration preflight. Never run two Portal launchers at once.
Do not make a destructive recovery attempt to resolve an unexpected migration,
credential mismatch, port collision or H12 permission problem; stop and diagnose.

**Optional minimal backup (not a precondition):** after verifying the current Portal
checkout and compatibility, the operator may execute its existing
`scripts/alpha-local.sh backup FILE` command to save SQL rows only, with mode 0600.
Do not upload the backup or any private state. A full WSL export is not required.
**Important limitation:** because no local backup was taken, loss or corruption of the
retained SQL/IdleProof state may be irreversible. Reusing it is possible; reverting
modified files or changing Git branches is not equivalent to data restoration.

**0.3 Install candidate source/tools in a separate directory** (the current `dw` / `idleproof` stay installed; the existing Portal Docker state is shared):

```bash
ls -d ~/alpha-stab                     # must fail (No such file or directory): start from a new, empty directory
mkdir -p ~/alpha-stab && cd ~/alpha-stab
git clone https://github.com/PaititeResearch/diffwitness core && git -C core checkout 8ee8ee29a5fcc0557b968d9033485251ad80a8e2
git clone https://github.com/PaititeResearch/idleproof idleproof && git -C idleproof checkout cd59df2c6d4b9e74c5ae6224079e1db8b443e088
git clone https://github.com/PaititeResearch/idleproof-portal portal && git -C portal checkout 5c4b98ccfb21b4ba1929f94ab4bd7a4eb4a7e548
git -C core rev-parse HEAD; git -C idleproof rev-parse HEAD; git -C portal rev-parse HEAD   # exactly the three SHAs above
python3 -m venv core-venv && core-venv/bin/pip wheel ./core --no-deps -w wheels
(cd idleproof && npm pack)
ls wheels/*.whl idleproof/*.tgz        # exactly two lines: wheels/diffwitness-0.4.0a1-py3-none-any.whl and idleproof/idleproof-0.10.0.tgz
sha256sum wheels/diffwitness-0.4.0a1-py3-none-any.whl idleproof/idleproof-0.10.0.tgz   # write both on the sheet
core-venv/bin/pip install --no-deps wheels/diffwitness-0.4.0a1-py3-none-any.whl
npm install --prefix ~/alpha-stab/npm ./idleproof/idleproof-0.10.0.tgz
mkdir -p bin && ln -sf ~/alpha-stab/core-venv/bin/dw bin/dw && ln -sf ~/alpha-stab/npm/node_modules/.bin/idleproof bin/idleproof
```

If `ls` lists more than one wheel or tarball, stop: something was left from an earlier attempt; start
again in a new empty directory rather than choosing a file.

In **every** terminal used below, first run `export PATH="$HOME/alpha-stab/bin:$PATH"` and check that
`command -v dw` and `command -v idleproof` both print a path under `~/alpha-stab/bin`. Only `dw` and
`idleproof` are linked: **no Python directory is added to `PATH`** (E2E-ALPHA-01 needed a PATH prefix;
this recipe must pass without one).

**0.4 Start candidate Portal only after the preservation check in §0.2:**

If the earlier Portal is running, **do not** start this checkout in parallel. Identify
the previous Portal checkout and its process, obtain operator approval, then stop it
via that checkout's own `scripts/alpha-local.sh stop` (retaining volumes).

```bash
cd ~/alpha-stab/portal && scripts/alpha-local.sh start && scripts/alpha-local.sh status
```

Use the same retained database only after confirming schema compatibility. Recheck
that the previous accounts, projects, receipts and decisions remain visible. If any
item disappears or the launcher reports an unexpected migration, STOP; do not reset.

Expected: `Portal: http://localhost:3000 (running)`, `Ingest: … (running)`. Sign in with your existing
account (or create one as in the first-use guide §4). Write on the sheet the first 40 characters of
`cat ~/.local/state/idleproof-portal-alpha/build.revision` (must be the Portal commit above).
Never run two Portal checkouts at once: they share the Docker project `idleproof-portal` and the
launcher state directory, which is why §0.2 stops the current one first.

## 1. Test project (shared by S1 and S2)

```bash
mkdir -p ~/code/stab-cart && cd ~/code/stab-cart && git init -q
mkdir -p src tests && touch src/__init__.py
printf 'def apply_discount(total):\n    return total * 0.9 if total >= 100 else total\n' > src/cart.py
printf 'from src.cart import apply_discount\n\n\ndef test_small_order():\n    assert apply_discount(50) == 50\n' > tests/test_cart.py
printf '[diffwitness]\ntest = "python -m pytest -q"\n' > .diffwitness.toml
printf '.venv/\n__pycache__/\n.pytest_cache/\n' > .gitignore
python3 -m venv .venv && .venv/bin/pip install -q pytest && .venv/bin/python -m pytest -q
git add -A && git commit -qm base
dw setup --agent codex --idleproof-command "$(command -v idleproof)"   # or --agent claude; approve the hooks in the agent when it asks
dw doctor --view technical
```

`--idleproof-command` matters: without it, `dw setup` arms the `idleproof` entry point bundled in the
Core wheel, and the IdleProof **Local** cockpit then sees no session (Proof still runs).

| Check | Expected |
|---|---|
| `pytest` in `.venv` | `1 passed` |
| `dw doctor --view technical` | a line `Python env: project-local · /home/<you>/code/stab-cart/.venv`, no `PROBLEM:` |
| `.idleproof/diffwitness.json` | `"requireDiffWitness": true`, `diffWitnessCommand` = `…/alpha-stab/core-venv/bin/dw` |
| `.codex/hooks.json` | 9 hooks, each `"…/node" "…/alpha-stab/npm/node_modules/idleproof/bin/idleproof-hook.mjs" codex` |

Connect the project to Portal (first-use guide §5): `idleproof portal identity`, create the project in
Portal, `idleproof portal configure --endpoint '<URL>' --token-stdin`, `idleproof portal sync`,
`idleproof portal auto-debt enable`. *Check connection* in Portal must say **connected**.

Open Local in a second terminal (same `PATH` export): `cd ~/code/stab-cart && IDLEPROOF_EXPERIMENTAL_ATLAS=1 idleproof start`.

## S1. Nominal flow (≈25 min)

Start the agent **from a terminal with the `PATH` export only** (no other prefix) in `~/code/stab-cart`.

| # | Action | Expected | Covers |
|---|---|---|---|
| 1 | Prompt: *"Add `gift_wrap_fee_cents(item_count: int) -> int` to src/cart.py: 150 cents per item, capped at 600. Add tests."* Let the agent finish. | The agent edits `src/cart.py` and `tests/test_cart.py`; hooks run with no error shown by the agent. | hooks |
| 2 | Watch Local while the agent works. | Activity appears live; the current task is the gift-wrap request. | Local live |
| 3 | When the agent stops: read the agent's Stop message. | `DiffWitness Proof accepted: dw2_…` (or another accepted family). **Not** `stable-fail`, **not** `test-runner-unavailable`. Write the certificate id. | #136 |
| 4 | Local → *Native Proof*. | **Proof accepted**, same certificate id as step 3, the exact change id `dwchg_…` (write it), claim *causal*. Never "The code is ready" without Core's acceptance. | #53/#54 |
| 5 | Local → explanation of the change. | Subject is `src/cart.py` / `gift_wrap_fee_cents`; wording "this change adds …". **Fail if** it names `test_small_order` or `apply_discount` as the subject, says "Work around …", or speaks of authentication, sessions, users or SQL tables. Unchanged `apply_discount` may appear only as existing context. | #29 |
| 6 | Wait for `idleproof portal auto-debt status` to show the change as *measured · delivered*. | Debt points/obligations shown (0/0 is acceptable **only** when it is displayed as measured). | debt |
| 7 | `git add -A && git commit -qm "gift wrap fee"` then ask the agent a follow-up question about what it changed. | The answer refers to `gift_wrap_fee_cents`; Local keeps the same change history. | continuity |
| 8 | Portal → project → timeline, in **Guided** then **Technical**. | One block for the change with the exact `dwchg_…` of step 4: Guided says **Causally verified** once; Technical shows `change dwchg_…`, `certificate dw2_…` (same as step 3), the receipt id carrying the proof, debt, and the receipt count. Every individual receipt is still listed below; an update without its own result says *not attached to this receipt*, not "failed". Human mastery shows **Not assessed** (never 0 %). | #55, #48 |
| 9 | `dw decision record "Gift wrap fee capped at 600 cents" --id DEC-S1 && idleproof portal sync` | Portal shows DEC-S1 as **DECLARED** (never VERIFIED). | memory |
| 10 | Reload Portal and Local (F5). | Same statuses, same ids; nothing reverts to "pending" or "not attached yet". | persistence |

## S2. Failure and recovery (≈20 min)

| # | Action | Expected |
|---|---|---|
| 1 | Prompt: *"Make gift_wrap_fee_cents return 0 for every input. Do not modify any test."* | The change contradicts the tests written in S1. |
| 2 | Read the Stop message. | Proof **not** accepted (a refusal with its reason, e.g. a failing test); no certificate presented as accepted. The agent may be asked to continue (at most 3 continuations, then a stop that needs a person). |
| 3 | Local → *Native Proof*. | **Proof not accepted** or **Proof stopped · needs a person**, with Core's reason. Never "accepted", never "The code is ready". |
| 4 | Portal timeline. | The new change appears as **Proof not accepted** or **Observed, not verified** (if no result was delivered yet) — never *Causally verified*. Debt not measured shows *Missing debt is not zero debt*. |
| 5 | Prompt: *"Revert that change; keep the cap at 600."* (or `git checkout -- src/cart.py`), then let the agent stop. | Stop: accepted again, or *No change to prove* if the tree equals the accepted one. |
| 6 | Local and Portal history. | The refused change keeps its own verdict (Local: the change with **Proof not accepted** stays in the session's change history; Portal: the refused change and its receipts kept). The reverted tree shows **No change to prove** or **Proof accepted**. Nothing was deleted. |
| 7 | Optional negative: `mv .venv .venv.off`, make a small change, let the agent stop, then `mv .venv.off .venv`. | The refusal carries an explicit `cause:` line (`test-runner-unavailable`, `evidence-command-unavailable` when Ubuntu has no `python` command, or `missing-module` naming the module) — never a bare `stable-fail`, never accepted. |

## C2. Atlas and notes (≈10 min)

In Local (started with `IDLEPROOF_EXPERIMENTAL_ATLAS=1`): *Repository Atlas* → open it (use the
existing capture; the Atlas never scans by itself) → add a note on `src/cart.py` → **Save view** → reload
the page → reopen the Atlas. Expected: the note is still there, marked as declared; no paid/BYOK call was
made (`idleproof ai status` unchanged). Deep analysis, if opened, runs only on demand.

## C3. Stop / start (≈5 min)

```bash
cd ~/alpha-stab/portal && scripts/alpha-local.sh stop && scripts/alpha-local.sh status
scripts/alpha-local.sh start && scripts/alpha-local.sh start && scripts/alpha-local.sh status
```

Expected: after `stop`, nothing running and no orphaned Portal/ingest process or port 3000 listener
(`ss -ltnp | grep -E ':3000|:54321'` empty); the second `start` is a no-op or a clean restart; the S1
timeline, debt and DEC-S1 are intact.

## C4. Real Windows reboots (×2, ≈15 min + reboots)

**Before C4, repeat the read-only preservation and compatibility checks in §0.2.**
Two actual Windows reboots are still required for an eventual full H12 human qualification.
Reboot interrupts other WSL processes; obtain explicit operator approval for each restart.
The backup remains optional, but without one a loss of SQL/WSL state may be permanent.
Do not claim reboot-safe recovery until both real tests have passed.

1. Leave Portal **running**. Restart Windows (Start → Restart; not `wsl --shutdown`).
2. Open Ubuntu: `cd ~/alpha-stab/portal && export PATH="$HOME/alpha-stab/bin:$PATH" && scripts/alpha-local.sh start`.
   - Expected: Portal and Ingest running **without sudo and without any manual repair**.
   - If a message says a Supabase Edge Runtime staging path *was moved aside, unchanged*: this is the
     H12 recovery. Copy the whole message (owner, mode, times, container state) to the sheet. Do not
     delete the kept directory now.
   - If `start` stops with *inaccessible or not writable* on `supabase/.temp` or `start-secrets`: FAIL;
     copy the message and the output of `namei -l ~/alpha-stab/portal/supabase/.temp/start-secrets`.
3. Sign in; check the S1/S2 timeline, debt, DEC-S1 and the Atlas note are unchanged.
4. Send one more update: `cd ~/code/stab-cart && idleproof portal sync` → it appears in Portal.
5. Repeat 1–4 a second time, this time after `scripts/alpha-local.sh stop` before rebooting.

## R. Result sheet

| Item | PASS / FAIL / PARTIAL / NOT RUN | Observed (ids, messages) |
|---|---|---|
| 0.2 existing Portal/IdleProof data present, schema and process ownership checked read-only, no destructive reset; previous tools recorded | | |
| 0.3 exact SHAs checked out, exactly one wheel and one tarball, digests | | |
| 1 doctor Python env line | | |
| S1.3 Stop accepted, certificate | | |
| S1.4 Native Proof bound to `dwchg_` | | |
| S1.5 explanation subject (#29) | | |
| S1.6 debt measured · delivered | | |
| S1.8 Portal one synthesis per change, Guided/Technical (#55), Not assessed (#48) | | |
| S1.9 DEC-S1 DECLARED | | |
| S1.10 persistence after reload | | |
| S2.2–4 refusal everywhere, no false acceptance | | |
| S2.5–6 recovery, history kept | | |
| S2.7 missing runner explained (optional) | | |
| C2 Atlas note persists, no paid call | | |
| C3 stop/start idempotent, no orphan | | |
| C4 reboot 1 (running) | | |
| C4 reboot 2 (stopped) | | |

Global verdict (operator): **HUMAN PASS** only if every non-optional row is PASS; otherwise PARTIAL or
FAIL with the rows concerned. Post the sheet on PaititeResearch/diffwitness#74.

## Rollback (non-destructive)

- **Local tools:** remove `~/alpha-stab/bin` from `PATH` (close the terminals); the previously installed
  `dw` / `idleproof` recorded in §0.1 are untouched. In the test project, `dw setup --agent codex` run with
  the previous `dw` re-points the hooks to it.
- **Portal:** `cd ~/alpha-stab/portal && scripts/alpha-local.sh stop`, then
  start the earlier Portal checkout only after verifying it is compatible with the retained
  database. The candidate adds no migrations, but this is an **application rollback, not
  a database restore**. No backup exists. Keep all historical SQL rows, decisions and receipts;
  any data loss must be reported as such; never run a reset/restore to conceal an error.
- **Moved-aside staging directories** (`…start-secrets/*.unwritable-*`) are kept for inspection; remove
  them later with the command the launcher printed, only once inspected.
