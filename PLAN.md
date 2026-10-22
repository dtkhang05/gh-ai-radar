# Nhật ký các giai đoạn

Tài liệu này ghi từng giai đoạn của dự án: làm gì, đo được gì, còn thiếu gì. Mọi số liệu là số đo thật trên dữ liệu đã tải (01/03 → 31/05/2025), trừ chỗ ghi "ước tính". Kết quả tổng hợp nằm trong [README.md](README.md).

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| 1 | Tải dữ liệu thử 1 tháng | Xong |
| 2 | Kho DuckDB và kiểm tra mốc dữ liệu | Xong |
| 3 | Lớp kiểm tra chất lượng dữ liệu | Xong bản đầu |
| 4 | Tải thêm dữ liệu lịch sử | Một phần (01–02/2025 tạm dừng; mẫu 2023–2024 đã tải) |
| 5 | Xác định repo AI | Xong (độ phủ 82–89%, độ chính xác ước tính 70–95% tùy nhóm; vòng 3 thử xuống 30 star) |
| 6 | dbt và kiểm thử | Xong |
| 7 | Phân tích | Xong 2 câu hỏi (2025) + mẫu 2023–2024 (đã gộp đổi tên, đã kiểm độ phủ, độ chính xác, ngày bất thường) |
| 8 | Dashboard, bài viết, đăng GitHub | Xong |
| 9 | Mở rộng | Một phần (mẫu 2023–2024, vòng 3); phần còn lại là hướng phát triển |

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
- Chạy lại `ingest.py 2025-01-01 2025-02-28 2` sẽ tiếp tục từ chỗ dừng. 
- **Mẫu 2023–2024** (`scripts/ingest_sample.py` → `data/parquet_sample/`, tách khỏi `data/parquet/` nên pipeline 2025 không đọc nhầm): thứ Tư tuần 2, 3, 4 của mỗi tháng từ 01/2023 đến 12/2024 = 72 ngày, 1.728 giờ, 341.798.089 sự kiện, 4,0 GB Parquet. Tải mất 10.968 giây (~3 tiếng, ~6,3 giây/giờ; mạng lúc này nhanh hơn lúc tải 01–02/2025). Cố định thứ Tư để thay đổi giữa các tháng không lẫn hiệu ứng cuối tuần.
- **Kiểm tra chất lượng mẫu** (`scripts/dq_sample.py`): so mỗi giờ với trung vị cùng giờ của 6 ngày mẫu gần nhất (3 trước, 3 sau), cùng ngưỡng 0,70/1,50. Kết quả: 1.717 giờ ok, 8 low, 3 high; đủ 24 file mỗi ngày.

  | Phát hiện | Chi tiết | Trạng thái |
  |---|---|---|
  | Lỗi của nguồn | 14/08/2024 23:00 UTC chỉ có 489 sự kiện (0,3%), file 170.922 byte so với ~75 MB. Tải lại thẳng từ máy chủ: cùng kích thước | Lỗi ở GH Archive, không phải do mạng của tôi |
  | Hoạt động thật của bot | 12/04/2023 02–04h UTC cao 1,54–1,65 lần; `dependabot[bot]` tạo 110.425 sự kiện trong giờ 03h (~50%) | Không phải lỗi dữ liệu nhưng làm lệch số đếm; phân tích sau nên loại bot |
  | Chưa rõ nguyên nhân | 13/03/2024 00h (0,67); 11/09/2024 14h (0,59); 25/12/2024 có 6 giờ 0,66–0,69 và cả ngày bằng 0,70 trung vị quý | Giả thuyết ngày lễ chưa kiểm tra |
  | Không thấy | Đợt sụt kéo dài kiểu 23/05/2025 | Ngày thấp nhất ngoài Giáng sinh bằng 0,90 trung vị quý |
  | Mức nền | Trung vị theo ngày ~4,0–4,4 triệu sự kiện (2023), ~5,0–5,5 triệu (2024), ~5,4–5,9 triệu (03–05/2025) | Chưa biết là tăng trưởng thật hay GH Archive đổi cách thu thập |

  - **Giới hạn:** chỉ 3 ngày/tháng và đường cơ sở nhìn cả trước lẫn sau nên không bắt được một đợt sụt dài quá ~3 tháng; chưa tạo cột chất lượng này trong dbt.
