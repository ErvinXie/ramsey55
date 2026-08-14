from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.materialize_cnf_cube import materialize_cnf_cube, read_cube


class MaterializeCnfCubeTests(unittest.TestCase):
    def test_materializes_selected_cube_as_units(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            cnf = temporary / "tiny.cnf"
            cnf.write_text("c tiny\np cnf 3 1\n1 -2 0\n", encoding="ascii")
            cubes = temporary / "tiny.icnf"
            cubes.write_text("a 1 -3 0\na -1 2 0\n", encoding="ascii")
            cube = read_cube(cubes, 1)
            output = temporary / "augmented.cnf"
            shape = materialize_cnf_cube(cnf, cube, output)
            self.assertEqual(cube, (-1, 2))
            self.assertEqual(shape, (3, 3))
            self.assertEqual(
                output.read_text(encoding="ascii"),
                "c tiny\np cnf 3 3\n1 -2 0\n-1 0\n2 0\n",
            )

    def test_rejects_out_of_range_literal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            cnf = temporary / "tiny.cnf"
            cnf.write_text("p cnf 2 1\n1 0\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "outside"):
                materialize_cnf_cube(cnf, (3,), temporary / "bad.cnf")


if __name__ == "__main__":
    unittest.main()
