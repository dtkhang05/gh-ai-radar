# Nhật ký các giai đoạn

Tài liệu này ghi từng giai đoạn của dự án: làm gì, đo được gì, còn thiếu gì. Mọi số liệu là số đo thật trên dữ liệu đã tải (01/03 → 31/05/2025), trừ chỗ ghi "ước tính". Kết quả tổng hợp nằm trong [README.md](README.md).

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| 1 | Tải dữ liệu thử 1 tháng | Xong |
| 2 | Kho DuckDB và kiểm tra mốc dữ liệu | Xong |
| 3 | Lớp kiểm tra chất lượng dữ liệu | Xong bản đầu |
| 4 | Tải thêm dữ liệu lịch sử | Tạm dừng |
| 5 | Xác định repo AI | Xong bản đầu, độ phủ thấp |
| 6 | dbt và kiểm thử | Xong |
| 7 | Phân tích | Xong 2 câu hỏi |
| 8 | Dashboard, bài viết, đăng GitHub | Xong |
| 9 | Mở rộng | Chưa làm |

## 1. Tải dữ liệu thử
**Mục tiêu:** có pipeline tải → lọc → Parquet → xóa file thô, và đo thời gian, dung lượng thật.

- `scripts/ingest.py` xử lý từng giờ: tải file, giữ 5 cột (id, type, ts, actor, repo), ghi `data/parquet/YYYY-MM-DD-H.parquet`, xóa file thô. Chạy lại được (bỏ qua giờ đã xong), thử lại khi lỗi mạng.
- Mỗi giờ ghi một dòng vào `data/manifest.jsonl`: số byte, số sự kiện theo loại, thời gian xử lý, trạng thái.
- **Đo trên 05/2025:** 744/744 giờ thành công, 150,5 triệu sự kiện, Parquet 2.569 MB (~3,45 MB/giờ), ~10 giây/giờ với 4 luồng.
- **Bài học:** GH Archive trả lỗi 403 nếu thiếu header User-Agent.

## 2. Kho DuckDB và kiểm tra mốc dữ liệu
**Mục tiêu:** xem dữ liệu 05/2025 có đáng tin không.

- Đủ 24 file mỗi ngày, nhưng số sự kiện theo giờ **sụt khoảng 35% đột ngột từ khoảng 16–17h UTC ngày 23/05/2025** (từ ~250 nghìn xuống ~150 nghìn mỗi giờ) và không hồi lại. Tải thêm 04/2025 để loại trừ yếu tố mùa vụ: ngày thường ổn định ~5,4–5,9 triệu sự kiện. Nguyên nhân chưa kiểm tra.
- **Quyết định:** mốc cuối của mọi phân tích là 22/05/2025.
- **Giảm dung lượng** (đo trên 24 giờ ngày 15/04/2025): bỏ 4 loại sự kiện ít dùng chỉ tiết kiệm 2%, nên không làm. Đổi id sang BIGINT, sắp theo repo, nén zstd mức 9 tiết kiệm 29% (102 → 73 MB), đã áp dụng cho toàn bộ file (5,55 → 4,00 GB, số dòng giữ nguyên 312.944.716).
- **Thiết kế:** `raw_events` là VIEW đọc thẳng Parquet. Bản đầu sao chép dữ liệu vào bảng làm file DuckDB nặng 9,3 GB, gấp ~3,6 lần Parquet.
- **Giới hạn tài nguyên:** một truy vấn thăm dò từng dùng 12 GB RAM và 16 GB file tạm; mọi script giờ đặt giới hạn RAM, số luồng và dung lượng file tạm.

## 3. Lớp kiểm tra chất lượng dữ liệu
**Cách làm** (`scripts/dq_hourly.py`, sau đó là mô hình dbt `fct_hourly_quality`): so số sự kiện mỗi giờ với trung vị của cùng thứ, cùng giờ trong 4 tuần trước. Cờ `low` nếu dưới 0,70, `high` nếu trên 1,50, `no_baseline` nếu có dưới 3 giá trị trước đó.