- **Phân tích mẫu 2023–2024** (`scripts/sample_waves.py`, đếm `WatchEvent` của người, loại `[bot]`). Có hai bản; **bản 2 (tập dựng từ mẫu, tên đã gộp) là bản chính**:
  - **Bản 1 (tập 4.033 repo dựng từ star 2025):** phần star thuộc repo AI tăng từ 3,5–4,3% (2023-Q1) lên 7,7–9,2% (2024-Q4).
  - **Bản 2 (`RADAR_UNIVERSE_MODE=sample`, 8.313 repo AI dựng từ 64.714 repo ≥30 star trong chính mẫu, mọi tên cũ gộp về tên hiện tại):** phần star thuộc repo AI trên tổng star mọi repo, theo quý:

  | Quý | Bản 2 đầy đủ | Bản 2 lõi (tên/topic) | Bản 1 đầy đủ | Bản 1 lõi |
  |---|---|---|---|---|
  | 2023-Q1 | 8,1% | 6,9% | 4,3% | 3,5% |
  | 2023-Q2 | 14,8% | 12,8% | 7,1% | 6,1% |
  | 2023-Q3 | 11,9% | 10,3% | 6,2% | 5,4% |
  | 2023-Q4 | 12,5% | 10,6% | 7,3% | 6,2% |
  | 2024-Q1 | 11,5% | 9,8% | 7,1% | 6,1% |
  | 2024-Q2 | 12,3% | 10,5% | 8,4% | 7,3% |
  | 2024-Q3 | 11,5% | 9,8% | 8,3% | 7,1% |
  | 2024-Q4 | 11,7% | 9,8% | 9,2% | 7,7% |

  - **Kết luận đổi:** bản 1 cho thấy xu hướng tăng đều, nhưng đó phần lớn là thiên lệch người sống sót (tập chỉ gồm repo còn ≥100 star năm 2025). Bản 2 cho thấy **một bước nhảy ở 2023-Q2 (làn sóng AutoGPT, đỉnh 14,8%) rồi đi ngang ở khoảng 11,5–12,5%**, không tăng đều. Mức tuyệt đối cũng gần gấp đôi bản 1 ở 2023 (8,1% so với 4,3% ở Q1).
  - **Tổng star mọi repo** gần như phẳng (~190–240 nghìn/ngày mẫu), trừ 2023-03 (~405 nghìn, chưa xem nguyên nhân).
  - **Làn sóng:** top 3 repo mỗi quý theo star/ngày mẫu (bản 2, tên hiện tại, bỏ chủ sở hữu cho gọn):

  | Quý | Hạng 1 | Hạng 2 | Hạng 3 |
  |---|---|---|---|
  | 2023-Q1 | prompts.chat (531) | awesome-chatgpt-prompts-zh (334) | stable-diffusion-webui (322) |
  | 2023-Q2 | AutoGPT (1.649) | gpt-engineer (803) | gpt4free (478) |
  | 2023-Q3 | llama (408) | MetaGPT (308) | quivr (269) |
  | 2023-Q4 | generative-ai-for-beginners (282) | ollama (281) | lobehub (244) |
  | 2024-Q1 | OpenHands (270) | ollama (259) | copilot-gpt4-service (211) |
  | 2024-Q2 | llm.c (337) | ollama (305) | dify (239) |
  | 2024-Q3 | Deep-Live-Cam (330) | invisible_dots (258) | claude-engineer (193) |
  | 2024-Q4 | markitdown (372) | swarm (182) | PDFMathTranslate (166) |

  Chỉ là mô tả top 5, chưa có phép đo "làn sóng" nào chặt hơn. Ở bản 1 hạng 1 của 2023-Q2 là `gpt-engineer`; `AutoGPT` đổi tên từ `Auto-GPT` nên có thể lịch sử bị tách (tôi chưa kiểm tra riêng ca này). Chủ đề đổi theo đợt: prompt/ChatGPT (đầu 2023) → agent tự chạy (giữa 2023) → chạy cục bộ và RAG/công cụ (2024).
  - **Dự án giảm dần (bản 2):** 215 repo có đỉnh quý 2023 ≥50 star/ngày mẫu; 200 (93%) còn dưới 50% đỉnh ở 2024-Q3/Q4, 157 (73%) còn dưới 20%. Bộ lõi: 176 repo, 162 (92%) và 125 (71%). Bộ dò đổi tên thô còn nghi 3/215 ca; loại ra thì 198/212 và 157/212. Bản 1: 132 repo, 89% và 61%. Kết luận định tính (đa số mất sức hút) không đổi, nhưng đây vẫn **chỉ tính repo còn ≥30 star trong mẫu**, nên không đọc là "bao nhiêu % repo AI chết".
  - **Thiên lệch còn lại:** bản 2 bỏ được thiên lệch người sống sót với nhóm ≥30 star ở 2023–2024, nhưng repo bị xóa (149 repo AI) chỉ phân loại theo tên, repo <30 star mẫu không có mặt, và độ phủ của luật là 84–88% (xem bên dưới) nên phần AI có thể bị đánh giá thấp hơn thực tế; mặt khác nhóm chỉ khớp qua mô tả sai khoảng 12–30%, nên bộ lõi và bộ đầy đủ là hai đầu của khoảng.
  - **Đổi tên:** 4.130 repo trong tập 64.714 (6,4%) đổi tên hoặc chuyển chủ; bản 2 gộp bằng tên hiện tại mà GitHub trả về.
  - **Kiểm tay bước nhảy 2023-Q2 (bản 2):** xem 60 repo có nhiều star nhất trong số repo AI của quý (tổng 308.877 star AI trong các ngày mẫu của quý): 57 đúng, 2 sai (`shadcn-ui/ui` 1.602, `ruoyi-vue-pro` 831), 1 ranh giới (`novel`, 739). Thêm 25 repo chỉ khớp qua mô tả có nhiều star nhất: 19 đúng, 3 sai (`ruoyi-vue-pro`, `openobserve` 647, `yudao-cloud` 472), 3 ranh giới (`funNLP`, `AppFlowy`, `go-proxy-bingai`). Các ca sai chiếm khoảng 1,2% star AI của quý (≈3.550/308.877), cộng ranh giới khoảng 0,6% nữa: 14,8% giảm cùng lắm còn ~14,6% nếu loại sai, ~14,0% nếu loại cả ranh giới. `AutoGPT` riêng chỉ chiếm ~0,7 điểm. **Bước nhảy không do phân loại nhầm hay một repo.** Một điều đã tra, một điều chưa: tổng star ngày mẫu 08/03/2023 là 585.902 (ngày khác cùng giai đoạn ~230–350 nghìn), rải trên 369.981 repo, cao nhất vào 22–23h UTC; repo đứng đầu ngày chỉ có vài trăm star, trong đó có nhiều repo kiểu cheat/crack game (cùng một chủ, mỗi repo ~460–490 star, mỗi người star một lần). Trông như một đợt star hàng loạt không phải AI (kết luận từ hình dạng dữ liệu, chưa kiểm tài khoản). Bỏ riêng ngày đó thì phần AI của 2023-Q1 là **9,2%** thay vì 8,1% (bước nhảy lên Q2 nhỏ hơn: 9,2% → 14,8%); số star AI mỗi ngày mẫu tăng đều từ ~12 nghìn (01/2023) lên ~47 nghìn (12/04/2023) rồi đi ngang/giảm nhẹ ở ~37–43 nghìn, nên làn sóng đầu 2023 là thật, mẫu số chỉ làm nó trông lệch. Chưa kiểm tra: mô tả repo là mô tả 2026 (`quivr` giờ là sản phẩm khác), chỉ ảnh hưởng nhãn, không ảnh hưởng star. Mẫu 85 repo là các repo lớn nhất, chấm một người; không suy ra độ chính xác cho phần đuôi dài.
  - **Quét ngày bất thường trong 72 ngày mẫu** (`scripts/sample_day_anomalies.py`; ngày bị gắn cờ khi tổng star > 1,5× trung vị 6 ngày mẫu gần nhất): **chỉ 08/03/2023** (585.902 star, gấp 2,21 lần; 358.278 trong 369.975 repo chỉ có 1–2 star ngày đó). Không có ngày nào thấp hơn 0,7× đường tham chiếu. Hạ ngưỡng xuống 1,25× thì thêm 3 ngày (22/03/2023 1,31×, 12/06/2024 1,26×, 13/11/2024 1,32×), nhỏ hơn nhiều và chưa xem nguyên nhân. Phần AI theo quý chỉ đổi ở 2023-Q1 (8,1% → 9,2%); các quý khác không có ngày bị gắn cờ.
  - **Tuổi tài khoản của đợt star 08/03/2023** (`scripts/check_account_age_march2023.py`, 200 + 100 + 100 tài khoản ngẫu nhiên): nhóm A (star vào repo ≤2 star ngày đó): tạo <30 ngày trước đó chỉ 0,5%, tuổi trung vị 1.303 ngày, 3,1% không có repo công khai, 8/200 không tra được. Nhóm B (repo >2 star cùng ngày): 5,1% mới, trung vị 1.022 ngày. Nhóm C (ngày thường 15/03): 5,7%, trung vị 1.416 ngày. **Kết luận: không phải tài khoản mới tạo hàng loạt; tài khoản cũ như bình thường.** Vậy "star giả bằng tài khoản mới" bị loại, nhưng đợt này vẫn có thể do tài khoản cũ bị chiếm hoặc một chiến dịch trả tiền; mình chưa biết nguyên nhân. Nhóm B có 21/100 không tra được (cao hơn A 4% và C 13%), chưa giải thích.
  - **Kiểm tay độ chính xác của tập bản 2 trên mẫu ngẫu nhiên** (hash cố định, không chọn theo star): 50 repo từ nhóm 30–99 star mẫu và 50 repo từ nhóm ≥100 (tập 8.313 repo, 5.192 + 3.121 repo). Nhóm 30–99: 39 đúng, 8 ranh giới (ví dụ `awesome-colab-notebooks`, `lumen` - công cụ git có AI, `mx-space/core` - CMS có tính năng AI), 3 sai (`Orb` - hiệu ứng SwiftUI có topic `ai`, `yuka` - AI trò chơi, 1 repo crack spam). Nhóm ≥100: 39 đúng, 6 ranh giới, 5 sai (admin template Next.js, RocketMQ-Rust, form designer Vue, bộ dựng site Hugo, trang bài phỏng vấn). Gộp: **78 đúng, 14 ranh giới, 8 sai trên 100** (sai 8%, khoảng ước tính thô ~4–15%; sai hoặc ranh giới 22%). Tỉ lệ sai theo số repo ~7,5% sau khi nhân trọng số 2 nhóm. Một người chấm, mẫu 100; đây là độ chính xác của **nhãn "là AI"** chứ không phải của số liệu phần trăm star (repo lớn chiếm phần star, nhóm ≥100 sai 10%).
  - **Độ nhạy ngưỡng tài khoản mỏng** (`scripts/sample_thin_sensitivity.py`, tập bản 2, 5 ngưỡng "mỏng" × 4 ngưỡng tỉ lệ × 2 ngưỡng số star): với ngưỡng gốc (≤3 sự kiện, ≥60%, ≥500 star) cho 1 repo-quý bị gắn cờ trên 490 repo-quý đủ điều kiện (trước đây 1 trên 366 với tập bản đầu) và 0/64 repo top 8 mỗi quý. Nới lỏng: ≤3 sự kiện, ≥40%, ≥200 star → 38 repo-quý bị gắn cờ, 1/64 trong top 8. Chỉ khi coi "mỏng" là ≤10 sự kiện (33% tài khoản bị tính là mỏng) mới có nhiều top 8 bị gắn cờ (24/64 ở ngưỡng 40%, 0/64 ở 60%). Kết luận 'không thấy kiểu Repo X trong top các quý' giữ nguyên với mọi tổ hợp ngưỡng ≥60%.
  - **Một phát hiện mới từ phép nhạy:** với ngưỡng nới (≥50% mỏng, ≥200 star) hai repo của Repo X và Repo X2 (cùng tổ chức) hiện ra ở **2024-Q4**: mỗi repo ~480 star trong quý, 57–63% là tài khoản mỏng, gần như cùng lúc (cùng hai ngày mẫu 11/12 và 25/12/2024, ~180–190 star mỗi repo mỗi ngày). Ở 2023-Q4 chỉ khoảng 100 star, 30% mỏng. Nghĩa là dấu hiệu bất thường có thể bắt đầu từ cuối 2024, **trước** đợt 04/2025 đã phân tích. **Đã kiểm tuổi tài khoản** (`scripts/check_account_age_dec2024.py`, 200 tài khoản ngẫu nhiên star hai repo trong hai ngày đó, so với 100 tài khoản star repo AI khác cùng hai ngày): **14,1% tạo đúng ngày star** (nhóm đối chứng 1,1%), tuổi trung vị 430 ngày (đối chứng 1.997), 30/200 (15%) không tra được vì đã bị xóa (đối chứng 8%; nếu nhiều tài khoản giả đã bị xóa thì con số 14,1% còn thấp hơn thực tế). Cùng kiểu với 2025 nhưng nhẹ hơn nhiều: Repo X ở 2025 là 95,2% tạo trong ngày, trung vị 0. Kết luận: **có dấu hiệu thật từ cuối 2024, gấp khoảng 13 lần đối chứng, nhưng quy mô nhỏ hơn 2025 và chỉ từ 2 ngày mẫu**; chưa biết nó bắt đầu từ ngày nào, và mẫu 200 người nên sai số vài điểm %.
  - **"Làn sóng" đo chặt hơn** (`scripts/sample_waves_strict.py`): làn sóng = repo-quý có ≥100 star/ngày mẫu và ≥3× quý trước (repo vắng quý trước tính như vô hạn). Mỗi quý có 8–24 làn sóng, mang 6–21% star AI của quý (2023-Q2: 24 làn sóng, 21,1%; các quý sau 6,0–11,4%). Hai quý sau chỉ 9/73 làn sóng (12%) còn ≥50% mức đỉnh (2023-Q2: 2/24; chưa tính 2024-Q3/Q4 vì chưa đủ 2 quý sau). Top 3 gần như trùng với danh sách top 5 trước, nên danh sách đó không phải do cách đếm lỏng. Số 100 star/ngày và 3× do tôi chọn, chưa thử độ nhạy; hai quý sau dùng quý hiện tại +2, nên mẫu 3 ngày/tháng có thể bỏ lỡ đợt ngắn.
  - **Kiểm tay bộ phân loại trên 52 repo đứng top 8 mỗi quý (2023–2024):** 46 đúng, 4 ranh giới (`Follow` đọc RSS có AI, `markitdown` chuyển file cho LLM, `PDFMathTranslate`, `gpt-crawler`), 2 sai (`shadcn-ui/ui`, `drawdb`: thư viện giao diện và công cụ vẽ sơ đồ CSDL). Hai repo sai chiếm tối đa 0,5–1,5% star/ngày mẫu của tập AI mỗi quý nên không đổi kết luận. Mẫu chọn theo thứ hạng star (repo nổi tiếng, dễ phân loại đúng), nên không suy ra độ chính xác cho cả 4.033 repo; tôi là người xem và chấm.
  - **Kiểm tra tài khoản mỏng** (`scripts/sample_thin_stars.py`): tài khoản mỏng = ≤3 sự kiện trong cả mẫu 72 ngày. Cả tập AI: 15,3% người star là tài khoản mỏng. Trong 366 cặp repo-quý có ≥500 star, chỉ 1 cặp có ≥60% mỏng (`ruoyi-vue-pro`, 2023-Q2, 61,3%, 831 star; mẫu kiểm tay không thấy có AI, có thể là repo phân loại nhầm). 0/64 repo top 8 mỗi quý bị gắn cờ; 5 repo đầu mỗi quý có 9–25% mỏng. Kết luận: không thấy dấu hiệu kiểu Repo X trong top các quý. Điểm yếu: mẫu chỉ ~10% số ngày nên tài khoản "mỏng" ở đây là "ít hoạt động trong các ngày mẫu", yếu hơn phép đo 12 tuần liên tục của 2025; ngưỡng 60% và 500 star do tôi chọn (độ nhạy đã thử ở bullet bên trên); tuổi tài khoản bằng API đã kiểm cho top 3 mỗi quý (bullet dưới). "Không thấy" chưa phải "không có".
  - **Ca bị gắn cờ mỏng là phân loại nhầm:** `ruoyi-vue-pro` là bộ khung hệ thống quản trị Java (Spring Boot + Vue); mô tả chỉ liệt kê \"AI 大模型\" là một trong nhiều tính năng và kết thúc bằng lời xin star. Nó vào tập AI chỉ nhờ khớp từ khóa trong mô tả (`by_desc`), không có topic AI, và không thuộc top 8 của quý nào. Đây là ca sai thứ 3 tìm thấy (ngoài `shadcn-ui/ui`, `drawdb`), cùng kiểu lỗi: từ khóa AI nằm trong danh sách tính năng. Chưa đo có bao nhiêu repo khác trong 4.033 mắc lỗi này; con số 76–86% chính xác của phần topic/mô tả (mẫu 2025) vẫn là ước tính duy nhất.
  - **Tuổi tài khoản cho 2023–2024** (`scripts/check_account_age_sample.py`, GraphQL qua đăng nhập `gh`, 100 tài khoản/lượt, 7 lượt): 3 repo đầu mỗi quý × 25 người star ngẫu nhiên trong các ngày mẫu của quý đó (24 nhóm) + 100 người star ngẫu nhiên của các repo AI (nhóm nền). Tuổi = số ngày từ lúc tạo tài khoản đến lúc star.

    | Chỉ số | 2023–2024: 24 nhóm repo-quý | 2023–2024: nhóm nền | 2025, Repo X (đối chiếu) | 2025, repo lan truyền thật (đối chiếu) |
    |---|---|---|---|---|
    | Tạo <30 ngày trước khi star | 0% – 17,4% (cao nhất 4/23; 6 nhóm ≥9%) | 2,1% (2/96) | 95,2% (20/21) | 0–8% |
    | Tuổi trung vị (ngày) | 1.432 – 3.072 | 2.021 | 0 | 2.050 – 3.820 |
    | Chưa có repo công khai | 0% – 26,1% | 9,4% | 90,5% (19/21) | 4–9% |

    - **Kết luận:** không nhóm nào giống kiểu Repo X của 2025 (≥90% tài khoản tạo ngay trong ngày). Vài nhóm có tỉ lệ cao hơn nhóm nền (cao nhất 4/23); lan truyền ra mắt thường kéo theo nhiều tài khoản mới, và mẫu 25 người/nhóm nên khoảng sai lớn; chưa thử kiểm định thống kê.
    - **Thiên lệch có hướng:** 38/700 tài khoản (5,4%) không tra được (đã xóa); nếu tài khoản giả bị xóa sau đó thì phép đo này đánh giá thấp. Chưa biết bao nhiêu trong 38 là tài khoản giả.
    - **Giới hạn:** chỉ 3 repo đầu mỗi quý (không kiểm các repo khác); ngày star nằm trong các ngày mẫu; so sánh với 2025 dùng mẫu khác (21–25 người, API công khai không đăng nhập).
  - **Độ phủ cho repo ít người biết** (cách đo khác: không dùng danh sách chọn tay mà xem tay mẫu các repo bộ phân loại bác bỏ, `hash(repo || 'neg1')`, chỉ repo tra được metadata): trong 100 repo 30–99 star bị xếp "không phải AI", mình thấy 6 repo rõ ràng là AI bị bỏ sót (`HtmlRAG`, bộ mã hóa ảnh Selftok, `LGM` tạo 3D, API CosyVoice, `torch_musa`, công cụ TradingView-Machine-Learning) và 4 ranh giới; trong 50 repo ≥100 star bị bác bỏ có 4 repo rõ ràng là AI bị sót (`GLM-4`, `detectron2`, `MLOps-Basics`, `TripoSR`) và 1 ranh giới.
    - **Ước lượng thô, chưa phải số đo:** tỉ lệ bỏ sót 6% (khoảng ~2–12%) ở nhóm 30–99 star và 8% (~3–19%) ở nhóm ≥100 → độ phủ khoảng 76% và 79% nếu áp tỉ lệ đó lên toàn bộ repo tra được metadata (33.572 và 13.364 repo bị bác bỏ), với khoảng sai rất rộng (~60–90%). Gần với 82–89% đo trên danh sách chọn tay nổi tiếng, tức là danh sách chọn tay hơi lạc quan hơn nhưng không khác xa.
    - **Kiểu sót điển hình:** `RAG` dính liền trong tên ghép (`HtmlRAG`), `LMs` thay vì `LLMs`, thị giác máy tính và tạo 3D không có từ khóa AI trong mô tả, `MLOps`. Các luật được giữ nguyên để không làm hỏng tính độc lập của hai danh sách đo trước; sửa luật là việc riêng.
    - **Giới hạn:** người chấm là mình, chỉ dựa vào tên/mô tả/topic (cùng thông tin bộ phân loại thấy); repo không tra được metadata (~17%) không xem được nên không nằm trong ước lượng; định nghĩa "là AI" có vùng mờ.
  - **Độ phủ và đổi tên (đã đo, tập 64.714 repo ≥30 star trong mẫu, metadata API tra được 53.928):**
    - Độ phủ trên 3 danh sách viết tay: 84% (57/68), 88% (63/72), **86% (101/117, danh sách 3 viết riêng cho 2023–2024 trước khi chạy)**.
    - Dùng tập repo AI dựng từ star 2025 (tên cũ không khớp) thì danh sách 3 chỉ còn 72% (84/117): chênh 14 điểm là do đổi tên/chuyển chủ (4.130 repo, 6,4% của tập, đã gộp về tên hiện tại; 1.052 trong số đó là repo AI).
    - Bỏ sót điển hình: thư viện hạ tầng không có từ khóa AI trong tên/mô tả (`jax`, `mlx`, `accelerate`, `flash-attention`, `whisper`). Luật giữ nguyên, không chỉnh theo danh sách.
    - 149 repo AI bị xóa/không tra được vẫn chỉ phân loại theo tên.
  - **Chưa kiểm tra:** bộ lõi và bộ đầy đủ của bản 2 chưa được kiểm tay độ chính xác riêng (mẫu kiểm tay 50/52 repo ở trên là của bản 1); danh sách tham chiếu do một người viết, không phải mẫu ngẫu nhiên; mẫu 3 ngày/tháng nên một đợt lan truyền ngắn có thể rơi ngoài mẫu; star đột biến do tài khoản giả không được lọc (đã thấy ở 2025).
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

