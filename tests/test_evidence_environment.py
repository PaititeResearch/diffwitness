"""Issue #136: evidence commands use the project's Python environment, never Core's by accident."""

from __future__ import annotations

import os
import subprocess
import sys
import sysconfig
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from diffwitness import evidence_env
from diffwitness.evidence_env import (
    EvidenceEnvironmentError,
    apply_python_environment,
    diagnose_unrunnable,
    editable_source_roots,
    resolve_python_environment,
    runner_module,
)
from diffwitness.gitops import git_metadata_path
from diffwitness.ide_handoff import finalize_ide_session
from diffwitness.ide_plugin import session_start
from diffwitness.models import CommandResult
from diffwitness.runner import command_env

BIN = "Scripts" if os.name == "nt" else "bin"
PYTHON = "python.exe" if os.name == "nt" else "python"


def _fake_venv(root: Path) -> Path:
    """A directory with the virtualenv layout; enough for resolution, not for running code."""
    (root / BIN).mkdir(parents=True)
    (root / "pyvenv.cfg").write_text("home = /usr/bin\n", encoding="utf-8")
    (root / BIN / PYTHON).write_text("", encoding="utf-8")
    return root


def _real_venv(root: Path) -> Path:
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(root)], check=True)
    return root


def _site(root: Path) -> Path:
    path = Path(sysconfig.get_path("purelib", scheme="venv", vars={"base": str(root), "platbase": str(root)}))
    path.mkdir(parents=True, exist_ok=True)
    return path


# The project's own test runner, installed only in the project's environment. Without it, the
# evidence command fails exactly like `python -m pytest` in an interpreter without pytest.
RUNNER = textwrap.dedent(
    """
    import sys, unittest
    suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
    sys.exit(0 if unittest.TextTestRunner(verbosity=0).run(suite).wasSuccessful() else 1)
    """
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.DEVNULL)


