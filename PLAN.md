# Kế hoạch theo phase

Mỗi phase có **đầu ra kiểm chứng được**. Xong phase nào đánh dấu [x] rồi mới sang phase sau. Ghi số đo thật vào README.

## Phase 1: Thu thập thử 1 tháng (05/2025)  [x]
Kết quả đo (20/10/2026): 744/744 giờ ok, 0 lỗi; 150,5 triệu sự kiện; Parquet 2.569 MB (~3,45 MB/giờ); ~10 giây/giờ với 4 luồng, cả tháng ~2 giờ; ổ không bị đầy. Ngoại suy 29 tháng: ~72 GB, ~2,3 ngày (chưa đo, chỉ dựa trên 05/2025).
Mục tiêu: đo thời gian + dung lượng thật, có pipeline tải → lọc → Parquet → xóa file thô.
- `scripts/ingest.py`: với mỗi giờ, tải về `data/raw/`, DuckDB lọc 5 cột, ghi `data/parquet/YYYY-MM-DD-H.parquet`, xóa file thô.
- Mỗi giờ ghi một dòng vào `data/manifest.jsonl`: số byte nén, tổng sự kiện, số sự kiện theo loại, thời gian xử lý, trạng thái. Đây là nguyên liệu cho lớp kiểm tra chất lượng (Phase 3).
- Chạy lại được (bỏ qua giờ đã xong), thử lại khi lỗi mạng, ổ C không bao giờ chứa quá vài file thô cùng lúc.
- Kiểm chứng: thử 2 giờ trước; sau đó chạy cả tháng, đối chiếu số giờ (744) = số file Parquet + số giờ lỗi.
- Đầu ra: thời gian/giờ, MB Parquet/tháng → ước tính thật cho 29 tháng.

## Phase 2: Kho DuckDB + kiểm tra mốc 05/2025  [x] (kết luận: mốc 05/2025 KHÔNG an toàn)
Kết quả: có đủ 24 giờ mỗi ngày nhưng số sự kiện sụt ~35% đột ngột từ khoảng 2025-05-23 16-17h UTC (từ ~250k xuống ~150k sự kiện/giờ), và không hồi lại đến hết tháng. Star sụt tương tự (~9k → ~4k/giờ). Nguyên nhân chưa kiểm tra. Còn 1 dòng NULL và 55 id trùng trên 150 triệu dòng (cần xử lý ở staging).
Hệ quả: mốc cuối nên là ~22/05/2025, không phải 31/05/2025.
Đã tải thêm 04/2025 (720/720 giờ ok): ổn định, ngày thường ~5,4–5,9 triệu sự kiện, cuối tuần ~4,6–4,8 triệu, nên điểm sụt 23/05 là thật chứ không phải do mùa vụ. Còn lệch nhỏ chưa tìm hiểu: star 01–02/05 thấp (~159k vs ~210k), push 10/04 cao bất thường (4,37 triệu).
Giảm dung lượng (đã đo trên 24 giờ 15/04/2025): bỏ 4 loại sự kiện ít dùng chỉ tiết kiệm 2%, không làm. Đổi id sang BIGINT + sắp theo repo + zstd mức 9 tiết kiệm 29% (102 → 73 MB/24 giờ), đã áp dụng trong `ingest.py` và ghi lại 1.464 file cũ bằng `scripts/recompress.py` (5,55 → 4,00 GB, số dòng giữ nguyên 312.944.716). Ngoại suy 29 tháng ≈ 51 GB (chưa đo).
Lưu ý thiết kế: `raw_events` là VIEW đọc Parquet (bản đầu tạo TABLE làm DuckDB nặng 9,3 GB, gấp ~3,6 lần Parquet, đã sửa). Chưa xem trước 04/2025.
- Nạp Parquet vào DuckDB (`data/radar.duckdb`) bảng `raw_events`.
- Vẽ số sự kiện theo giờ/ngày theo loại: xác nhận mốc dữ liệu còn đáng tin.
- Quyết: chạy đủ 01/2023 → 05/2025 hay chỉnh mốc.

