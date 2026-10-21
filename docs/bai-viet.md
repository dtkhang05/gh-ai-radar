# Nguồn dữ liệu công khai mất 35% sự kiện mà không báo, và hệ thống kiểm tra của tôi bắt được

Dự án học dữ liệu bắt đầu ngày 20/10/2026: dựng pipeline trên GH Archive (mọi sự kiện công khai của GitHub, mỗi giờ một file) để xem hệ sinh thái AI mã nguồn mở vận động thế nào.

- Đo thử vài giờ mẫu mỗi tháng cho thấy số star giảm dần từ giữa 2025 và còn rất ít từ 05/2026 (mỗi số là một giờ trong tháng, chưa phải cả tháng).
- Phần còn lại của dự án đo điều đó cho chắc, và tránh để nó làm hỏng các kết luận khác.

## Điểm sụt nằm giữa tháng 5/2025

- Dữ liệu: 2.208 file giờ, 01/03 → 31/05/2025.
- Cách kiểm tra: so mỗi giờ với trung vị của cùng thứ, cùng giờ trong 4 tuần trước; dưới 70% thì gắn cờ.
- Theo ngày, dữ liệu trông bình thường vì cả 24 file đều có.
- Theo giờ: từ khoảng 17h UTC ngày 23/05/2025, số sự kiện rơi từ ~250 nghìn xuống ~150 nghìn mỗi giờ và không hồi lại.
- Mức giảm là **35,5%** (trung bình mỗi giờ của 12–17/05 so với 26–31/05, cùng các thứ trong tuần).
- Nguyên nhân chưa biết. Cộng đồng đã báo lỗi mất sự kiện cho chủ kho, chưa có xác nhận chính thức, và tôi chưa kiểm tra đó có phải cùng nguyên nhân hay không.
- Bộ kiểm tra còn bắt được một giờ tôi bỏ sót lúc tải: file 01h UTC ngày 08/05/2025 tải báo thành công nhưng chỉ có 27.469 sự kiện (12% mức thường), nặng 11,6 MB thay vì ~105 MB. Script tải chỉ kiểm tra file có tải được, không kiểm tra nội dung.
- Vì vậy mọi phân tích dừng ở 22/05/2025.

## Star tăng đột biến: đa số là người thật

- Phạm vi: 4.033 repo AI có từ 100 star trong 12 tuần.
- Ngày đột biến: ≥50 star và gấp 5 lần trung vị 14 ngày trước. Có 1.513 ngày như vậy ở 526 repo.
- Tài khoản "mỏng": không quá 3 sự kiện trong 12 tuần. Ngày đột biến có 6,7% tài khoản mỏng, thấp hơn ngày thường (8,2%).
- Đọc: phần lớn đột biến đến từ ra mắt hoặc được chia sẻ rộng.

**Hai repo lệch hẳn (Repo X và Repo X2, cùng một tổ chức)**
- Các ngày 11, 12, 14, 15/04/2025: 85–93% người star là tài khoản mỏng, so với ~30% ngày thường.
- Cả hai bị gắn cờ ở 9/9 bộ ngưỡng thử.
- Repo X2 chỉ hiện ra sau khi tôi mở rộng tập repo ra ngoài tên repo; bộ lọc cũ chỉ thấy Repo X.

**Kiểm chứng bằng tuổi tài khoản** (GitHub API, mẫu 21–25 tài khoản mỗi nhóm):

| Nhóm | Tuổi trung vị | Tạo <30 ngày |
|---|---|---|
| Repo X, 14–15/04 | 0 ngày | 20/21 |
| Repo X2, 14–15/04 | 0 ngày | 22/24 |
| Repo Y, 25/04 | 419 ngày | 2/25 |
| github-mcp-server, ra mắt (đối chứng) | 3.820 ngày | 0/22 |
| system-prompts…, lan truyền (đối chứng) | 2.050 ngày | 2/24 |

- Repo X và X2: phần lớn star đến từ tài khoản tạo ngay trong ngày, khác hẳn hai đợt lan truyền thật.
- Repo Y bị gắn cờ ở 6/9 bộ ngưỡng, một ngày, nhưng tuổi tài khoản không xác nhận. Tỉ lệ mỏng ngày thường của nó vốn đã 60%.
- Chỉ cho biết đó là tài khoản dùng một lần, không cho biết ai tạo ra. Tôi không gán lỗi cho ai.
- Mẫu nhỏ, và hai repo đối chứng do tôi chọn vì tin chúng là lan truyền thật.

