# Phase 8: build a self-contained static dashboard (docs/index.html) from the dbt tables and the account-age samples.
# No server, no extra packages: the page embeds its data and draws SVG charts itself, so it can be served by GitHub Pages.
# The repo flagged by the star-spike analysis is shown as "Repo X" unless --show-names is passed: naming a real
# project on a public page is a decision for the author, and the evidence is a small sample (see PLAN.md, Phase 7).
# Usage: python -I -X utf8 scripts/build_dashboard.py [--show-names]
import duckdb, json, os, statistics, sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "radar_dbt.duckdb")
DERIVED = os.path.join(ROOT, "data", "derived")
OUT = os.path.join(ROOT, "docs", "index.html")
SHOW_NAMES = "--show-names" in sys.argv
CUTOFF = "2025-05-23 16:00"             # first hour of the sudden drop: data from here on is not trusted
XTICKS = ["2025-03-01", "2025-03-15", "2025-04-01", "2025-04-15", "2025-05-01", "2025-05-15"]

con = duckdb.connect(DB, read_only=True)
def q(sql): return con.sql(sql).fetchall()
def iso(ts): return ts.strftime("%Y-%m-%d %H:%M")

# ---- chart 1: hourly quality -------------------------------------------------------------------
hourly = [dict(hr=iso(r[0]), events=r[1], base=r[2], ratio=r[3], flag=r[4], pre_cut_flag=(r[4] in ("low", "high") and iso(r[0]) < CUTOFF))
          for r in q("select hr, events, base_events, events_ratio, flag from fct_hourly_quality order by hr")]
daily = [dict(d=str(r[0]), events=r[1], low_hours=r[2]) for r in q(
    "select hr::date, sum(events), count(*) filter (flag = 'low') from fct_hourly_quality group by 1 order by 1")]
# drop size: same weekdays (Mon-Sat) one week before vs after the break, average events per hour
def avg_events(a, b): return q(f"select avg(events) from fct_hourly_quality where hr >= '{a}' and hr < date '{b}' + 1")[0][0]
before, after = avg_events("2025-05-12", "2025-05-17"), avg_events("2025-05-26", "2025-05-31")
drop_pct = (1 - after / before) * 100

# ---- chart 2: star spikes ------------------------------------------------------------------------
sp = q("select repo, d, stars, baseline, x_baseline from fct_star_spike_days order by d")
# A day is flagged only where the share of "thin" stargazers jumped >= 0.30 above the repo's normal days on a day with >= 100 stars
# (same rule as PLAN.md Phase 7). That share is not a dbt column, so it comes from star_anomalies.py's output for the main config.
flagged = {(r[0], str(r[1])) for r in con.sql(
    f"select repo, d from read_parquet('{DERIVED.replace(chr(92), '/')}/star_spikes.parquet') where n >= 100 and jump >= 0.30").fetchall()}
# Any repo with a flagged day is shown as "Repo X" unless --show-names: nothing in the code names a specific project.
flagged_repos = {repo for repo, _ in flagged}
def label(repo): return repo if (SHOW_NAMES or repo not in flagged_repos) else "Repo X"
points = [dict(label=label(r[0]), d=str(r[1]), stars=r[2], base=float(r[3]), x=float(r[4]), suspect=((r[0], str(r[1])) in flagged)) for r in sp]
top = max(sp, key=lambda r: r[2])
short = lambda s: s if len(s) <= 24 else s[:23] + "…"

# ---- chart 3: account age samples ----------------------------------------------------------------
def load(name): return [json.loads(l) for l in open(os.path.join(DERIVED, name), encoding="utf-8")]
def summarize(rows, text, accent=False):
    ok = [r for r in rows if r["status"] == 200]
    return dict(label=text, accent=accent, asked=len(rows), ok_n=len(ok), new_n=sum(r["age_days"] < 30 for r in ok),
                pct_new=100 * sum(r["age_days"] < 30 for r in ok) / len(ok), median_age=statistics.median(r["age_days"] for r in ok),
                pct_zero_repos=100 * sum(r["public_repos"] == 0 for r in ok) / len(ok))
flagged_sample = load("account_sample_flagged_repo.jsonl")  # written by check_account_age.py for the flagged repo
name_x = ", ".join(sorted(flagged_repos)) if SHOW_NAMES else "Repo X"
accounts = [
    summarize([r for r in flagged_sample if r["grp"] == "spike"], f"{name_x} · ngày đột biến 14–15/04", True),
    summarize([r for r in flagged_sample if r["grp"] == "normal"], f"{name_x} · ngày thường"),
    summarize(load("account_sample_github__github-mcp-server.jsonl"), "github-mcp-server · ra mắt 07–08/04"),
    summarize(load("account_sample_x1xhlol__system-prompts-and-models-of-ai-tools.jsonl"), "system-prompts… · lan truyền 19–22/04"),
]

