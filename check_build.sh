#!/usr/bin/env bash
# Is the committed geometry what build_body_36mm.py actually produces?
#
#   ./check_build.sh          -> IN SYNC / OUT OF SYNC, and it diffs the hashes
#
# The STLs are committed so the repo holds printable files, but they are
# generated: change a parameter, forget to rebuild, commit, and the repo ships
# a model that contradicts its own script.  The meshes are byte-reproducible
# across rebuilds, so build_summary.json carries each STL's sha256 and this
# compares a fresh build against it.
set -uo pipefail
cd "$(dirname "$0")"

python3 - <<'PY'
import json
d = json.load(open("build_summary.json"))
with open("/tmp/body36_committed.txt", "w") as fh:
    for k, v in d["stl_sha256"].items():
        fh.write("%s  %s\n" % (v, k))
PY

cp build_summary.json /tmp/body36_summary_backup.json
./build.sh >/tmp/body36_build.out 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "BUILD FAILED (exit $rc) - see /tmp/body36_build.out"
  exit "$rc"
fi

python3 - <<'PY'
import json
old = json.load(open("/tmp/body36_summary_backup.json"))
new = json.load(open("build_summary.json"))
a, b = old["stl_sha256"], new["stl_sha256"]
name = {"body36.stl": "body", "body36_gauge.stl": "gauge",
        "body36_cord_anchor.stl": "cord anchor"}
bad = []
for k in sorted(a):
    same = a.get(k) == b.get(k)
    print("%-14s committed %s  rebuilt %s  %s"
          % (name.get(k, k), a[k][:16], (b.get(k) or "-")[:16],
             "same" if same else "DIFFERENT"))
    if not same:
        bad.append(k)
print()
if bad:
    print("OUT OF SYNC: %s" % ", ".join(bad))
    print("Rebuild and commit the STLs, or throw the edit away with "
          "`git checkout -- .` (the STLs come back too, being tracked).")
    raise SystemExit(1)
print("IN SYNC: the committed STLs are exactly what the script produces.")
PY