## Người đóng góp mới ít khi ở lại

- Phạm vi: 143.991 người (push, PR, issue, bình luận, review; loại bot), chia theo tuần đầu tiên họ xuất hiện.
- Còn hoạt động sau 1 tuần: 16,7%; sau 4 tuần: 7,9%; sau 8 tuần: 7,2%.
- Người bắt đầu bằng code giữ lại tốt hơn: 29,0% sau 1 tuần và 14,9% sau 8 tuần, so với 14,3% và 5,6% ở người chỉ để lại issue hoặc bình luận.
- Số 8 tuần cao hơn khi mở rộng tập repo (trước đó 5,8%). Nguyên nhân chưa kiểm tra; giả thuyết: repo thư viện và framework giữ người lâu hơn repo ứng dụng nhỏ.

**Hai chỗ yếu**
- Dữ liệu bắt đầu từ 01/03, nên người cũ vắng hai tuần đầu bị tính là người mới. Xu hướng giảm giữa các cohort vì vậy không có nghĩa hệ sinh thái yếu đi.
- "Còn hoạt động" chỉ tính trong tập repo đã lọc; người chuyển sang repo khác bị tính là rời đi.
- Chưa có mốc so sánh bên ngoài để nói 17% là cao hay thấp.

## Thử nhìn lại 2023–2024 (bản đầu)

- Dữ liệu: 72 ngày thứ Tư (3 ngày mỗi tháng), 341,8 triệu sự kiện. Kiểm tra chất lượng thấy một giờ lỗi ở nguồn (14/08/2024 chỉ có 489 sự kiện) và một đợt bot (12/04/2023), không thấy đợt sụt kéo dài kiểu 05/2025.
- Tổng star mọi repo gần như phẳng, nhưng phần thuộc repo AI tăng:

| Quý | Bộ đầy đủ (4.033 repo) | Bộ lõi (bỏ nhóm chỉ khớp qua mô tả, 3.357 repo) |
|---|---|---|
| 2023-Q1 | 4,3% | 3,5% |
| 2023-Q2 | 7,1% | 6,1% |
| 2023-Q3 | 6,2% | 5,4% |
| 2023-Q4 | 7,3% | 6,2% |
| 2024-Q1 | 7,1% | 6,1% |
| 2024-Q2 | 8,4% | 7,3% |
| 2024-Q3 | 8,3% | 7,1% |
| 2024-Q4 | 9,2% | 7,7% |

- Hai cột cho xu hướng giống nhau nhưng mức chênh 0,8–1,5 điểm phần trăm, nên nên đọc như khoảng, không phải một số chính xác.
- Top repo mỗi quý đổi theo từng làn sóng: prompt/ChatGPT (đầu 2023: `awesome-chatgpt-prompts`) → agent tự chạy (giữa 2023: `gpt-engineer`, `MetaGPT`) → chạy mô hình cục bộ và RAG (2024: `ollama`, `dify`, `LightRAG`).
- Trong 132 repo có đỉnh ≥50 star/ngày mẫu ở 2023, 89% còn dưới nửa đỉnh sau một năm rưỡi (86% nếu dùng bộ lõi).

**Các phép kiểm tra bộ phân loại và star**

| Phép kiểm | Kết quả | Giới hạn |
|---|---|---|
| Xem tay 52 repo đứng top 8 mỗi quý | 46 đúng, 4 ranh giới, 2 sai (thư viện giao diện, công cụ vẽ sơ đồ); hai repo sai chiếm ≤1,5% star của tập | Thiên về repo nổi tiếng, một người chấm |
| Xem tay 50 repo chỉ khớp qua mô tả (676 repo) | 35 đúng, 9 ranh giới, 6 sai (mẫu quản trị, sách Rust, bot tiền mã hóa...) | Mẫu nhỏ, một người chấm |
| Tài khoản mỏng (≤3 sự kiện trong cả mẫu) | 15,3% người star của tập AI; 0/64 repo top 8 có ≥60% tài khoản mỏng | Mẫu chỉ ~10% số ngày nên yếu hơn bản 2025; "không thấy" chưa phải "không có" |

- Thiên lệch: tập repo xác định từ dữ liệu 2025–2026 nên repo chết trước 2025 không có mặt; con số trên không phải tỉ lệ repo AI chết. Repo đổi tên bị tách lịch sử (chưa xử lý được hết).

