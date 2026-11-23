> **Tài liệu lịch sử.** Các kết quả dưới đây thuộc lượt phát triển được ghi ngày trong tài liệu. Trạng thái đóng gói hiện tại ở VERIFICATION.md (`VERIFICATION.md`, tài sản lịch sử ngoài bản chọn lọc). Đường dẫn ghi dạng văn bản tới kho dữ liệu/log ngoài bản chọn lọc không có trong clone.

# SMC ICT Observer — native TradingView validation, 2026-11-16

Đã compile và chạy trực tiếp trong TradingView bằng trình duyệt tích hợp Codex, qua UI/Pine Editor và Playwright locators. Không dùng web mô phỏng TradingView. **Compile đạt; parity trong ma trận đạt; toàn bộ E2E có giới hạn và có gate không đạt**, được giữ nguyên dưới đây.

## Đúng bản được kiểm tra

- Production: `dist/lux_custom/SMC_ICT_OBSERVER.pine`, 522 dòng, SHA256 `5b5dfcb788360bfae69fb52d9202262bdebf01a6d1b5cfd09359437722d1dee1`, build token `64157540051458`.
- Không sửa logic production trong lượt kiểm tra này. Không thêm BUY/SELL, entry, SL/TP hoặc strategy.
- Native compiler hiển thị `Compiled.` và `Updated on chart.` lúc 11:17:45 và 11:39:49 giờ Việt Nam. Bằng chứng cuối (`../output/playwright/lux-observer-20261116/compile-final.txt`, tài sản lịch sử ngoài bản chọn lọc), ảnh (`../output/playwright/lux-observer-20261116/compile-final.jpg`, tài sản lịch sử ngoài bản chọn lọc).
- Đối chiếu clipboard editor với file production (`../output/playwright/lux-observer-20261116/base-editor-verification.json`, tài sản lịch sử ngoài bản chọn lọc): đúng SHA, byte-equal sau chuẩn hóa CRLF/LF.
- Parity sử dụng bản audit chỉ nối logger và hai request OHLC H1/H4, SHA `dee0842e91a902aee36a03fda50139f48f964bcc88ffeb769c434362df132eb1`. Mã audit (`../output/playwright/lux-observer-20261116/OBSERVER_AUDIT.pine`, tài sản lịch sử ngoài bản chọn lọc), manifest (`../output/playwright/lux-observer-20261116/OBSERVER_AUDIT.json`, tài sản lịch sử ngoài bản chọn lọc), editor hash (`../output/playwright/lux-observer-20261116/editor-source-verification.json`, tài sản lịch sử ngoài bản chọn lọc). Bản audit không phải file người dùng cần cài.

## Ma trận native và đối chứng Python

Pine Logs được tải qua nút Download logs của TradingView. Oracle tuần tự nhận **chính OHLC đã log từ native**, đúng mintick từng feed; không so sánh hai nhà cung cấp giá khác nhau. History phải bắt đầu bar_index 0, liên tục, đúng token. Sai số float tối đa `1e-8`, không điều chỉnh để làm pass.

| Feed | Khung | Nến đã đóng | Phép đối chiếu | Sai lệch |
|---|---:|---:|---:|---:|
| FOREXCOM:NAS100 | M5 | 5.594 | 105.253 | 0 |
| FOREXCOM:NAS100 | M15 | 6.935 | 130.349 | 0 |
| FOREXCOM:NAS100 | H1 | 5.247 | 99.045 | 0 |
| FOREXCOM:NAS100 | H4 | 5.986 | 107.704 | 0 |
| OANDA:XAUUSD | M5 | 5.585 | 103.759 | 0 |
| OANDA:XAUUSD | M15 | 6.911 | 129.262 | 0 |
| OANDA:XAUUSD | H1 | 5.164 | 97.117 | 0 |
| OANDA:XAUUSD | H4 | 5.992 | 107.990 | 0 |
| **Tổng** | | **47.414** | **880.479** | **0** |

Kết quả máy đọc và hash CSV (`../output/playwright/lux-observer-20261116/matrix-final.json`, tài sản lịch sử ngoài bản chọn lọc). Đây là tổng bar-executions của các khung có thời gian chồng nhau, không phải 47.414 thời điểm độc lập. Tất cả tám export không trùng log.