def _project(root: Path, *, package: bool = False) -> Path:
    repo = root / "project"
    (repo / "tests").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "env@example.test")
    _git(repo, "config", "user.name", "Env Test")
    source = repo / "src" / "shop" if package else repo
    source.mkdir(parents=True, exist_ok=True)
    if package:
        (source / "__init__.py").write_text("", encoding="utf-8")
    (source / "cart.py").write_text("def apply_discount(total):\n    return total * 0.9 if total >= 100 else total\n", encoding="utf-8")
    module = "shop.cart" if package else "cart"
    (repo / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "tests" / "test_cart.py").write_text(
        f"import unittest\nfrom {module} import apply_discount\n\n"
        "class Small(unittest.TestCase):\n    def test_small_order(self):\n        self.assertEqual(apply_discount(50), 50)\n",
        encoding="utf-8",
    )
    (repo / ".diffwitness.toml").write_text('[diffwitness]\ntest = "python -m projrunner"\n', encoding="utf-8")
    (repo / ".gitignore").write_text(".venv/\n__pycache__/\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    return repo


def _change(repo: Path, *, package: bool = False) -> None:
    source = repo / "src" / "shop" / "cart.py" if package else repo / "cart.py"
    source.write_text(
        source.read_text(encoding="utf-8") + "\n\ndef gift_wrap_fee_cents(item_count):\n    return min(item_count * 150, 600)\n",
        encoding="utf-8",
    )
    module = "shop.cart" if package else "cart"
    (repo / "tests" / "test_gift.py").write_text(
        f"import unittest\nfrom {module} import gift_wrap_fee_cents\n\n"
        "class Gift(unittest.TestCase):\n    def test_fee(self):\n        self.assertEqual(gift_wrap_fee_cents(2), 300)\n"
        "        self.assertEqual(gift_wrap_fee_cents(9), 600)\n",
        encoding="utf-8",
    )


def _install_runner(venv: Path) -> None:
    (_site(venv) / "projrunner.py").write_text(RUNNER, encoding="utf-8")


class ResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        patcher = mock.patch.dict(os.environ, {}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in (evidence_env.ENV_OVERRIDE, "VIRTUAL_ENV"):
            os.environ.pop(name, None)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_no_environment_keeps_the_inherited_path(self) -> None:
        self.assertIsNone(resolve_python_environment(self.repo))

    def test_dot_venv_is_preferred_to_venv_and_to_an_inherited_virtualenv(self) -> None:
        _fake_venv(self.repo / "venv")
        os.environ["VIRTUAL_ENV"] = str(_fake_venv(self.root / "elsewhere"))
        self.assertEqual(resolve_python_environment(self.repo).root, self.repo / "venv")
        _fake_venv(self.repo / ".venv")
        selected = resolve_python_environment(self.repo)
        self.assertEqual((selected.root, selected.source), (self.repo / ".venv", "project-local"))

    def test_a_directory_without_the_virtualenv_layout_is_not_an_environment(self) -> None:
        (self.repo / ".venv" / BIN).mkdir(parents=True)
        self.assertIsNone(resolve_python_environment(self.repo))

    def test_configuration_and_override_take_precedence_and_inherit_turns_selection_off(self) -> None:
        _fake_venv(self.repo / ".venv")
        configured = _fake_venv(self.root / "envs" / "project")
        (self.repo / ".diffwitness.toml").write_text(f'[diffwitness]\npython_env = "{configured.as_posix()}"\n', encoding="utf-8")
        self.assertEqual(resolve_python_environment(self.repo).root, configured)
        override = _fake_venv(self.root / "override")
        os.environ[evidence_env.ENV_OVERRIDE] = str(override)
        self.assertEqual(resolve_python_environment(self.repo).root, override)
        os.environ[evidence_env.ENV_OVERRIDE] = "inherit"
        self.assertIsNone(resolve_python_environment(self.repo))

    def test_a_relative_configured_environment_is_resolved_from_the_repository(self) -> None:
        _fake_venv(self.repo / "envs" / "test")
        (self.repo / ".diffwitness.toml").write_text('[diffwitness]\npython_env = "envs/test"\n', encoding="utf-8")
        self.assertEqual(resolve_python_environment(self.repo).source, "configured")

    def test_an_unusable_configured_environment_fails_explicitly_instead_of_falling_back(self) -> None:
        _fake_venv(self.repo / ".venv")
        (self.repo / ".diffwitness.toml").write_text('[diffwitness]\npython_env = "missing-env"\n', encoding="utf-8")
        with self.assertRaisesRegex(EvidenceEnvironmentError, "not a usable Python virtualenv"):
            resolve_python_environment(self.repo)
        with self.assertRaisesRegex(EvidenceEnvironmentError, "not a usable"):
            command_env(self.repo)

    def test_empty_or_non_string_python_env_is_rejected_by_the_config_contract(self) -> None:
        from diffwitness.config import load_config

        for value in ('""', "3"):
            (self.repo / ".diffwitness.toml").write_text(f"[diffwitness]\npython_env = {value}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(self.repo, None)

    def test_an_inherited_virtualenv_that_is_core_runtime_is_ignored(self) -> None:
        core = _fake_venv(self.root / "diffwitness-venv")
        os.environ["VIRTUAL_ENV"] = str(core)
        with mock.patch.object(evidence_env, "core_runtime_root", return_value=core.resolve()):
            self.assertIsNone(resolve_python_environment(self.repo))
        other = _fake_venv(self.root / "project-env")
        os.environ["VIRTUAL_ENV"] = str(other)
        with mock.patch.object(evidence_env, "core_runtime_root", return_value=core.resolve()):
            self.assertEqual(resolve_python_environment(self.repo).source, "inherited-virtualenv")

    def test_editable_installs_of_the_source_repository_are_mapped_and_others_ignored(self) -> None:
        venv = _fake_venv(self.repo / ".venv")
        site = _site(venv)
        (self.repo / "src" / "pkg").mkdir(parents=True)
        (self.repo / "lib").mkdir()
        (site / "__editable__.pkg-1.0.pth").write_text(f"{self.repo / 'src'}\n", encoding="utf-8")
        (site / "other.pth").write_text(f"# comment\n{self.root}\n../../../../lib\n", encoding="utf-8")
        (site / "__editable__.flat-1.0.pth").write_text("import __editable___flat_1_0_finder; __editable___flat_1_0_finder.install()\n", encoding="utf-8")
        (site / "__editable___flat_1_0_finder.py").write_text(
            f"MAPPING: dict[str, str] = {{'flat': {str(self.repo / 'flat')!r}, 'mod': {str(self.repo / 'tools' / 'mod.py')!r}}}\nNAMESPACES = {{}}\n",
            encoding="utf-8",
        )
        roots = editable_source_roots(venv, self.repo)
        self.assertIn("src", roots)
        self.assertIn(".", roots)
        self.assertIn("tools", roots)
        self.assertNotIn("..", roots)
        self.assertTrue(all(not Path(root).is_absolute() for root in roots))

    def test_apply_activates_the_environment_and_maps_editable_roots_into_the_worktree(self) -> None:
        venv = _fake_venv(self.repo / ".venv")
        selected = evidence_env.PythonEnvironment(venv, venv / BIN, venv / BIN / PYTHON, "project-local", ("src", "."))
        env = {"PATH": "/core/bin", "PYTHONHOME": "/core", "PYTHONPATH": "/kept"}
        worktree = self.root / "worktree"
        apply_python_environment(env, selected, cwd=worktree)
        self.assertEqual(env["PATH"].split(os.pathsep)[0], str(venv / BIN))
        self.assertEqual(env["VIRTUAL_ENV"], str(venv))
        self.assertNotIn("PYTHONHOME", env)
        self.assertEqual(env["PYTHONPATH"].split(os.pathsep), [str(worktree / "src"), str(worktree), "/kept"])

    def test_node_modules_bin_keeps_first_place_on_path(self) -> None:
        _fake_venv(self.repo / ".venv")
        (self.repo / "node_modules" / ".bin").mkdir(parents=True)
        parts = command_env(self.repo, cwd=self.repo)["PATH"].split(os.pathsep)
        self.assertEqual(parts[:2], [str(self.repo / "node_modules" / ".bin"), str(self.repo / ".venv" / BIN)])


class DiagnosisTests(unittest.TestCase):
    def _run(self, *, stderr: str = "", stdout: str = "", returncode: int = 1) -> list[CommandResult]:
        return [CommandResult(returncode=returncode, duration_s=0.1, stdout_tail=stdout, stderr_tail=stderr)]

    def test_runner_module(self) -> None:
        self.assertEqual(runner_module("python -m pytest -q"), "pytest")
        self.assertEqual(runner_module("python3.12 -X dev -m unittest discover"), "unittest")
        self.assertIsNone(runner_module("pytest -q"))
        self.assertIsNone(runner_module("npm test"))

    def test_missing_runner_is_an_environment_cause_not_an_assertion_failure(self) -> None:
        env = {"PATH": os.path.dirname(sys.executable)}
        message = diagnose_unrunnable("python -m pytest -q", self._run(stderr="/x/bin/python: No module named pytest\n"), env=env)
        self.assertIn("cause: test-runner-unavailable", message)
        self.assertIn("not a failing assertion", message)
        self.assertIn("never installs packages", message)
        missing = diagnose_unrunnable("python -m pytest", self._run(stdout="E   ModuleNotFoundError: No module named 'requests'\n"), env=env)
        self.assertIn("cause: missing-module ('requests'", missing)
        absent = diagnose_unrunnable("pytest -q", self._run(stderr="sh: 1: pytest: not found", returncode=127), env={"PATH": ""})
        self.assertIn("cause: test-runner-unavailable (`pytest` not found", absent)
        other = diagnose_unrunnable("make check", self._run(stderr="make: command not found", returncode=127), env={"PATH": ""})
        self.assertIn("cause: evidence-command-unavailable", other)

    def test_ordinary_failures_get_no_environment_cause(self) -> None:
        env = {"PATH": os.path.dirname(sys.executable)}
        for output in ("FAILED tests/test_cart.py::test_fee - assert 0 == 300", "No module named pytest_plugin_x", ""):
            self.assertIsNone(diagnose_unrunnable("python -m pytest -q", self._run(stdout=output), env=env), output)


class DoctorDescriptionTests(unittest.TestCase):
    """`dw doctor` reports the evidence interpreter statically, before any Proof runs."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        patcher = mock.patch.dict(os.environ, {}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in (evidence_env.ENV_OVERRIDE, "VIRTUAL_ENV"):
            os.environ.pop(name, None)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_project_environment_with_and_without_its_runner(self) -> None:
        venv = _fake_venv(self.repo / ".venv")
        missing = evidence_env.describe(self.repo, "python -m pytest -q")
        self.assertFalse(missing["ready"])
        self.assertIn("`pytest` is not installed", missing["problem"])
        (_site(venv) / "pytest").mkdir()
        self.assertTrue(evidence_env.describe(self.repo, "python -m pytest -q")["ready"])
        self.assertTrue(evidence_env.describe(self.repo, "python -m unittest discover")["ready"])
        (venv / "pyvenv.cfg").write_text("include-system-site-packages = true\n", encoding="utf-8")
        self.assertIsNone(evidence_env.describe(self.repo, "python -m surely_missing_runner")["runnerAvailable"])

    def test_core_runtime_first_on_path_without_the_runner_is_reported(self) -> None:
        core = Path(sys.executable).parent.parent
        os.environ["PATH"] = os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", "")
        with mock.patch.object(evidence_env, "core_runtime_root", return_value=core.resolve()):
            state = evidence_env.describe(self.repo, "python -m surely_missing_runner_136")
        self.assertTrue(state["interpreterIsCoreRuntime"])
        self.assertFalse(state["ready"])
        self.assertIn("DiffWitness's own runtime", state["problem"])

    def test_readiness_is_not_ready_when_the_runner_is_missing(self) -> None:
        from diffwitness.readiness import verification_readiness

        _fake_venv(self.repo / ".venv")
        readiness = verification_readiness(self.repo, {"test": "python -m pytest -q"})
        self.assertFalse(readiness["ready"])
        self.assertEqual(readiness["pythonEnvironment"]["source"], "project-local")
        self.assertIn("pytest", readiness["reason"])


class NativeStopEndToEndTests(unittest.TestCase):
    """Real virtualenvs, the real native Stop and a PATH whose `python` is another environment."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # The interpreter first on PATH lacks the project's runner, like DiffWitness's own venv in #136.
        self.foreign = _real_venv(self.root / "foreign-env")
        patcher = mock.patch.dict(os.environ, {"PATH": str(self.foreign / BIN) + os.pathsep + os.environ.get("PATH", "")})
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in (evidence_env.ENV_OVERRIDE, "VIRTUAL_ENV", "PYTHONPATH"):
            os.environ.pop(name, None)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _stop(self, repo: Path, *, package: bool = False) -> dict:
        session = f"evidence-env-{len(list(self.root.iterdir()))}"
        payload = {"cwd": str(repo), "session_id": session, "source": "startup", "provider": "codex"}
        session_start(payload)
        _change(repo, package=package)
        return finalize_ide_session(payload)

    def _envelope_claim(self, repo: Path) -> str:
        import json

        return json.loads(git_metadata_path(repo, "diffwitness/change-envelope.json").read_text(encoding="utf-8"))["proof"]["claim"]

    def test_project_dot_venv_is_used_even_when_another_python_is_first_on_path(self) -> None:
        repo = _project(self.root)
        _install_runner(_real_venv(repo / ".venv"))
        result = self._stop(repo)
        self.assertNotIn("decision", result, result)
        self.assertIn("Proof accepted", result["systemMessage"])
        self.assertEqual(self._envelope_claim(repo), "causal")

    def test_without_a_project_environment_the_refusal_names_the_missing_runner(self) -> None:
        repo = _project(self.root)
        result = self._stop(repo)
        self.assertEqual(result.get("decision"), "block", result)
        self.assertIn("classification: stable-fail", result["reason"])
        self.assertIn("cause: test-runner-unavailable (`python -m projrunner`: No module named projrunner)", result["reason"])

    def test_an_editable_install_tests_the_worktree_variant_not_the_original_source(self) -> None:
        repo = _project(self.root, package=True)
        venv = _real_venv(repo / ".venv")
        _install_runner(venv)
        # What `pip install -e .` leaves for a src layout: the source repository on sys.path.
        (_site(venv) / "__editable__.shop-0.1.pth").write_text(f"{repo / 'src'}\n", encoding="utf-8")
        result = self._stop(repo, package=True)
        # Importing the original source made the base pass too: a misleading `preservation` refusal.
        self.assertNotIn("decision", result, result)
        self.assertEqual(self._envelope_claim(repo), "causal")

    def test_a_configured_environment_outside_the_repository_and_an_invalid_one(self) -> None:
        repo = _project(self.root)
        env = _real_venv(self.root / "envs" / "shop")
        _install_runner(env)
        config = repo / ".diffwitness.toml"
        config.write_text(config.read_text(encoding="utf-8") + f'python_env = "{env.as_posix()}"\n', encoding="utf-8")
        _git(repo, "commit", "-qam", "configure the evidence environment")
        result = self._stop(repo)
        self.assertIn("Proof accepted", result.get("systemMessage", ""), result)

        broken = _project(self.root / "second")
        config = broken / ".diffwitness.toml"
        config.write_text(config.read_text(encoding="utf-8") + 'python_env = "no-such-env"\n', encoding="utf-8")
        _git(broken, "commit", "-qam", "configure a missing environment")
        refused = self._stop(broken)
        self.assertEqual(refused.get("decision"), "block", refused)
        self.assertIn("not a usable Python virtualenv", refused["reason"])


if __name__ == "__main__":
    unittest.main()
