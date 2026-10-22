# Analysis on the 2023-2024 sample (data/parquet_sample, 3 Wednesdays a month): stars per sampled day for the AI-repo universe.
# The universe (data/derived/ai_repo_universe.parquet) is defined from 2025 stars and 2026 GitHub metadata, so it only contains repos that
# still existed and had >= 100 stars in 03-05/2025: repos that died before 2025 are invisible (survivorship bias).
# Usage: RADAR_FLAGGED_REPO=<owner/name> python -I -X utf8 scripts/sample_waves.py
# RADAR_UNIVERSE_MODE=sample: use data/derived/ai_repo_universe_sample.parquet instead (built from the sample's own >= 30-star pool, see
# ai_repos_classify_sample.py) and merge renamed repos: every event repo is mapped to its current name (canon) before aggregating.
import os
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "data", "parquet_sample", "*.parquet").replace(os.sep, "/")
SAMPLE_MODE = os.environ.get("RADAR_UNIVERSE_MODE") == "sample"
UNIVERSE = os.path.join(ROOT, "data", "derived", "ai_repo_universe_sample.parquet" if SAMPLE_MODE else "ai_repo_universe.parquet").replace(os.sep, "/")
OUT = os.path.join(ROOT, "data", "derived", "sample_repo_quarters" + ("_canon" if SAMPLE_MODE else "") + ".parquet").replace(os.sep, "/")

con = duckdb.connect()
con.execute("set memory_limit='4GB'; set threads=4")
if SAMPLE_MODE:
    # canon = current name; old and new names of one repo are summed into one row per day.
    con.execute(f"create view m as select repo, coalesce(canon, repo) canon, is_ai, by_name, by_topic from read_parquet('{UNIVERSE}')")
    con.execute("create view u as select distinct canon repo from m where is_ai")
    con.execute("create view core_src as select distinct canon repo from m where is_ai and (by_name or by_topic)")
else:
    con.execute(f"create view u as select repo from read_parquet('{UNIVERSE}') where is_ai")
    con.execute(f"create view core_src as select repo from read_parquet('{UNIVERSE}') where is_ai and (by_name or by_topic)")
# Stars only (WatchEvent), humans only; one row per repo-day. A stargazer counted once per name; sample mode can double count
# an actor who starred under both names on one day (negligible: needs two stars of one repo in one day).
src = "coalesce(m.canon, w.repo)" if SAMPLE_MODE else "w.repo"
join = "left join m on m.repo = w.repo" if SAMPLE_MODE else ""
con.execute(f"""create table s as
  select {src} repo, w.ts::date d, count(*) stars, count(distinct w.actor) stargazers
  from read_parquet('{SAMPLE}') w {join} where w.type = 'WatchEvent' and w.actor not like '%[bot]' group by 1, 2""")
con.execute("create table days as select d, strftime(d, '%Y') || '-Q' || quarter(d) q, strftime(d, '%Y-%m') m from (select distinct d from s)")
print("sample days", con.sql("select count(*) from days").fetchone()[0], "universe", con.sql("select count(*) from u").fetchone()[0])

print("\nper month: stars per sampled day, all repos vs AI universe (ai_pct = % of all stars)")
for r in con.sql("""select dd.m, round(sum(s.stars) / count(distinct s.d)) all_per_day,
                           round(sum(s.stars) filter (where s.repo in (select repo from u)) / count(distinct s.d)) ai_per_day,
                           round(100.0 * sum(s.stars) filter (where s.repo in (select repo from u)) / sum(s.stars), 2) ai_pct
                    from s join days dd using (d) group by 1 order by 1""").fetchall():
    print("  ", r)

con.execute("""create table rq as
  select s.repo, dd.q, sum(s.stars) / (select count(*) from days d2 where d2.q = dd.q) stars_per_day
  from s join days dd using (d) where s.repo in (select repo from u) group by 1, 2""")
con.execute(f"copy rq to '{OUT}' (format parquet)")

flagged = os.environ.get("RADAR_FLAGGED_REPO", "")
print("\ntop 5 AI repos per quarter by stars per sampled day (flagged repo masked):")
for q, in con.sql("select distinct q from rq order by 1").fetchall():
    rows = con.execute("select case when repo = ? then 'Repo X' else repo end, round(stars_per_day) from rq where q = ? order by stars_per_day desc limit 5", [flagged, q]).fetchall()
    print("  ", q, rows)

