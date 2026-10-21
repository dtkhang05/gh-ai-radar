# Radar hệ sinh thái AI mã nguồn mở

Pipeline dữ liệu trên [GH Archive](https://www.gharchive.org/) (mọi sự kiện công khai của GitHub, mỗi giờ một file): thu thập → kiểm tra chất lượng → dbt + DuckDB → phân tích hệ sinh thái AI mã nguồn mở.

- Dự án học tập; kết quả mang tính khám phá, giới hạn nêu ở từng phần.
- Xem: [dashboard](https://dtkhang05.github.io/gh-ai-radar/) · [tài liệu dbt](https://dtkhang05.github.io/gh-ai-radar/dbt/) · [bài viết](docs/bai-viet.md) · [PLAN.md](PLAN.md) (nhật ký và số đo từng bước)

## Kết quả chính

- **Nguồn mất sự kiện, lớp kiểm tra tự phát hiện được.** Từ ~17h UTC ngày 23/05/2025, số sự kiện mỗi giờ giảm ~35% và không hồi lại. Phân tích chỉ dùng dữ liệu đến 22/05/2025. Lớp kiểm tra cũng bắt được một file giờ chỉ có 12% sự kiện thường lệ (08/05/2025 01:00 UTC).
- **Star đột biến: phần lớn là người thật.** 4.033 repo AI có 1.513 ngày đột biến ở 526 repo; nhìn chung không nhiều tài khoản "mỏng" hơn ngày thường. Hai repo cùng một tổ chức bị gắn cờ ở 9/9 bộ ngưỡng (ngày 11–15/04/2025) và được kiểm chứng thêm bằng tuổi tài khoản.
- **Người đóng góp mới ít khi ở lại.** 16,7% còn hoạt động sau 1 tuần, 7,2% sau 8 tuần; người bắt đầu bằng code giữ lại tốt hơn nhiều.
- **Mẫu 2023–2024 (bản đầu).** Phần star thuộc repo AI tăng từ 3,5–4,3% (01–03/2023) lên 7,7–9,2% (cuối 2024), tùy có tính nhóm chỉ khớp qua mô tả hay không; top repo mỗi quý đổi theo từng làn sóng; 86–89% repo có đỉnh ≥50 star/ngày mẫu ở 2023 còn dưới nửa đỉnh sau 1,5 năm. Thiên lệch người sống sót nên không phải tỉ lệ repo AI chết.
- **Repo AI xác định bằng tên, topic và mô tả.** Độ phủ 82% và 89% trên hai danh sách chọn tay (chỉ theo tên: 25% và 20%), chỉ cho repo ≥100 star. Xem [Giới hạn](#giới-hạn).

## Cách hệ thống hoạt động

| Lớp | Thành phần | Việc làm |
|---|---|---|
| Thu thập | `scripts/ingest.py` | Tải từng giờ, giữ 5 cột, ghi Parquet, **xóa file thô ngay**; ghi `data/manifest.jsonl`; chạy lại được |
| Lưu trữ | Parquet (zstd 9) + DuckDB | Một bản dữ liệu (~2,7 MB/giờ); DuckDB đọc bằng view. Bảng sao chép nặng gấp 3,6 lần nên đã bỏ |
| Xác định repo AI | `top_repos_by_stars.py`, `fetch_repo_metadata.py`, `ai_repos_classify.py` | 20.000 repo nhiều star → topic và mô tả qua GitHub GraphQL (100 repo/lần) → phân loại theo tên, topic, mô tả |
| Mô hình | `dbt_radar/` (dbt-core 1.12, dbt-duckdb 1.11) | staging → intermediate → marts: `fct_star_daily`, `fct_star_spike_days`, `fct_contributor_week`, `fct_cohort_retention`, `fct_hourly_quality` |
| Chất lượng | `fct_hourly_quality` + 28 test | So mỗi giờ với trung vị cùng thứ, cùng giờ của 4 tuần trước (đường trượt) và của 4 tuần đầu (đường cố định); test bắt giờ thiếu, giờ bất thường, id trùng, giá trị lạ |
| Kiểm thử tự động | `ci/`, `.github/workflows/ci.yml` | Chạy dbt trên dữ liệu tổng hợp có lỗi cài sẵn; đỏ nếu test không bắt được lỗi hoặc báo nhầm trên dữ liệu sạch |
| Điều phối | `scripts/run_pipeline.py` | Kiểm tra trước → (tùy chọn) tải → `dbt build` → tóm tắt; dừng ngay khi lỗi, ghi log |
| Trình bày | `docs/index.html` | HTML tĩnh tự chứa, dựng từ bảng dbt bằng `scripts/build_dashboard.py` |

- Mọi script DuckDB giới hạn bộ nhớ và file tạm (sau một truy vấn thăm dò từng chiếm 12 GB RAM và 16 GB file tạm).

## Dữ liệu và độ tin cậy của nguồn

- GH Archive: mỗi giờ một file `https://data.gharchive.org/YYYY-MM-DD-H.json.gz` (giờ UTC, H không có số 0 đầu).
- Nguồn có hiện tượng mất sự kiện. Đo ngày 20/10/2026 trên giờ 12:00 UTC của một ngày mỗi tháng (`scripts/compare_hours.py`; mỗi số chỉ là **một giờ mẫu**, chưa phải cả tháng):

| Giờ | Tổng sự kiện | Star | Fork | Push |
|---|---|---|---|---|
| 2024-10-19 12h | 235.653 | 8.027 | 2.269 | 169.807 |
| 2025-06-19 12h | 172.056 | 5.075 | 1.316 | 110.447 |
| 2025-10-19 12h | 152.793 | 3.336 | 804 | 121.807 |
| 2026-04-19 12h | 156.528 | 3.148 | 621 | 119.300 |
| 2026-05-19 12h | 147.393 | 284 | 51 | 124.068 |
| 2026-06-19 12h | 158.838 | 160 | 33 | 136.595 |
| 2026-07-19 12h | 167.845 | 59 | 9 | 160.925 |
| 2026-08-19 12h | 26.242 | 141 | 37 | 23.794 |
| 2026-09-01 12h | 1.387 | 120 | 25 | 0 |
| 2026-09-19 12h | 120.276 | 146 | 46 | 103.814 |
| 2026-10-01 12h | 92.323 | 356 | 56 | 70.908 |
| 2026-10-10 12h | 40.599 | 346 | 87 | 30.564 |
| 2026-10-19 12h | 46.849 | 274 | 43 | 34.389 |

- Star giảm dần từ giữa 2025 và còn rất ít từ 05/2026; từ 08/2026 tổng sự kiện cũng thất thường (ví dụ `anthropics/claude-code` chỉ 8 star cả ngày 19/10/2026).
- Cộng đồng đã báo lỗi ([gharchive #320](https://github.com/igrigorik/gharchive.org/issues/320), [discussion #178788](https://github.com/orgs/community/discussions/178788)); chưa có xác nhận chính thức, và chưa kiểm tra điểm sụt 23/05/2025 có cùng nguyên nhân không.
- **Đã tải:** 03, 04, 05/2025 đủ giờ (744 + 720 + 744 file, không lỗi) và 960/1.416 giờ của 01–02/2025 (dừng vì mạng chậm). Phân tích dùng 01/03 → 22/05/2025 (12 tuần). Thêm mẫu 2023–2024: 72 ngày thứ Tư (3 ngày mỗi tháng), 1.728 giờ, 4,0 GB, đã kiểm tra chất lượng (1 giờ nguồn lỗi: 14/08/2024 23:00 chỉ có 489 sự kiện), có bản phân tích đầu (xem [Giới hạn](#giới-hạn) và `docs/bai-viet.md`).
- **Chi phí:** ~100 MB nén mỗi giờ → 2.208 giờ là ~230 GB tải qua mạng (không lưu) và ~6 GB Parquet giữ lại. Ngoại suy 29 tháng: ~57 GB Parquet, **chưa đo**.

## Kết quả chi tiết

### Star đột biến có phải người thật không?

Dữ liệu: 01/03 → 22/05/2025, 4.033 repo AI ≥100 star.

- **Định nghĩa:** ≥50 star và ≥5 lần trung vị 14 ngày trước; repo phải có star ở ≥7 trong 14 ngày đó (không thì ngày ra mắt bị tính nhầm).
- **Kết quả:** 1.513 ngày ở 526 repo (626–2.772 ngày tùy 9 bộ ngưỡng).
- **Tài khoản "mỏng"** (≤3 sự kiện trong 12 tuần): ngày đột biến 6,3–7,6% so với ngày thường 7,4–9,0% (9 bộ ngưỡng) → đa số đột biến đến từ ra mắt hoặc chia sẻ rộng.
- **Repo X và Repo X2** (cùng tổ chức): gắn cờ ở 9/9 bộ ngưỡng, cùng các ngày 11, 12, 14, 15/04/2025; 85–93% mỏng so với ~30% ngày thường.
- **Repo Y:** gắn cờ ở 6/9 bộ ngưỡng, một ngày (25/04/2025: 95% mỏng so với 60% ngày thường, 124 star).
- **Kiểm chứng độc lập bằng tuổi tài khoản** (GitHub API, mẫu 21–25 tài khoản mỗi nhóm):

| Nhóm | Tuổi trung vị | Tạo <30 ngày | Chưa có repo |
|---|---|---|---|
| Repo X, 14–15/04/2025 | 0 ngày | 20/21 | 19/21 |
| Repo X2, 14–15/04/2025 | 0 ngày | 22/24 | 21/24 |
| Repo Y, 25/04/2025 | 419 ngày | 2/25 | 2/25 |
| Repo X, ngày thường | 442 ngày | 0/23 | 1/23 |
| github-mcp-server, ra mắt 07–08/04 (đối chứng) | 3.820 ngày | 0/22 | 1/22 |
| system-prompts…, 19–22/04 (đối chứng) | 2.050 ngày | 2/24 | 2/24 |

- **Đọc kết quả:**
  - Repo X và X2: star ngày đó phần lớn từ tài khoản tạo ngay trong ngày, chưa có repo; khác hẳn hai đợt lan truyền thật.
  - Repo Y: tài khoản lâu năm, nên tuổi tài khoản không xác nhận dấu hiệu "mỏng" (tỉ lệ mỏng ngày thường của nó vốn 60%).
  - **Không** cho biết ai đứng sau (chủ repo, bên bán star hay người ngoài) nên không gán lỗi cho ai.
- **Tên repo bị ẩn** trong tài liệu, mã và dashboard vì bằng chứng chỉ là mẫu nhỏ về dự án thật.
  - Chạy lại: đặt `RADAR_FLAGGED_REPO=owner/repo` (tên nằm trong `data/derived/star_spikes.parquet` sau `star_anomalies.py`).
  - Hiện tên trên dashboard: thêm `--show-names` khi chạy `build_dashboard.py`.

### Người đóng góp mới có ở lại không?

- 143.991 người (push, PR, issue, bình luận, review; loại bot), 11 khối 7 ngày từ 01/03/2025.
- "Người mới" = lần đầu xuất hiện từ khối 3; hai khối đầu chỉ để nhận ra người cũ.

| Sau | Còn hoạt động | Lần đầu là code (push/PR) | Lần đầu chỉ issue/bình luận/review |
|---|---|---|---|
| 1 tuần | 16,7% | 29,0% | 14,3% |
| 2 tuần | 10,2% | 20,0% | 8,3% |
| 4 tuần | 7,9% | 16,5% | 6,2% |
| 8 tuần | 7,2% | 14,9% | 5,6% |

- Dữ liệu bắt đầu 01/03 nên người cũ vắng hai tuần đầu bị tính là mới → cohort sớm cao ảo; xu hướng giảm giữa các cohort không có nghĩa hệ sinh thái yếu đi.
- "Còn hoạt động" chỉ tính trong tập repo đã lọc; người chuyển repo bị tính là rời đi.
- Chưa có mốc so sánh bên ngoài để nói 17% là cao hay thấp.

## Giới hạn

- **Cách xác định repo AI còn thô.** AI = tên khớp từ khóa, hoặc topic AI (`llm`, `machine-learning`, `mcp`...), hoặc mô tả chứa từ khóa AI. Chỉ xét 19.704 repo ≥100 star (top 20.000 theo star); 4.033 được xếp là AI. Thử thêm 48.081 repo 30–99 star: thêm 6.252 repo AI nhưng chỉ ~10% star của repo AI (chạy lại đột biến và giữ chân với tập này: đột biến không đổi, giữ chân cao hơn ~0,5 điểm %).
  - **Độ phủ:** 82% (62/76) trên danh sách 1, 89% (63/71) trên danh sách 2; chỉ theo tên: 25% và 20%.
  - Hai danh sách do tác giả chọn từ trí nhớ, thiên về repo nổi tiếng. Danh sách 2 (`ai_reference_repos_2.txt`) viết trước khi chạy bộ phân loại nên độc lập hơn. Repo ít người biết có thể thấp hơn.
  - Còn sót: `jax`, `triton`, `mlx`, `tinygrad`, `segment-anything`, `faiss`.
  - **Độ chính xác (ước tính):** ~95% phần khớp tên (38/40 repo xem bằng mắt); 76–86% phần thêm từ topic/mô tả (mẫu 50: 38 đúng, 7 ranh giới, 5 sai). Hai mẫu nhỏ, một người đánh giá, sai số ~±10 điểm %.
  - **Thời điểm:** topic và mô tả lấy năm 2026, không phải 03–05/2025; 2.350 repo (12%) không tra được nên chỉ khớp theo tên.
- **Phân tích chính dùng 12 tuần dữ liệu đáng tin;** mẫu 2023–2024 chỉ có bản phân tích đầu (3 ngày/tháng, tập repo AI xác định từ dữ liệu 2025–2026 nên thiên lệch người sống sót, repo đổi tên bị tách lịch sử).
- **Star đột biến chỉ là tín hiệu nghi ngờ.** Mẫu tuổi tài khoản nhỏ (21–25 người mỗi nhóm); hai repo đối chứng do tác giả chọn vì tin là lan truyền thật.
- **Ngưỡng do tác giả chọn** (50 star, ×5, ≤3 sự kiện, 0,70). Ngưỡng star thử 9 bộ; các ngưỡng khác chưa thử độ nhạy.
- **Đường cơ sở:** đường trượt chỉ gắn cờ đợt sụt kéo dài vài tuần đầu; đường cố định (4 tuần đầu) gắn cờ suốt nhưng không phân biệt lỗi với thay đổi mức dài hạn thật. Dữ liệu thật chỉ có 8 ngày sau điểm sụt nên sự khác biệt này mới chứng minh bằng dữ liệu tổng hợp.
- **Kiểm tra id trùng** chỉ chạy trên một tuần mẫu (kiểm toàn bộ cần băm >300 triệu id): tuần mẫu có 24 id trùng; một phép đo trước đó ghi 55 id trùng trong 150 triệu dòng.

## Dựng lại kết quả từ đầu

- Đã chạy trên Windows 11, Python 3.13. Chạy script bằng `.venv\Scripts\python -X utf8 scripts\...`.
- Dữ liệu và kết quả trung gian nằm trong `data/` (không đưa lên git), nên dựng theo thứ tự:

1. **Cài đặt.**
   ```
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```
2. **Tải dữ liệu** (giai đoạn đáng tin; `2` là số luồng).
   ```
   .venv\Scripts\python -I -X utf8 scripts\ingest.py 2025-03-01 2025-05-31 2
   ```
   - ~230 GB tải qua mạng, giữ ~6 GB Parquet; ~2 giờ mỗi tháng khi mạng ổn (có lúc chậm hơn 10 lần).
   - Chạy lại sẽ bỏ qua giờ đã xong.
3. **Repo AI và star đột biến** (tạo `data/derived/`).
   - `fetch_repo_metadata.py` gọi GitHub GraphQL bằng đăng nhập `gh` (`gh auth login`): ~200 lượt, ~1 giờ, tự tiếp tục khi bị ngắt.
   ```
   .venv\Scripts\python -I -X utf8 scripts\top_repos_by_stars.py
   .venv\Scripts\python -I -X utf8 scripts\fetch_repo_metadata.py
   .venv\Scripts\python -I -X utf8 scripts\ai_repos_classify.py
   .venv\Scripts\python -I -X utf8 scripts\star_anomalies.py
   ```
4. **Kiểm tra tuổi tài khoản** (API công khai, 60 lượt/giờ; cần ~150 lượt nên phải chờ giữa các lần chạy).
   - Tên repo bị gắn cờ: `select repo, count(*) from 'data/derived/star_spikes.parquet' where n >= 100 and jump >= 0.30 group by 1`.
   ```
   set RADAR_FLAGGED_REPO=owner/repo
   .venv\Scripts\python -I -X utf8 scripts\check_account_age.py
   .venv\Scripts\python -I -X utf8 scripts\check_account_age.py github/github-mcp-server 2025-04-07 2025-04-08
   .venv\Scripts\python -I -X utf8 scripts\check_account_age.py x1xhlol/system-prompts-and-models-of-ai-tools 2025-04-19 2025-04-22
   .venv\Scripts\python -I -X utf8 scripts\check_account_age.py owner/repo-x2 2025-04-14 2025-04-15
   .venv\Scripts\python -I -X utf8 scripts\check_account_age.py owner/repo-y 2025-04-25 2025-04-25
   ```
5. **Pipeline dbt (mô hình + test).**
   ```
   .venv\Scripts\python -X utf8 scripts\run_pipeline.py
   ```
   - Dừng với mã thoát 1 nếu một test mức lỗi không đạt (ví dụ thiếu giờ: `assert_no_missing_hours`). Đó là hành vi đúng.
6. **Dashboard.**
   ```
   .venv\Scripts\python -I -X utf8 scripts\build_dashboard.py
   ```

- **Kiểm thử tự động** (không cần dữ liệu thật; thời gian chạy với 4 kịch bản chưa đo): `.venv\Scripts\python -X utf8 ci\check_scenarios.py`. Dựng 4 bộ dữ liệu tổng hợp (sạch, lỗi cài sẵn, loại sự kiện lạ, sụt kéo dài 5 tuần), chạy `dbt build` và kiểm tra từng lỗi có bị bắt đúng không (`ci/make_synthetic.py`).
- **Đã kiểm chứng:**
  - Clone sạch → cài môi trường → tải thật 2 giờ → `run_pipeline.py`: dựng đủ 7 mô hình, 24 test đạt (lúc đó chưa có 4 test sau này), dừng đúng ở test thiếu giờ. Kho trống dữ liệu dừng ngay với thông báo rõ.
  - Bảng dbt khớp script phân tích ở các chỉ số đã so (ngày đột biến, số repo, giữ chân, độ phủ).
- **Chưa kiểm chứng:** dựng lại toàn bộ con số trên máy khác (~230 GB); Linux/macOS cho pipeline thật (CI chỉ chạy dữ liệu tổng hợp); các bước 3, 4, 6 trong clone sạch.

## Cấu trúc thư mục

| Chỗ | Là gì |
|---|---|
| `scripts/ingest.py` | Thu thập theo giờ |
| `scripts/run_pipeline.py` | Điều phối cả chuỗi |
| `dbt_radar/` | Dự án dbt (staging → intermediate → marts, 28 test). Chạy trong thư mục này: `..\.venv\Scripts\dbt.exe build --profiles-dir .` |
| `ci/`, `.github/workflows/ci.yml` | Dữ liệu tổng hợp có lỗi cài sẵn + kiểm tra tự động (GitHub Actions) |
| `scripts/top_repos_by_stars.py`, `fetch_repo_metadata.py`, `ai_repos_classify.py` | Chọn 20.000 repo, tra topic/mô tả, phân loại AI, đo độ phủ từng tín hiệu |
| `scripts/ai_repos_recall.py`, `ai_reference_repos.txt`, `ai_reference_repos_2.txt` | Đo độ phủ end-to-end trên hai danh sách chọn tay |
| `scripts/star_anomalies.py` | Ngày star đột biến và tỉ lệ tài khoản mỏng, 9 bộ ngưỡng |
| `scripts/check_account_age.py` | Kiểm tuổi tài khoản bằng GitHub API công khai |
| `scripts/ingest_sample.py`, `dq_sample.py`, `sample_waves.py`, `sample_thin_stars.py` | Mẫu 2023–2024: tải, kiểm tra chất lượng, star theo quý của repo AI |
| `scripts/cohort_retention.py` | Giữ chân theo cohort (bản script; bản dbt: `fct_cohort_retention`) |
| `scripts/build_dashboard.py`, `dashboard_template.html` | Tạo `docs/index.html` |
| `scripts/build_dbt_docs.py` | Tạo `docs/dbt/index.html` (cần chạy `run_pipeline.py` trước) |
| `scripts/ai_repos_probe.py`, `dq_hourly.py`, `build_db.py` | Bản đầu (lọc theo tên, kiểm tra chất lượng, view DuckDB); không còn dùng trong pipeline |
| `scripts/compare_hours.py`, `probe_day.py`, `recompress.py` | Đo thử ban đầu; chuyển Parquet cũ sang định dạng gọn (dùng một lần) |
| `docs/` | Dashboard, tài liệu dbt (GitHub Pages) và bài viết |
| `PLAN.md` | Nhật ký từng bước: kế hoạch, số đo, lỗi đã gặp |
| `data/` | Dữ liệu (không đưa lên git) |

## Hướng phát triển

- Làm sâu phân tích mẫu 2023–2024: đo độ phủ của bộ phân loại cho 2023–2024, kiểm tuổi tài khoản, xử lý đổi tên repo.
- Phân loại repo AI: nâng độ chính xác (76–86%; nhóm chỉ khớp qua mô tả ~70%) và độ phủ (82–89%): đo độ phủ cho repo ít người biết (repo 30–99 star đã thử: chỉ thêm ~10% star), gán nhãn bằng mô hình ngôn ngữ, mẫu kiểm tay lớn hơn.
- Câu hỏi mới trả lời sơ bộ (mẫu 2023–2024, 3 ngày/tháng): dự án nào giảm dần, các làn sóng nối tiếp nhau thế nào. Cần dữ liệu đầy đủ hơn và xử lý đổi tên repo để kết luận chắc.
- Nguồn thay thế như OpenDigger (tương thích GH Archive, [gharchive #323](https://github.com/igrigorik/gharchive.org/issues/323)) chưa thử.

## Giấy phép

Mã nguồn dùng giấy phép MIT (xem `LICENSE`). Dữ liệu gốc thuộc [GH Archive](https://www.gharchive.org/) và GitHub, không nằm trong kho này.