## Phase 3: Lớp kiểm tra chất lượng dữ liệu  [~] (bản đầu chạy được: `scripts/dq_hourly.py`)
Kết quả trên 04–05/2025 (1.464 giờ): 845 ok, 115 low, 504 no_baseline (3 tuần đầu). Bắt đúng điểm sụt 23/05 (giờ đầu bị cờ: 17h UTC, ratio 0,655) và bắt một giờ file ok nhưng thiếu nội dung: 2025-05-08 01:00 UTC chỉ 27.469 sự kiện (12% bình thường), file nặng 11,6 MB so với ~105 MB. Nguyên nhân chưa kiểm tra.
Còn thiếu: (1) baseline cố định từ giai đoạn đã biết ổn, vì baseline trượt "thích nghi" với mức sụt kéo dài (31/05 chỉ còn 4 giờ bị cờ); (2) chưa thử ngưỡng 0,70/1,50 trên tháng khác; (3) `ingest.py` nên cảnh báo khi dung lượng file nén thấp bất thường.
Nội dung dự kiến ban đầu:
- Bảng `dq_hourly` từ manifest: baseline (trung vị cùng giờ trong tuần), cờ giờ bất thường (ví dụ < 50% baseline), giờ thiếu file.
- Chạy trên các tháng 2025–2026 để tái hiện phát hiện "mất ~90% star".
- Đầu ra: biểu đồ + đoạn kể cho CV, có số đo thật.

## Phase 4: Thu thập toàn bộ 01/2023 → 05/2025  [~] (tạm dừng)
Hiện có: 03/2025, 04/2025, 05/2025 đủ; 01/2025 + 02/2025 dở (960/1.416 giờ, tải đến 2025-02-09; dừng 20/10/2026 vì mạng chậm bất thường ~2 phút/giờ, nguyên nhân chưa biết, và để nhường mạng cho dự án khác). Chạy lại `ingest.py 2025-01-01 2025-02-28 2` sẽ tiếp tục, tự bỏ qua giờ đã xong. Chưa tải 2023–2024.
- Chạy `ingest.py` theo tháng (chạy đêm, theo dõi ổ đĩa). Chốt cách tải (máy nhà hay BigQuery) dựa số đo Phase 1.

## Phase 5: Xác định repo AI  [~] (thăm dò xong: `scripts/ai_repos_probe.py`)
**ĐO ĐỘ PHỦ (20/10/2026, `scripts/ai_repos_recall.py`, danh sách chọn tay `scripts/ai_reference_repos.txt`, 78 repo): 19/76 = 25%** (2 repo không có trong dữ liệu, không tính). Bộ lọc theo tên sót 57/76 repo AI nổi tiếng: (a) từ khóa ở tên tổ chức, không ở tên repo (modelcontextprotocol/servers 33K star, openai/codex, openai/whisper, huggingface/trl, huggingface/peft); (b) tên ghép không tách được từ (autogpt, comfyui, ragflow, openhands, smolagents, litellm, unsloth, vllm, sglang, mlx, nanogpt); (c) thư viện AI nổi tiếng không có từ khóa (pytorch, tensorflow, scikit-learn, keras, jax, ray, mlflow, gradio, ultralytics). Giới hạn của phép đo: danh sách do tác giả chọn từ trí nhớ, thiên về repo nổi tiếng. Hệ quả: mọi kết quả Phase 7 chỉ đúng cho nhóm repo có tên khớp từ khóa; đã cập nhật README, bài viết, dashboard. Sửa nguyên nhân (định nghĩa tập repo AI không chỉ dựa vào tên) là việc kế tiếp.
Kết quả (cửa sổ 01/03–22/05/2025, khớp từ khóa nguyên từ trong tên repo): 650.472 repo khớp, 8.068 repo ≥10 star; top 25 theo star gần như toàn AI thật. Mẫu ngẫu nhiên 40 repo ≥10 star, mình xem tên bằng mắt: 38/40 là AI, 2 đáng ngờ → precision thô ~95% (sai số ±7 điểm %, chưa mở repo kiểm). Danh sách ứng viên lưu ở `data/derived/ai_repo_candidates.parquet`.
Chưa đo: recall (repo AI không có từ khóa, ví dụ vllm/pytorch/ComfyUI có thể bị sót, chưa kiểm), precision phần đuôi <10 star.
Bài học: script thăm dò đầu tiên chiếm 12 GB RAM + 16 GB file tạm do tạo bảng chứa 440 triệu dòng; bản nhẹ giới hạn RAM 4 GB, 2 luồng, file tạm 5 GB, lọc theo tên trước khi gom nhóm.
- Từ khóa tên (đã có) + danh sách tay các repo lớn + (tùy chọn) topic qua GitHub API. Đo precision bằng mẫu 100 repo kiểm tay.