**Nhóm chỉ khớp qua mô tả** (không có tên hay topic AI; 676 repo = 16,8% của 4.033): mẫu 50 repo (xếp theo `hash(repo || 's1')`, lấy 50 đầu), tác giả xem tên và mô tả đầy đủ: 35 đúng (70%), 9 ranh giới (18%), 6 sai (12%). Sai: `yudao-ui-admin-vue3` (mẫu quản trị, cùng kiểu `ruoyi-vue-pro`), `rainbond` (nền tảng container), `sunface/rust-course` (sách Rust), `better-genshin-impact` (tự động hóa game), `legacy-cc` (bot giao dịch tiền mã hóa), `Bend` (ngôn ngữ lập trình). Ranh giới: `scalene`, `viral-predictor`, `Element-Plus-X`, `physics-sims`, `bambot`, `warp`, `datahub`, `Conference-Acceptance-Rate`, `AiEditor`. Nếu tính 12% sai trên 676 repo thì khoảng 80 repo (ước tính, khoảng tin cậy rộng vì mẫu 50: sai có thể từ ~5% đến ~24%), tức ~2% của tập 4.033; chưa đo, và mẫu do một người chấm. Hai repo `NVIDIA/AgentIQ` và `AIQToolkit` cùng mô tả (một dự án đổi tên, đếm hai lần). Lỗi điển hình: từ khóa AI nằm trong danh sách tính năng hoặc là phụ của sản phẩm không phải AI. Ảnh hưởng lên kết luận 2023–2024 chưa tính lại; repo nhóm này nhỏ (lấy mẫu có 100–1.500 star năm 2025) nên ít khả năng vào top các quý.