Đối chiếu mỗi nến: ATR14, internal/swing break và loại break, bias, sweep/EQ, inversion, số vùng/pool, nhận định, thời điểm HTF đã khả dụng. Toàn bộ thuộc tính vùng/pool được snapshot mỗi **50 nến**, không phải mỗi nến. Oracle không độc lập về đặc tả: nó triển khai lại cùng quy tắc trong Python; parity không chứng minh đặc tả SMC đúng hay có lợi nhuận.

Đối chứng chéo OHLC H1/H4 native với tuple mà M5/M15 nhận: tám tổ hợp đều 0 sai lệch. Bias H1/H4 cũng khớp oracle HTF sau 500 nến warmup; mọi nến LTF có overlap trong các export này đều nằm sau warmup. Kết quả (`../output/playwright/lux-observer-20261116/htf-cross-check.json`, tài sản lịch sử ngoài bản chọn lọc). Chưa chứng minh parity từng biên vùng SR/SD/OB/FVG HTF hoặc bias D1/W1.

## E2E giao diện và lịch sử

| Kịch bản | Kết quả và phạm vi |
|---|---|
| Bật/tắt 5 lớp hiển thị | Tắt toàn bộ: CSV byte-equal baseline XAU M5; ảnh xác nhận lớp Observer được ẩn. Drawings cũ của người dùng được giữ. |
| Bật cả previous high/low, nền phiên; giới hạn vùng 16 | Hiển thị được; 5.585 nến chung không đổi. Export có 1 bản ghi trùng hoàn toàn, gate log-uniqueness FAIL. |
| Heikin Ashi | Bảng báo cần chart nến tiêu chuẩn; không phát event/vùng/pool chart. 5.586 nến kiểm tra guard. Không thử mọi loại chart tổng hợp. |
| Chart D1 | Bối cảnh H1/H4 không được diễn giải như HTF; chart structure vẫn chạy. |
| Bar Replay D1 thật | Start, tiến 1 bước rồi tổng 5 bước, thoát Replay không lưu. 9.998 / 9.990 / 9.994 nến overlap có 0 trường thay đổi khi so prefix/bản đầy đủ. Chỉ bỏ trường wrapper feed chứa Replay session ID ở phép so cuối. |
| Đổi khung rồi quay lại NAS M15 | 6.935 nến chung, không thay đổi trường đã log. |
| Yêu cầu reload trong cùng tab | NAS M5 5.597 và XAU M5 5.586 nến chung không đổi; **không dùng làm bằng chứng chắc chắn document đã khởi động lại**, vì draft chưa lưu có thể giữ trạng thái. |
| Mở tab/document mới và compile audit lại | Native parity riêng 5.599 nến / 105.328 phép kiểm tra đạt. So với phiên cũ có khác dữ liệu, chi tiết bên dưới. |

So sánh các lần chạy (`../output/playwright/lux-observer-20261116/run-comparison.json`, tài sản lịch sử ngoài bản chọn lọc), toggle/HA (`../output/playwright/lux-observer-20261116/toggle-ha-parity.json`, tài sản lịch sử ngoài bản chọn lọc), parity phiên mới (`../output/playwright/lux-observer-20261116/cold-parity.json`, tài sản lịch sử ngoài bản chọn lọc).

### Gate không đạt: bất biến tuyệt đối giữa hai document

5.594 nến chung NAS M5 có **691 trường log thay đổi**: 5 trường OHLC trên 3 nến, 630 giá trị ATR, 12 H1 close, 36 H4 close và 8 snapshot vùng. Không có thay đổi trường sự kiện, bias hoặc câu nhận định trong phần chung đã log.

Ví dụ timestamp `1794347700000`: close phiên đầu `27803.1`, phiên mới `27802.9`; timestamp `1794438000000`: open/high từ `28342.4` thành `28343.7`. Giá đầu vào khác được quan sát trực tiếp trong native export. Đây là bằng chứng dữ liệu nhận về thay đổi giữa hai lần tải, chưa xác định thay đổi phát sinh tại broker hay bộ nhớ/cache TradingView. Cả hai lần đều khớp oracle khi dùng bộ OHLC tương ứng. **Không gọi kết quả này là pass reload tuyệt đối hoặc cam kết non-repaint bất kể nguồn giá.** Tool comparison giữ exit code 1 cho gate này.

### Log trùng và giới hạn logger

