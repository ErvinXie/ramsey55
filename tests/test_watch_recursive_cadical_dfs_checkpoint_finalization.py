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
WATCHER = ROOT / "scripts/watch_recursive_cadical_dfs_checkpoint_finalization.sh"
FINALIZER = ROOT / "tools/finalize_cadical_dfs_checkpoint.py"
AUDITOR = ROOT / "tools/audit_cadical_dfs_checkpoint_finalization.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(
    shutil.which("flock") and Path("/usr/bin/time").is_file(),
    "recursive watcher requires Linux flock and GNU time",
)
class WatchRecursiveCadicalDfsCheckpointFinalizationTests(unittest.TestCase):
    def test_waits_for_evidence_and_runs_independent_recursive_gate(self) -> None:
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
            shutil.copyfile(FINALIZER, tools / FINALIZER.name)
            shutil.copyfile(AUDITOR, tools / AUDITOR.name)
            checker.write_text(
                "#!/usr/bin/env python3\nraise SystemExit(1)\n",
                encoding="utf-8",
            )
            checker.chmod(0o755)
            override_checker.write_text(
                "#!/usr/bin/env python3\nprint('s VERIFIED')\n",
                encoding="utf-8",
            )
            override_checker.chmod(0o755)

            cnf = directory / "base.cnf"
            source_root = directory / "source.icnf"
            snapshot = directory / "snapshot.tsv"
            frontier = directory / "frontier.icnf"
            replay = directory / "replay.json"
            prefix = directory / "prefix.drat"
            child = directory / "child.drat"
            evidence = directory / "child.log"
            cnf.write_text("p cnf 1 1\n1 0\n", encoding="ascii")
            source_root.write_text("a 1 0\n", encoding="ascii")
            snapshot.write_text(
                "root\tattempt\tdepth\tlimit\tstatus\tcore\tsplit\tseconds\n",
                encoding="ascii",
            )
            frontier.write_bytes(source_root.read_bytes())
            prefix.write_bytes(b"d\x02\0a\x02\0")
            child.write_bytes(b"d\x04\0a\x04\0")
            evidence.write_text(
                "proof_fragment\t1\n"
                "root_index\tall\n"
                "status\t20\n"
                "cubes\t1\n"
                "attempts\t1\n"
                "splits\t0\n"
                "maximum_extra_depth\t0\n",
                encoding="ascii",
            )
            replay.write_text(
                json.dumps(
                    {
                        "schema": "ramsey55.cadical-dfs-prefix-replay.v2",
                        "source_root": str(source_root),
                        "source_root_sha256": sha256(source_root),
                        "snapshot": str(snapshot),
                        "snapshot_sha256": sha256(snapshot),
                        "snapshot_rows": 0,
                        "processed_attempts": 0,
                        "processed_splits": 0,
                        "maximum_processed_depth": 0,
                        "source_root_count": 1,
                        "root_frontier_counts": [1],
                        "output": str(frontier),
                        "output_sha256": sha256(frontier),
                        "output_count": 1,
                        "proof_prefix": str(prefix),
                        "proof_prefix_sha256": sha256(prefix),
                    }
                ),
                encoding="utf-8",
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
                    "parent",
                    str(cnf),
                    str(replay),
                    str(prefix),
                    str(child),
                    str(evidence),
                ],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("RAMSEY55_RECURSIVE_PREFIX_ACCEPTED", completed.stdout)
            audit = json.loads(
                (directory / "parent-final-v1.audit.log").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(audit["verified"])
            self.assertTrue(audit["replay_independently_verified"])
            self.assertTrue(audit["checker_rerun"]["verified"])


if __name__ == "__main__":
    unittest.main()