### Vòng 3: mở rộng xuống 30 star (21/10/2026)
Câu hỏi: bỏ qua repo dưới 100 star có làm lệch kết luận không? Làm bằng cách tra thêm 48.081 repo có 30–99 star (480 lượt GraphQL, mỗi lượt 1 điểm, không lỗi) rồi chạy cùng bộ phân loại ở chế độ `RADAR_INCLUDE_LOW=1`. Kết quả ghi ở `ai_repo_universe_low.parquet`; `ai_repo_universe.parquet` (dbt đọc) và mọi phân tích khác **không đổi**.

| Nhóm (star trong 12 tuần) | Repo | Repo AI | Star của repo AI | AI / star cùng nhóm | Không tra được (trong repo AI) |
|---|---|---|---|---|---|
| ≥100 | 19.704 | 4.033 | 2.829.767 | 34,1% | 43 |
| 30–99 | 48.081 | 6.252 | 328.906 | 13,3% | 152 |

- **Kết luận chính:** nhóm 30–99 star thêm 6.252 repo AI (+155% số repo) nhưng chỉ thêm 328.906 star, tức 10,4% tổng star của repo AI (từ 30 star). Phân tích chính dùng ≥100 star vì vậy thấy khoảng 90% khối lượng star của repo AI theo định nghĩa này; đã tính lại hai chỉ số chính ở bên dưới.
- **Độ phủ gần như không đổi:** danh sách 1 vẫn 82% (62/76); danh sách 2 là 89% (64/72), có thêm 1 repo thuộc nhóm 30–99 star (trước đây 63/71) và bộ phân loại bắt được repo đó. Đây chỉ là 1 repo nên không nói được gì về độ phủ cho repo ít người biết, vẫn **chưa đo**.
- **Tra không được nhiều hơn:** 8.409/48.081 repo (17,5%) so với 12% ở nhóm ≥100; các repo này chỉ khớp được theo tên.
- **Độ chính xác nhóm 30–99** (mẫu 50 repo xếp theo `hash(repo || 's2')`, tác giả xem tên, mô tả, topic): 41 đúng (82%), 5 ranh giới (10%), 4 sai (8%). Sai: ghi chú môn học tổng hợp ĐH có chữ "AI" trong topic, thư viện RPA, ngôn ngữ CSS, framework Go. Ranh giới: repo thực tập AI/IoT, công cụ mở khóa Copilot, bản đóng gói Claude Desktop cho Debian, trợ lý giọng nói, repo dịch PDF. Mẫu nhỏ, một người chấm; khoảng sai có thể từ ~3% đến ~19%.
- **Chạy lại hai phân tích trên tập 10.285 repo AI** (`RADAR_UNIVERSE=ai_repo_universe_low.parquet RADAR_OUT_SUFFIX=_low`; file `_low` không đè file dashboard đọc; `cohort_retention.py` 80 giây, `star_anomalies.py` vài phút):