## Phase 6: dbt (raw → staging → marts) + tests  [x] (bản đầu, 20/10/2026)
Thư mục `dbt_radar/` (dbt-core 1.12.6, dbt-duckdb 1.11.0, DuckDB giữ 1.5.6). Chạy từ trong `dbt_radar/`: `..\.venv\Scripts\dbt.exe build --profiles-dir . --no-version-check` (đặt `DBT_SEND_ANONYMOUS_USAGE_STATS=False`).
Mô hình: `stg_events` (view trên Parquet, bỏ dòng thiếu id/ts) → `int_ai_repo_candidates` → `fct_star_daily`, `fct_star_spike_days`, `fct_contributor_week`, `fct_cohort_retention`; `fct_hourly_quality` (lớp chất lượng). Ngưỡng và cửa sổ là biến trong `dbt_project.yml`. Bảng nằm trong `data/radar_dbt.duckdb`.
Kết quả build lần đầu: 7 mô hình, 25 test: 23 đạt, 2 cảnh báo có chủ đích, 0 lỗi (~2,5 phút). Cảnh báo 1: `unique_stg_events_id` tìm thấy 24 id trùng trong tuần mẫu 01–07/05/2025 (chỉ kiểm 1 tuần vì kiểm toàn bộ cần hash hơn 300M id). Cảnh báo 2: 2 giờ bất thường trong cửa sổ tin cậy (2025-04-13 01:00 ratio 0,606; 2025-05-08 01:00 ratio 0,121).
Đối chiếu với kết quả Python trước đó: KHỚP chính xác (8.068 repo; 444 ngày đột biến ở 153 repo; 91.655 dòng người-tuần, 52.417 người; cờ chất lượng 1.588 ok / 116 low / 504 no_baseline; retention gộp 16,9% / 10,4% / 7,6% / 5,8%).
Điều phối một lệnh: `scripts/run_pipeline.py` (preflight kiểm tra file Parquet và ≥20 GB ổ trống → tùy chọn `--ingest <từ> <đến>` rồi kiểm manifest xem có giờ lỗi → `dbt build` → tóm tắt từ `run_results.json`). Dừng ngay khi lỗi (mã thoát ≠ 0), ghi log có dấu thời gian vào `logs/pipeline.log`. Mặc định không tải dữ liệu.
Đã thử: (1) chạy từ đầu sau khi xóa `radar_dbt.duckdb` và `target/`: 166 giây, mã thoát 0, 7 mô hình + 23 test đạt + 2 cảnh báo, số liệu khớp Python từng con số; (2) đường lỗi: ngày không hợp lệ ở bước tải → dừng, mã thoát 1, dbt không chạy.
Chưa thử: đường lỗi khi một test dbt ở mức error; tải thật qua pipeline (mạng chậm); chạy trên máy khác.
Hạn chế: chưa có tài liệu dbt docs, chưa có CI; test duy nhất kiểm id trùng chỉ chạy trên 1 tuần; `fct_hourly_quality` chỉ phủ 01/03–31/05/2025 (01–02/2025 tải dở nên bị loại); danh sách repo AI vẫn dựa trên tên.
- `dbt-duckdb`; staging làm sạch; marts: `fct_repo_daily`, `dim_repo`, `fct_contributor_cohort`.
- Tests: not null, unique, accepted values, test số sự kiện theo giờ.

