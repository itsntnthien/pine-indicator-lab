# Cài chỉ báo trên TradingView

## Chọn đúng file

| Bạn muốn quan sát | Script |
|---|---|
| Setup intraday dựa trên vùng HTF | [ICT Intraday](../dist/intraday/ICT_INTRADAY_EXPERIMENTAL.pine) |
| Cấu trúc, thanh khoản và vùng bối cảnh | [SMC / ICT Observer](../dist/lux_custom/SMC_ICT_OBSERVER.pine) |
| VSA kết hợp sweep/cấu trúc và điều kiện hội tụ | [VSA Observer v3](../dist/vsa_observer/VSA_OBSERVER_V3.pine) |

Đọc [trạng thái kiểm chứng](VERIFICATION.md) của script trước khi chọn. Repo không
quy định một chỉ báo chính đã được chấp nhận để giao dịch.

## Thao tác cài đặt

1. Đăng nhập GitHub bằng tài khoản có quyền xem repo Private.
2. Mở file trong bảng trên, chọn Raw, sao chép toàn bộ nội dung; dòng đầu phải là
   `//@version=6`. Không sao chép Markdown hoặc các dấu backtick.
3. Mở Pine Editor trong TradingView và tạo indicator mới.
4. Thay toàn bộ nội dung editor bằng script vừa sao chép, lưu bằng tên riêng.
5. Add to chart; chọn chart nến tiêu chuẩn và đúng feed/symbol.
6. Chờ đủ dữ liệu warmup. Kiểm tra bảng trạng thái trước khi đọc bối cảnh.

Giới hạn editor/chart/alert có thể phụ thuộc tài khoản TradingView. Không cần
publish script lên thư viện TradingView để dùng riêng.

## Feed và khung thời gian

- **ICT Intraday:** M5 dùng H1; M15 dùng H4. Phạm vi đã nghiên cứu là
  OANDA:XAUUSD và FOREXCOM:NAS100. Các khung H1/H4 chủ yếu dùng quan sát bối cảnh.
- **SMC / ICT Observer:** ma trận lịch sử gồm M5/M15/H1/H4 trên hai feed trên;
  không suy rộng kết quả sang feed khác. Xem quy tắc HTF trong hướng dẫn riêng.
- **VSA v3:** hỗ trợ ánh xạ M1/M3/M5/M15/M30/H1/H4 theo bảng trong
  [đặc tả](VSA_OBSERVER_V3.md). Warmup mặc định 600 nến cho hội tụ; thiếu volume
  hoặc HTF phải được xem là thiếu dữ liệu, không phải tín hiệu trung tính hợp lệ.

Không dùng Heikin Ashi/Renko hoặc nến tổng hợp để diễn giải các quy tắc OHLC chuẩn.
Giá và volume khác feed có thể làm kết quả khác nhau.

## Input và cách đọc

**SMC / ICT:** bật/tắt cấu trúc, vùng HTF/chart, premium/discount và dashboard.
Tên TĂNG/GIẢM biểu thị trạng thái thuật toán; không phải lệnh vào. Các vùng mới
khả dụng tại thời điểm xác nhận, dù được liên hệ tới một nến nguồn cũ.

**VSA:** chọn vị trí/cỡ dashboard, Present/Historical và số đối tượng hiển thị.
Giới hạn vẽ không phải giới hạn dữ liệu tính toán. Dấu ✓ biểu thị điều kiện
đã thỏa; hội tụ không phải xác suất thắng hoặc lệnh giao dịch.

**Intraday:** đọc [định nghĩa setup](INTRADAY_V1.md) về vùng, cửa sổ xác nhận,
cực trị và snapshot; không xem các mức tham chiếu như mô hình khớp lệnh broker.

## Nâng cấp và quay lại

- Lưu bản cũ trước khi thay mã. Dùng một instance cho mỗi chỉ báo để tránh chồng UI.
- Sau thay đổi input/default, kiểm tra lại Settings; instance cũ có thể giữ input
  đã lưu. Dùng Reset settings khi cần áp dụng bộ mặc định của bản mới.
- VSA v2 được giữ tại [XAU_VSA_OBSERVER.pine](../dist/vsa_observer/XAU_VSA_OBSERVER.pine)
  làm baseline hồi quy/rollback. Đây là bản đóng băng, không phải v3 mới nhất.
- Nếu dùng alert, kiểm tra lại điều kiện và input khi đổi phiên bản. Lần đóng gói
  này chưa kiểm thử server alert delivery.

## Xử lý vấn đề thường gặp

| Hiện tượng | Kiểm tra |
|---|---|
| Lỗi thiếu hàm/biến sau khi dán | Có dùng toàn bộ file `dist/*.pine`, thay vì một module `src/`, hay không |
| Bảng hoặc đường vẽ bị trùng | Có nhiều instance chỉ báo đang bật hay không |
| Hội tụ không sẵn sàng | Warmup, volume, ATR, HTF, khung hỗ trợ và nến tiêu chuẩn |
| Kết quả khác một ảnh cũ | Phiên bản/hash, feed, timeframe, input và phạm vi dữ liệu |
| Python test đạt nhưng Pine báo lỗi | Hai cổng kiểm chứng khác nhau; ghi lỗi native, không bỏ qua |

Báo lỗi với tên script, SHA trong manifest, symbol/feed, khung, input và mô tả
các bước tái hiện. Không gửi cookie, tài khoản broker hoặc private key.
