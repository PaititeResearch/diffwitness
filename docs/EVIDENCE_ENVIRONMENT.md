# Evidence Python environment — issue #136

## Finding

HUMAN E2E-ALPHA-01 (WSL, Codex 0.162.0, Core `0.4.0a1`): Codex added `gift_wrap_fee_cents` and its tests, which passed 16/16 with the project's `.venv`. The native Stop ran the configured evidence `python -m pytest -q` with DiffWitness's own virtualenv interpreter, which has no pytest, and refused three times with `classification: stable-fail`, nothing more. A `PATH` prefix on the Stop hook alone made the same change pass (`dw2_510e50ee0bed56a15eaa`).

Reproduced deterministically with two independent virtualenvs (Core on Python 3.12 without pytest, project `.venv` on Python 3.13 with pytest) and Core's `bin/` first on `PATH`: the native Stop refused with `stable-fail` and no cause. The documented alpha install adds the whole Core virtualenv `bin/` (which holds `python`) to `PATH` in `~/.bashrc`; a hook shell that reads it puts Core's `python` first, whatever the shell that launched Codex exported. That this is what the operator's Codex did is consistent with the observation but not proven on that host.

A second, independent defect was found while reproducing: when the project is installed in editable mode (`pip install -e .`, src layout) in the environment the evidence uses, every proof worktree imported the original source repository instead of its own variant. The base then "passed" with the candidate's code and the Stop refused with a misleading `canonical Proof claim is 'preservation'`.

## Contract

Two interpreters are distinct and never substituted for each other:

- **Core runtime**: the interpreter running `dw`. It runs DiffWitness only.
- **Evidence environment**: the interpreter and dependencies of the user's project. Evidence and `prepare` commands run with it, inside each disposable proof worktree.

The evidence environment is selected in this order (`src/diffwitness/evidence_env.py`, applied by `runner.command_env`, the single place every evidence and preparation subprocess gets its environment):

1. `DIFFWITNESS_PYTHON_ENV`, then `[diffwitness] python_env` in `.diffwitness.toml`: a virtualenv directory, relative to the repository root or absolute. `"inherit"` turns selection off. A configured value that is not a virtualenv (`pyvenv.cfg` plus its interpreter) fails the Proof explicitly; it never falls back silently.
2. A project-local virtualenv: `.venv/`, then `venv/`.
3. `VIRTUAL_ENV` inherited from the caller, unless it is the Core runtime.
4. Otherwise the inherited `PATH`, unchanged (previous behaviour).

The selected environment's `bin/` (`Scripts\` on Windows) goes first on `PATH` and `VIRTUAL_ENV` names it, as an activated virtualenv would; `PYTHONHOME` is removed. `node_modules/.bin` keeps first place, as before. Nothing is installed or modified. Like `node_modules/.bin`, which evidence already used, the project's environment is part of the user's own test toolchain.

Editable installs of the source repository in that environment (`.pth` path entries and setuptools PEP 660 finder mappings) are read statically; their source roots inside the repository are put first on `PYTHONPATH` at the same relative path inside the proof worktree. `PYTHONPATH` precedes both `.pth` entries and editable import finders, so each variant imports its own code. Roots outside the repository are left alone.

## Diagnosis

The run classification is unchanged: a command that cannot start its test runner is still not green, and the stability, causality and budget rules are not touched. When the candidate is not green, the refusal gains one explicit line when the evidence never reached the project's tests:

- `cause: test-runner-unavailable` — `python -m <runner>` reported `No module named <runner>`, or the runner executable (`pytest`, `tox`, `nox`) was not found;
- `cause: evidence-command-unavailable` — the evidence executable was not found;
- `cause: missing-module` — a module imported by the tests is not importable (a missing dependency or a wrong import).

The line names the interpreter and says when it is DiffWitness's own runtime. IdleProof Local shows the cause as an environment problem, never as a failing assertion.

`dw doctor` reports the selected environment statically, without running project code: its source, root, mapped editable roots, and whether the runner module is installed (Core's own runtime is asked in-process; a project virtualenv's `site-packages` is inspected; a virtualenv that includes system site-packages is reported unknown). A runner known to be missing makes verification not ready.

## Install guidance

Do not put a whole virtualenv `bin/` on `PATH` to reach `dw`: it also exposes that virtualenv's `python` and `pip`. Link only the launcher, e.g. `ln -s ~/.local/share/diffwitness-venv/bin/dw ~/.local/bin/dw`, or use `pipx`.

## Qualification

- `tests/test_evidence_environment.py`: resolution order, explicit failure, Core runtime ignored, editable mapping (path and finder), diagnosis, doctor; and four end-to-end native Stops with real virtualenvs and another environment's `python` first on `PATH`: project `.venv` accepted (causal), no project environment refused with `cause: test-runner-unavailable`, editable src-layout accepted (causal, previously `preservation` refusal), configured external environment accepted and invalid one refused explicitly.
- The human WSL/Codex requalification with several virtualenvs remains to be run on the consolidated candidate; this document does not claim it.
