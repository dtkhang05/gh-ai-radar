# Builds the dbt documentation site (model/column descriptions, tests, lineage graph) as ONE self-contained HTML file,
# docs/dbt/index.html, so GitHub Pages can serve it next to the dashboard. Needs data/radar_dbt.duckdb (run run_pipeline.py first):
# `dbt docs generate` reads the table structure from the database, not the data itself.
# Usage: python -X utf8 scripts/build_dbt_docs.py
import os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DBT = ROOT / "dbt_radar"
env = dict(os.environ, DBT_SEND_ANONYMOUS_USAGE_STATS="False")
exe = Path(sys.executable).parent / ("dbt.exe" if os.name == "nt" else "dbt")
subprocess.run([str(exe), "docs", "generate", "--static", "--profiles-dir", ".", "--no-version-check"], cwd=DBT, env=env, check=True)
out = ROOT / "docs" / "dbt" / "index.html"
out.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(DBT / "target" / "static_index.html", out)
print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
