# Synthetic GH Archive-like events for the CI check (ci/check_scenarios.py): 7 weeks of hourly data, ~400 events/hour with a daily
# and weekly pattern, 40 "AI" repos plus a "viral" repo, no real data. Scenarios plant known faults so the checks can prove the
# data-quality layer and dbt tests catch them:
#   clean    : nothing planted.
#   faulty   : one hour at 12% of normal (04-09 01:00), one hour with no events (04-10 05:00), a sustained 35% drop from 04-15 16:00,
#              and a star burst of 400 one-event accounts on the viral repo on 04-02.
#   bad_type : one event with a type dbt does not know (an accepted_values test must fail and block downstream models).
#   long_drop: a 35% drop from 03-15 that lasts 5 weeks to the end of the data, longer than the rolling baseline's 4 weeks of memory
#              (checked with dq_fixed_weeks=2 so the reference window is 03-01..03-14).
# Usage: python ci/make_synthetic.py <out_dir> <clean|faulty|bad_type>   (writes <out_dir>/events.parquet and universe.parquet)
import duckdb, sys
from pathlib import Path

START, END_EXCL = "2025-03-01", "2025-04-19"   # 49 days = 7 blocks of 7 days
SCENARIOS = ("clean", "faulty", "bad_type", "long_drop")


def generate(out_dir, scenario):
    assert scenario in SCENARIOS, scenario
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("set threads=1")        # one thread + setseed => the same rows on every run
    con.execute("select setseed(0.42)")
    faulty = scenario == "faulty"
    con.execute(f"""create table hours as
      select ts h, round(400 * (0.6 + 0.4 * sin(pi() * hour(ts) / 24)) * (case when dayofweek(ts) in (0, 6) then 0.8 else 1 end)
                         * (0.97 + 0.06 * random())) n
      from (select unnest(generate_series(timestamp '{START}', timestamp '{END_EXCL}' - interval 1 hour, interval 1 hour)) ts)""")
    if faulty:
        con.execute("""update hours set n = round(n * 0.12) where h = timestamp '2025-04-09 01:00';
                       update hours set n = 0 where h = timestamp '2025-04-10 05:00';
                       update hours set n = round(n * 0.65) where h >= timestamp '2025-04-15 16:00' and h <> timestamp '2025-04-10 05:00'""")
    if scenario == "long_drop":
        con.execute("update hours set n = round(n * 0.65) where h >= timestamp '2025-03-15'")
    con.execute("""create table base as
      select h + to_seconds(floor(random() * 3600)::bigint) ts, r,
             -- the user pool grows by 60 a day, so new contributors keep appearing after the burn-in blocks (retention needs them)
             'user' || (1 + floor(random() * (300 + 60 * datediff('day', timestamp '2025-03-01', h)))::int) actor,
             case when random() < 0.8 then 'lab/ai-' || (1 + floor(random() * 40)::int) else 'org/other-' || (1 + floor(random() * 300)::int) end repo
      from (select h, random() r, unnest(range(n::bigint)) k from hours)""")
    con.execute("""create table typed as
      select ts, actor, repo,
             case when r < .60 then 'PushEvent' when r < .70 then 'WatchEvent' when r < .75 then 'IssuesEvent'
                  when r < .83 then 'IssueCommentEvent' when r < .91 then 'PullRequestEvent' when r < .96 then 'CreateEvent' else 'ForkEvent' end as type
      from base""")
    con.execute(f"""insert into typed   -- viral repo: 10 stars every day, so a later burst counts as a spike and not as a launch
      select d + to_seconds(floor(random() * 86400)::bigint), 'user' || (1 + floor(random() * 3000)::int), 'lab/viral', 'WatchEvent'
      from (select unnest(generate_series(date '{START}', date '{END_EXCL}' - interval 1 day, interval 1 day))::timestamp d), range(10)""")
    if faulty:
        con.execute("""insert into typed
          select timestamp '2025-04-02' + to_seconds(floor(random() * 86400)::bigint), 'burst-' || k, 'lab/viral', 'WatchEvent'
          from range(400) t(k)""")
    if scenario == "bad_type":
        con.execute("insert into typed values (timestamp '2025-03-20 10:00', 'user1', 'lab/ai-1', 'WeirdEvent')")
    con.execute(f"""copy (select (row_number() over (order by ts, actor, repo) + 1000000)::bigint id, type, ts, actor, repo from typed order by ts)
                    to '{(out / 'events.parquet').as_posix()}' (format parquet)""")
    con.execute(f"""copy (select repo, true by_name, false by_topic, false by_desc
                          from (select 'lab/ai-' || i repo from range(1, 41) t(i) union all select 'lab/viral'))
                    to '{(out / 'universe.parquet').as_posix()}' (format parquet)""")
    return out


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    print("wrote", generate(sys.argv[1], sys.argv[2]))