- **Kết quả** (2.208 giờ, 01/03 → 31/05/2025): 1.588 ok, 116 low, 504 no_baseline.
- Bắt đúng điểm sụt 23/05 (giờ đầu bị cờ: 17h UTC, tỉ lệ 0,655).
- Bắt một giờ mà file tải thành công nhưng thiếu nội dung: **08/05/2025 01:00 UTC chỉ có 27.469 sự kiện** (12% mức thường), file 11,6 MB so với ~105 MB. Script tải chỉ kiểm tra file có tải được, không kiểm tra nội dung.
- **Còn thiếu:** đường cơ sở cố định lấy từ giai đoạn đã biết ổn (đường cơ sở trượt thích nghi với đợt sụt kéo dài nên chỉ gắn cờ trong vài tuần đầu); chưa thử ngưỡng 0,70/1,50 trên tháng khác; `ingest.py` chưa cảnh báo khi file nén nhỏ bất thường.

## 4. Tải thêm dữ liệu lịch sử
- Hiện có đủ 03, 04, 05/2025. Tháng 01–02/2025 tải dở (960/1.416 giờ, đến 09/02/2025), tạm dừng vì mạng chậm (~2 phút/giờ).
- Chạy lại `ingest.py 2025-01-01 2025-02-28 2` sẽ tiếp tục từ chỗ dừng. Dữ liệu 2023–2024 chưa tải.
- Ước tính (chưa đo): ~51 GB Parquet cho 29 tháng.

## 5. Xác định repo AI
**Cách làm** (`scripts/ai_repos_probe.py`, macro dbt `ai_name_pattern`): khớp từ khóa nguyên từ trong tên repo, giữ repo có ≥10 star trong cửa sổ phân tích.

- **Kết quả:** 650.472 repo khớp, 8.068 repo ≥10 star.
- **Độ chính xác (precision) ~95%:** mẫu ngẫu nhiên 40 repo, tác giả xem tên bằng mắt, 38/40 là AI. Sai số lớn (±7 điểm %), chưa mở repo để kiểm.
- **Độ phủ (recall) 25%:** `scripts/ai_repos_recall.py` đo trên 76 repo AI nổi tiếng do tác giả chọn tay (`scripts/ai_reference_repos.txt`; 2 repo không có trong dữ liệu): bắt được 19/76. Bộ lọc bỏ sót ba nhóm: từ khóa nằm ở tên tổ chức (`modelcontextprotocol/servers`, `openai/codex`), tên ghép (`vllm`, `comfyui`, `autogpt`), thư viện nổi tiếng không có từ khóa (`pytorch`, `tensorflow`). Danh sách chọn từ trí nhớ nên thiên về repo nổi tiếng.
- **Hệ quả:** mọi kết quả ở giai đoạn 7 chỉ đúng cho nhóm repo khớp từ khóa. README, bài viết và dashboard đã ghi rõ.
- **Việc kế tiếp:** định nghĩa tập repo AI bằng topic và mô tả repo qua GitHub API, kết hợp với bộ lọc tên, rồi đo lại độ phủ bằng danh sách mới.

## 6. dbt và kiểm thử
**Cấu trúc** (`dbt_radar/`, dbt-core 1.12.6, dbt-duckdb 1.11.0, DuckDB 1.5.6): `stg_events` (view trên Parquet) → `int_ai_repo_candidates` → `fct_star_daily`, `fct_star_spike_days`, `fct_contributor_week`, `fct_cohort_retention`, và `fct_hourly_quality`. Ngưỡng và cửa sổ thời gian là biến trong `dbt_project.yml`.

- **Build:** 7 mô hình, 25 test: 23 đạt, 2 cảnh báo có chủ đích, 0 lỗi, ~166 giây.
  - Cảnh báo 1: 24 id trùng trong tuần mẫu 01–07/05/2025 (chỉ kiểm 1 tuần vì kiểm toàn bộ cần băm hơn 300 triệu id).
  - Cảnh báo 2: 2 giờ bất thường trong cửa sổ tin cậy (13/04 01:00, tỉ lệ 0,606; 08/05 01:00, tỉ lệ 0,121).
