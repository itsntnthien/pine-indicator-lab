> **Tài liệu lịch sử.** Các kết quả dưới đây thuộc lượt phát triển được ghi ngày trong tài liệu. Trạng thái đóng gói hiện tại ở VERIFICATION.md (`VERIFICATION.md`, tài sản lịch sử ngoài bản chọn lọc). Đường dẫn ghi dạng văn bản tới kho dữ liệu/log ngoài bản chọn lọc không có trong clone.

# Kiểm chứng ICT Intraday và tái sử dụng dữ liệu cũ

Cập nhật ngày 2026-11-15 (giờ Việt Nam); bằng chứng TradingView được thu ngày 2026-11-14. **Compile và chạy chart đã đạt ở các lượt quan sát; nghiệm thu E2E chưa đạt.** Không chứng nhận lợi nhuận hoặc khớp lệnh.

## Những tài sản cũ đã sử dụng

Đã tra catalog 1.038 bản ghi/817 đường dẫn dữ liệu và tìm tên liên quan NAS100/US100/USTEC/NASDAQ/NDX/NQ/FOREXCOM trong 281 ZIP, tổng 865.870 entry. Không tìm thấy ứng viên NAS qua phép tìm tên này; không có nghĩa mọi file có tên chung đều đã được phân loại theo nội dung. Không giải nén toàn bộ, không đọc giá holdout.

| Nguồn giá đã xác minh hash | Số nến | HTF dựng lại | Setup Python |
|---|---:|---:|---:|
| OANDA XAUUSD M5 (`../data/ds-c887bbc8c83a486f/8b93065c867ccbeb/XAUUSD_OANDA_M5.csv`, tài sản lịch sử ngoài bản chọn lọc) | 5.723 | 476 H1; bỏ 2 kỳ thiếu nến | 133: BUY 72, SELL 61 |
| OANDA XAUUSD M15 (`../data/ds-480fd665ccafca84/9ff3225d7ff84d67/XAUUSD_OANDA_M15.csv`, tài sản lịch sử ngoài bản chọn lọc) | 2.405 | 130 H4; bỏ 33 kỳ thiếu nến | 32: BUY 10, SELL 22 |

Hai file là dữ liệu validation cũ, từ tháng 6–7/2026. Đã dùng lại `resample` và `OHLCBar` của harness pivot; oracle mới cũng dùng `true_ranges` cũ. Chạy lại toàn bộ và ba đoạn lịch sử cắt ngắn đều giữ nguyên snapshot setup/open; kiểm tra nguồn chỉ được dùng sau xác lập, không dùng hai lần, SL có risk dương. Cả sáu loại nguồn vùng đều xuất hiện.

Giới hạn: HTF được ghép theo UTC, thời điểm đóng LTF là danh nghĩa, tick lịch sử giả định 0,001. Chúng phù hợp cho hồi quy offline nhưng chưa chứng minh nến H1/H4 đúng biên phiên OANDA hoặc ATR khớp Pine. Các cột tín hiệu của chỉ báo cũ không được dùng làm đáp án cho chỉ báo mới. Không dùng giá khác feed làm bằng chứng NAS100.

Lệnh tái lập:

```powershell
python -B tools/check_intraday_legacy.py
python -B -m unittest discover -s tests -v
```

## Kết quả native TradingView

Bản ghép SHA-256 `6a86470dad0992b87502b973b462fc0e9a9e8822de3896bda11128993232d2dc`, build token `158879367533117`.

Đã sửa biến `text` bị Pine từ chối thành `setupText`; compiler sau sửa báo `Compiled.` và `Updated on chart.`. Đã chỉnh indicator dùng chung thang giá phải với nến: trước đó layout để `No scale`, gây vùng/SL/TP trông lệch dù giá trong bảng đúng. Đây là thiết lập layout, không phải thay đổi công thức giá.

| Feed / chart | Runtime quan sát | SETUP + OPEN xuất được | So sánh reload |
|---|---|---:|---|
| OANDA:XAUUSD M5 | Đạt | 119 + 119 | Log giống từng byte |
| OANDA:XAUUSD M15 | Đạt | 129 + 129 | Chưa thu log reload |
| FOREXCOM:NAS100 M5 | Đạt | 150 + 150 | **7 dòng SETUP khác ATR** |
| FOREXCOM:NAS100 M15 | Đạt | 131 + 131 | Log giống từng byte |
| Cả hai feed H1/H4 | Chỉ quan sát, không phát SETUP | 0 | Chưa kiểm tra reload riêng |

