> **Tài liệu lịch sử.** Các kết quả dưới đây thuộc lượt phát triển được ghi ngày trong tài liệu. Trạng thái đóng gói hiện tại ở VERIFICATION.md (`VERIFICATION.md`, tài sản lịch sử ngoài bản chọn lọc). Đường dẫn ghi dạng văn bản tới kho dữ liệu/log ngoài bản chọn lọc không có trong clone.

# SMC ICT Observer — bản quan sát và nhận định

Ngày: 2026-11-15; kiểm chứng native cập nhật 2026-11-16. Đây là bản custom nghiên cứu độc lập từ các khái niệm trong mã nguồn LuxAlgo công khai và module HTF sẵn có của workspace. Không phải sản phẩm chính thức của LuxAlgo.

**Mục đích:** hiển thị bối cảnh để người dùng tự đánh giá việc vào lệnh. Không có BUY/SELL, entry, SL, TP, RR, khối lượng lệnh, điểm mua/bán hoặc chiến lược tự động. “TĂNG/GIẢM” trong bảng là trạng thái cấu trúc theo thuật toán, không phải chỉ dẫn giao dịch.

## Mở và dùng

1. Mở [SMC_ICT_OBSERVER.pine](../dist/lux_custom/SMC_ICT_OBSERVER.pine), sao chép toàn bộ vào một indicator mới trong Pine Editor của TradingView.
2. Chọn chart nến giá tiêu chuẩn. M5 dùng vùng H1; M15 và các khung lớn hơn M5 đến H4 dùng vùng H4. Bảng vẫn trình bày H1/H4/D1/W1 nếu khung đó không thấp hơn chart. H4 hiển thị H1 = N/A; chart lớn hơn H4 không diễn giải vùng H1/H4.
3. Add to chart để kiểm tra trực tiếp. Đúng hash bàn giao đã compile và chạy native trên TradingView; xem [báo cáo kiểm chứng](LUX_CUSTOM_VALIDATION_20261116.md) và các giới hạn còn lại.
4. Mặc định bật cấu trúc, vùng HTF, vùng chart, premium/discount và bảng. Previous high/low, nền phiên và thông báo bối cảnh mặc định tắt; bật trong Settings khi cần.

Tên bản hướng đến XAU/NAS, nhưng mã dùng `syminfo.mintick` của chart, không khóa feed. Ma trận native hiện bao gồm OANDA:XAUUSD và FOREXCOM:NAS100 trên M5/M15/H1/H4; không suy rộng sang feed khác. Không diễn giải chart Heikin Ashi, Renko hoặc các chart tổng hợp khác.

## Những thông tin nhìn thấy

| Lớp | Nội dung | Cách đọc |
|---|---|---|
| Hướng đa khung | H1/H4 là bối cảnh chính, D1/W1 tham chiếu | Cùng hướng, trái hướng hoặc chưa rõ; không cộng điểm |
| Internal / swing chart | `i` = pivot 2/2; `s` = pivot 5/5; INIT, BOS, CHoCH | INIT xác lập hướng ban đầu; BOS tiếp diễn; CHoCH phá ngược hướng đang lưu |
| Thanh khoản chart | Pool đỉnh/đáy, EQH/EQL, quét BSL/SSL | Các mức suy ra từ OHLC; không phải dữ liệu lệnh ngân hàng |
| Vùng HTF | SR, OB, FVG, SD, BSL/SSL | Nhãn H1/H4, teal/orange; tối đa 8 vùng gần giá mặc định |
| Vùng chart | OB, BRK, FVG, IFVG | Nhãn Chart, aqua/fuchsia, viền chấm; tối đa 8 vùng gần giá |
| Vị trí | Premium / equilibrium / discount theo swing chart | Vị trí tương đối trong cặp swing gần nhất; nằm ngoài biên được ghi riêng |
| Thời gian | Giờ phiên địa phương; tùy chọn PDH/PDL/PWH/PWL | Mốc tham khảo, không lọc sự kiện hoặc suy ra xác suất |
| Bảng nhận định | Trạng thái, điểm thận trọng, điều cần quan sát tiếp | Câu theo quy tắc xác định, không phải AI dự báo hoặc khuyến nghị vào lệnh |

Đường pool nét đứt biểu thị mức đã có pivot gần bằng nhau; nét chấm là pool đơn. Nhãn EQ/sweep xuất hiện ở nến phát hiện. Đường nối cấu trúc có thể bắt đầu ở pivot cũ để giải thích mức giá, nhưng nhãn phá cấu trúc nằm ở nến xác nhận phá. Các box vùng mới bắt đầu tại thời điểm vùng khả dụng, không vẽ giả như đã biết vùng từ trước.

## Định nghĩa để đối chứng