- **Đối chiếu với các script Python viết trước đó:** khớp từng con số (8.068 repo; 444 ngày đột biến ở 153 repo; 91.655 dòng người-tuần, 52.417 người; cờ chất lượng 1.588/116/504).
- **Điều phối một lệnh** (`scripts/run_pipeline.py`): kiểm tra file Parquet và ≥20 GB ổ trống → tùy chọn tải (`--ingest <từ> <đến>`, rồi kiểm manifest xem có giờ lỗi) → `dbt build` → tóm tắt. Dừng ngay khi lỗi, ghi log có dấu thời gian vào `logs/pipeline.log`.
- **Đã thử:** chạy từ đầu sau khi xóa kho và `target/` (mã thoát 0); đường lỗi khi ngày không hợp lệ (dừng, mã thoát 1, dbt không chạy); cài đặt và chạy trên bản clone sạch.
- **Chưa thử:** đường lỗi khi một test dbt ở mức error; dựng lại toàn bộ từ đầu trên máy khác; Linux/macOS.
- **Còn thiếu:** tài liệu `dbt docs`, CI chạy test tự động.

## 7. Phân tích
Phạm vi: 01/03 → 22/05/2025, nhóm repo AI khớp từ khóa (xem giai đoạn 5).

### Câu 1: star tăng đột biến có phải người thật?
**Định nghĩa** (`scripts/star_anomalies.py`, mô hình `fct_star_spike_days`): ngày đột biến là ngày có ≥50 star và ≥5 lần trung vị 14 ngày trước, với điều kiện repo có ≥7 ngày có star trong 14 ngày đó (loại ngày ra mắt có mức thường bằng 0; lỗi này từng làm bản đầu báo 823 ngày). Tài khoản "mỏng" là tài khoản có ≤3 sự kiện trong cửa sổ.

- **Kết quả:** 444 ngày đột biến ở 153 repo. Tỉ lệ mỏng trung bình ở ngày đột biến là 7,6%, thấp hơn ngày thường (9,2%): phần lớn đột biến đến từ ra mắt hoặc được chia sẻ rộng. Kết quả giữ nguyên ở cả 9 bộ ngưỡng thử (≥30/50/100 star × 3/5/10 lần).
- **Một repo lệch hẳn** (ẩn tên, gọi là Repo X; bị gắn cờ ở 9/9 bộ ngưỡng): ngày 11, 12, 14, 15/04/2025 có 85–93% người star là tài khoản mỏng, so với 30% ngày thường của chính nó.
- **Kiểm tra độc lập bằng tuổi tài khoản** (`scripts/check_account_age.py`, GitHub API công khai, mẫu ~25 người mỗi nhóm):

| Nhóm | Đọc được | Tuổi trung vị | Tạo <30 ngày | Chưa có repo |
|---|---|---|---|---|
| Repo X, ngày đột biến 14–15/04 | 21 | 0 ngày | 20/21 | 19/21 |
| Repo X, ngày thường | 23 | 442 ngày | 0/23 | 1/23 |
| github-mcp-server, ra mắt 07–08/04 (đối chứng) | 22 | 3.820 ngày | 0/22 | 1/22 |
| system-prompts-and-models-of-ai-tools, lan truyền 19–22/04 (đối chứng) | 24 | 2.050 ngày | 2/24 | 2/24 |

- **Giới hạn:** "mỏng" không có nghĩa là giả. Mẫu nhỏ (21–24 người mỗi nhóm, 3 repo). Hai repo đối chứng do tác giả chọn vì tin là lan truyền thật. Kết quả cho biết các tài khoản đó là tài khoản dùng một lần, không cho biết ai đứng sau, nên không gán lỗi cho chủ repo. Ngưỡng "mỏng ≤3 sự kiện" chưa thử độ nhạy.

### Câu 2: người đóng góp mới có ở lại không?
**Định nghĩa** (`scripts/cohort_retention.py`, mô hình `fct_cohort_retention`): chia 01/03 → 16/05/2025 thành 11 khối 7 ngày; người mới là người lần đầu xuất hiện từ khối 3 (khối 1–2 làm giai đoạn khởi động); chỉ tính push, PR, issue, bình luận, review; loại bot.

