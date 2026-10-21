# Nhật ký các giai đoạn

Tài liệu này ghi từng giai đoạn của dự án: làm gì, đo được gì, còn thiếu gì. Mọi số liệu là số đo thật trên dữ liệu đã tải (01/03 → 31/05/2025), trừ chỗ ghi "ước tính". Kết quả tổng hợp nằm trong [README.md](README.md).

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| 1 | Tải dữ liệu thử 1 tháng | Xong |
| 2 | Kho DuckDB và kiểm tra mốc dữ liệu | Xong |
| 3 | Lớp kiểm tra chất lượng dữ liệu | Xong bản đầu |
| 4 | Tải thêm dữ liệu lịch sử | Tạm dừng |
| 5 | Xác định repo AI | Xong (độ phủ 82–89%, độ chính xác ước tính 76–95%) |
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
- **Đường cơ sở cố định** (`fixed_base_events`, `fixed_ratio`, `fixed_flag` trong `fct_hourly_quality`): cùng ngưỡng, nhưng so với trung vị cùng thứ, cùng giờ của 4 tuần đầu (01–28/03, biến `dq_fixed_weeks`), không thích nghi. Lý do: đường cơ sở trượt coi mức mới là bình thường nên chỉ gắn cờ một đợt sụt kéo dài trong vài tuần đầu. Giờ trong 4 tuần tham chiếu có cờ `reference`.
  - **Đo trên dữ liệu thật** (1.536 giờ ngoài tuần tham chiếu): trong cửa sổ tin cậy (đến 22/05) cờ cố định gắn đúng hai giờ đã biết (13/04 01:00, 08/05 01:00), không thêm cảnh báo giả. Từ 23/05 (216 giờ): 158 giờ `low` so với 114 của đường trượt (thêm 44 giờ, nằm ở cuối ngày 23/05 và các ngày sau).
  - **Chưa chứng minh trên dữ liệu thật:** dữ liệu chỉ có 8 ngày sau điểm sụt nên chưa đủ dài để đường trượt "quên" mất đợt sụt; sự khác biệt đó chỉ được kiểm chứng bằng dữ liệu tổng hợp (mục 6, kịch bản sụt 5 tuần).
  - **Điểm yếu:** nó không phân biệt lỗi thật với thay đổi mức dài hạn thật (tăng trưởng, mùa vụ). Tỉ lệ trung bình theo tuần đã trôi từ ~0,98 (đầu tháng 4) xuống 0,93–0,96 (tháng 4–5); chưa biết là tăng trưởng thật hay nhiễu, nhưng còn cách ngưỡng 0,70 khá xa.
- **Còn thiếu:** chưa thử ngưỡng 0,70/1,50 trên tháng khác; `ingest.py` chưa cảnh báo khi file nén nhỏ bất thường.

## 4. Tải thêm dữ liệu lịch sử
- Hiện có đủ 03, 04, 05/2025. Tháng 01–02/2025 tải dở (960/1.416 giờ, đến 09/02/2025), tạm dừng vì mạng chậm (~2 phút/giờ).
- Chạy lại `ingest.py 2025-01-01 2025-02-28 2` sẽ tiếp tục từ chỗ dừng. Dữ liệu 2023–2024 chưa tải.
- Ước tính (chưa đo): ~51 GB Parquet cho 29 tháng.

## 5. Xác định repo AI
Làm hai vòng. Vòng 2 sửa điểm yếu mà vòng 1 đo ra.

### Vòng 1: lọc theo tên repo (`scripts/ai_repos_probe.py`)
Khớp từ khóa nguyên từ trong tên repo (`llm`, `gpt`, `agent`, `mcp`, ...), giữ repo có ≥10 star trong cửa sổ phân tích.