**Pivot và break.** Pivot phải cao/thấp hơn nghiêm ngặt các nến bên trái và được phép bằng phía bên phải; plateau lấy điểm đầu tiên. Pivot internal cần 2 nến bên phải, swing cần 5. Break chỉ dùng close nến đã đóng vượt một pivot đã biết trước nến đó, mỗi pivot được phá một lần. Không coi wick vượt mức là BOS. Nếu cùng lúc thỏa break cả hai phía của hai mức cũ không còn có thứ tự hợp lệ, hướng về chưa rõ và không gán một phía tùy ý.

**Pool và sweep.** Pool chart sinh từ swing 5/5 đã xác nhận. BSL ở đỉnh, SSL ở đáy. Sweep yêu cầu wick vượt mức ít nhất 1 tick và close lấy lại ít nhất 1 tick; chạm đúng mức không phải sweep. Nến quét cả hai phía được ghi rõ là hai phía. Pool bị loại khi close vượt theo chiều phá, đã sweep, quá 200 nến hoặc vượt giới hạn lưu 40 pool. EQ so pivot mới với pool cùng phía còn tồn tại, dung sai `max(1 tick, 0.05 ATR14)`; không gom các pool đã bị tiêu thụ.

**FVG chart.** Ba nến: bullish nếu `low > high[2]` và `close[1] > high[2]`; bearish đối xứng. Chiều rộng tối thiểu `max(1 tick, 0.1 ATR14)`. Chỉ tạo sau khi ATR đủ dữ liệu. Nến tạo vùng không được tính là lần quay lại chạm vùng đó.

**OB chart.** Khi swing INIT/BOS/CHoCH phá một phía, tìm nến trái hướng gần nhất trong 10 nến trước, lấy toàn bộ high/low. Đây là biến thể OB theo cấu trúc được chọn cho bản này; không giống nguyên xi cách chọn cực trị của mọi chỉ báo OB LuxAlgo và không dùng pivot-volume.

**Vòng đời vùng chart.** `Mới → đã chạm → đã lấp bằng wick` là trạng thái tiếp xúc. Close đi xuyên biên xa chuyển FVG thành IFVG hoặc OB thành BRK, đổi phía một lần. Sau đảo, close xuyên biên xa mới loại vùng. Chạm râu không tự đảo vai. TTL là 200 nến tính từ tạo ban đầu, không reset khi đảo; tối đa 64 vùng trong bộ nhớ. BRK ở đây có nghĩa OB đảo vai theo close, không tuyên bố đáp ứng mọi định nghĩa breaker của ICT. IFVG ở đây là *inversion*, không phải *implied FVG*.

**HTF kế thừa workspace.** Các tuple `request.security` đều lấy nến trước `[1]` cùng `lookahead_on`; thời gian pivot đồng bộ qua `[3]`. Structure HTF dùng pivot 2/2 và close phá mức. Vùng OB theo 10 nến ngược; FVG HTF là khoảng trống ba nến, cùng ngưỡng ATR/tick nhưng không yêu cầu close nến giữa như lớp Chart. SR = pivot ±0.2 ATR. SD = base 1–3 nến thân nhỏ, tổng biên ≤ ATR trước, sau đó nến thân ≥ ATR trước rời base. HTF chỉ hết hiệu lực khi close HTF xuyên biên hoặc quá 100 nến HTF; không có trạng thái chạm/đảo của lớp Chart. Các lớp được đặt nhãn riêng vì định nghĩa và vòng đời khác nhau.

**Phiên và ngày/tuần.** Tokyo 09:00–18:00 Asia/Tokyo, London 08:00–17:00 Europe/London, New York 08:00–17:00 America/New_York, thứ Hai–thứ Sáu. Đây là giờ tham chiếu, không phải lịch giao dịch/ngày lễ của broker hay killzone ICT. IANA xử lý DST; không dùng UTC−5 cố định. PDH/PDL/PWH/PWL lấy nến ngày/tuần trước của feed chart, không phải ngày Việt Nam. Timestamp nhận định hiển thị giờ Việt Nam.

## Quy tắc nhận định, theo thứ tự ưu tiên

1. HTF cần dùng thấp hơn chart: không diễn giải bối cảnh đó.
2. Hướng HTF chưa xác lập: ghi chưa rõ.
3. H1 và H4 hợp lệ nhưng trái hướng: nêu mâu thuẫn trước các dấu hiệu đồng thuận khác.
4. Trong 5 nến gần đây có sweep hai phía: ghi bối cảnh nhiễu.
5. Internal và swing cùng hướng HTF đang dùng: ghi cùng hướng.
6. Internal ngược HTF: ghi nhịp hồi hay đảo chiều chưa rõ.
7. Trường hợp còn lại: cấu trúc chart chưa đồng thuận đầy đủ.

Ví dụ: **“H1 và H4 đang trái hướng” → “Không suy đồng thuận từ một khung” → “Theo dõi swing đối diện và vùng HTF còn hiệu lực”.** Không chuyển câu này thành buy/sell. Sweep được nhắc là phản ứng giá, chưa đủ kết luận đảo chiều. Premium/discount được nhắc là vị trí, không phải tín hiệu.

