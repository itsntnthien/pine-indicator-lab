> **Tài liệu lịch sử.** Các kết quả dưới đây thuộc lượt phát triển được ghi ngày trong tài liệu. Trạng thái đóng gói hiện tại ở VERIFICATION.md (`VERIFICATION.md`, tài sản lịch sử ngoài bản chọn lọc). Đường dẫn ghi dạng văn bản tới kho dữ liệu/log ngoài bản chọn lọc không có trong clone.

# VSA Observer v3 RC

File dùng trên TradingView: `dist/vsa_observer/VSA_OBSERVER_V3.pine`. Pine v6, một indicator overlay; không có lệnh, nhãn BUY/SELL hoặc tính khối lượng giao dịch. Bản v2 được giữ nguyên để quay lại.

## UI chuyển từ các nguồn LuxAlgo

Lượt trước chỉ tham khảo màu và đường cấu trúc. Lượt này thay toàn bộ các lớp trình bày hiện có bằng cách tổ chức từ sáu nguồn LuxAlgo open-source; danh mục 114 nguồn đã được quét thành `output/playwright/vsa-v3-lux-system/catalog-ui-inventory.json`. Không tuyên bố đã chạy hoặc nhập cả 114 thuật toán.

| Thành phần Observer | Nguồn UI | Cách áp dụng |
|---|---|---|
| Inputs / palette / nhãn cấu trúc | Smart Money Concepts (CnB3fSph) | Nhóm và hàng inline; màu bullish/bearish chỉnh riêng; Colored/Monochrome; nhãn trong suốt đặt giữa đoạn ngang. |
| Dashboard | Market Structure Fractal (ZpHqSrBK) | Nền #1e222d, viền #373a46 rộng 1, tiêu đề gộp, hai cột hướng, cỡ Tiny/Small/Normal. Nội dung là nhận định Observer. |
| OB và đường trung điểm | Order Block Detector (KvGhxGxY) | Vùng kéo dài sang phải, viền nhạt, đường ngang nét đứt đúng trung điểm hình học. |
| Quét | Liquidity Sweeps (JRqryeJ5) | Hộp mờ từ mức quét đến cực trị râu và nét dọc rộng 3; nhãn × có tooltip. |
| Thanh khoản / display mode | Buyside & Sellside Liquidity (Qk4vBbfL) | Tên Buyside/Sellside trên mức; Present/Historical chỉ đổi dữ liệu được vẽ. |
| FVG / tổ chức lớp | ICT Concepts (ib4uqBJx) | FVG +/−, màu xanh/đỏ riêng, nhóm Market Structure/Liquidity/OB/FVG. |

Nguồn, phiên bản, hash và phần phái sinh: `docs/VSA_OBSERVER_LUX_UI_SOURCES.json`. UI phái sinh ghi công © LuxAlgo, **CC BY-NC-SA 4.0** (phi thương mại, chia sẻ cùng giấy phép). Không phải sản phẩm chính thức LuxAlgo. Lõi tính toán vẫn của Observer.

Bảng hai cột **HỒI LÊN / HỒI XUỐNG**: Quét đáy/đỉnh, Cấu trúc, Chờ điều kiện còn thiếu; rê cột để đọc lý do chặn, mức hủy, vùng tham chiếu, VSA và EMA. ✓ chỉ là tiêu chí đã đạt, không phải lệnh vào. Header ghi symbol, khung và giờ đóng nến theo giờ Việt Nam; tooltip có ngày. Footer hiển thị hướng thân hai nến lớn đã đóng và cảnh báo dữ liệu. Hướng thân nến lớn không đồng nghĩa xu hướng cấu trúc.

Dashboard mặc định **Giữa trái**, tránh nhãn giá ở cạnh phải trên cửa sổ hẹp; có ba góc cũ để chọn. Đây là điều chỉnh vị trí cho Observer, không tuyên bố mặc định này lấy nguyên xi từ Fractal. Cỡ chữ mặc định Nhỏ như bảng nguồn, có Vừa và Rất nhỏ.