| Chỉ số | Tập ≥100 star (4.033 repo) | Tập ≥30 star (10.285 repo) |
|---|---|---|
| Ngày star đột biến (≥50 star, ×5) | 1.513 ngày, 526 repo | 1.513 ngày, 526 repo (0 ngày thuộc nhóm 30–99) |
| Tài khoản mỏng: ngày đột biến / ngày thường | 6,7% / 8,2% | 6,7% / 8,2% |
| Repo bị gắn cờ nghi vấn | 3 repo ở ≥6/9 bộ ngưỡng (Repo X, X2 cùng tổ chức; Repo Y) | cùng 3 repo, cùng 9/9, 9/9, 6/9; thêm 2 repo khác ở 3/9 (không nêu tên: chỉ là tín hiệu yếu), chưa đối chiếu với tập ≥100 vì bản cũ không lưu cả lưới ngưỡng |
| Người đóng góp (loại bot) | 143.991 | 165.869 (+15%) |
| Giữ chân sau 1 / 2 / 4 / 8 tuần | 16,7 / 10,2 / 7,9 / 7,2% | 17,2 / 10,7 / 8,3 / 7,7% |
| Mở đầu bằng code, 1 / 8 tuần | 29,0 / 14,9% | 29,4 / 15,3% |
| Mở đầu bằng issue/bình luận, 1 / 8 tuần | 14,3 / 5,6% | 14,5 / 5,8% |

  - **Đột biến ở cấu hình chính (50 star, ×5) không đổi theo thiết kế, không phải do lọc kỹ** (các cấu hình ngưỡng thấp hơn trong lưới 9 bộ chưa đối chiếu): luật yêu cầu ≥50 star trong một ngày và ≥7 ngày có star trong 14 ngày trước, mà repo nhóm 30–99 có dưới 100 star cả 12 tuần nên gần như không thể thỏa. Vậy phép kiểm tra này **không nhìn thấy** repo nhỏ; kết quả "không có đột biến ở nhóm nhỏ" là hệ quả của ngưỡng, chưa phải bằng chứng repo nhỏ sạch.
  - **Giữ chân cao hơn khoảng 0,4–0,5 điểm phần trăm** ở mọi mốc, cùng chiều và cùng thứ tự (code-first cao hơn gấp đôi); kết luận định tính không đổi. Chưa biết vì sao cao hơn (có thể người đóng góp repo nhỏ gắn bó hơn, hoặc do khác biệt trong cách tính cohort); chưa kiểm tra.
