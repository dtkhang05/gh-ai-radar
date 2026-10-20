# Radar hệ sinh thái AI mã nguồn mở

Dự án dữ liệu cho CV, theo hướng **Analytics Engineer**: tự xây hệ thống dữ liệu (thu → làm sạch → mô hình hóa → kiểm tra chất lượng), rồi biến nó thành insight có thể đọc được.

**Xem kết quả:** [dashboard](https://dtkhang05.github.io/gh-ai-radar/) · [bài viết](docs/bai-viet.md) · kế hoạch và số đo từng phase: [PLAN.md](PLAN.md)

Tạo ngày 20/10/2026. Trạng thái (20/10/2026): **có script thu thập, lớp kiểm tra chất lượng, dự án dbt có test (kết quả khớp các phân tích bằng script), đã tải 03–05/2025 và một phần 01–02/2025, có 2 kết quả insight (star bất thường, giữ chân người đóng góp), dashboard tĩnh và một bài viết. Chưa có CI, chưa tải 2023–2024.**

**Về tên repo bị gắn cờ:** vì bằng chứng chỉ là một mẫu nhỏ về một dự án thật, tên repo được ẩn thành "Repo X" trong tài liệu, mã và dashboard. Để chạy lại phép kiểm tra tuổi tài khoản, đặt biến môi trường `RADAR_FLAGGED_REPO=owner/repo` (tên nằm trong `data/derived/star_spikes.parquet` sau khi chạy `scripts/star_anomalies.py`); để dashboard hiện tên thật, thêm `--show-names` khi chạy `scripts/build_dashboard.py`.

## Mục tiêu
- Một dự án "xịn" để đưa vào CV, không nhằm kiếm tiền.
- Có đủ hai vế: **hệ thống thật** (dữ liệu thật, lớn, chạy tự động, có kiểm thử) và **insight thật** (bài phân tích, dashboard công khai).
- Repo công khai trên GitHub để nhà tuyển dụng xem được.

## Dữ liệu
[GH Archive](https://www.gharchive.org/): mọi sự kiện công khai trên GitHub (star, fork, push, PR, issue, comment…), mỗi giờ một file `https://data.gharchive.org/YYYY-MM-DD-H.json.gz` (giờ UTC, H không có số 0 ở đầu). Miễn phí, không cần tài khoản.

### Phát hiện quan trọng: dữ liệu từ giữa 2025 bị thiếu nặng
Đo ngày 20/10/2026, cùng giờ 12:00 UTC ngày 19 của từng tháng (`scripts/compare_hours.py`):

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

- Star giảm dần từ giữa 2025, sụp khoảng 90% từ tháng 5/2026. Từ tháng 8/2026 tổng số sự kiện cũng thất thường.
- Ví dụ: `anthropics/claude-code` chỉ có 8 star trong cả ngày 19/10/2026, rõ ràng thiếu.
- Lỗi phía nguồn, cộng đồng đã báo: [gharchive issue #320](https://github.com/igrigorik/gharchive.org/issues/320), [GitHub community #178788](https://github.com/orgs/community/discussions/178788). Nguyên nhân chưa ai xác nhận chính thức.
- Nguồn thay thế có thể xem: OpenDigger chạy một kho tương thích GH Archive từ 06/09/2026 ([issue #323](https://github.com/igrigorik/gharchive.org/issues/323)). **Chưa kiểm tra.**

Mỗi con số trên chỉ là **một giờ mẫu** mỗi tháng, chưa phải toàn bộ tháng.

### Đo thử 1 ngày (19/10/2026)
- 24 file, 222 MB nén, tải trong ~8 giây (tải song song).
- 1.042.693 sự kiện, 452.785 repo, 326.716 người. DuckDB nạp 5 cột cần dùng trong ~1 giây.
- Ghi Parquet 5 cột: 42 MB.
- Lọc repo AI bằng từ khóa trong tên (`scripts/probe_day.py`): 63.170 sự kiện, 27.711 repo, khoảng 6%. Lọc theo tên là thô, cần cách tốt hơn (xem "Việc cần quyết").
- Một giờ năm 2024 nặng ~67 MB nén, nên giai đoạn 2023–2025 có thể là hơn 1 TB tải về. **Ước tính, chưa đo.**

## Số đo thật khi thu thập (20/10/2026)
- Đã tải tháng 03, 04, 05/2025 đủ giờ (744 + 720 + 744 giờ, 0 lỗi) và 960/1.416 giờ của 01–02/2025 (dừng vì mạng chậm bất thường, nguyên nhân chưa biết).
- Dung lượng Parquet: khoảng 2,7 MB mỗi giờ sau khi tối ưu (id số nguyên, sắp theo repo, zstd mức 9: nhỏ hơn 29% so với mặc định). Ngoại suy 29 tháng khoảng 57 GB, **chưa đo cả khoảng đó**.
- **Mốc dữ liệu đáng tin kết thúc khoảng 22/05/2025**, không phải 31/05: từ 23/05/2025 ~16–17h UTC số sự kiện sụt ~35% đột ngột và không hồi lại. Lớp kiểm tra `dq_hourly.py` tự bắt được điểm này, và bắt thêm một giờ file tải `ok` nhưng thiếu nội dung (08/05/2025 01:00 UTC, chỉ 12% bình thường).
- Chưa xem dữ liệu trước 03/2025 bằng lớp kiểm tra (3 tuần đầu của mỗi chuỗi chưa có baseline).

## Kết quả đầu tiên: ngày star tăng đột biến có phải người dùng thật không?
Dữ liệu: 01/03 → 22/05/2025, khoảng 8.000 repo có tên khớp từ khóa AI (độ chính xác thô ~95% trên mẫu 40 repo xem bằng mắt). **Độ phủ chỉ ~25%**: trên 76 repo AI nổi tiếng chọn tay (`scripts/ai_reference_repos.txt`), bộ lọc bắt được 19 (đo bằng `scripts/ai_repos_recall.py`). Nó sót repo có từ khóa ở tên tổ chức (`modelcontextprotocol/servers`, `openai/codex`), tên ghép (`vllm`, `comfyui`, `autogpt`) và thư viện nổi tiếng không có từ khóa (`pytorch`, `tensorflow`). Vì vậy các kết quả dưới đây chỉ đúng cho nhóm repo có tên khớp từ khóa, không phải toàn bộ hệ sinh thái AI.
1. Một ngày được coi là đột biến khi có ≥50 star và ≥5 lần trung vị 14 ngày trước, và repo đã có ≥7 ngày có star trước đó (nếu không, ngày ra mắt bị tính nhầm). Có 444 ngày đột biến ở 153 repo (190–806 ngày tùy 9 bộ ngưỡng thử).
2. Dấu hiệu 1: tỉ lệ người star có ≤3 sự kiện trong 12 tuần ("tài khoản mỏng"). Nhìn chung ngày đột biến **không** mỏng hơn ngày thường (7–8,5% vs 8–11%): đa số đột biến là lan truyền thật. Chỉ `Repo X` bị cờ ở cả 9 bộ ngưỡng.
3. Dấu hiệu 2, kiểm chứng độc lập bằng GitHub API (mẫu 21–24 tài khoản mỗi nhóm):

| Nhóm | Tuổi tài khoản lúc star (trung vị) | Tạo <30 ngày trước | Chưa có repo |
|---|---|---|---|
| Repo X, 14–15/04/2025 | 0 ngày | 20/21 | 19/21 |
| Repo X, ngày thường | 442 ngày | 0/23 | 1/23 |
| github-mcp-server, ra mắt 07–08/04 (đối chứng) | 3.820 ngày | 0/22 | 1/22 |
| system-prompts…, 19–22/04 (đối chứng) | 2.050 ngày | 2/24 | 2/24 |

**Kết luận có giới hạn:** các lượt star ngày 14–15/04/2025 của `Repo X` phần lớn đến từ tài khoản tạo ngay trong ngày và chưa có repo, khác hẳn hai đợt lan truyền thật. **Không chứng minh được ai đứng sau** (chủ repo, bên bán star, hay người ngoài), nên dự án không gán lỗi cho ai.
Giới hạn: mẫu nhỏ, 3 repo, hai repo đối chứng do mình chọn vì tin là thật (chưa kiểm độc lập), ngưỡng do mình chọn, chỉ 12 tuần, danh sách repo AI dựa trên tên. Mã: `scripts/ai_repos_probe.py`, `star_anomalies.py`, `check_account_age.py`.

## Hướng đã chốt
1. **Insight chính** dùng giai đoạn **01/2023 → 05/2025** (dữ liệu còn đáng tin; đúng giai đoạn bùng nổ AI: ChatGPT → agent). Mốc cuối 05/2025 cần kiểm lại bằng số liệu theo ngày.
2. **Lớp kiểm tra chất lượng dữ liệu** là một tính năng chính: tự phát hiện nguồn mất sự kiện. Câu chuyện cho CV: *"Hệ thống phát hiện nguồn công khai mất ~90% sự kiện; tôi điều chỉnh phân tích để không kết luận sai."*
3. **Phần chạy hằng ngày** để sau, bằng nguồn khác (OpenDigger hoặc GitHub API cho một danh sách repo). Chưa thử.

## Kiến trúc dự kiến
| Lớp | Công cụ | Việc |
|---|---|---|
| Thu | Python | Tải từng giờ, lọc phần cần, ghi Parquet, **xóa file thô ngay** để không đầy ổ |
| Kho | DuckDB | Lưu Parquet theo tháng |
| Mô hình | dbt (dbt-duckdb) | raw → staging → marts; kiểm thử dữ liệu (not null, unique, khoảng giá trị, số sự kiện theo giờ) |
| Chất lượng | dbt tests + bảng theo dõi | Số sự kiện mỗi giờ theo loại, cảnh báo khi giảm bất thường |
| Chạy tự động | GitHub Actions | Sau này, cho phần cập nhật hằng ngày |
| Insight | SQL + notebook | Báo cáo theo chủ đề (dưới đây) |
| Hỏi bằng tiếng Việt | LLM viết SQL | Có bộ câu hỏi mẫu để chấm độ đúng; cần khóa API (tốn ít tiền), làm sau cùng |
| Trình bày | Dashboard công khai (Evidence.dev hoặc Streamlit) | Kèm vài bài viết insight |

## Câu hỏi insight dự kiến
- Repo AI nào tăng trưởng thật, repo nào tăng star bất thường (có thể là star mua)?
- Người đóng góp mới có ở lại không? Phân tích **cohort retention**, giống giữ chân khách hàng.
- Dự án nào đang chết dần (ít commit, issue không ai trả lời)?
- Hệ sinh thái chuyển dịch thế nào qua các làn sóng (LangChain → agent → MCP…)?

## Khác gì GitHub Trending, OSS Insight, Star History?
Những web đó là công cụ **xem** (bảng xếp hạng, đường star của từng repo). Dự án này không cạnh tranh với họ. Nó tập trung vào những câu hỏi họ không trả lời sẵn:
- Người đóng góp mới có ở lại không (cohort retention của cả hệ sinh thái)?
- Star tăng thật hay bất thường?
- Dự án nào đang chết dần?
- Làn sóng nào nối làn sóng nào?

Nó còn có lớp kiểm tra chất lượng dữ liệu: OSS Insight cũng lấy từ GH Archive và bị cộng đồng báo cùng lỗi mất dữ liệu ([#178788](https://github.com/orgs/community/discussions/178788)).

Nếu phỏng vấn hỏi "sao không dùng OSS Insight?": họ cho xem số liệu, còn dự án này chứng minh mình tự xây được hệ thống, biết nghi ngờ nguồn, và tự rút ra kết luận. Chưa kiểm tra kỹ từng tính năng của OSS Insight; cần xem trước khi chọn câu hỏi insight, để tránh làm trùng.

## Việc cần quyết
- Cách xác định "repo AI": từ khóa trong tên (thô), danh sách tay, hay lấy topic qua GitHub API.
- Tải 1 TB về máy (chạy đêm) hay dùng BigQuery (bảng công khai `githubarchive`, cần tài khoản Google Cloud; gói miễn phí 1 TB truy vấn/tháng; chưa thử).

## Bước tiếp theo
Chưa quyết. Các hướng còn lại: tải thêm dữ liệu 2023–2024 (mạng chậm nên tốn nhiều giờ), thêm baseline cố định cho lớp chất lượng, thêm CI. Xem `PLAN.md`.

## Thư mục
| Chỗ | Là gì |
|---|---|
| `scripts/probe_day.py` | Đo thử 1 ngày: nạp, đếm, lọc AI theo tên, ghi Parquet (từ khóa thô, đã được thay bằng `ai_repos_probe.py`) |
| `scripts/compare_hours.py` | So số sự kiện của các file giờ (dùng để phát hiện mất dữ liệu) |
| `scripts/ingest.py` | Thu thập: tải từng giờ, lọc, ghi Parquet, xóa file thô, ghi `data/manifest.jsonl`; chạy lại được |
| `scripts/recompress.py` | Một lần: chuyển file Parquet cũ sang định dạng gọn hơn |
| `scripts/build_db.py` | Tạo `data/radar.duckdb` với view đọc Parquet (không sao chép dữ liệu) |
| `scripts/dq_hourly.py` | Kiểm tra chất lượng: số sự kiện mỗi giờ so với trung vị 4 tuần trước, gắn cờ giờ bất thường |
| `scripts/ai_repos_probe.py` | Lọc repo AI theo từ khóa nguyên từ trong tên |
| `scripts/star_anomalies.py` | Tìm ngày star đột biến và tỉ lệ tài khoản mỏng, thử 9 bộ ngưỡng |
| `scripts/check_account_age.py` | Kiểm chứng tuổi tài khoản bằng GitHub API công khai (60 lượt/giờ) |
| `scripts/run_pipeline.py` | Một lệnh chạy cả chuỗi: kiểm tra trước → (tùy chọn) tải → `dbt build` (mô hình + test) → tóm tắt; dừng khi lỗi, ghi `logs/pipeline.log`. Chạy: `.venv\Scripts\python -X utf8 scripts\run_pipeline.py` |
| `docs/index.html` | Dashboard tĩnh (mở trực tiếp bằng trình duyệt, đăng được bằng GitHub Pages). Tạo lại: `.venv\Scripts\python -I -X utf8 scripts\build_dashboard.py` (thêm `--show-names` để hiện tên repo bị gắn cờ; mặc định ẩn) |
| `scripts/build_dashboard.py`, `scripts/dashboard_template.html` | Tạo dashboard từ các bảng dbt và các file mẫu tài khoản |
| `dbt_radar/` | Dự án dbt (dbt-duckdb): staging → intermediate → marts, có 25 test. Chạy từ trong thư mục này: `..\.venv\Scripts\dbt.exe build --profiles-dir .` |
| `PLAN.md` | Kế hoạch theo phase, số đo và kết quả từng phase |
| `data/` | Dữ liệu (không đưa lên git) |
| `CLAUDE.md` | Hướng dẫn cho Claude khi làm dự án này |

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
   Cảnh báo chi phí: mỗi giờ là một file khoảng 100 MB nén, nên 2.208 giờ là **khoảng 230 GB phải tải qua mạng** (không lưu lại: mỗi file bị xóa sau khi lọc) và chỉ giữ khoảng 6 GB Parquet. Khi mạng ổn mất khoảng 2 giờ mỗi tháng; tôi từng gặp lúc mạng chậm hơn 10 lần. Chạy lại lệnh này sẽ bỏ qua các giờ đã xong.
3. **Danh sách repo AI và star đột biến** (các script này tạo `data/derived/`, mà bước sau cần):
   ```
   .venv\Scripts\python -I -X utf8 scripts\ai_repos_probe.py
   .venv\Scripts\python -I -X utf8 scripts\star_anomalies.py
   ```
4. **Kiểm tra tuổi tài khoản** (gọi API công khai của GitHub, giới hạn 60 lượt/giờ, cần khoảng 75 lượt nên có thể phải chờ giữa các lần chạy). Tên repo bị gắn cờ không ghi trong mã; lấy nó từ kết quả bước 3: `select distinct repo from 'data/derived/star_spikes.parquet' where n >= 100 and jump >= 0.30`.
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
6. **Dashboard.** Tạo `docs/index.html`; thêm `--show-names` để hiện tên repo bị gắn cờ (mặc định ẩn).
   ```
   .venv\Scripts\python -I -X utf8 scripts\build_dashboard.py
   ```

**Đã kiểm chứng:** tải kho từ GitHub về thư mục trống, cài môi trường, tải thật 2 giờ dữ liệu bằng `ingest.py`, rồi chạy `run_pipeline.py`: dbt dựng đủ 7 mô hình, 24 test đạt và pipeline dừng đúng ở test thiếu giờ (kết quả mong đợi với 2 giờ dữ liệu). Chạy kho trống dữ liệu cũng dừng ngay với thông báo rõ ràng.
**Chưa kiểm chứng:** dựng lại toàn bộ con số từ đầu trên một máy khác (cần tải khoảng 230 GB), chạy trên Linux/macOS, và các bước 3, 4, 6 trong một bản clone sạch (chỉ chạy được trên máy của tác giả, nơi dữ liệu đã có).

## Giấy phép
Mã nguồn dùng giấy phép MIT (xem `LICENSE`). Dữ liệu gốc thuộc [GH Archive](https://www.gharchive.org/) và GitHub, không nằm trong kho này.
