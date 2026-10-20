# Nguồn dữ liệu công khai mất 35% sự kiện mà không báo, và hệ thống kiểm tra của tôi bắt được

Ngày 20/10/2026 tôi bắt đầu một dự án học dữ liệu: dựng pipeline trên GH Archive (mọi sự kiện công khai của GitHub, mỗi giờ một file) để xem hệ sinh thái AI mã nguồn mở vận động thế nào. Việc đầu tiên tôi làm là đo thử vài giờ mẫu mỗi tháng, và kết quả làm tôi đổi hướng: trong các giờ mẫu đó, số star giảm dần từ giữa năm 2025 và còn rất ít từ tháng 5/2026 (mỗi con số chỉ là một giờ trong tháng, chưa phải cả tháng). Phần còn lại của dự án xoay quanh việc đo điều đó cho chắc và tránh để nó làm hỏng các kết luận khác.

## Điểm sụt nằm giữa tháng 5/2025

Tôi tải 2.208 file giờ từ 01/03 đến 31/05/2025 và so mỗi giờ với trung vị của cùng thứ, cùng giờ trong 4 tuần trước. Nếu một giờ thấp hơn 70% mức đó thì bị gắn cờ. Theo ngày, dữ liệu trông bình thường, vì cả 24 file đều tồn tại. Theo giờ thì khác: từ khoảng 17h UTC ngày 23/05/2025, số sự kiện rơi từ khoảng 250 nghìn xuống 150 nghìn mỗi giờ và không hồi lại. So trung bình mỗi giờ của 12–17/05 với 26–31/05 (cùng các thứ trong tuần), mức giảm là 35,5%. Tôi chưa biết nguyên nhân. Cộng đồng đã báo lỗi mất sự kiện của nguồn này cho chủ kho dữ liệu, nhưng chưa có xác nhận chính thức, và tôi cũng chưa kiểm tra đó có phải cùng nguyên nhân với điểm sụt này hay không.

Cùng bộ kiểm tra còn bắt được một giờ mà tôi đã bỏ sót lúc tải: file 01h UTC ngày 08/05/2025 tải về báo thành công, nhưng chỉ chứa 27.469 sự kiện (12% mức thường) và nặng 11,6 MB thay vì khoảng 105 MB. Script tải của tôi chỉ kiểm tra file có tải được hay không, không kiểm tra nội dung. Từ đó mọi phân tích dừng ở 22/05/2025.

## Star tăng đột biến: đa số là người thật, trừ một repo

Trong khoảng 8.000 repo có tên khớp từ khóa AI, tôi tìm các ngày có ít nhất 50 star và gấp 5 lần trung vị 14 ngày trước. Có 444 ngày như vậy ở 153 repo. Với mỗi ngày, tôi xem người star có "mỏng" không, tức có không quá 3 sự kiện nào trong 12 tuần. Trung bình, ngày đột biến có 7,6% tài khoản mỏng, thấp hơn ngày thường (9,2%): phần lớn đột biến đến từ ra mắt hoặc được chia sẻ rộng.

Một repo lệch hẳn. Tôi gọi nó là Repo X. Ở 4 ngày (11, 12, 14 và 15/04/2025), 85–93% người star là tài khoản mỏng, trong khi ngày thường của chính repo này là 30%. Repo X bị gắn cờ ở cả 9 bộ ngưỡng tôi thử. Để không dừng ở một chỉ số, tôi lấy mẫu người star và hỏi API công khai của GitHub về ngày tạo tài khoản. Nhóm ngày đột biến có tuổi tài khoản trung vị 0 ngày: 20/21 tài khoản đọc được mới tạo chưa đến 30 ngày và 19/21 chưa có repo nào. Hai đợt lan truyền thật làm đối chứng cho kết quả khác hẳn: tuổi trung vị 3.820 ngày (github-mcp-server) và 2.050 ngày (một repo tập hợp system prompt).

Kết quả này chỉ cho biết các tài khoản đó là tài khoản dùng một lần. Nó không cho biết ai tạo ra chúng, nên tôi không gán lỗi cho ai. Mẫu chỉ có 21–24 tài khoản mỗi nhóm trên 3 repo, và hai repo đối chứng là do tôi chọn vì tin chúng là lan truyền thật.

## Người đóng góp mới ít khi ở lại

