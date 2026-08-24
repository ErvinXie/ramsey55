from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).parents[1]
WATCHER = ROOT / "scripts/watch_cadical_dfs_forest_continuation_finalization.sh"
FINALIZER = ROOT / "tools/finalize_cadical_dfs_checkpoint.py"
AUDITOR = ROOT / "tools/audit_cadical_dfs_checkpoint_finalization.py"
SELECTOR = ROOT / "tools/select_cadical_dfs_race.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(
    shutil.which("flock") and Path("/usr/bin/time").is_file(),
    "forest watcher requires Linux flock and GNU time",
)
class WatchCadicalDfsForestContinuationFinalizationTests(unittest.TestCase):
    def test_selects_complete_forest_and_runs_independent_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repository"
            data_root = root / "data"
            directory = data_root / "build/run"
            tools = repository / "tools"
            checker = repository / ".tools/src/drat-trim/drat-trim"
            override_checker = repository / "long-checker"
            tools.mkdir(parents=True)
            checker.parent.mkdir(parents=True)
            directory.mkdir(parents=True)
            for source in (FINALIZER, AUDITOR, SELECTOR):
                shutil.copyfile(source, tools / source.name)
            checker.write_text(
                "#!/usr/bin/env python3\nraise SystemExit(1)\n", encoding="utf-8"
            )
            checker.chmod(0o755)
            override_checker.write_text(
                "#!/usr/bin/env python3\nprint('s VERIFIED')\n", encoding="utf-8"
            )
            override_checker.chmod(0o755)

            cnf = directory / "base.cnf"
            source = directory / "source.icnf"
            prefix_snapshot = directory / "prefix.tsv"
            frontier = directory / "frontier.icnf"
            replay = directory / "replay.json"
            prefix = directory / "prefix.drat"
            continuation = directory / "continuation.drat"
            continuation_snapshot = directory / "continuation.tsv"
            continuation_log = directory / "continuation.log"
            cnf.write_text("p cnf 2 1\n1 0\n", encoding="ascii")
            source.write_text("a 1 0\n", encoding="ascii")
            prefix_snapshot.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "0\t0\t0\t100\t0\t0\t2\t0.125\n",
                encoding="ascii",
            )
            frontier.write_text("a 1 2 0\na 1 -2 0\n", encoding="ascii")
            prefix.write_bytes(b"d\x02\0a\x02\0")
            replay.write_text(
                json.dumps(
                    {
                        "schema": "ramsey55.cadical-dfs-prefix-replay.v2",
                        "source_root": str(source),
                        "source_root_sha256": sha256(source),
                        "snapshot": str(prefix_snapshot),
                        "snapshot_sha256": sha256(prefix_snapshot),
                        "snapshot_rows": 1,
                        "processed_attempts": 1,
                        "processed_splits": 1,
                        "maximum_processed_depth": 0,
                        "source_root_count": 1,
                        "root_frontier_counts": [2],
                        "output": str(frontier),
                        "output_sha256": sha256(frontier),
                        "output_count": 2,
                        "proof_prefix": str(prefix),
                        "proof_prefix_sha256": sha256(prefix),
                    }
                ),
                encoding="utf-8",
            )
            continuation.write_bytes(b"d\x04\0a\x04\0")
            continuation_snapshot.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n"
                "0\t0\t0\t100\t20\t1\t0\t0.250\n"
                "1\t1\t0\t100\t20\t1\t0\t0.375\n",
                encoding="ascii",
            )
            continuation_log.write_text(
                "proof_fragment\t1\n"
                "root_index\tall\n"
                "status\t20\n"
                "cubes\t2\n"
                "attempts\t2\n"
                "splits\t0\n"
                "maximum_extra_depth\t0\n",
                encoding="ascii",
            )

            environment = os.environ.copy()
            environment.update(
                {
                    "RAMSEY55_POLL_SECONDS": "1",
                    "RAMSEY55_FINALIZER_LOCK": str(root / "finalizer.lock"),
                    "RAMSEY55_DRAT_CHECKER": str(override_checker),
                }
            )
            completed = subprocess.run(
                [
                    str(WATCHER),
                    str(repository),
                    str(data_root),
                    "build/run",
                    "forest",
                    str(cnf),
                    str(replay),
                    str(prefix),
                    str(frontier),
                    str(continuation),
                    str(continuation_snapshot),
                    str(continuation_log),
                ],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("RAMSEY55_FOREST_CONTINUATION_ACCEPTED", completed.stdout)
            audit = json.loads(
                (directory / "forest-final-v1.audit.log").read_text(encoding="utf-8")
            )
            self.assertTrue(audit["verified"])
            self.assertEqual(audit["forest_continuations"], 1)
            self.assertTrue(audit["checker_rerun"]["verified"])


if __name__ == "__main__":
    unittest.main()
