# Radar hệ sinh thái AI mã nguồn mở

Pipeline dữ liệu trên [GH Archive](https://www.gharchive.org/) (mọi sự kiện công khai của GitHub, mỗi giờ một file): thu thập, kiểm tra chất lượng, mô hình hóa bằng dbt và DuckDB, rồi phân tích hệ sinh thái AI mã nguồn mở. Đây là một dự án học tập. Kết quả mang tính khám phá, và các giới hạn được nêu rõ ở từng phần.

**Xem kết quả:** [dashboard](https://dtkhang05.github.io/gh-ai-radar/) · [bài viết](docs/bai-viet.md) · nhật ký kế hoạch và số đo từng bước: [PLAN.md](PLAN.md)

## Kết quả chính

- **Nguồn dữ liệu mất sự kiện, và lớp kiểm tra chất lượng tự phát hiện được.** Từ khoảng 17h UTC ngày 23/05/2025, số sự kiện mỗi giờ giảm khoảng 35% và không hồi lại. Phân tích vì vậy chỉ dùng dữ liệu đến 22/05/2025. Cùng lớp kiểm tra còn bắt được một file giờ tải về báo thành công nhưng chỉ chứa 12% số sự kiện thường lệ (08/05/2025 01:00 UTC).
- **Star tăng đột biến: phần lớn là người dùng thật.** Trong khoảng 8.000 repo có tên khớp từ khóa AI có 444 ngày đột biến ở 153 repo, và nhìn chung các ngày đó không có nhiều tài khoản "mỏng" hơn ngày thường. Một repo nổi bật bất thường, được kiểm chứng thêm bằng tuổi tài khoản (xem bên dưới).
- **Người đóng góp mới ít khi ở lại.** 16,9% còn hoạt động sau 1 tuần và 5,8% sau 8 tuần; người bắt đầu bằng code giữ lại tốt hơn nhiều so với người chỉ để lại issue hoặc bình luận.
- **Giới hạn lớn nhất: tập repo "AI" chỉ là tập con theo tên repo, độ phủ khoảng 25%.** Các kết quả trên chỉ đúng cho nhóm repo đó. Xem phần [Giới hạn](#giới-hạn).

## Cách hệ thống hoạt động

| Lớp | Thành phần | Việc làm |
|---|---|---|
| Thu thập | `scripts/ingest.py` | Tải từng giờ, giữ 5 cột, ghi Parquet, **xóa file thô ngay** để không đầy ổ; ghi `data/manifest.jsonl`; chạy lại được (bỏ qua giờ đã xong) |
| Lưu trữ | Parquet (zstd mức 9, id số nguyên, sắp theo repo) + DuckDB | Dữ liệu chỉ lưu một bản trong Parquet (khoảng 2,7 MB mỗi giờ); DuckDB đọc trực tiếp bằng view. Bản đầu sao chép vào bảng DuckDB nặng gấp 3,6 lần Parquet nên đã bỏ |
| Mô hình | `dbt_radar/` (dbt-core 1.12, dbt-duckdb 1.11) | staging (view) → intermediate → marts: `fct_star_daily`, `fct_star_spike_days`, `fct_contributor_week`, `fct_cohort_retention`, `fct_hourly_quality` |
| Chất lượng | `fct_hourly_quality` + 25 test dbt | So số sự kiện từng giờ với trung vị của cùng thứ và giờ trong 4 tuần trước; test bắt giờ thiếu, giờ bất thường, id trùng, giá trị lạ |
| Điều phối | `scripts/run_pipeline.py` | Một lệnh: kiểm tra trước → (tùy chọn) tải → `dbt build` → tóm tắt; dừng ngay khi lỗi (mã thoát khác 0) và ghi log có dấu thời gian |
| Trình bày | `docs/index.html` | Trang HTML tĩnh tự chứa (không cần máy chủ), dựng từ các bảng dbt bằng `scripts/build_dashboard.py` |

Mọi script DuckDB đặt giới hạn bộ nhớ và dung lượng file tạm, sau một lần một truy vấn thăm dò chiếm 12 GB RAM và tràn 16 GB file tạm ra ổ đĩa.

## Dữ liệu và độ tin cậy của nguồn

GH Archive cung cấp miễn phí mỗi giờ một file `https://data.gharchive.org/YYYY-MM-DD-H.json.gz` (giờ UTC, H không có số 0 ở đầu).

**Nguồn có hiện tượng mất sự kiện.** Đo ngày 20/10/2026 trên cùng giờ 12:00 UTC ngày 19 của từng tháng (`scripts/compare_hours.py`; mỗi con số chỉ là **một giờ mẫu** của tháng, chưa phải cả tháng):

| Giờ | Tổng sự kiện | Star (WatchEvent) | Fork | Push |
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

Star giảm dần từ giữa 2025 và còn rất ít từ tháng 5/2026; từ tháng 8/2026 tổng số sự kiện cũng thất thường. Ví dụ `anthropics/claude-code` chỉ có 8 star trong cả ngày 19/10/2026, rõ ràng thiếu. Cộng đồng đã báo lỗi mất sự kiện ([gharchive issue #320](https://github.com/igrigorik/gharchive.org/issues/320), [GitHub discussion #178788](https://github.com/orgs/community/discussions/178788)); nguyên nhân chưa được xác nhận chính thức, và chưa kiểm tra liệu điểm sụt 23/05/2025 có cùng nguyên nhân hay không.

**Đã tải và kiểm tra:** tháng 03, 04, 05/2025 đủ giờ (744 + 720 + 744 file, không file nào lỗi) và 960 trong 1.416 giờ của 01–02/2025 (dừng giữa chừng vì mạng chậm). Phân tích chính dùng 01/03 → 22/05/2025 (12 tuần). Chưa tải 2023–2024.

**Chi phí thu thập:** mỗi giờ là một file khoảng 100 MB nén, nên 2.208 giờ (03–05/2025) là khoảng 230 GB phải tải qua mạng (không lưu lại) và khoảng 6 GB Parquet giữ lại. Ngoại suy cho 29 tháng (01/2023 – 05/2025) khoảng 57 GB Parquet; **chưa đo cả khoảng đó**, chỉ ngoại suy từ 3 tháng.

## Kết quả chi tiết

### Ngày star tăng đột biến có phải người dùng thật không?

Dữ liệu: 01/03 → 22/05/2025, khoảng 8.000 repo có tên khớp từ khóa AI (độ chính xác thô khoảng 95% trên mẫu 40 repo xem bằng mắt).

1. Một ngày được coi là đột biến khi có ít nhất 50 star và gấp 5 lần trung vị 14 ngày trước, và repo đã có star ở ít nhất 7 trong 14 ngày đó (nếu không, ngày ra mắt của repo mới bị tính nhầm). Kết quả: 444 ngày đột biến ở 153 repo (190–806 ngày tùy 9 bộ ngưỡng thử).
2. **Dấu hiệu thứ nhất:** tỉ lệ người star có không quá 3 sự kiện trong 12 tuần ("tài khoản mỏng"). Nhìn chung ngày đột biến không mỏng hơn ngày thường (7–8,5% so với 8–11%), nên đa số đột biến đến từ ra mắt hoặc được chia sẻ rộng. Chỉ một repo, gọi là "Repo X", bị gắn cờ ở cả 9 bộ ngưỡng.
3. **Dấu hiệu thứ hai, kiểm chứng độc lập bằng GitHub API** (mẫu 21–24 tài khoản mỗi nhóm):

| Nhóm | Tuổi tài khoản lúc star (trung vị) | Tạo <30 ngày trước | Chưa có repo |
|---|---|---|---|
| Repo X, 14–15/04/2025 | 0 ngày | 20/21 | 19/21 |
| Repo X, ngày thường | 442 ngày | 0/23 | 1/23 |
| github-mcp-server, ra mắt 07–08/04 (đối chứng) | 3.820 ngày | 0/22 | 1/22 |
| system-prompts…, 19–22/04 (đối chứng) | 2.050 ngày | 2/24 | 2/24 |

Kết quả cho thấy các lượt star ngày 14–15/04/2025 của Repo X phần lớn đến từ tài khoản tạo ngay trong ngày và chưa có repo nào, khác hẳn hai đợt lan truyền thật. Nó **không** cho biết ai đứng sau (chủ repo, bên bán star hay người ngoài), nên dự án không gán lỗi cho ai. Vì bằng chứng chỉ là một mẫu nhỏ về một dự án thật, tên repo được ẩn thành "Repo X" trong tài liệu, mã và dashboard. Để chạy lại phép kiểm tra, đặt biến môi trường `RADAR_FLAGGED_REPO=owner/repo` (tên nằm trong `data/derived/star_spikes.parquet` sau khi chạy `scripts/star_anomalies.py`); để dashboard hiện tên thật, thêm `--show-names` khi chạy `scripts/build_dashboard.py`.

### Người đóng góp mới có ở lại không?

52.417 người đóng góp (push, PR, issue, bình luận, review; loại bot) trên cùng tập repo, 11 khối 7 ngày từ 01/03/2025. "Người mới" là người lần đầu xuất hiện từ khối thứ 3 trở đi; hai khối đầu chỉ dùng để nhận ra người cũ.

| Sau | Còn hoạt động | Nếu lần đầu là code (push/PR) | Nếu lần đầu chỉ là issue/bình luận/review |
|---|---|---|---|
| 1 tuần | 16,9% | 29,8% | 12,5% |
| 2 tuần | 10,4% | 21,0% | 6,7% |
| 4 tuần | 7,6% | 15,6% | 4,6% |
| 8 tuần | 5,8% | 12,9% | 3,3% |

Hai điều cần nhớ: dữ liệu bắt đầu từ 01/03 nên người cũ vắng mặt hai tuần đầu bị tính là người mới, làm các cohort sớm cao ảo (xu hướng giảm giữa các cohort không có nghĩa hệ sinh thái yếu đi); và "còn hoạt động" chỉ tính trong tập repo đã lọc, nên người chuyển sang repo khác bị tính là rời đi. Chưa có mốc so sánh bên ngoài để nói 17% là cao hay thấp.

## Giới hạn

- **Độ phủ của tập repo AI chỉ khoảng 25%.** Bộ lọc dựa vào từ khóa trong tên repo; trên 76 repo AI nổi tiếng chọn tay (`scripts/ai_reference_repos.txt`), nó chỉ chứa 19 (đo bằng `scripts/ai_repos_recall.py`). Nó sót repo có từ khóa ở tên tổ chức (`modelcontextprotocol/servers`, `openai/codex`), tên ghép (`vllm`, `comfyui`, `autogpt`) và thư viện nổi tiếng không có từ khóa (`pytorch`, `tensorflow`). Danh sách tham chiếu do tác giả chọn từ trí nhớ và thiên về repo nổi tiếng, nên con số này có thể vẫn tốt hơn thực tế với repo ít người biết. Tập repo cũng chỉ gồm repo có ít nhất 10 star trong chính cửa sổ phân tích.
- **Chỉ 12 tuần dữ liệu đáng tin** (01/03 → 22/05/2025); chưa có dữ liệu 2023–2024 nên chưa nói được gì về xu hướng nhiều năm.
- **Star đột biến chỉ là tín hiệu nghi ngờ.** Mẫu kiểm tra tuổi tài khoản nhỏ (21–24 tài khoản mỗi nhóm, 3 repo) và hai repo đối chứng do tác giả chọn vì tin là lan truyền thật.
- **Các ngưỡng do tác giả chọn** (50 star mỗi ngày, gấp 5 lần, ≤3 sự kiện, 0,70 cho cờ chất lượng). Ngưỡng star được thử 9 bộ; các ngưỡng còn lại chưa thử độ nhạy.
- **Lớp kiểm tra chất lượng dùng đường cơ sở trượt**, nên một đợt sụt kéo dài chỉ bị gắn cờ trong vài tuần đầu. Ba tuần đầu của mỗi chuỗi dữ liệu chưa có đường cơ sở nên chưa được kiểm tra.
- **Kiểm tra id trùng** chỉ chạy trên một tuần mẫu vì kiểm toàn bộ cần băm hơn 300 triệu id (tuần mẫu có 24 id trùng; một phép đo trước đó trên tháng 05/2025 ghi 55 id trùng trong 150 triệu dòng).

## Dựng lại kết quả từ đầu

Đã chạy trên Windows 11, Python 3.13. Chạy script bằng `.venv\Scripts\python -X utf8 scripts\...` (`-X utf8` để in bảng không lỗi phông). Dữ liệu và kết quả trung gian nằm trong `data/` (không đưa lên git), nên phải dựng theo thứ tự sau:

1. **Cài đặt.**
   ```
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```
2. **Tải dữ liệu** (chỉ giai đoạn đã kiểm tra là đáng tin). `2` là số luồng tải.
   ```
   .venv\Scripts\python -I -X utf8 scripts\ingest.py 2025-03-01 2025-05-31 2
   ```
   Chi phí: khoảng 230 GB phải tải qua mạng, chỉ giữ khoảng 6 GB Parquet. Khi mạng ổn mất khoảng 2 giờ mỗi tháng; có lúc mạng chậm hơn 10 lần. Chạy lại lệnh sẽ bỏ qua các giờ đã xong.
3. **Danh sách repo AI và star đột biến** (các script này tạo `data/derived/`, mà bước sau cần):
   ```
   .venv\Scripts\python -I -X utf8 scripts\ai_repos_probe.py
   .venv\Scripts\python -I -X utf8 scripts\star_anomalies.py
   ```
4. **Kiểm tra tuổi tài khoản** (gọi API công khai của GitHub, giới hạn 60 lượt/giờ, cần khoảng 75 lượt nên có thể phải chờ giữa các lần chạy). Lấy tên repo bị gắn cờ từ kết quả bước 3: `select distinct repo from 'data/derived/star_spikes.parquet' where n >= 100 and jump >= 0.30`.
   ```
   set RADAR_FLAGGED_REPO=owner/repo
   .venv\Scripts\python -I -X utf8 scripts\check_account_age.py
   .venv\Scripts\python -I -X utf8 scripts\check_account_age.py github/github-mcp-server 2025-04-07 2025-04-08
   .venv\Scripts\python -I -X utf8 scripts\check_account_age.py x1xhlol/system-prompts-and-models-of-ai-tools 2025-04-19 2025-04-22
   ```
5. **Pipeline dbt (mô hình + test).**
   ```
   .venv\Scripts\python -X utf8 scripts\run_pipeline.py
   ```
   Pipeline dừng với mã thoát 1 nếu một test mức lỗi không đạt, ví dụ khi dữ liệu còn thiếu giờ (test `assert_no_missing_hours`). Đó là hành vi đúng, không phải lỗi cài đặt.
6. **Dashboard.**
   ```
   .venv\Scripts\python -I -X utf8 scripts\build_dashboard.py
   ```

**Đã kiểm chứng:** tải kho từ GitHub về thư mục trống, cài môi trường, tải thật 2 giờ dữ liệu bằng `ingest.py`, rồi chạy `run_pipeline.py`: dbt dựng đủ 7 mô hình, 24 test đạt và pipeline dừng đúng ở test thiếu giờ (kết quả mong đợi với 2 giờ dữ liệu). Chạy trên kho trống dữ liệu cũng dừng ngay với thông báo rõ ràng. Kết quả dbt khớp từng con số với các phân tích bằng script viết trước đó.
**Chưa kiểm chứng:** dựng lại toàn bộ con số từ đầu trên một máy khác (cần tải khoảng 230 GB), chạy trên Linux hoặc macOS, và các bước 3, 4, 6 trong một bản clone sạch (hiện chỉ chạy được trên máy của tác giả, nơi dữ liệu đã có).

## Cấu trúc thư mục

| Chỗ | Là gì |
|---|---|
| `scripts/ingest.py` | Thu thập dữ liệu theo giờ |
| `scripts/run_pipeline.py` | Điều phối cả chuỗi (kiểm tra trước → tải → dbt → tóm tắt) |
| `dbt_radar/` | Dự án dbt: staging → intermediate → marts và 25 test. Chạy từ trong thư mục này: `..\.venv\Scripts\dbt.exe build --profiles-dir .` |
| `scripts/ai_repos_probe.py` | Lọc repo AI theo từ khóa nguyên từ trong tên repo |
| `scripts/ai_repos_recall.py`, `scripts/ai_reference_repos.txt` | Đo độ phủ của bộ lọc trên danh sách repo AI nổi tiếng chọn tay |
| `scripts/star_anomalies.py` | Tìm ngày star đột biến và tỉ lệ tài khoản mỏng, thử 9 bộ ngưỡng |
| `scripts/check_account_age.py` | Kiểm chứng tuổi tài khoản bằng GitHub API công khai |
| `scripts/cohort_retention.py` | Giữ chân người đóng góp theo cohort (bản script; bản dbt là `fct_cohort_retention`) |
| `scripts/dq_hourly.py`, `scripts/build_db.py` | Bản script đầu của lớp kiểm tra chất lượng và của view DuckDB; nay đã có bản dbt tương đương |
| `scripts/compare_hours.py`, `scripts/probe_day.py` | Đo thử ban đầu: so số sự kiện các giờ mẫu; đo thử một ngày |
| `scripts/recompress.py` | Dùng một lần: chuyển Parquet cũ sang định dạng gọn hơn |
| `scripts/build_dashboard.py`, `scripts/dashboard_template.html` | Tạo `docs/index.html` từ các bảng dbt và các file mẫu tài khoản |
| `docs/` | Dashboard (`index.html`, phục vụ qua GitHub Pages) và bài viết (`bai-viet.md`) |
| `PLAN.md` | Nhật ký theo từng bước: kế hoạch, số đo, kết quả, lỗi đã gặp |
| `data/` | Dữ liệu (không đưa lên git) |

## Hướng phát triển

Chưa làm: tải dữ liệu 2023–2024 (có thể lấy mẫu một vài ngày mỗi tháng thay vì tải đủ, để vẫn thấy xu hướng nhiều năm); mở rộng cách xác định repo AI để không chỉ dựa vào tên repo (ví dụ dùng chủ đề và mô tả repo qua GitHub API) rồi đo lại độ phủ; đường cơ sở cố định cho lớp kiểm tra chất lượng; chạy kiểm thử trên CI; các câu hỏi chưa trả lời (dự án nào đang chết dần, làn sóng nối tiếp nhau như thế nào). Nguồn dữ liệu thay thế như OpenDigger (một kho tương thích GH Archive, [gharchive issue #323](https://github.com/igrigorik/gharchive.org/issues/323)) chưa được thử.

## Giấy phép

Mã nguồn dùng giấy phép MIT (xem `LICENSE`). Dữ liệu gốc thuộc [GH Archive](https://www.gharchive.org/) và GitHub, không nằm trong kho này.