- **Kết quả:** 650.472 repo khớp, 8.068 repo ≥10 star.
- **Độ chính xác ~95%:** mẫu ngẫu nhiên 40 repo, tác giả xem tên bằng mắt, 38/40 là AI. Sai số lớn (±7 điểm %), chưa mở repo để kiểm.
- **Độ phủ 25%** (`scripts/ai_repos_recall.py`, danh sách 1 `scripts/ai_reference_repos.txt`: 76 repo AI nổi tiếng chọn tay đang có trong dữ liệu): bắt được 19/76. Bộ lọc sót ba nhóm: từ khóa ở tên tổ chức (`modelcontextprotocol/servers`, `openai/codex`), tên ghép (`vllm`, `comfyui`, `autogpt`), thư viện nổi tiếng không có từ khóa (`pytorch`, `tensorflow`).
- **Bài học:** script thăm dò đầu tiên chiếm 12 GB RAM và 16 GB file tạm vì tạo bảng 440 triệu dòng; bản nhẹ giới hạn RAM, luồng, file tạm và lọc theo tên trước khi gom nhóm.

### Vòng 2: thêm topic và mô tả repo (20/10/2026)
**Cách làm:**
1. `scripts/top_repos_by_stars.py`: lấy 20.000 repo nhiều star nhất trong 12 tuần, bất kể tên (ngưỡng thấp nhất 98 star; có 177.129 repo ≥10 star và 19.704 repo ≥100 star).
2. `scripts/fetch_repo_metadata.py`: tra mô tả, topic, ngôn ngữ qua GitHub GraphQL API bằng đăng nhập `gh`, 100 repo mỗi lần gọi (200 lượt gọi, mỗi lượt tốn 1 trong 5.000 điểm mỗi giờ, ~18 giây mỗi lượt, tự tiếp tục khi bị ngắt). 17.598 repo tra được; 2.402 không tra được (đổi tên, xóa, riêng tư).
3. `scripts/ai_repos_classify.py`: một repo là AI nếu tên khớp (như vòng 1), hoặc topic nằm trong một danh sách cố định (`llm`, `machine-learning`, `mcp`, `pytorch`, ...), hoặc mô tả khớp một mẫu từ khóa. Danh sách và mẫu được chốt trước khi chạy danh sách 2. Kết quả lưu ở `data/derived/ai_repo_universe.parquet`.
4. Mô hình dbt `int_ai_repo_candidates` đọc file này; ngưỡng `min_stars` đổi từ 10 lên 100 cho khớp phạm vi của bước 1.

**Kết quả** (trong 19.704 repo ≥100 star, 4.033 được xếp là AI: 1.239 theo tên, 2.759 theo topic, 2.497 theo mô tả, 2.794 do metadata thêm vào):

| Danh sách tham chiếu | Chỉ tên | Chỉ topic | Chỉ mô tả | Bất kỳ tín hiệu |
|---|---|---|---|---|
| 1 (76 repo trong nhóm xét, dùng để nhìn ra các nhóm bị sót) | 25% | 66% | 66% | **82%** (62/76) |
| 2 (71 repo, viết trước khi chạy bộ phân loại, `scripts/ai_reference_repos_2.txt`) | 20% | 70% | 66% | **89%** (63/71) |

Độ phủ đo lại end-to-end trên bảng dbt bằng `ai_repos_recall.py` cho cùng 82% và 89%. Repo còn sót có `jax`, `triton`, `mlx`, `tinygrad`, `segment-anything`, `faiss`, `pgvector`.

**Độ chính xác của phần thêm** (2.794 repo chỉ khớp theo topic/mô tả): mẫu 50 repo, tác giả xem tên và mô tả: 38 đúng, 7 ranh giới (ví dụ `opencv`, `umap`, `bm25s`), 5 sai (ví dụ repo chỉ có "AI" trong mô tả, topic `ai` dùng cho AI trong trò chơi) → 76% nếu đếm chặt, 86% nếu tính cả ranh giới. Ước tính cho cả tập: ~85% (gộp 95% của phần theo tên và 76–86% của phần thêm, theo tỉ lệ 1.239 : 2.794; đây là phép tính từ hai mẫu nhỏ, không phải số đo).