## Pipeline và những chỗ tôi làm sai

**Pipeline**
- Tải từng giờ → lọc 5 cột → Parquet → xóa file thô.
- DuckDB đọc trực tiếp Parquet; dbt có 7 mô hình và 28 test.
- Một lệnh `run_pipeline.py` chạy cả chuỗi, dừng ngay khi lỗi, ghi log. Chạy từ đầu mất 70–140 giây (hai lần đo khác nhau): 25 test đạt, 3 cảnh báo có chủ đích.
- Kết quả dbt khớp với các script phân tích ở các chỉ số tôi đã so (số ngày đột biến, giữ chân người đóng góp, độ phủ).
- CI chạy dbt trên dữ liệu tổng hợp có lỗi cài sẵn và báo đỏ nếu test không còn bắt được lỗi.

**Lỗi đã gặp và sửa**
- `build_db.py` bản đầu sao chép dữ liệu vào bảng DuckDB: 9,3 GB so với 2,6 GB Parquet (gấp 3,6 lần). Đổi sang view.
- Một truy vấn thăm dò chiếm 12 GB RAM và tràn 16 GB file tạm. Từ đó mọi script đều giới hạn bộ nhớ và file tạm.
- Lần đầu tìm star đột biến, repo mới ra mắt bị tính nhầm vì mức thường bằng 0. Thêm điều kiện repo phải có lịch sử star.
- Trên dashboard, tôi từng tô cam cả một ngày không có gì bất thường. Chỉ thấy khi mở ảnh chụp màn hình.

## Giới hạn

**Cách xác định repo AI**
- Bản đầu chỉ lọc theo từ khóa trong tên: độ phủ 25% (19/76 repo nổi tiếng chọn tay).
- Sót repo có từ khóa ở tên tổ chức (`modelcontextprotocol/servers`), tên ghép (`vllm`, `comfyui`) và thư viện không có từ khóa (`pytorch`).
- Bản hiện tại thêm topic và mô tả repo (GitHub API, 20.000 repo nhiều star nhất): độ phủ **82%** trên danh sách cũ, **89%** trên danh sách thứ hai (71 repo, viết trước khi chạy bộ phân loại; bộ lọc theo tên chỉ đạt 20% ở đó).
- Độ chính xác giảm: phần thêm từ topic/mô tả đúng khoảng 76–86% (mẫu 50 repo tôi xem bằng mắt), so với ~95% của bộ lọc theo tên.
- Nhóm chỉ khớp qua mô tả (676 repo) kém hơn: mẫu 50 repo cho 35 đúng, 9 ranh giới, 6 sai (mẫu quản trị, sách Rust, bot tiền mã hóa...). Mẫu nhỏ, một người chấm.
- Topic và mô tả là của năm 2026, không phải 03–05/2025. 12% repo không tra được (đổi tên, xóa) nên chỉ khớp theo tên.
- Chỉ xét repo có từ 100 star. Thử thêm 48.081 repo 30–99 star: thêm 6.252 repo AI (xem tay mẫu 50: 41 đúng, 5 ranh giới, 4 sai) nhưng chỉ khoảng 10% star của repo AI, nên chưa đưa vào các phân tích. Hai danh sách kiểm tra do tôi chọn từ trí nhớ, thiên về repo nổi tiếng; repo ít người biết có thể có độ phủ thấp hơn.

**Chung**
- Phân tích chính chỉ dùng 12 tuần dữ liệu (01/03 – 22/05/2025). Mẫu 2023–2024 (72 ngày thứ Tư) chỉ có bản phân tích đầu, tập repo AI thiên lệch người sống sót (xem mục trên).
- Các ngưỡng (50 star, gấp 5 lần, 3 sự kiện, 0,70) do tôi chọn; chỉ ngưỡng star được thử nhiều bộ.
- Đường cơ sở trượt chỉ gắn cờ đợt sụt kéo dài trong vài tuần đầu, nên tôi thêm đường cố định (4 tuần đầu). Dữ liệu thật chỉ có 8 ngày sau điểm sụt, nên khác biệt này mới kiểm chứng bằng dữ liệu tổng hợp; đường cố định cũng không phân biệt được lỗi với thay đổi mức thật.
- Đây là dự án học tập, kết quả mang tính khám phá.

Mã nguồn, các bảng dbt, tài liệu dbt và dashboard nằm cùng kho với bài viết này.