Present vẽ cấu trúc cuối mỗi hướng trong bộ lịch sử đang giữ; Historical vẽ toàn bộ bộ đệm (mặc định 12, tối đa 40). Chỉ thay cách trình bày, không sửa lịch sử dùng trong tính toán. Các đoạn bắt đầu ở pivot nguồn nhưng chỉ xuất hiện sau nến xác nhận phá. Swing là cấu trúc của lõi hiện tại; không đổi nhãn sang MSS, Strong/Weak hay EQH/EQL khi lõi không có định nghĩa tương ứng.

OB/FVG có màu, số vùng và Extend riêng trong Inputs; đường 50% chỉ là trung điểm vùng. Dấu · sau tên vùng đánh dấu vùng được bảng tham chiếu; không phải xác suất hoặc điểm vào. Tắt tên vùng cũng tắt tên các mức. Khi bật thanh khoản, ẩn tên swing để tránh hai tên chồng nhau trên cùng mức. EMA/dải tham chiếu và nhãn VSA chi tiết vẫn có trong nhóm VSA / Reference.

## Quy tắc tính toán đã chốt

- Chỉ commit khi nến chuẩn đóng. Nến đang chạy không thay snapshot, lịch sử cấu trúc hoặc vùng đã commit.
- Swing xác nhận 5 trái/5 phải. Pivot có thời điểm nguồn và thời điểm xác nhận riêng; không coi vị trí nguồn là thời điểm có thể biết pivot.
- Pool giữ đến khi giá đóng phá mức hoặc hết tuổi 500 nến. FVG/OB giữ tối đa 250 nến, tuổi bằng giới hạn vẫn hợp lệ. Giới hạn vẽ không loại dữ liệu tính toán. Trần bất biến: 1.002 pool, 251 FVG, 251 OB; vi phạm dừng bằng lỗi rõ ràng, không âm thầm cắt dữ liệu.
- Quét là giá vượt pool rồi đóng lấy lại mức. Giá đóng đúng cực trị quét chưa vô hiệu; đóng vượt mới vô hiệu và trạng thái này được giữ đến lần quét mới.
- Quét và BOS/CHoCH cùng nến: **chờ giữ mức**. Chỉ nến kế tiếp đóng tiếp bên kia mức phá mới xác nhận. Nếu thất bại, cần một sự kiện cấu trúc mới; sự kiện cũ không tự hồi sinh khi giá trở lại.
- Một lần quét mới reset bằng chứng cấu trúc của chu kỳ trước. Tuổi setup hợp lệ 0–10; từ 11 hết hạn. Quét hai phía còn hiệu lực chặn hội tụ.
- FVG cần ba nến liên tục theo `time/time_close`; gap nghỉ phiên không được tính như FVG liên tục. OB chỉ xuất hiện khi có phá cấu trúc và FVG cùng hướng; nến nguồn khác nến xác nhận. Retest OB bắt đầu từ nến sau xác nhận, kể cả nến tạo OB đã giao với biên nguồn.
- VSA vẫn giữ ngưỡng cơ sở: volume tương đối so với 20 nến trước, biên nến tương đối và vị trí đóng. Cần 21 nến volume dương liên tục. Một nến thiếu/0 làm VSA chưa sẵn sàng cho đến khi đủ lại cửa sổ; giá/quét/cấu trúc vẫn hoạt động.
- Warmup hội tụ: `max(21, 3 × chu kỳ EMA)`, mặc định 600 nến. ATR14; khoảng cách EMA >2,5 ATR chặn hội tụ.
- Thiếu volume/ATR/warmup/HTF, khung ngoài danh sách hoặc nến phi tiêu chuẩn không được báo đầy đủ hội tụ. VSA là mẫu OHLC/volume, không xác minh dòng tiền tổ chức hay pha Wyckoff hoàn chỉnh.