Replay step1 có 1 log trùng, step5 có 5; một số capture bật tùy chọn/reload XAU có 1. Nội dung trùng giống hệt, không có conflicting duplicate. Checker mặc định từ chối duplicate; tùy chọn collapse chỉ cho đối chiếu ngữ nghĩa và vẫn ghi `log_uniqueness: FAIL`. CSV gốc được giữ. Không suy ra từ log trùng rằng alert sẽ gửi trùng hay không gửi trùng.

Bản logger thử nghiệm ban đầu snapshot toàn bộ state mỗi nến gặp `Memory limits exceeded`. Đã giảm snapshot xuống mỗi 50 nến, giữ event/count mỗi nến; ma trận và phiên mới sau sửa chạy được. Lỗi này thuộc phần instrumentation, không xuất hiện trên bản production đã kiểm tra. Bằng chứng lỗi ban đầu (`../output/playwright/lux-observer-20261116/audit-memory-limit.txt`, tài sản lịch sử ngoài bản chọn lọc).

Pine Logs giới hạn 10.000 record: export D1 bắt đầu giữa lịch sử, không đủ seed từ bar_index 0 nên **không chạy/không tuyên bố full D1 Python parity**. Replay D1 chỉ chứng minh prefix trên phần overlap.

## Giới hạn còn lại

- Intraday Bar Replay bị màn hình nâng cấp tài khoản chặn. Ảnh gate (`../output/playwright/lux-observer-20261116/intraday-replay-blocked.jpg`, tài sản lịch sử ngoài bản chọn lọc). Không mua gói, không vượt paywall. D1 Replay đã thực hiện không thay thế được intraday Replay.
- Chưa kiểm chứng alert server gửi thực tế, duplicate delivery, webhook hoặc realtime nhiều giờ/ngày. Không tạo alert hay giao dịch.
- Chưa test feed khác, mọi loại chart, mobile và mọi kích thước màn hình. Có kiểm tra UI thực tế tại hai viewport sẵn có 880×885 và 1280×720; không phải responsive matrix đầy đủ.
- Chưa có benchmark CPU/memory production định lượng hoặc chứng minh không lỗi ở mọi lịch sử. Ảnh/chart chỉ chứng minh các tình huống đã chạy.
- Không backtest lợi nhuận vì đây là chỉ báo quan sát, không có động cơ vào lệnh.

## Tái lập và bàn giao

21 unit tests custom/checker và 31 test module intraday đều chạy lại đạt ở lượt này (52 tests). Log kiểm thử (`../evidence/lux_custom/native-unit-tests.json`, tài sản lịch sử ngoài bản chọn lọc). Có negative controls: sai ATR, token, thiếu seed, future HTF, duplicate/conflicting log, snapshot bị cắt.

```powershell
python -B -m unittest discover -s tests -p 'test_lux*.py'
python -B tools/check_lux_native.py output/playwright/lux-observer-20261116/nas-m5.csv --token 64157540051458 --output output/playwright/lux-observer-20261116/nas-m5-parity.json
python -B tools/compare_lux_runs.py
```

Lệnh cuối hiện **exit 1 đúng chủ đích của gate strict** vì phiên mới nhận OHLC khác, không được đổi thành pass bằng cách bỏ các trường khác biệt. Muốn capture mới: build audit bằng `tools/build_lux_audit.py`, paste vào Pine Editor, compile, chọn feed/khung và Download logs; không có headless runner gọi API riêng của TradingView. UI automation diễn ra qua Playwright trong trình duyệt Codex; các file Python là bộ phân tích có thể tái chạy, không phải bộ Playwright CI tự đăng nhập.

Đã phục hồi draft gốc (so nội dung), layout đã lưu NAS100 H4 với ICT EXP 12/1.5 và hai chỉ báo khác ẩn, Watchlist và Autosave về trạng thái ban đầu. Không publish/push/save layout thử nghiệm, không xóa drawings. Bằng chứng phục hồi (`../output/playwright/lux-observer-20261116/restoration.json`, tài sản lịch sử ngoài bản chọn lọc).

Ảnh production chạy native (`../output/playwright/lux-observer-20261116/observer-final.jpg`, tài sản lịch sử ngoài bản chọn lọc). [Tổng hợp có hash](../evidence/lux_custom/native-20261116.json).
