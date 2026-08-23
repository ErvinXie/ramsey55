import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "audit_upstream_hol_enumfinal.py"
SPEC = importlib.util.spec_from_file_location("audit_upstream_hol_enumfinal", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class UpstreamHolEnumfinalAuditTests(unittest.TestCase):
    def populate(self, root: Path) -> dict[str, Path]:
        upstream = root / "upstream"
        enump = upstream / "src/enump"
        enumf = upstream / "src/enumf"
        buildheap = enumf / "buildheap"
        enump.mkdir(parents=True)
        buildheap.mkdir(parents=True)
        records = [{"theory": f"ramseyEnumX{i}"} for i in range(1239)]
        enumeration_audit = root / "enumeration.json"
        enumeration_audit.write_text(
            json.dumps(
                {
                    "schema": MODULE.ENUMERATION_SCHEMA,
                    "directory": str(enump.resolve()),
                    "records": records,
                    "summary": {
                        "complete": True,
                        "scripts": 1239,
                        "complete_five_artifact_theories": 1239,
                    },
                }
            ),
            encoding="utf-8",
        )
        open_template = enumf / "open_template"
        open_template.write_text(
            "open " + " ".join(record["theory"] + "Theory" for record in records) + "\n",
            encoding="utf-8",
        )
        script_template = enumf / "ramseyEnumScript_template"
        script_template.write_text("open HolKernel\n", encoding="utf-8")
        (enumf / "ramseyEnumScript.sml").write_bytes(
            open_template.read_bytes() + script_template.read_bytes()
        )
        for suffix in MODULE.THEORY_SUFFIXES[1:]:
            (enumf / f"ramseyEnum{suffix}").write_text("x\n", encoding="utf-8")
        buildheap_lines = [
            'Created theory "ramseyEnum"',
            *(
                f'Saved theorem _____ "{name}"'
                for name, _, _, _, _ in MODULE.EXPECTED_THEOREMS
            ),
            'Exporting theory "ramseyEnum" ... done.',
            'Theory "ramseyEnum" took 1.0s to build',
        ]
        (buildheap / "buildheap_ramseyEnumScript").write_text(
            "\n".join(buildheap_lines) + "\n", encoding="utf-8"
        )
        build_log = root / "build.log"
        build_log.write_text("RAMSEY55_ENUMF_MEMORY_MB 50000\n", encoding="utf-8")
        load_lines = ["RAMSEY55_ENUMF_LOAD_MEMORY_MB 50000"]
        load_lines.extend(
            f"RAMSEY55_ENUMF_LOAD {name} {size} {bluen} {redn} "
            f"F EXACT_BASE_HYPOTHESES {'COVER' if has_cover else 'NO_COVER'} "
            "NO_FALSE_HYP"
            for name, size, bluen, redn, has_cover in MODULE.EXPECTED_THEOREMS
        )
        load_lines.append(
            f"RAMSEY55_ENUMF_KERNEL_LOAD_{len(MODULE.EXPECTED_THEOREMS)}_OK"
        )
        load_log = root / "load.log"
        load_log.write_text("\n".join(load_lines) + "\n", encoding="utf-8")
        build_time = root / "build.time"
        load_time = root / "load.time"
        build_time.write_text("Exit status: 0\n", encoding="utf-8")
        load_time.write_text("  Exit status: 0\n", encoding="utf-8")
        return {
            "enumeration_audit": enumeration_audit,
            "upstream_root": upstream,
            "build_log": build_log,
            "build_time_log": build_time,
            "load_log": load_log,
            "load_time_log": load_time,
            "expected_memory_mb": 50000,
        }

    def test_accepts_exact_fresh_loaded_final_theory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            document = MODULE.audit(**self.populate(Path(raw)))
            self.assertTrue(document["verified"])
            self.assertEqual(document["summary"]["enumeration_theories"], 1239)
            self.assertEqual(
                document["summary"]["fresh_loaded_exact_shape_theorems"], 25
            )

    def test_rejects_wrong_generated_concatenation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            generated = paths["upstream_root"] / "src/enumf/ramseyEnumScript.sml"
            generated.write_text("wrong\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exact template concatenation"):
                MODULE.audit(**paths)

    def test_rejects_missing_theory_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            (paths["upstream_root"] / "src/enumf/ramseyEnumTheory.dat").unlink()
            with self.assertRaisesRegex(ValueError, "missing or empty artifact"):
                MODULE.audit(**paths)

    def test_rejects_reordered_load_markers(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            load_log = paths["load_log"]
            text = load_log.read_text(encoding="utf-8")
            first = "RAMSEY55_ENUMF_LOAD R355 5 3 5"
            second = "RAMSEY55_ENUMF_LOAD R356 6 3 5"
            text = text.replace(first, "RAMSEY55_ENUMF_SWAP", 1)
            text = text.replace(second, first, 1)
            text = text.replace("RAMSEY55_ENUMF_SWAP", second, 1)
            load_log.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not exact and ordered"):
                MODULE.audit(**paths)

    def test_rejects_wrong_memory_marker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            paths["build_log"].write_text(
                "RAMSEY55_ENUMF_MEMORY_MB 8000\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "build memory marker"):
                MODULE.audit(**paths)

    def test_rejects_missing_saved_theorem_marker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            paths = self.populate(Path(raw))
            buildheap = (
                paths["upstream_root"]
                / "src/enumf/buildheap/buildheap_ramseyEnumScript"
            )
            buildheap.write_text(
                buildheap.read_text(encoding="utf-8").replace(
                    'Saved theorem _____ "R4418"\n', ""
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "R4418"):
                MODULE.audit(**paths)


if __name__ == "__main__":
    unittest.main()
