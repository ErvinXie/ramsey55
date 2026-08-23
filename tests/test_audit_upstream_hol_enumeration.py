import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "audit_upstream_hol_enumeration.py"
SPEC = importlib.util.spec_from_file_location("audit_upstream_hol_enumeration", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class UpstreamHolEnumerationAuditTests(unittest.TestCase):
    def populate(self, root: Path, theories: int = 2) -> None:
        for index in range(theories):
            base = f"ramseyEnum4412_{index}"
            (root / f"{base}Script.sml").write_text("script\n", encoding="utf-8")
            for suffix in MODULE.THEORY_SUFFIXES:
                (root / f"{base}{suffix}").write_text(
                    f"{base} {suffix}\n", encoding="utf-8"
                )

    def test_complete_family_is_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.populate(root)
            evidence = root / "build.log"
            evidence.write_text("success\n", encoding="utf-8")
            document = MODULE.audit(root, 2, [evidence])
            self.assertTrue(document["summary"]["complete"])
            self.assertEqual(document["summary"]["scripts"], 2)
            self.assertEqual(len(document["records"]), 2)
            self.assertEqual(
                document["records"][0]["artifacts"]["Theory.sml"]["bytes"],
                len("ramseyEnum4412_0 Theory.sml\n"),
            )
            self.assertEqual(document["evidence"][0]["path"], str(evidence.resolve()))

    def test_missing_theory_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.populate(root)
            (root / "ramseyEnum4412_1Theory.uo").unlink()
            with self.assertRaisesRegex(ValueError, "Theory.uo set mismatch"):
                MODULE.audit(root, 2)

    def test_extra_theory_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.populate(root)
            (root / "ramseyEnum4412_9Theory.sml").write_text(
                "unexpected\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "Theory.sml set mismatch"):
                MODULE.audit(root, 2)

    def test_empty_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.populate(root)
            (root / "ramseyEnum4412_1Theory.dat").write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "missing or empty artifact"):
                MODULE.audit(root, 2)


if __name__ == "__main__":
    unittest.main()