Nhận định, vùng chart và sự kiện chart chốt khi nến đóng. Các hàng hướng HTF có thể cập nhật khi nến HTF trước vừa khả dụng; hàng “Nến chart đã chốt” cho biết mốc của nhận định. Phiên hiện tại và lựa chọn các vùng gần giá nhất phục vụ hiển thị có thể thay đổi trong nến đang chạy. Không gọi mọi thành phần hình vẽ là bất biến nội nến.

## Mã, nguồn và quyền sử dụng

- Danh mục quyết định cho cả 114 nguồn (`../research/luxalgo-custom-20261115/coverage.csv`, tài sản lịch sử ngoài bản chọn lọc), chi tiết pattern và hash (`../research/luxalgo-custom-20261115/coverage.json`, tài sản lịch sử ngoài bản chọn lọc).
- Đánh giá và lý do chọn (`../research/luxalgo-custom-20261115/REVIEW.md`, tài sản lịch sử ngoài bản chọn lọc).
- [Attribution: 7 nguồn nền, phiên bản, SHA và phần đã đổi](LUX_CUSTOM_ATTRIBUTION.json).
- Module riêng: [config](../src/lux_custom/config.pine), [structure](../src/lux_custom/structure.pine), [regions](../src/lux_custom/regions.pine), [assessment](../src/lux_custom/assessment.pine), [ui](../src/lux_custom/ui.pine).
- Reuse `src/intraday/context.pine` và phần ingestion của `zones.pine`; builder cắt trước `f_contact`, không mang theo động cơ setup/target. Không sửa bản gốc của LuxAlgo.

Bản phái sinh ghi công © LuxAlgo và các thay đổi riêng, dùng [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/): giữ attribution, phi thương mại, chia sẻ bản phái sinh theo cùng giấy phép. Nguồn MPL và nguồn `CHECK_HEADER` không được tích hợp. Không suy từ “open-source” trên TradingView thành quyền bán lại tùy ý; công bố trên TradingView còn cần tuân thủ quy tắc tái sử dụng của nền tảng. Chưa publish/push bản này.

## Kiểm chứng và giới hạn

- 15 kiểm thử riêng: delay/plateau, INIT/BOS/CHoCH, single-use, sweep hai phía/exact touch, warmup, inversion/TTL, future HTF, trạng thái nhận định, prefix/reload và build không chứa entry engine. 31 kiểm thử nền intraday cũng đạt; các kiểm thử này không chứng minh chỉ báo mới đã chạy native.
- Replay trên **5.723 nến M5 + 2.405 nến M15 OANDA:XAUUSD = 8.128 nến**: lịch sử sự kiện giống nhau khi chạy prefix 1/3, 2/3, trước nến cuối và toàn bộ. Đủ break tăng/giảm, sweep và inversion. M5 tối đa 35 vùng/14 pool; M15 tối đa 30 vùng/12 pool, trong giới hạn 64/40.
- Bằng chứng replay (`../evidence/lux_custom/offline-regression.json`, tài sản lịch sử ngoài bản chọn lọc): chỉ lớp Chart của oracle Python; không phải so sánh Pine/Python trên chart. Tick lịch sử giả định 0.001, close theo độ dài nến danh nghĩa; không đánh giá lợi nhuận.
- Phân tích ngữ nghĩa Pine chính thức (`../evidence/lux_custom/pine-analysis.json`, tài sản lịch sử ngoài bản chọn lọc): 0 lỗi cho SHA ghi trong evidence; negative-control dùng biến không tồn tại nhận lỗi. Đây là `translate_light`, **không phải full compile, chart runtime, screenshot hoặc kiểm thử reload realtime**.
- Cập nhật 2026-11-16: native compile/render đạt, 8 tổ hợp / 47.414 lượt nến / 880.479 phép đối chiếu không có sai lệch. [Báo cáo đầy đủ](LUX_CUSTOM_VALIDATION_20261116.md) ghi rõ Replay D1, guard Heikin Ashi, toggle, phiên mới, log trùng và giới hạn. Intraday Replay bị gate nâng cấp; tính bất biến tuyệt đối giữa hai document NAS không đạt vì OHLC nhận về khác nhau. Không kết luận hiệu quả giao dịch từ tính nhất quán.

Tái lập từ workspace, không cần cài dependency mới:

```powershell
# Audit collection gốc không đóng gói; xem attribution manifest.
python -B -m unittest discover -s tests -p test_lux_custom.py
python -B tools/check_lux_custom.py --pine
```

Lệnh cuối gửi chính mã Pine đã build tới dịch vụ phân tích công khai của TradingView; bỏ `--pine` để chỉ chạy offline. [Manifest build](../dist/lux_custom/SMC_ICT_OBSERVER.build.json) ghi hash các module và output để đối chiếu đúng bản.