- **Kết quả** (52.417 người, trung bình có trọng số theo cohort): 16,9% hoạt động lại sau 1 tuần, 10,4% sau 2, 7,6% sau 4, 5,8% sau 8.
- **Theo hoạt động đầu tiên:** bắt đầu bằng push/PR giữ lại 29,8% sau 1 tuần và 12,9% sau 8 tuần; chỉ issue/bình luận/review là 12,5% và 3,3%.
- **Giới hạn:** (1) không có dữ liệu trước 01/03 nên người cũ vắng 2 tuần đầu bị tính là người mới, làm các cohort đầu cao hơn thực tế, vì vậy xu hướng giảm giữa các cohort không có nghĩa hệ sinh thái yếu đi; (2) "còn hoạt động" chỉ tính trong tập repo đã lọc; (3) chưa có mốc so sánh bên ngoài; (4) cohort muộn quan sát ngắn; (5) giờ 08/05 01:00 UTC thiếu dữ liệu nằm trong khối 9.

### Chưa làm
Dự án chết dần; làn sóng LangChain → agent → MCP (cần dữ liệu nhiều năm); so với các nguồn tương tự như OSS Insight (chưa kiểm tra).

## 8. Dashboard, bài viết, đăng GitHub
- **Dashboard** `docs/index.html`: trang HTML tĩnh tự chứa, tự vẽ SVG, không cần máy chủ, đăng bằng GitHub Pages. Tạo bởi `scripts/build_dashboard.py` và `scripts/dashboard_template.html` từ các bảng dbt và file mẫu tài khoản. Chọn HTML tĩnh thay vì Streamlit vì Streamlit kéo nhiều gói nặng và mạng máy rất chậm (~16 kB/s khi cài dbt).
- **Nội dung:** con số chính (−35%), 4 thẻ số, 4 biểu đồ có tooltip, điều hướng bàn phím và bảng số liệu, mục giới hạn; hỗ trợ chế độ sáng/tối. Bảng màu 3 slot đạt kiểm tra `validate_palette.js` ở cả hai chế độ (xanh ngọc ở chế độ sáng chỉ đạt tương phản 2,74:1, nên có nhãn trực tiếp và bảng số liệu bù lại).
- **Đã kiểm bằng ảnh chụp:** chế độ sáng và tối ở 1.100–1.200 px, và 390 px. Các lỗi tìm thấy khi xem ảnh đã sửa: tô cam sai ngày, nhãn tràn mép, nhãn bị cắt.
- **Tên repo bị gắn cờ được ẩn mặc định** ("Repo X"); `--show-names` để hiện. Lý do: mẫu nhỏ và là repo của một tổ chức thật.
- **Bài viết:** `docs/bai-viet.md`.
- **Đăng:** repo công khai `dtkhang05/gh-ai-radar`, giấy phép MIT, trang tại `https://dtkhang05.github.io/gh-ai-radar/`.
- **Chưa làm:** thử trên trình duyệt khác ngoài Edge; đưa `build_dashboard.py` vào `run_pipeline.py` (nó cần file do các script phân tích khác tạo).

## 9. Hướng mở rộng
Theo thứ tự nên làm:

1. **Sửa tập repo AI** (giai đoạn 5): thêm topic và mô tả qua GitHub API, đo lại độ phủ; sau đó dựng lại các bảng dbt, dashboard và bài viết.
2. **CI:** GitHub Actions chạy test dbt trên dữ liệu tổng hợp có cài sẵn một đợt sụt và một đợt star đột biến, để chứng minh test bắt được lỗi.
3. **Đường cơ sở cố định** cho lớp chất lượng (giai đoạn 3) và `dbt docs` đăng cùng Pages.
4. **Dữ liệu nhiều năm:** lấy mẫu vài ngày mỗi tháng từ 2023 để xem các làn sóng và dự án chết dần, vì tải đủ 29 tháng quá chậm với mạng hiện tại.
5. **Chạy định kỳ hằng ngày** và nguồn dữ liệu bổ sung (chưa thử).
