"""The Python environment that evidence commands run with.

DiffWitness Core runs in its own interpreter, often a dedicated virtualenv. The project's tests need
the project's interpreter and dependencies. The two are resolved separately, in this order:

1. ``DIFFWITNESS_PYTHON_ENV`` in the environment, then ``python_env`` in ``.diffwitness.toml``: a
   virtualenv directory, relative to the repository root or absolute. ``"inherit"`` turns
   project-environment selection off and keeps the inherited ``PATH``.
2. A project-local virtualenv at the repository root: ``.venv/``, then ``venv/``.
3. ``VIRTUAL_ENV`` inherited from the caller, unless it is DiffWitness's own runtime.
4. Otherwise the inherited ``PATH`` is used unchanged.

The selected environment's executable directory goes first on ``PATH`` and ``VIRTUAL_ENV`` names
it, as an activated virtualenv would; nothing is installed or modified. The environment belongs
to the user's test toolchain, like ``node_modules/.bin``, which evidence already uses.

An editable install of the source repository in that environment would make the evidence import the
original source instead of the proof worktree's variant. Its source roots are therefore put first on
``PYTHONPATH`` at the same relative location inside the worktree, which takes precedence over both
``.pth`` path entries and editable import finders.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ENV_OVERRIDE = "DIFFWITNESS_PYTHON_ENV"
INHERIT = "inherit"
PROJECT_LOCAL_NAMES = (".venv", "venv")
_MAX_PTH_BYTES = 256 * 1024
_MAX_PTH_FILES = 512


class EvidenceEnvironmentError(ValueError):
    """The configured evidence environment cannot be used; evidence must not silently fall back."""


@dataclass(frozen=True, slots=True)
class PythonEnvironment:
    root: Path
    bin_dir: Path
    interpreter: Path
    source: str
    editable_roots: tuple[str, ...] = ()


def _layout(root: Path) -> tuple[Path, Path] | None:
    if not (root / "pyvenv.cfg").is_file():
        return None
    candidates = (
        [root / "Scripts" / "python.exe"] if os.name == "nt"
        else [root / "bin" / "python", root / "bin" / "python3"]
    )
    for interpreter in candidates:
        # A virtualenv interpreter is usually a symlink to its base interpreter; a broken link means
        # the environment cannot start.
        if interpreter.exists():
            return interpreter.parent, interpreter
    return None


def core_runtime_root() -> Path | None:
    """DiffWitness's own virtualenv, when Core runs from one."""
    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        return None
    return Path(sys.prefix).resolve()


def _same(a: Path, b: Path | None) -> bool:
    if b is None:
        return False
    try:
        return a.resolve() == b.resolve()
    except OSError:
        return False


def _configured(source_repo: Path) -> tuple[str, str] | None:
    override = os.environ.get(ENV_OVERRIDE)
    if override is not None and override.strip():
        return override.strip(), f"{ENV_OVERRIDE}"
    try:
        from .config import load_config

        value = load_config(source_repo, None).get("python_env")
    except (OSError, ValueError):
        # An unreadable configuration is reported by the command that loads it for its own settings.
        return None
    if isinstance(value, str) and value.strip():
        return value.strip(), "python_env"
    return None


def _site_packages(root: Path) -> list[Path]:
    if os.name == "nt":
        found = [root / "Lib" / "site-packages"]
    else:
        found = sorted((root / "lib").glob("python*/site-packages"))
    return [path for path in found if path.is_dir()]


_FINDER_MAPPING = re.compile(r"^MAPPING\s*(?::[^=]+)?=\s*(\{.*?\})\s*$", re.M | re.S)


def _finder_paths(site: Path, line: str) -> list[str]:
    # setuptools PEP 660 editable installs: `import __editable___<name>_finder; ...install()`.
    match = re.match(r"import\s+(__editable___[A-Za-z0-9_]+_finder)\b", line)
    if not match:
        return []
    module = site / f"{match.group(1)}.py"
    try:
        text = module.read_text(encoding="utf-8")[:_MAX_PTH_BYTES]
        mapping = _FINDER_MAPPING.search(text)
        values = ast.literal_eval(mapping.group(1)) if mapping else {}
    except (OSError, ValueError, SyntaxError):
        return []
    # Each value is a package directory or a module file; its parent is the import root.
    return [str(Path(value).parent) for value in values.values() if isinstance(value, str)] if isinstance(values, dict) else []