- **Giới hạn thêm:** vẫn bỏ repo dưới 30 star; "AI / star cùng nhóm" thấp hơn ở nhóm nhỏ (13,3% so với 34,1%) có thể do repo AI nhỏ ít hơn thật, hoặc do metadata repo nhỏ thiếu hơn (topic/mô tả trống) nên khớp ít hơn; chưa phân biệt được hai khả năng.

**Giới hạn:** hai danh sách do tác giả chọn từ trí nhớ nên thiên về repo nổi tiếng; chỉ xét repo ≥100 star trong phân tích chính (vòng 3 thử xuống 30 star, repo dưới 30 star vẫn bị bỏ); topic và mô tả là của năm 2026, không phải 03–05/2025; 12% repo không tra được chỉ khớp được theo tên; mẫu độ chính xác nhỏ, một người đánh giá; chưa thử ngưỡng nào khác cho danh sách topic và mẫu mô tả.

## 6. dbt và kiểm thử

### Mô hình và kết quả build
- `dbt_radar/` (dbt-core 1.12.6, dbt-duckdb 1.11.0, DuckDB 1.5.6). Luồng: `stg_events` (view trên Parquet) → `int_ai_repo_candidates` → `fct_star_daily`, `fct_star_spike_days`, `fct_contributor_week`, `fct_cohort_retention`, `fct_hourly_quality`. Ngưỡng và cửa sổ là biến trong `dbt_project.yml`.
- Build: 7 mô hình, 28 test: 25 đạt, 3 cảnh báo có chủ đích, 0 lỗi, ~140 giây trong lần chạy gần nhất (cả hai lần chạy 21/10/2026 đều ~140 giây, lần đo ~70 giây từ trước) (đã từng đo ~70 giây; chưa tìm nguyên nhân chênh lệch, có thể do máy bận). Lúc đầu ~166 giây; nhanh hơn nhờ ghép danh sách repo trước khi gom nhóm.
- Cảnh báo 1: 24 id trùng trong tuần mẫu 01–07/05/2025 (chỉ kiểm 1 tuần vì kiểm toàn bộ cần băm >300 triệu id).
- Cảnh báo 2: 2 giờ bất thường trong cửa sổ tin cậy (13/04 01:00 tỉ lệ 0,606; 08/05 01:00 tỉ lệ 0,121).
- Cảnh báo 3: cùng 2 giờ đó theo đường cơ sở cố định (`assert_no_anomalous_hours_vs_fixed_baseline`).
- **Kiểm tra chất lượng mẫu 2023–2024 trong dbt** (`fct_hourly_quality_sample`, 21/10/2026): bật bằng `--vars '{with_sample: true}'`; `run_pipeline.py` tự bật khi `data/parquet_sample` có file, nên CI (không có mẫu) vẫn dựng 7 mô hình và 28 test. Giờ lấy từ tên file Parquet (cùng định nghĩa với manifest). Có 6 test: `not_null`/`unique` cho `hr`, `not_null` và `accepted_values` cho `flag`, `assert_sample_has_all_hours` (đủ 72 ngày × 24 giờ, không giờ nào 0 sự kiện; mức lỗi), `assert_no_anomalous_hours_in_sample` (mức cảnh báo, 11 dòng).
  - **Khớp script:** 1.728 giờ, 0 giờ lệch cờ, chênh lệch tỉ lệ tối đa 0,0 so với `dq_sample.py` (8 low, 3 high, 1.717 ok).
  - **Chạy đủ pipeline thật** (có mẫu): 8 mô hình, 34 test: 30 đạt, 4 cảnh báo (`unique_stg_events_id` 24 dòng, 2 giờ trong cửa sổ tin cậy, 2 giờ theo đường cố định, 11 giờ mẫu), 0 lỗi, 140 giây. Mô hình mẫu dựng trong ~1 giây.
  - **Thử đột biến:** đặt `sample_expected_days: 73` thì `assert_sample_has_all_hours` đỏ (1 dòng) như mong đợi.
  - **Giới hạn:** đường cơ sở nhìn cả trước lẫn sau, không bắt được đợt sụt dài quá ~3 tháng; chưa có kiểm tra giờ trùng/đổi tên trong mẫu.
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

- Đã chạy cả 4 kịch bản trên GitHub Actions (Ubuntu, Python 3.13, 21/10/2026): 26 kiểm tra đạt (bản trước khi thêm đường cố định: 18). Chưa đo thời gian chạy.
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

1. **Làm sâu phân tích mẫu 2023–2024** (độ phủ, đổi tên, tuổi tài khoản đã làm, xem mục 4): đã làm cả độ nhạy ngưỡng tài khoản mỏng, "làn sóng" chặt hơn, kiểm tay độ chính xác tập bản 2; còn lại: ngày 22/03/2023, 12/06/2024, 13/11/2024 (ngưỡng 1,25×).
2. **Kiểm tra thêm tập repo AI:** mẫu kiểm tay độ chính xác lớn hơn; tính lại các chỉ số chính (đột biến, giữ chân) với nhóm 30–99 star (đã có phân loại, xem vòng 3); đo độ phủ cho repo ít người biết.
3. **Chạy định kỳ hằng ngày** và nguồn dữ liệu bổ sung (chưa thử).
