# CI check: does the pipeline catch faults that we plant on purpose? For each scenario in make_synthetic.py it builds synthetic data,
# runs the real dbt project (`dbt build`, models + tests) into a throwaway DuckDB file, then asserts on the test statuses in
# run_results.json and on the model tables. A failed assertion exits 1, so CI turns red if a test or model stops catching a fault
# (or starts raising false alarms on clean data).
# Usage: python ci/check_scenarios.py        (run from the repo root; needs requirements.txt installed; ~1 min)
import json, os, subprocess, sys, tempfile
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_synthetic import SCENARIOS, START, END_EXCL, generate

ROOT = Path(__file__).resolve().parent.parent
DBT = ROOT / "dbt_radar"
os.environ["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "False"
failures = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


def run_dbt(work, scenario):
    data = generate(work / "data", scenario)
    os.environ["RADAR_DB"] = str(work / "radar.duckdb")
    vars_ = dict(parquet_glob=(data / "events.parquet").as_posix(), ai_universe_parquet=(data / "universe.parquet").as_posix(),
                 window_start=START, window_end=END_EXCL, dq_start=START, dq_end=END_EXCL, min_stars=20, retention_blocks=7, burn_in_blocks=2)
    # A subprocess, like run_pipeline.py: dbt keeps the DuckDB file open for the life of its process, so the tables could not be read here.
    cmd = [sys.executable, "-c", "from dbt.cli.main import cli; cli()", "build", "--quiet", "--no-version-check", "--project-dir", str(DBT),
           "--profiles-dir", str(DBT), "--target-path", str(work / "target"), "--log-path", str(work / "logs"), "--vars", json.dumps(vars_)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    results = json.loads((work / "target" / "run_results.json").read_text(encoding="utf-8"))["results"]
    status = {r["unique_id"].split(".")[2]: r["status"] for r in results}   # "test.radar.<name>.<hash>" / "model.radar.<name>"
    return proc.returncode == 0, status, str(work / "radar.duckdb")


def status_of(status, prefix):
    hits = [v for k, v in status.items() if k.startswith(prefix)]
    return hits[0] if hits else None


def q(db, sql):
    con = duckdb.connect(db, read_only=True)
    try:
        return con.sql(sql).fetchall()
    finally:
        con.close()


for scenario in SCENARIOS:
    print(f"\n== scenario: {scenario}")
    with tempfile.TemporaryDirectory() as tmp:
        ok, status, db = run_dbt(Path(tmp), scenario)
        counts = {s: sum(v == s for v in status.values()) for s in sorted(set(status.values()))}
        print("  dbt statuses:", counts)
        if scenario == "clean":
            check(ok, "dbt build succeeds on clean data")
            check(not {"fail", "error", "warn", "skipped"} & set(status.values()), "no failing, warning or skipped node on clean data")
            flags = dict(q(db, "select flag, count(*) from fct_hourly_quality group by 1"))
            check(not any(f in flags for f in ("low", "high", "missing")), f"no false alarm in the hourly quality flags {flags}")
            check(flags.get("ok", 0) > 0, "hourly quality has hours with a baseline")
            check(q(db, "select count(*) from fct_star_spike_days")[0][0] == 0, "no star spike on clean data")
            check(q(db, "select count(*) from fct_cohort_retention where still_active > 0")[0][0] > 0, "retention table has new contributors who came back")
        elif scenario == "faulty":
            check(not ok, "dbt build fails when an hour has no events")
            check(status_of(status, "assert_no_missing_hours") == "fail", "assert_no_missing_hours fails (planted missing hour)")
            check(status_of(status, "assert_no_anomalous_hours_in_trusted_window") == "warn", "anomalous-hours test warns (planted low hours)")
            flag = dict(q(db, "select hr::varchar, flag from fct_hourly_quality"))
            check(flag.get("2025-04-10 05:00:00") == "missing", "missing hour 04-10 05:00 is flagged 'missing'")
            check(flag.get("2025-04-09 01:00:00") == "low", "hour at 12% of normal (04-09 01:00) is flagged 'low'")
            after = [f for h, f in flag.items() if h >= "2025-04-15 16:00:00"]
            check(len(after) > 0 and all(f == "low" for f in after), f"every hour of the sustained 35% drop is 'low' ({len(after)} hours)")
            stray = [h for h, f in flag.items() if f in ("low", "high", "missing")
                     and not (h >= "2025-04-15 16:00:00" or h in ("2025-04-10 05:00:00", "2025-04-09 01:00:00"))]
            check(not stray, f"no flagged hour outside the planted ones ({len(stray)} stray)")
            spikes = q(db, "select repo, d::varchar from fct_star_spike_days")
            check(spikes == [("lab/viral", "2025-04-02")], f"the planted star burst is the only spike: {spikes}")
            check(status.get("fct_star_spike_days") == "success", "other models still build when the quality test fails")
        elif scenario == "bad_type":
            check(not ok, "dbt build fails on an unknown event type")
            check(status_of(status, "accepted_values_stg_events_type") == "fail", "accepted_values test on event type fails")
            check(status.get("fct_star_daily") in ("skipped", None), "models downstream of the failed test are skipped")

print()
if failures:
    print(f"{len(failures)} check(s) FAILED")
    sys.exit(1)
print("all scenario checks passed")