def editable_source_roots(environment_root: Path, source_repo: Path) -> tuple[str, ...]:
    """Import roots inside ``source_repo`` that the environment adds through editable installs."""
    repo = source_repo.resolve()
    roots: list[str] = []
    for site in _site_packages(environment_root):
        try:
            pth_files = sorted(site.glob("*.pth"))[:_MAX_PTH_FILES]
        except OSError:
            continue
        for pth in pth_files:
            try:
                lines = pth.read_text(encoding="utf-8", errors="replace")[:_MAX_PTH_BYTES].splitlines()
            except OSError:
                continue
            for raw in lines:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                entries = _finder_paths(site, line) if line.startswith("import") else [line]
                for entry in entries:
                    candidate = Path(entry)
                    if not candidate.is_absolute():
                        candidate = site / candidate
                    try:
                        relative = candidate.resolve().relative_to(repo)
                    except (OSError, ValueError):
                        continue
                    key = relative.as_posix() or "."
                    if key not in roots:
                        roots.append(key)
    return tuple(roots)


def _environment(root: Path, source: str, source_repo: Path) -> PythonEnvironment | None:
    layout = _layout(root)
    if layout is None:
        return None
    bin_dir, interpreter = layout
    return PythonEnvironment(
        root=root,
        bin_dir=bin_dir,
        interpreter=interpreter,
        source=source,
        editable_roots=editable_source_roots(root, source_repo),
    )


def resolve_python_environment(source_repo: Path) -> PythonEnvironment | None:
    """Select the project's Python environment for evidence, or None to keep the inherited PATH."""
    configured = _configured(source_repo)
    if configured is not None:
        value, origin = configured
        if value == INHERIT:
            return None
        root = Path(value).expanduser()
        if not root.is_absolute():
            root = source_repo / root
        selected = _environment(root, "configured", source_repo)
        if selected is None:
            raise EvidenceEnvironmentError(
                f"{origin} = {value!r} is not a usable Python virtualenv (expected pyvenv.cfg and its interpreter in {root}). "
                f"Fix it, or set it to {INHERIT!r} to use the inherited PATH."
            )
        return selected
    for name in PROJECT_LOCAL_NAMES:
        selected = _environment(source_repo / name, "project-local", source_repo)
        if selected is not None:
            return selected
    inherited = os.environ.get("VIRTUAL_ENV")
    if inherited:
        root = Path(inherited)
        if not _same(root, core_runtime_root()):
            return _environment(root, "inherited-virtualenv", source_repo)
    return None


def apply_python_environment(env: dict[str, str], environment: PythonEnvironment | None, *, cwd: Path | None) -> None:
    if environment is None:
        return
    env["PATH"] = str(environment.bin_dir) + os.pathsep + env.get("PATH", "")
    env["VIRTUAL_ENV"] = str(environment.root)
    env.pop("PYTHONHOME", None)
    env.pop("__PYVENV_LAUNCHER__", None)
    if environment.editable_roots and cwd is not None:
        roots = [str((cwd / relative) if relative != "." else cwd) for relative in environment.editable_roots]
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = os.pathsep.join([*roots, *([existing] if existing else [])])


def _tokens(command: str) -> list[str]:
    import shlex

    try:
        return shlex.split(command, posix=os.name != "nt")
    except ValueError:
        return []


_PYTHON_LAUNCHERS = {"python", "python3", "python.exe", "python3.exe", "py"}


def _is_python_launcher(token: str) -> bool:
    name = Path(token).name.lower()
    return name in _PYTHON_LAUNCHERS or re.fullmatch(r"python3\.\d+(?:\.exe)?", name) is not None


def runner_module(command: str) -> str | None:
    """The module a ``python -m <module>`` evidence command starts, if any."""
    tokens = _tokens(command)
    if not tokens or not _is_python_launcher(tokens[0]):
        return None
    for index, token in enumerate(tokens[1:-1], start=1):
        if token == "-m":
            return tokens[index + 1].split(".")[0]
    return None


def _interpreter_label(executable: str | None) -> str:
    if not executable:
        return "not found on the evidence PATH"
    core = core_runtime_root()
    if core is not None and _inside(Path(executable), core):
        return f"{executable} (DiffWitness's own runtime, not the project's environment)"
    return executable