529 setup có cả BUY/SELL, đủ sáu loại vùng, trường hợp nhiều nguồn, thiếu TP và RR thấp. [Checker log](../tools/check_intraday_logs.py) xác nhận ID, thời điểm khả dụng nguồn, dùng nguồn một lần, làm tròn SL và RR/open theo dữ liệu được ghi. Đây là kiểm tra tính nhất quán của log, không phải đối chiếu tính đúng của thuật toán từ OHLC. Không có mẫu gap bất lợi native trong tập này; trường hợp đó được kiểm bằng fixture tổng hợp.

NAS100 M15 với Heikin Ashi hiển thị yêu cầu nến giá tiêu chuẩn và không tạo setup; sau đó đã chuyển lại Candles. Data Window NAS cho mintick 0,1 và build token đúng. Tick OANDA 0,001 trong checker chưa được xác nhận riêng bằng bản chụp audit Data Window.

### Sai khác chưa giải thích được

NAS100 M5 có cùng 150 ID setup, nguồn, cực trị, SL/TP và 150 open, nhưng 7 giá trị ATR sau reload khác lần đầu. Ví dụ nến 2026-11-12 06:00 +07:00: `42.7161985428` → `42.6233413999`. Sai khác giảm ở các nến tiếp theo. **Chưa xác định nguyên nhân; chưa chứng minh đầu vào OHLC hai lượt giống nhau.** Không tự kết luận do feed, không sửa thuật toán hoặc nới dung sai để che kết quả.

Chi tiết từng dòng: reload-comparison.json (`../evidence/intraday/native-20261114/reload-comparison.json`, tài sản lịch sử ngoài bản chọn lọc). Cần thu cùng OHLC/history seed và chạy lại để phân biệt thay đổi dữ liệu với lỗi trạng thái. Dữ liệu OANDA cũ không giải quyết được sai khác NAS này.

## Giới hạn E2E và việc còn lại

Trong phiên tài khoản đã thử, TradingView hiển thị giới hạn khi xuất chart CSV, chạy intraday Bar Replay và tạo technical alert (0 alert). Không có alert được tạo, không kiểm chứng được thông báo đến điện thoại. Không vượt paywall hoặc mua gói. Vì thiếu CSV LTF/HTF cùng build và đủ lịch sử, chưa chạy numerical parity Pine/Python. Thị trường đóng cửa trong phiên thử nên chưa kiểm chứng realtime tick/alert dedup.

Sau khi môi trường công cụ đổi, phiên điều khiển browser cũ không còn sẵn để tiếp tục thu log; lượt này hoàn tất kiểm tra các file bằng chứng đã có. Các gate cần tiếp tục: giải thích NAS M5 ATR; reload OANDA M15; numerical parity trên cả hai feed; Bar Replay; realtime alert/dedup và app delivery. Các ảnh H4 NAS trước sửa scale chưa phải bằng chứng bố cục cuối cùng.

Đã thấy 11 script lưu trong tài khoản, trong khi hộp giới hạn báo chỉ cho 1 script. Chart vẫn có hai bản cũ XAU-VSA/XAU-SCALP-R1; chưa xác định chắc biến thể Evolution nào là nguồn của XAU-VSA. Chưa xóa script nào. Bản mới đã chạy trên chart nhưng chưa lưu thành script độc lập trong tài khoản. Xóa các bản dư không mở quyền CSV/Replay/alert và chưa chắc giải quyết được giới hạn lưu khi vẫn giữ hai script đang có. Source mới đầy đủ vẫn nằm trong workspace.

## Kiểm thử và bằng chứng

Lượt chạy toàn workspace ngày 2026-11-15: 58 unittest đạt (gồm 31 test intraday), 154 test + 18 subtest nghiên cứu đạt, 49 test observer đạt, 22 test pivot đạt. Trong pivot có 11 placeholder, không tính chúng là bằng chứng hành vi. Không điều chỉnh tham số từ kết quả này.

- Trạng thái và hash hiện tại (`../evidence/intraday/verification.json`, tài sản lịch sử ngoài bản chọn lọc).
- Bằng chứng native, ảnh và CSV log (`../evidence/intraday/native-20261114/`, tài sản lịch sử ngoài bản chọn lọc).
- Hồi quy dùng dữ liệu cũ (`../evidence/intraday/native-20261114/legacy-regression.json`, tài sản lịch sử ngoài bản chọn lọc).
- NAS M5 sau sửa scale (`../evidence/intraday/native-20261114/nas-m5-scale-fixed.png`, tài sản lịch sử ngoài bản chọn lọc).

Chưa đánh giá P/L, chi phí, khớp lệnh hay hiệu quả ngoài mẫu. Chưa đạt điều kiện tuyên bố chỉ báo sẵn sàng giao dịch thực tế.