**Giới hạn:** hai danh sách do tác giả chọn từ trí nhớ nên thiên về repo nổi tiếng; chỉ xét repo ≥100 star (repo ít star hơn bị bỏ); topic và mô tả là của năm 2026, không phải 03–05/2025; 12% repo không tra được chỉ khớp được theo tên; mẫu độ chính xác nhỏ, một người đánh giá; chưa thử ngưỡng nào khác cho danh sách topic và mẫu mô tả.

## 6. dbt và kiểm thử

### Mô hình và kết quả build
- `dbt_radar/` (dbt-core 1.12.6, dbt-duckdb 1.11.0, DuckDB 1.5.6). Luồng: `stg_events` (view trên Parquet) → `int_ai_repo_candidates` → `fct_star_daily`, `fct_star_spike_days`, `fct_contributor_week`, `fct_cohort_retention`, `fct_hourly_quality`. Ngưỡng và cửa sổ là biến trong `dbt_project.yml`.
- Build: 7 mô hình, 28 test: 25 đạt, 3 cảnh báo có chủ đích, 0 lỗi, ~140 giây trong lần chạy gần nhất (đã từng đo ~70 giây; chưa tìm nguyên nhân chênh lệch, có thể do máy bận). Lúc đầu ~166 giây; nhanh hơn nhờ ghép danh sách repo trước khi gom nhóm.
- Cảnh báo 1: 24 id trùng trong tuần mẫu 01–07/05/2025 (chỉ kiểm 1 tuần vì kiểm toàn bộ cần băm >300 triệu id).
- Cảnh báo 2: 2 giờ bất thường trong cửa sổ tin cậy (13/04 01:00 tỉ lệ 0,606; 08/05 01:00 tỉ lệ 0,121).
- Cảnh báo 3: cùng 2 giờ đó theo đường cơ sở cố định (`assert_no_anomalous_hours_vs_fixed_baseline`).
- Khớp script Python ở mọi chỉ số đã so:
  - Vòng 1 (tập theo tên): 8.068 repo; 444 ngày đột biến ở 153 repo; 91.655 dòng người-tuần; cờ chất lượng 1.588 / 116 / 504.
  - Vòng 2 (4.033 repo AI): 1.513 ngày đột biến ở 526 repo; giữ chân 16,7% / 10,2% / 7,9% / 7,2%. Chưa so lại số dòng người-tuần.

### Điều phối, lỗi đã gặp, đã thử
- `scripts/run_pipeline.py`: kiểm tra (có Parquet, ≥20 GB trống) → tải tùy chọn (`--ingest <từ> <đến>`, kiểm manifest có giờ lỗi) → `dbt build` → tóm tắt. Dừng ngay khi lỗi, log có dấu thời gian ở `logs/pipeline.log`.
- Lỗi khi đổi sang tập repo mới:
  - `temp_directory` trong `profiles.yml` gây "Cannot switch temporary directory…" khi một luồng mở kết nối sau khi luồng khác đã dùng đĩa tạm. Sửa: bỏ cài đặt.
  - `int_ai_repo_candidates` gom nhóm mọi repo rồi mới ghép nên tràn file tạm 5 GB. Sửa: ghép trước khi gom nhóm.
- Đã thử: chạy từ đầu sau khi xóa kho và `target/` (mã thoát 0); ngày không hợp lệ ở bước tải (dừng, mã thoát 1); clone sạch.
- Chưa thử: test dbt mức error trên dữ liệu thật; máy khác; Linux/macOS cho pipeline thật.

### Kiểm thử tự động (CI)
- Tệp: `ci/make_synthetic.py`, `ci/check_scenarios.py`, `.github/workflows/ci.yml`. Sinh 49 ngày dữ liệu tổng hợp (~370 nghìn dòng, 40 repo AI và một repo "viral"), chạy chính dự án dbt (`--vars` cho đường dẫn và cửa sổ, `RADAR_DB` cho kho tạm).