def diagnose_unrunnable(command: str, results, *, env: dict[str, str]) -> str | None:
    """Explain an evidence run that never reached the project's tests, or None.

    It only recognises a test runner or command that could not start. It never changes the
    classification of the runs; it makes the reason explicit.
    """
    if not results:
        return None
    last = results[-1]
    output = f"{getattr(last, 'stdout_tail', '')}\n{getattr(last, 'stderr_tail', '')}"
    tokens = _tokens(command)
    if not tokens:
        return None
    executable = shutil.which(tokens[0], path=env.get("PATH")) if os.path.sep not in tokens[0] else tokens[0]
    module = runner_module(command)
    if module and re.search(rf"No module named '?{re.escape(module)}'?(?:\s|$)", output):
        return (
            f"cause: test-runner-unavailable (`{command}`: No module named {module})\n"
            f"interpreter: {_interpreter_label(executable)}\n"
            "This is an environment problem, not a failing assertion. Give the project a virtualenv with its test "
            "dependencies (.venv/ at the repository root is used automatically), or set [diffwitness] python_env; "
            "DiffWitness never installs packages."
        )
    missing = re.search(r"ModuleNotFoundError: No module named '([A-Za-z0-9_.]+)'", output)
    if missing:
        return (
            f"cause: missing-module ('{missing.group(1)}' is not importable by the evidence command)\n"
            f"interpreter: {_interpreter_label(executable)}\n"
            "Either the evidence environment lacks this dependency (an environment problem: DiffWitness never "
            "installs packages) or the change imports a module that does not exist."
        )
    not_found = getattr(last, "returncode", None) in {127, 9009} or re.search(
        r"(?:command not found|is not recognized as an internal or external command|No such file or directory)", output
    )
    if executable is None and not_found:
        cause = "test-runner-unavailable" if Path(tokens[0]).name in {"pytest", "py.test", "tox", "nox"} else "evidence-command-unavailable"
        return (
            f"cause: {cause} (`{tokens[0]}` not found on the evidence PATH)\n"
            "This is an environment problem, not a failing assertion. Install the command in the project's environment "
            "or set [diffwitness] python_env; DiffWitness never installs packages."
        )
    return None


def _module_installed(root: Path, module: str) -> bool | None:
    """Static check of a virtualenv's own site-packages; None when it cannot be known statically."""
    if module in getattr(sys, "stdlib_module_names", ()):
        return True
    try:
        if "include-system-site-packages = true" in (root / "pyvenv.cfg").read_text(encoding="utf-8", errors="replace").lower():
            return None
    except OSError:
        return None
    for site in _site_packages(root):
        if (site / module).is_dir() or (site / f"{module}.py").is_file() or any(site.glob(f"{module}.*.pyd")) or any(site.glob(f"{module}.*.so")):
            return True
    return False


def describe(source_repo: Path, command: str | None = None) -> dict[str, object]:
    """Doctor view of the evidence Python environment. Static: no project code runs."""
    try:
        selected = resolve_python_environment(source_repo)
    except EvidenceEnvironmentError as exc:
        return {"ready": False, "source": "configured", "problem": str(exc)}
    core = core_runtime_root()
    module = runner_module(command or "")
    if selected is None:
        tokens = _tokens(command or "")
        launcher = tokens[0] if tokens and _is_python_launcher(tokens[0]) else "python"
        python = shutil.which(launcher) or shutil.which("python3")
        own = bool(python and core and _inside(Path(python), core))
        state: dict[str, object] = {
            "source": "inherited-path",
            "interpreter": python,
            "coreRuntime": str(core) if core else None,
            "interpreterIsCoreRuntime": own,
            "runnerModule": module,
            # Core's own runtime is this process: it can be asked without running project code.
            "runnerAvailable": importlib.util.find_spec(module) is not None if own and module else None,
        }
    else:
        state = {
            "source": selected.source,
            "root": str(selected.root),
            "interpreter": str(selected.interpreter),
            "coreRuntime": str(core) if core else None,
            "interpreterIsCoreRuntime": _same(selected.root, core),
            "editableRoots": list(selected.editable_roots),
            "runnerModule": module,
            "runnerAvailable": _module_installed(selected.root, module) if module else None,
        }
    if state["runnerAvailable"] is False:
        where = "DiffWitness's own runtime" if state["interpreterIsCoreRuntime"] else f"the {state['source']} environment"
        state["problem"] = (
            f"`{command}` would run with {where} ({state['interpreter']}), where `{module}` is not installed. "
            "Give the project a virtualenv with its test dependencies (.venv/ is used automatically) or set "
            "[diffwitness] python_env; DiffWitness never installs packages."
        )
    state["ready"] = "problem" not in state
    return state


def _inside(path: Path, root: Path) -> bool:
    # Resolve the directory, not the file: a virtualenv's python is a symlink to its base interpreter.
    try:
        path.absolute().parent.resolve().relative_to(root)
        return True
    except (OSError, ValueError):
        return False
