import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "audit_upstream_hol_gluing_theories.py"
SPEC = importlib.util.spec_from_file_location(
    "audit_upstream_hol_gluing_theories", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class UpstreamHolGluingTheoryAuditTests(unittest.TestCase):
    def populate(self, root: Path) -> dict[str, Path]:
        pairs = [(11, 17), (13, 19)]
        problem_list = root / "pbl"
        problem_list.write_text("11 17\n13 19\n", encoding="ascii")
        theories = root / "theories"
        theories.mkdir()
        buildheap = theories / "buildheap"
        buildheap.mkdir()
        for pair in pairs:
            name = MODULE.theory_name(pair)
            for suffix in MODULE.THEORY_SUFFIXES:
                path = theories / f"{name}{suffix}"
                content = (
                    MODULE.expected_script(pair)
                    if suffix == "Script.sml"
                    else "x\n"
                )
                path.write_text(content, encoding="utf-8")
            (buildheap / f"buildheap_{name}Script").write_text(
                f'Created theory "{name}"\n'
                f'Saved theorem _____ "{name}"\n'
                f'Exporting theory "{name}" ... done.\n'
                f'Theory "{name}" took 1.0s to build\n',
                encoding="utf-8",
            )
        build_log = root / "build.log"
        build_log.write_text(
            "RAMSEY55_GLUE358_MEMORY_MB 8000\n"
            "RAMSEY55_GLUE358_START 0 11 17\n"
            "RAMSEY55_GLUE358_DONE 0\n"
            "RAMSEY55_GLUE358_START 1 13 19\n"
            "RAMSEY55_GLUE358_DONE 1\n"
            "RAMSEY55_GLUE358_KERNEL_FULL_2_OK\n",
            encoding="utf-8",
        )
        load_log = root / "load.log"
        load_log.write_text(
            "RAMSEY55_GLUE358_LOAD 0 F C4524B C4524R NO_FALSE_HYP\n"
            "RAMSEY55_GLUE358_LOAD 1 F C4524B C4524R NO_FALSE_HYP\n"
            "RAMSEY55_GLUE358_KERNEL_LOAD_2_OK\n",
            encoding="utf-8",
        )
        build_time = root / "build.time"
        load_time = root / "load.time"
        build_time.write_text("Exit status: 0\n", encoding="utf-8")
        load_time.write_text("  Exit status: 0\n", encoding="utf-8")
        return {
            "problem_list": problem_list,
            "theory_directory": theories,
            "build_log": build_log,
            "build_time_log": build_time,
            "load_log": load_log,
            "load_time_log": load_time,
        }

    def audit(self, paths: dict[str, Path]) -> dict[str, object]:
        return MODULE.audit(label="GLUE358", expected_memory_mb=8000, **paths)

    def test_accepts_exact_theory_family(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            document = self.audit(self.populate(Path(raw)))
            self.assertTrue(document["verified"])
            self.assertEqual(document["summary"]["fresh_loaded_false_theorems"], 2)
            self.assertEqual(document["summary"]["build_memory_limit_mb"], 8000)

    def test_rejects_nonexact_script(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            script = next(paths["theory_directory"].glob("*Script.sml"))
            script.write_text("wrong\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "script is not exact"):
                self.audit(paths)

    def test_rejects_missing_theory_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            next(paths["theory_directory"].glob("*Theory.dat")).unlink()
            with self.assertRaisesRegex(ValueError, "missing or empty"):
                self.audit(paths)

    def test_rejects_buildheap_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            buildheap_log = next(
                (paths["theory_directory"] / "buildheap").iterdir()
            )
            buildheap_log.write_text(
                buildheap_log.read_text(encoding="utf-8") + "fallback\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "forbidden buildheap token"):
                self.audit(paths)

    def test_rejects_extra_theory_stem(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            (paths["theory_directory"] / "r45_23_29Theory.dat").write_text(
                "x\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "stem set mismatch"):
                self.audit(paths)

    def test_rejects_nonsequential_build_markers(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            paths["build_log"].write_text(
                "RAMSEY55_GLUE358_MEMORY_MB 8000\n"
                "RAMSEY55_GLUE358_START 0 11 17\n"
                "RAMSEY55_GLUE358_START 1 13 19\n"
                "RAMSEY55_GLUE358_DONE 0\n"
                "RAMSEY55_GLUE358_DONE 1\n"
                "RAMSEY55_GLUE358_KERNEL_FULL_2_OK\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "not sequential"):
                self.audit(paths)

    def test_rejects_wrong_memory_marker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            paths["build_log"].write_text(
                paths["build_log"].read_text(encoding="utf-8").replace(
                    "MEMORY_MB 8000", "MEMORY_MB 20000"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "memory marker"):
                self.audit(paths)

    def test_rejects_reordered_build_markers(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            paths["build_log"].write_text(
                paths["build_log"].read_text(encoding="utf-8")
                .replace("START 0 11 17", "START 0 13 19")
                .replace("START 1 13 19", "START 1 11 17"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "START markers"):
                self.audit(paths)

    def test_rejects_non_false_load_marker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            paths["load_log"].write_text(
                paths["load_log"].read_text(encoding="utf-8").replace(
                    "LOAD 1 F C4524B C4524R NO_FALSE_HYP", "LOAD 1 T"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "theorem-shape markers"):
                self.audit(paths)


if __name__ == "__main__":
    unittest.main()