# Fading: peak quarter in 2023 with >= 50 stars/day, vs average of the last two quarters of 2024.
print("\nfading: repos with peak quarter in 2023 (>= 50 stars/day) -> 2024-Q3/Q4 average, ratio")
con.execute("""create table pk as
  select repo, arg_max(q, stars_per_day) pq, max(stars_per_day) peak from rq where q like '2023%' group by 1 having max(stars_per_day) >= 50""")
con.execute("""create table fade as
  select pk.repo, pk.pq, round(pk.peak) peak, round(coalesce((select sum(stars_per_day) / 2 from rq where rq.repo = pk.repo and rq.q in ('2024-Q3', '2024-Q4')), 0)) late
  from pk""")
print("   repos", con.sql("select count(*) from fade").fetchone()[0],
      "| late < 50% of peak:", con.sql("select count(*) from fade where late < 0.5 * peak").fetchone()[0],
      "| late < 20% of peak:", con.sql("select count(*) from fade where late < 0.2 * peak").fetchone()[0])
for r in con.execute("select case when repo = ? then 'Repo X' else repo end, pq, peak, late from fade order by peak desc limit 12", [flagged]).fetchall():
    print("  ", r)

# Rename check: GitHub events carry the repo name at event time, and the universe uses the 2025 name. A repo that moved owner shows up as
# "fading" under the old name. Rough detector: another repo with the SAME name (part after '/') but a different owner has >= 20% of the
# old repo's peak stars/day in 2024-Q3/Q4. It also fires on forks/clones with the same name, so it is a flag to review, not a proof.
con.execute("""create table late_all as
  select repo, sum(stars_per_day) / 2 late from (
    select s.repo, dd.q, sum(s.stars) / (select count(*) from days d2 where d2.q = dd.q) stars_per_day
    from s join days dd using (d) where dd.q in ('2024-Q3', '2024-Q4') group by 1, 2) group by 1""")
con.execute("""create table fade_ren as
  select f.*, (select count(*) from late_all l where split_part(l.repo, '/', 2) = split_part(f.repo, '/', 2) and l.repo <> f.repo and l.late >= 0.2 * f.peak) possible_rename
  from fade f""")
print("\nfading repos with a possible rename (same repo name, other owner, >= 20% of peak late):",
      con.sql("select count(*) filter (where possible_rename > 0), count(*) from fade_ren").fetchone())
print("fading after dropping possible renames: late < 50% of peak:",
      con.sql("select count(*) from fade_ren where possible_rename = 0 and late < 0.5 * peak").fetchone()[0],
      "| < 20%:", con.sql("select count(*) from fade_ren where possible_rename = 0 and late < 0.2 * peak").fetchone()[0],
      "| of", con.sql("select count(*) from fade_ren where possible_rename = 0").fetchone()[0])

# Sensitivity: repeat the quarterly share and the fading count without the repos matched ONLY by description (676 repos, ~70% correct in a
# hand-checked sample of 50, see PLAN.md), i.e. keep repos matched by name or topic.
con.execute("create view core as select repo from core_src")
print("\nsensitivity: quarterly stars/day of the AI set (all humans-only stars in the sample = denominator)")
print("   quarter, all, full set, core (name/topic), core share of all % , full share %")
for r in con.sql("""select dd.q, round(sum(s.stars) / count(distinct s.d)) a,
                           round(sum(s.stars) filter (where s.repo in (select repo from u)) / count(distinct s.d)) f,
                           round(sum(s.stars) filter (where s.repo in (select repo from core)) / count(distinct s.d)) c,
                           round(100.0 * sum(s.stars) filter (where s.repo in (select repo from core)) / sum(s.stars), 2) cp,
                           round(100.0 * sum(s.stars) filter (where s.repo in (select repo from u)) / sum(s.stars), 2) fp
                    from s join days dd using (d) group by 1 order by 1""").fetchall():
    print("  ", r)
con.execute("""create table fade_core as
  select * from fade where repo in (select repo from core)""")
print("fading, core only: repos", con.sql("select count(*) from fade_core").fetchone()[0],
      "| late < 50% of peak:", con.sql("select count(*) from fade_core where late < 0.5 * peak").fetchone()[0],
      "| late < 20% of peak:", con.sql("select count(*) from fade_core where late < 0.2 * peak").fetchone()[0])