## Phase 7: Phân tích insight  [~] (câu 1 thử xong bản đầu: `scripts/star_anomalies.py`)
Câu 1 (star bất thường), 01/03–22/05/2025, ~8.000 repo AI ≥10 star: 823 ngày đột biến ở 303 repo (≥50 star/ngày và ≥5× trung vị 14 ngày trước). Tỉ lệ tài khoản "mỏng" (≤3 sự kiện trong cửa sổ): chung 12%; trung vị ngày đột biến 7,1% vs 8,4% ngày thường cùng repo → đột biến nhìn chung không đến từ tài khoản mỏng hơn (khớp với lan truyền/ra mắt thật). Vài repo nghi vấn cần xem thêm (chưa kết luận): Repo X 11–15/04 (85–93% mỏng vs 30%), chatgpt-helper-tech/*, GalaxyXieyu/didatodolist-mcp.
v2 (đã sửa): chỉ xét ngày đột biến khi repo có ≥7 ngày có star trong 14 ngày trước (loại ngày ra mắt có baseline 0); tỉ lệ mỏng của ngày thường chỉ dùng khi có ≥30 lượt star; thử 9 bộ ngưỡng (≥30/50/100 star/ngày × 3/5/10× baseline). Kết quả: 190–806 ngày đột biến tùy ngưỡng; ở cả 9 bộ, tỉ lệ mỏng ngày đột biến thấp hơn ngày thường (~7–8,5% vs ~8–11%) → đột biến nhìn chung đến từ người dùng thật. Chỉ 1 repo bị cờ ở 9/9 bộ: Repo X (11, 12, 14, 15/04/2025: 85–93% mỏng vs 30% thường; mức thường 30% cũng cao hơn mức chung 12%, chưa rõ vì sao). Các repo bị cờ ở v1 (chatgpt-helper-tech, didatodolist-mcp) biến mất khi đòi mẫu ≥30 → là nhiễu mẫu nhỏ.
Chưa biết: "mỏng" ≠ giả (người chỉ star vẫn là người thật); chưa có bằng chứng phân biệt chiến dịch quảng bá thật với star mua. Chưa kiểm tra tuổi tài khoản. Ngưỡng THIN_MAX=3 chưa thử độ nhạy.
Kiểm chứng tuổi tài khoản (`scripts/check_account_age.py`, GitHub API công khai, 50 lần gọi): Repo X, mẫu 25 người star ngày 14–15/04/2025 vs 25 người star ngày thường của cùng repo. Ngày đột biến: 21 tài khoản dùng được, tuổi trung vị lúc star 0 ngày, 20/21 tạo <30 ngày trước, 19/21 chưa có repo, followers 0, 4 bị xóa (404). Ngày thường: 23 dùng được, tuổi trung vị 442 ngày, 0/23 <30 ngày, 1/23 chưa có repo, trung vị 14 repo, 2 bị xóa. → Star ngày đột biến không giống người dùng tự nhiên.
Giới hạn: mẫu nhỏ, một repo; chưa đối chứng trên repo lan truyền thật (nếu repo thật cũng có nhiều tài khoản mới tạo ngày đó thì phép kiểm không phân biệt được); không cho biết ai đứng sau, không gán lỗi cho chủ repo. Dữ liệu mẫu: `data/derived/account_sample_flagged_repo.jsonl`.
Đối chứng (mỗi repo 25 người, cùng cách lấy mẫu): github/github-mcp-server 07–08/04: 22 dùng được, tuổi trung vị 3.820 ngày, 0/22 <30 ngày, trung vị 30 repo, 1/22 chưa có repo. x1xhlol/system-prompts… 19–22/04: 24 dùng được, tuổi trung vị 2.050 ngày, 2/24 <30 ngày, trung vị 16 repo, 2/24 chưa có repo. → hai đợt lan truyền thật có tài khoản lâu năm, còn Repo X 14–15/04 có 20/21 tạo <30 ngày: phép kiểm phân biệt được. Giới hạn: mẫu 21–24, 3 repo; hai repo đối chứng do mình chọn vì tin là lan truyền thật, chưa kiểm độc lập. Dữ liệu: `data/derived/account_sample_<owner>__<repo>.jsonl`.
Kết quả lưu: `data/derived/star_spikes.parquet` (cấu hình chính: ≥50/ngày, 5×).

Câu 2 (cohort retention, `scripts/cohort_retention.py`, 01/03–16/05/2025 = 11 khối 7 ngày, ~8.000 repo AI ≥10 star, loại bot, chỉ tính push/PR/issue/comment/review): 52.417 người đóng góp, ~8–9 nghìn người hoạt động mỗi tuần (khá phẳng). Người mới = lần đầu thấy từ khối 3 trở đi (khối 1–2 làm khởi động). Pooled (trọng số theo cohort): 16,9% hoạt động lại sau 1 tuần, 10,4% sau 2, 7,6% sau 4, 5,8% sau 8 (phẳng dần ~6–7%). Theo hoạt động đầu tiên: push/PR 29,8% sau 1 tuần → ~13–15% sau 6–8 tuần; chỉ issue/comment/review 12,5% → ~3–4%. Cohort muộn có retention tuần đầu thấp hơn (19,1% → 13,7% từ cohort 2 → 8).
Giới hạn quan trọng: (1) cohort đầu cao hơn có thể là ảo do không có dữ liệu trước 01/03: người cũ ngủ 2 tuần đầu bị tính là mới, và họ hay quay lại → xu hướng giảm giữa các cohort KHÔNG phải bằng chứng hệ sinh thái yếu đi; (2) "còn hoạt động" chỉ tính trên tập repo ứng viên (≥10 star trong chính cửa sổ này, thiên về repo nổi), người chuyển sang repo nhỏ/ngoài AI bị tính là rời bỏ; (3) chưa có mốc so sánh ngoài (không biết 17% là cao hay thấp); (4) cohort 8–9 quan sát ngắn; (5) giờ 08/05 01:00 UTC thiếu dữ liệu nằm trong khối 9. Lỗi hiển thị `cohort_size` (max thay vì sum) đã sửa.
Kết quả lưu: `data/derived/cohort_retention.parquet`.
- Tăng trưởng thật vs star bất thường; cohort retention; dự án chết dần; làn sóng LangChain → agent → MCP.
- Trước đó xem OSS Insight để tránh trùng (README ghi chưa kiểm tra).

## Phase 8: Trình bày + đẩy GitHub  [x] (dashboard + bài viết `docs/bai-viet.md`; đăng GitHub 20/10/2026, xem cuối mục)
Đã làm: `docs/index.html` (351 KB, trang HTML tĩnh tự chứa, tự vẽ SVG, không cần cài gì và không cần máy chủ, đăng được bằng GitHub Pages), tạo bởi `scripts/build_dashboard.py` + `scripts/dashboard_template.html` từ các bảng dbt `fct_*` và các file mẫu tài khoản. Chọn HTML tĩnh thay vì Streamlit vì mạng máy rất chậm (~16 kB/s khi cài dbt) và Streamlit kéo nhiều gói nặng.
Nội dung: con số chính (−35% sự kiện từ 23/05/2025), 4 thẻ số, 4 biểu đồ (sự kiện mỗi giờ + vùng không đáng tin; ngày star đột biến thang log; % tài khoản <30 ngày; đường giữ chân), mỗi biểu đồ có tooltip + điều hướng bàn phím + bảng số liệu, mục "Giới hạn". Hỗ trợ chế độ sáng/tối. Bảng màu 3 slot đã chạy `validate_palette.js`: đạt mọi kiểm tra ở cả hai chế độ (xanh ngọc ở chế độ sáng 2,74:1 → có nhãn trực tiếp và bảng số liệu bù lại).
Đã kiểm bằng ảnh chụp: chế độ tối + sáng ở 1200 px, và 390 px (nhúng iframe, vì Edge headless có bề rộng tối thiểu ~500 px). Đã sửa 3 lỗi tìm thấy khi xem ảnh: tô cam sai (theo repo thay vì theo ngày bị gắn cờ, hiện chỉ 4 ngày 11/12/14/15-04), nhãn tràn mép, nhãn bị cắt cụt. Còn nhỏ: nhãn repo lớn nhất chồng nhẹ lên vài chấm ở màn hình hẹp.
Tên repo bị gắn cờ ẨN mặc định ("Repo X"); `--show-names` để hiện. Quyết định này là của tác giả (mẫu nhỏ, repo của công ty thật).
Chưa làm: chưa thử trên trình duyệt khác ngoài Edge, `build_dashboard.py` chưa nằm trong `run_pipeline.py` vì nó cần `data/derived/star_spikes.parquet` và các file mẫu tài khoản do script khác tạo.
- Dashboard (Evidence.dev hoặc Streamlit), README đẹp, bài viết insight. Chỉ commit/đẩy khi bạn yêu cầu.

## Phase 9 (sau cùng, tùy chọn): hằng ngày + hỏi bằng tiếng Việt  [ ]
- Nguồn mới (OpenDigger/GitHub API, chưa thử), GitHub Actions, LLM viết SQL.