| Khung chart | Xác nhận | Neo |
|---|---|---|
| M1 | M5 | M15 |
| M3 | M15 | H1 |
| M5 | M15 | H1 |
| M15 | H1 | H4 |
| M30 | H1 | H4 |
| H1 | H4 | D |
| H4 | D | W |

HTF dùng dữ liệu native đã đóng. Hai request hiện tại/prior được kiểm tra timestamp; không dùng nến tương lai. Tên symbol/feed ảnh hưởng OHLC và ý nghĩa volume: kiểm thử trên OANDA/FOREXCOM không chứng nhận dữ liệu trùng Exness.

## Hiển thị và hiệu năng

Các slot cố định: 11 mức + 14 đường giữa vùng + N đoạn cấu trúc, 14 box vùng, N nhãn cấu trúc và 11 nhãn mức. N = giới hạn cấu trúc (2–40). Thêm tối đa `eventLimit` hộp quét, nét râu và nhãn sự kiện (2–120). Renderer tái sử dụng slot; hộp quét cũ được xóa khi vượt giới hạn. Giới hạn hình vẽ không cắt dữ liệu tính toán.

Khi thay mã trên instance cũ: **Settings → Defaults → Reset settings → Ok** để áp dụng nhóm Inputs và mặc định mới. Không cần Save as default tài khoản. Chỉ giữ một bản Observer để tránh hai dashboard trùng nhau. Lượt này không đổi website, theme TradingView, màu nến nền tảng hoặc tự tạo alert.

## Những giả thuyết chưa đưa vào mặc định

Đã chạy nghiên cứu phát triển cho HTF cấu trúc 5/5, chuẩn hóa volume theo cùng phút trong 20 phiên trước (tối thiểu 10), thời hạn bằng chứng VSA ba nến, và bộ lọc FVG middle-close + 0,05/0,10 ATR. Biến thể FVG chạy qua engine nghiên cứu riêng, bao gồm tạo OB phụ thuộc và chọn vùng. Mỗi nến đều kiểm tra rằng nó không thay bộ điều kiện hội tụ độc lập; FVG vốn chỉ là bối cảnh trong chỉ báo này.

Toàn bộ archive đã được xem trong các lượt trước nên được ghi là **development**, không gọi lại phần cuối là holdout độc lập. Chưa có archive NAS100 cùng feed và chưa xác minh thời điểm đóng D/W trong archive Exness. Không ứng viên nào được promote. Báo cáo: `research/vsa-v3-20261119/study.json`.

Trước khi promote: từng symbol/khung cần ít nhất 100 quan sát development và 50 holdout mới, không chồng chân trời 10 nến; giữ ít nhất 50% mẫu. Cần CI 95% của chênh lệch MFE10−MAE10 theo các block phiên ghép cặp lớn hơn 0. Đây là tiêu chí nghiên cứu đặt trước, không phải bảo đảm lợi nhuận.

## Cài và quay lại

Mở Pine Editor, tạo indicator mới, dán toàn bộ file v3 rồi Add to chart. Khi kiểm tra, chỉ giữ một bản Observer để tránh hai dashboard/nhãn trùng nhau. Bật Inputs → Bảng quan sát; cỡ Nhỏ, vị trí Giữa trái là mặc định.

Muốn quay lại: bỏ instance v3 và dùng `dist/vsa_observer/XAU_VSA_OBSERVER.pine` v2. Không cần sửa website hoặc chạy Python để dùng chỉ báo.

Trạng thái bàn giao là **RC**: xem `evidence/vsa_observer/v3-lux-system-acceptance.json` và `docs/VSA_OBSERVER_V3_E2E.md` để phân biệt kiểm tra đã chạy với các cổng chưa hoàn tất. Chưa có kiểm thử realtime 24 giờ mỗi feed hay bằng chứng hiệu quả giao dịch.