| Kịch bản | Lỗi cài sẵn | Kiểm tra |
|---|---|---|
| Sạch | Không | Build thành công, 28 test đạt; không cờ giả (đường trượt: 504 `no_baseline`, 672 `ok`; đường cố định: 672 `reference`, 504 `ok`); không ngày đột biến; giữ chân có người quay lại |
| Lỗi cài sẵn | Một giờ trống; một giờ còn 12%; sụt 35% từ 15/04 16:00; 400 tài khoản star một lần trong một ngày | `assert_no_missing_hours` thất bại; test giờ bất thường cảnh báo; giờ trống `missing`, giờ 12% `low`, cả 80 giờ sụt `low`; không cờ nào ngoài giờ cài sẵn; ngày đột biến duy nhất là ngày cài sẵn; mô hình khác vẫn dựng được |
| Loại sự kiện lạ | Một sự kiện có type lạ | `accepted_values` thất bại; mô hình phía sau bị bỏ qua |
| Sụt kéo dài | Sụt 35% từ 15/03 đến hết dữ liệu (5 tuần), tuần tham chiếu = 2 | Cả 840 giờ sụt `low` theo đường cố định, không cờ nào trước đó; đường trượt chỉ gắn 168/840 giờ (nó thích nghi); test đường cố định cảnh báo |

- Kịch bản 1–3: đã chạy trên GitHub Actions (Ubuntu, Python 3.13, 21/10/2026), đạt 18 kiểm tra. Kịch bản sụt kéo dài và các kiểm tra đường cố định (tổng 27 kiểm tra) mới chạy cục bộ, đạt hết (chưa đo thời gian); **chưa chạy trên GitHub Actions** (chưa đẩy).
- Đã kiểm chứng đột biến: hạ ngưỡng `low` 0,70 → 0,50 (đường trượt) làm kiểm tra đợt sụt 35% đỏ; hạ ngưỡng của đường cố định làm 2 kiểm tra kịch bản sụt kéo dài đỏ (kiểm tra không rỗng).
- Giới hạn: dữ liệu tổng hợp đơn giản (nhiễu ±3%, không chu kỳ dài hơn tuần, không tăng trưởng), nên chứng minh bắt được lỗi cài sẵn, không phải mọi lỗi thật. Chưa có kịch bản cho id trùng, và chưa có kịch bản cho thay đổi mức dài hạn thật (nơi đường cố định sẽ báo nhầm).

### Tài liệu dbt
- `scripts/build_dbt_docs.py` chạy `dbt docs generate --static` rồi chép ra `docs/dbt/index.html` (một file 2,5 MB, đăng cùng GitHub Pages). Mô tả mô hình và cột marts nằm trong `models/marts/schema.yml`.
- Đã kiểm tra: mở bằng Edge thấy trang `fct_hourly_quality` đúng; trang công khai trả về 200.
- Chưa làm: mở trang công khai bằng trình duyệt; mô tả cột `stg_events` ngoài `id`, `type`, `actor`, `repo`; sơ đồ phụ thuộc trong README.

## 7. Phân tích
Phạm vi: 01/03 → 22/05/2025, 4.033 repo AI có từ 100 star (giai đoạn 5, vòng 2). Mỗi câu hỏi có một dòng so với vòng 1 (tập theo tên, 8.068 repo ≥10 star).

### Câu 1: star tăng đột biến có phải người thật?
- Định nghĩa (`scripts/star_anomalies.py`, mô hình `fct_star_spike_days`):
  - Ngày đột biến: ≥50 star và ≥5 lần trung vị 14 ngày trước; repo phải có star ở ≥7 trong 14 ngày đó (không thì ngày ra mắt bị tính nhầm; lỗi này từng làm bản đầu báo 823 ngày).
  - Tài khoản "mỏng": ≤3 sự kiện trong cửa sổ.
