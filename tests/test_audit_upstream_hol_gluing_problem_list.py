import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "audit_upstream_hol_gluing_problem_list.py"
SPEC = importlib.util.spec_from_file_location(
    "audit_upstream_hol_gluing_problem_list", SCRIPT
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class UpstreamHolGluingProblemListAuditTests(unittest.TestCase):
    def populate(self, root: Path) -> tuple[Path, Path]:
        covers = root / "covers"
        covers.mkdir()
        (covers / "gen358").write_text(
            "11 witness\n13 witness\n", encoding="ascii"
        )
        (covers / "gen4416").write_text("17 witness\n19 witness\n", encoding="ascii")
        problem_list = root / "problems"
        problem_list.write_text(
            "11 17\n11 19\n13 17\n13 19\n", encoding="ascii"
        )
        return covers, problem_list

    def test_accepts_exact_ordered_product(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            covers, problem_list = self.populate(Path(raw))
            document = MODULE.audit(problem_list, covers, 8)
            self.assertTrue(document["verified"])
            self.assertEqual(document["summary"]["pairs"], 4)
            self.assertEqual(document["summary"]["unique_pairs"], 4)

    def test_rejects_missing_pair(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            covers, problem_list = self.populate(Path(raw))
            problem_list.write_text("11 17\n11 19\n13 17\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "not the exact ordered"):
                MODULE.audit(problem_list, covers, 8)

    def test_rejects_reordered_pair(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            covers, problem_list = self.populate(Path(raw))
            problem_list.write_text(
                "11 19\n11 17\n13 17\n13 19\n", encoding="ascii"
            )
            with self.assertRaisesRegex(ValueError, "first mismatch at 0"):
                MODULE.audit(problem_list, covers, 8)

    def test_rejects_duplicate_cover_code(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            covers, problem_list = self.populate(Path(raw))
            (covers / "gen358").write_text("11 a\n11 b\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "nonempty and unique"):
                MODULE.audit(problem_list, covers, 8)


if __name__ == "__main__":
    unittest.main()