# ---- chart 4: pooled retention ---------------------------------------------------------------------
retention = [dict(k=r[0], people=int(r[1]), all=float(r[2]), code=float(r[3]), issue=float(r[4])) for r in q("""
    select weeks_later, sum(cohort_size), 100.0 * sum(still_active) / sum(cohort_size),
           100.0 * sum(still_active) filter (first_is_code) / sum(cohort_size) filter (first_is_code),
           100.0 * sum(still_active) filter (not first_is_code) / sum(cohort_size) filter (not first_is_code)
    from fct_cohort_retention group by 1 order by 1""")]

# ---- header numbers ----------------------------------------------------------------------------------
n_hours = len(hourly)
n_low = sum(h["flag"] == "low" for h in hourly)
n_low_pre = sum(h["pre_cut_flag"] for h in hourly)
n_repos = q("select count(*) from int_ai_repo_candidates")[0][0]
n_people = q("select count(distinct actor) from fct_contributor_week")[0][0]
fmt = lambda n: f"{n:,}".replace(",", ".")

data = dict(
    meta=dict(window_text="01/03 → 22/05/2025 (UTC)",
              footer=f"Tạo bởi scripts/build_dashboard.py từ các bảng dbt lúc {datetime.now():%d/%m/%Y %H:%M}. "
                     "Mã nguồn, cách chạy và giới hạn đầy đủ nằm trong README.md và PLAN.md. Dự án học tập, không liên quan GitHub Inc."),
    hero=dict(drop_pct=drop_pct, text=(
        f"Số sự kiện GitHub mỗi giờ giảm khoảng {drop_pct:.0f}% từ 23/05/2025 và không hồi lại "
        "(so 12–17/05 với 26–31/05, cùng các thứ trong tuần). Nhiều khả năng nguồn dữ liệu mất sự kiện; nguyên nhân chưa được xác nhận.")),
    tiles=[
        dict(label="Giờ được kiểm tra", value=fmt(n_hours), note="01/03 → 31/05/2025"),
        dict(label="Giờ bị gắn cờ low", value=fmt(n_low), note=f"{n_low_pre} trước mốc sụt, còn lại sau 23/05"),
        dict(label="Repo khớp từ khóa AI", value=fmt(n_repos), note="≥10 star; độ phủ chỉ ~25% (19/76)"),
        dict(label="Người đóng góp", value=fmt(n_people), note="không tính bot, 11 tuần"),
    ],
    limits=[
        "Chỉ có 12 tuần dữ liệu đáng tin (01/03 → 22/05/2025); 2023–2024 chưa được tải.",
        "Tập repo \"AI\" chỉ là tập con theo từ khóa trong tên: độ chính xác ~95% (mẫu 40 repo xem bằng mắt), độ phủ 25% (19/76 repo nổi tiếng chọn tay). Mọi kết quả chỉ đúng cho nhóm này.",
        "Star đột biến là tín hiệu nghi ngờ, không phải bằng chứng star mua. Mẫu tuổi tài khoản nhỏ (21–24 người mỗi nhóm, 3 repo) và không cho biết ai đứng sau.",
        "Giữ chân: không có dữ liệu trước 01/03 nên các cohort đầu có thể cao hơn thực tế; chưa có mốc so sánh bên ngoài.",
        "Các ngưỡng do tác giả chọn; chỉ ngưỡng star được thử độ nhạy (9 bộ). Đường cơ sở trượt 4 tuần chỉ gắn cờ một đợt sụt kéo dài trong vài tuần đầu.",
    ],
    hourly=hourly, hourly_cutoff=CUTOFF, xticks=XTICKS, daily=daily,
    spikes=dict(points=points, x0="2025-03-01", x1="2025-05-22", suspect_label=name_x,
                top_label=f"{short(top[0].split('/')[1])} ({fmt(top[2])})"),
    xticks2=XTICKS, accounts=accounts, retention=retention,
)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_template.html"), encoding="utf-8") as f:
    html = f.read()
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
assert "/*DATA*/" in html
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html.replace("/*DATA*/", payload))
print(f"wrote {OUT} ({os.path.getsize(OUT)/1e3:.0f} KB); hero drop {drop_pct:.1f}%; names shown: {SHOW_NAMES}")
print("tiles:", n_hours, n_low, n_low_pre, n_repos, n_people, "| spikes:", len(points), "| flagged days:", sorted(d for _, d in flagged), "| accounts:", [(a['label'], round(a['pct_new'], 1)) for a in accounts])