- Kết quả chung:
  - 1.513 ngày ở 526 repo (626–2.772 ngày tùy 9 bộ ngưỡng: ≥30/50/100 star × 3/5/10 lần).
  - Tỉ lệ mỏng: ngày đột biến 6,7%, ngày thường 8,2% (cả 9 bộ: 6,3–7,6% so với 7,4–9,0%) → phần lớn đột biến đến từ ra mắt hoặc chia sẻ rộng.
  - Vòng 1: 444 ngày ở 153 repo; mỏng 7,6% so với 9,2%; chỉ một repo gắn cờ 9/9.
- Repo lệch (ẩn tên):
  - Repo X và Repo X2 (cùng tổ chức), gắn cờ 9/9: ngày 11, 12, 14, 15/04/2025 có 85–93% người star mỏng, so với ~30% ngày thường. Repo X2 không khớp từ khóa tên nên vòng 1 không thấy.
  - Repo Y, gắn cờ 6/9: một ngày (25/04/2025), 124 star, 95% mỏng so với 60% ngày thường.
  - Hai repo khác gắn cờ 3/9, không vượt ngưỡng ở cấu hình chính.
- Kiểm tra tuổi tài khoản (`scripts/check_account_age.py`, GitHub API công khai, ~25 người mỗi nhóm):

| Nhóm | Đọc được | Tuổi trung vị | Tạo <30 ngày | Chưa có repo |
|---|---|---|---|---|
| Repo X, đột biến 14–15/04 | 21 | 0 ngày | 20/21 | 19/21 |
| Repo X, ngày thường | 23 | 442 ngày | 0/23 | 1/23 |
| Repo X2, đột biến 14–15/04 | 24 | 0 ngày | 22/24 | 21/24 |
| Repo Y, đột biến 25/04 | 25 | 419 ngày | 2/25 | 2/25 |
| github-mcp-server, ra mắt 07–08/04 (đối chứng) | 22 | 3.820 ngày | 0/22 | 1/22 |
| system-prompts-and-models-of-ai-tools, lan truyền 19–22/04 (đối chứng) | 24 | 2.050 ngày | 2/24 | 2/24 |

- Diễn giải:
  - Repo X2 giống Repo X: tài khoản tạo ngay trong ngày.
  - Repo Y không: tài khoản lâu năm nên tuổi tài khoản không xác nhận "mỏng"; tỉ lệ mỏng ngày thường của nó vốn 60%, có thể chỉ là người dùng ít hoạt động.
- Giới hạn:
  - "Mỏng" không có nghĩa là giả.
  - Mẫu nhỏ (21–25 người mỗi nhóm, 5 repo); hai repo đối chứng do tác giả chọn vì tin là lan truyền thật.
  - Chỉ cho biết đó là tài khoản dùng một lần, không cho biết ai đứng sau, nên không gán lỗi cho chủ repo.
  - Ngưỡng "mỏng ≤3 sự kiện" chưa thử độ nhạy.

### Câu 2: người đóng góp mới có ở lại không?
- Định nghĩa (`scripts/cohort_retention.py`, mô hình `fct_cohort_retention`):
  - 11 khối 7 ngày, 01/03 → 16/05/2025; người mới = lần đầu xuất hiện từ khối 3 (khối 1–2 để khởi động).
  - Chỉ tính push, PR, issue, bình luận, review; loại bot.
- Kết quả (143.991 người, 273.688 dòng người-tuần, trung bình có trọng số theo cohort):
  - Còn hoạt động: 16,7% sau 1 tuần, 10,2% sau 2, 7,9% sau 4, 7,2% sau 8.
  - Bắt đầu bằng push/PR: 29,0% sau 1 tuần, 14,9% sau 8. Chỉ issue/bình luận/review: 14,3% và 5,6%.
- So với vòng 1 (52.417 người): 16,9% / 5,8% (1 và 8 tuần); code 29,8% / 12,9%; issue 12,5% / 3,3%.
  - Tuần 1 gần như không đổi; mức 8 tuần và nhóm issue-first cao hơn.
  - Nguyên nhân chưa kiểm tra; giả thuyết: repo thư viện/framework giữ người lâu hơn repo ứng dụng nhỏ.