Với 52.417 người đóng góp (push, PR, issue, bình luận, review; loại bot), tôi chia theo tuần đầu tiên họ xuất hiện rồi đếm bao nhiêu người còn hoạt động sau đó. Sau 1 tuần còn 16,9%, sau 4 tuần 7,6%, sau 8 tuần 5,8%. Người bắt đầu bằng code giữ lại tốt hơn nhiều: 29,8% sau 1 tuần và 12,9% sau 8 tuần, so với 12,5% và 3,3% ở người chỉ để lại issue hoặc bình luận.

Con số này có hai chỗ yếu. Dữ liệu bắt đầu từ 01/03 nên người cũ vắng mặt trong hai tuần đầu bị tính là người mới, làm các cohort đầu cao hơn thực tế; vì vậy xu hướng giảm giữa các cohort không có nghĩa hệ sinh thái yếu đi. Ngoài ra "còn hoạt động" chỉ tính trong tập repo đã lọc, nên người chuyển sang repo khác bị tính là đã rời đi. Tôi chưa có mốc so sánh bên ngoài để nói 17% là cao hay thấp.

## Pipeline và những chỗ tôi làm sai

Pipeline gồm script tải từng giờ (lọc 5 cột, ghi Parquet, xóa file thô), DuckDB đọc trực tiếp Parquet, và dbt với 7 mô hình và 25 test. Một lệnh `run_pipeline.py` chạy cả chuỗi, dừng ngay khi có lỗi và ghi log. Chạy từ đầu mất 166 giây; 23 test đạt, 2 cảnh báo có chủ đích, và kết quả dbt khớp từng con số với các script phân tích viết trước đó.

Một vài lỗi tôi đã gặp và sửa:

- Bản đầu của `build_db.py` sao chép dữ liệu vào bảng DuckDB, nặng 9,3 GB so với 2,6 GB Parquet, gấp 3,6 lần. Tôi đổi sang view để dữ liệu chỉ lưu một lần.
- Một truy vấn thăm dò chiếm 12 GB RAM và tràn 16 GB file tạm ra ổ đĩa. Từ đó mọi script đều đặt giới hạn bộ nhớ và dung lượng file tạm.
- Lần đầu tìm star đột biến, các repo mới ra mắt bị tính là đột biến vì mức thường bằng 0. Tôi thêm điều kiện repo phải có lịch sử star trước đó.
- Ở dashboard, tôi từng tô cam toàn bộ ngày đột biến của Repo X, kể cả một ngày không có gì bất thường. Tôi chỉ phát hiện khi mở ảnh chụp màn hình ra xem.

## Giới hạn chung

Tập repo "AI" ở trên chỉ là tập con theo tên repo, không phải toàn bộ hệ sinh thái. Trên mẫu 40 repo tôi xem bằng mắt, khoảng 95% repo khớp từ khóa thật sự là AI (độ chính xác); nhưng khi tôi đo ngược lại bằng 76 repo AI nổi tiếng chọn tay (độ phủ), bộ lọc chỉ bắt được 19, tức 25%. Nó bỏ sót những repo mà từ khóa nằm ở tên tổ chức (`modelcontextprotocol/servers`, `openai/codex`), tên ghép (`vllm`, `comfyui`, `autogpt`) hoặc thư viện nổi tiếng không có từ khóa nào (`pytorch`, `tensorflow`). Các kết luận về star và giữ chân người đóng góp vì vậy chỉ đúng cho nhóm repo có tên khớp từ khóa, và tôi chưa biết chúng lệch bao nhiêu so với phần còn lại. Danh sách 76 repo do tôi chọn tay từ trí nhớ và thiên về repo nổi tiếng, nên con số 25% có thể vẫn là mức tốt hơn thực tế cho các repo ít người biết.

Toàn bộ kết quả dựa trên 12 tuần dữ liệu (01/03 – 22/05/2025); dữ liệu 2023–2024 tôi chưa tải vì mạng chậm. Các ngưỡng (50 star, gấp 5 lần, 3 sự kiện, 0,70) do tôi chọn và chỉ ngưỡng của star được thử nhiều bộ. Lớp kiểm tra chất lượng dùng đường cơ sở trượt, nên một đợt sụt kéo dài chỉ bị gắn cờ trong vài tuần đầu. Đây là dự án học tập, các kết quả mang tính khám phá.

Mã nguồn, các bảng dbt và dashboard nằm cùng kho với bài viết này.