- Giới hạn:
  - Không có dữ liệu trước 01/03: người cũ vắng 2 tuần đầu bị tính là mới → cohort đầu cao ảo; xu hướng giảm giữa các cohort không có nghĩa hệ sinh thái yếu đi.
  - "Còn hoạt động" chỉ tính trong tập repo đã lọc.
  - Chưa có mốc so sánh bên ngoài; cohort muộn quan sát ngắn; giờ 08/05 01:00 UTC thiếu dữ liệu nằm trong khối 9.

### Chưa làm
- Dự án chết dần; làn sóng LangChain → agent → MCP (cần dữ liệu nhiều năm).
- So với nguồn tương tự như OSS Insight (chưa kiểm tra).

## 8. Dashboard, bài viết, đăng GitHub
- **Dashboard** `docs/index.html`: trang HTML tĩnh tự chứa, tự vẽ SVG, không cần máy chủ, đăng bằng GitHub Pages. Tạo bởi `scripts/build_dashboard.py` và `scripts/dashboard_template.html` từ các bảng dbt và file mẫu tài khoản. Chọn HTML tĩnh thay vì Streamlit vì Streamlit kéo nhiều gói nặng và mạng máy rất chậm (~16 kB/s khi cài dbt).
- **Nội dung:** con số chính (−35%), 4 thẻ số, 4 biểu đồ có tooltip, điều hướng bàn phím và bảng số liệu, mục giới hạn; hỗ trợ chế độ sáng/tối. Bảng màu 3 slot đạt kiểm tra `validate_palette.js` ở cả hai chế độ (xanh ngọc ở chế độ sáng chỉ đạt tương phản 2,74:1, nên có nhãn trực tiếp và bảng số liệu bù lại).
- **Đã kiểm bằng ảnh chụp:** chế độ sáng và tối ở 1.100–1.200 px, và 390 px. Các lỗi tìm thấy khi xem ảnh đã sửa: tô cam sai ngày, nhãn tràn mép, nhãn bị cắt.
- **Tên repo bị gắn cờ được ẩn mặc định** ("Repo X", "Repo X2", "Repo Y"); `--show-names` để hiện. Lý do: mẫu nhỏ và là repo của các tổ chức thật. Nhãn "Repo X" gán cho repo trong biến môi trường `RADAR_FLAGGED_REPO`, "Repo X2" cho repo cùng chủ sở hữu.
- **Cập nhật sau vòng 2 của giai đoạn 5:** thẻ số, câu mô tả, mục giới hạn, README và bài viết đã được viết lại theo tập 4.033 repo. Đã chụp lại ảnh dashboard ở chế độ tối 1.100 px; chưa chụp lại chế độ sáng và 390 px sau lần đổi này.
- **Bài viết:** `docs/bai-viet.md`.
- **Đăng:** repo công khai `dtkhang05/gh-ai-radar`, giấy phép MIT, trang tại `https://dtkhang05.github.io/gh-ai-radar/`.
- **Chưa làm:** thử trên trình duyệt khác ngoài Edge; đưa `build_dashboard.py` vào `run_pipeline.py` (nó cần file do các script phân tích khác tạo).

## 9. Hướng mở rộng
Theo thứ tự nên làm:

1. **Dữ liệu nhiều năm:** lấy mẫu vài ngày mỗi tháng từ 2023 để xem các làn sóng và dự án chết dần, vì tải đủ 29 tháng quá chậm với mạng hiện tại.
2. **Kiểm tra thêm tập repo AI:** mẫu kiểm tay độ chính xác lớn hơn; thử thêm repo dưới 100 star (cần tra thêm ~500 lượt GraphQL cho ngưỡng 30 star).
3. **Chạy định kỳ hằng ngày** và nguồn dữ liệu bổ sung (chưa thử).
