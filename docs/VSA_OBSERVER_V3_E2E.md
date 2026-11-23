> **Tài liệu lịch sử.** Các kết quả dưới đây thuộc lượt phát triển được ghi ngày trong tài liệu. Trạng thái đóng gói hiện tại ở VERIFICATION.md (`VERIFICATION.md`, tài sản lịch sử ngoài bản chọn lọc). Đường dẫn ghi dạng văn bản tới kho dữ liệu/log ngoài bản chọn lọc không có trong clone.

# VSA Observer v3 — kiểm thử và cổng bàn giao

Phạm vi: indicator Pine và các công cụ nghiên cứu/kiểm chứng của nó. Không sửa `local-terminal`, `chart-workspace` hoặc xây giao diện web. Hồ sơ bản lõi trước khi chỉnh UI nằm tại `evidence/vsa_observer/v3-acceptance.json`; hồ sơ bản UI hiện tại và hash bàn giao nằm tại `evidence/vsa_observer/v3-lux-system-acceptance.json`. Hai receipt cũ giữ làm lịch sử. Không dùng hash cũ để chứng nhận file mới.

## Lượt chuyển toàn bộ lớp UI — đang chờ kiểm chứng cuối

Receipt `v3-lux-system-acceptance.json` ghi **DRAFT_NATIVE_RETEST_BLOCKED**, không phải bản đã qua cổng bàn giao.

- Quét dấu hiệu UI trong 114 nguồn đã lưu; chuyển các thành phần hiện có từ sáu nguồn có attribution riêng. Không tuyên bố chạy đủ 114 indicator.
- 27 unit tests PASS trên file cuối; core/setup không đổi từng byte, block tính snapshot không đổi.
- Bản trung gian `ef5bf240…` đã compile native và PASS XAUUSD OANDA M5: mask/lifecycle, bounds, Present, trung điểm vùng và hình học sweep. Source trong editor được copy đối chiếu toàn bộ.
- Sau ảnh native đã sửa hai điểm: vị trí mặc định sang Giữa trái để tránh nhãn giá trên cửa sổ hẹp; ưu tiên tên pool thay tên swing chồng nhau. **Hash sau hai sửa này chưa được compile/chụp lại**. Không dùng bằng chứng bản trung gian để chứng nhận bản cuối.
- Công cụ web bị rút giữa phiên. Fallback TradingView desktop gặp thao tác trực tiếp của người dùng nên không tiếp tục điều khiển. Chưa xác nhận phục hồi tab web thử, editor/clipboard/favorites/Autosave; không ghi PASS khôi phục. Tab thử web đã tắt Autosave và không Save layout/publish.
- Còn cần: compile production cuối không harness, matrix hai symbol/bảy khung, Historical/Monochrome/ẩn hiện/giới hạn tối đa, screenshot hẹp/rộng và khôi phục phiên. Bằng chứng tại `output/playwright/vsa-v3-lux-system/`.

## Lượt bố trí tham khảo LuxAlgo trước đó (lịch sử)

- Dashboard hai cột hồi lên/hồi xuống, sáu dòng nội dung; palette teal/đỏ, đoạn cấu trúc nối pivot đến nến phá, vùng có tên ở mép phải. Không nhập thuật toán LuxAlgo. Core/setup và phần tính snapshot đối chiếu không đổi từng byte.
- 27 unit tests PASS. Native XAUUSD OANDA và NAS100 FOREXCOM đủ M1/M3/M5/M15/M30/H1/H4: 14/14 PASS. Harness bổ sung kiểm tra nguồn pivot, hai đầu đoạn cấu trúc, giá nhãn bằng giá bị phá và xóa tọa độ khi ẩn. NAS100 M5 với cấu trúc/dashboard tắt cũng PASS.
- Mã native trong editor được copy đối chiếu toàn bộ với production + hai harness, ràng buộc hash build. Bằng chứng riêng tại `output/playwright/vsa-v3-lux-ui/`; các kiểm tra production, screenshot và phục hồi phiên được liệt kê trong receipt hiện tại.
- Không lặp parity 1.500 nến, mutation, soak 24h, mobile/4K hoặc kiểm chứng lợi nhuận trong lượt UI. Không đổi theme toàn tài khoản: các ảnh mới kiểm tra nền sáng với bảng tối. Tài khoản Basic chặn tạo bản sao layout; test trên thay đổi chưa lưu, Autosave tắt, không Save layout/Save script/publish.

## Lượt chỉnh UI gọn trước đó (lịch sử)

- Core, setup và toàn bộ phép tính snapshot trước phần nhãn được đối chiếu không đổi. 27 unit tests PASS.
- Compile native trực tiếp, đối chiếu toàn bộ source trong editor với file build. Chạy lại XAUUSD OANDA và NAS100 FOREXCOM trên M1/M3/M5/M15/M30/H1/H4: 14/14 PASS; gồm 512 tổ hợp mask, 34 assertion vòng đời, 8 trường hợp hướng nhãn và 5 assertion mới cho cách viết lý do/khung thời gian. Khung giờ, giới hạn đối tượng, vùng tham chiếu và intrabar dùng harness đã có.
- Compile riêng file production không kèm harness; kiểm tra nền sáng/tối, bảng 5 dòng bình thường và 6 dòng khi thiếu volume, tooltip hai hướng, vị trí dưới trái/trên phải/dưới phải, cỡ chữ bảng Vừa/Nhỏ. Ảnh và log tại `output/playwright/vsa-v3-ui/`.
- Không chạy lại parity fixture 1.500 nến, negative control, soak 24h, mobile/4K hoặc kiểm chứng lợi nhuận cho lượt chỉ sửa UI này. Bằng chứng cũ giữ nguyên như lịch sử; các cổng nghiên cứu chưa đạt vẫn mở.
- Sự cố test theme: TradingView lưu cả layout khi đổi theme dù Autosave=false. Đã phải dựng lại cấu hình quan sát được: OANDA:XAUUSD H1, v3 trước sửa, XAU-SCALP-R1 ẩn và Observer cũ trong pane riêng; dùng mã backup, script đã lưu và các Inputs trong snapshot đầu lượt. Đây là phục hồi theo cấu hình đã ghi nhận, không phải bằng chứng pixel-identical hoặc chứng nhận mọi tùy chọn chưa ghi nhận. Bản nháp đầy đủ được khôi phục riêng, không compile phần test/audit vào panel phụ. Không lặp test theme trên layout gốc trong lần sau; dùng bản sao layout tách biệt.

## Kiểm tra đã thực hiện

1. **Hồi quy trước sửa:** năm ca mới thất bại trên oracle v2 (bốn FAIL, một ERROR). Bộ hiện tại gồm kiểm thử engine, build và nghiên cứu; kiểm tra pool thứ 9, FVG thứ 6 trở đi, gap, cùng nến, giữ mức thất bại, TTL, reset chu kỳ, thiếu volume, retest OB và tick equality.
2. **Tính nhân quả:** replay prefix 731 nến so với chuỗi 2.500 nến; từ chối nến trùng/đảo thời gian, HTF ở tương lai; warmup và cửa sổ volume 21 nến. Session-volume nghiên cứu chỉ lấy các phiên trước, tối thiểu 10, tối đa 20.
3. **Mutation Python:** cố ý khôi phục cap pool 8, cho phép gap, xác nhận cùng nến, làm sống lại break cũ, bỏ chặn thiếu volume. Cả năm bị bài test liên quan từ chối, không sửa file production để chạy mutation.
4. **Compile thực:** dán file vào Pine Editor của TradingView trong trình duyệt Codex; đọc compiler/runtime thực. Đã sửa hai lỗi compile khi phát triển và một API getter không tồn tại trong harness. File production cuối phải được compile lại riêng, không kèm harness.
5. **Parity native:** engine Pine chạy fixture 1.500 nến, so hash 15 trường từng nến với oracle Python; EMA/ATR làm tròn 1e-5. Có VSA, masks, phase inputs, zone IDs/location, sweep, trend, EMA/ATR, structure/pending. Thay giá trị kỳ vọng đầu tiên +1 phải gây lỗi `PARITY bar=0`; đã quan sát lỗi này trên TradingView.
6. **Native matrix:** OANDA:XAUUSD và FOREXCOM:NAS100, đủ M1/M3/M5/M15/M30/H1/H4. Mỗi lần chạy kiểm tra 512 tổ hợp điều kiện, 34 assertion vòng đời, 8 trường hợp vị trí nhãn, invariant trên toàn lịch sử có sẵn, HTF đóng đồng thời, không dùng timestamp tương lai, không retest OB ngay nến tạo, không FVG qua gap, bounds đối tượng, vùng bảng có đối tượng tương ứng. NAS100 feed này thiếu volume nên confluence phải bằng 0 hai hướng.
7. **Heikin Ashi:** không commit snapshot quan sát chuẩn; không tạo nhãn sự kiện hoặc hội tụ. Ticker trong log của TradingView có dạng mã hóa loại chart; không nhầm nó với symbol mới.
8. **Nghiên cứu archive:** chạy trên bảy khung XAUUSD Exness lưu sẵn, ghi hash tất cả đầu vào. Tất cả là development đã xem. Dò M5 35.733 nến cho 0 pool còn hiệu lực bị loại do cap; 63 OB giao nến tạo nhưng chưa bị ghi nhận như một retest. Đây là số đối tượng, không phải giao dịch.

Pine parity thay OHLCV/timestamp/tick và HTF bằng fixture; **không** thay thế test request native. Python không phải compiler Pine. PASS về tính toán không phải PASS về lợi nhuận.

## Quy trình UI và realtime

- Tắt autosave cho phiên test và ghi lại trạng thái ban đầu; giữ bản sao editor draft/clipboard. Chỉ xóa indicator trong layout tạm, không lưu layout hoặc publish script.
- Khi mở Pine Editor, đợi progressbar biến mất trước khi dán/compile. Compile quá sớm có thể tạo một pane rỗng báo `cannot compile script`; đây là lỗi thao tác khởi tạo editor, cần xóa pane đó và nạp lại source khi editor sẵn sàng.
- Kiểm tra screenshot với **một** instance; hai bản cùng overlay gây dashboard/nhãn trùng và làm đánh giá bố cục sai. Kiểm tra 1280×720, tooltip, font/vị trí bảng, vùng tắt/bật, giới hạn hiển thị và cấu hình tối đa. Những trường hợp thực tế đã chạy được ghi riêng trong acceptance; không mặc định toàn bộ danh sách này đều PASS.
- Để M1 chạy liên tục, thu log ở đầu và cuối; chỉ tính `SETUP_SNAPSHOT` xuất hiện mới từ timestamp sau snapshot bắt đầu. Các assertion intrabar kiểm tra snapshot/masks/RV/data-quality/renderer không đổi giữa các tick của nến chưa đóng. Không dùng log lịch sử vừa reload làm bằng chứng chạy live lâu.
- Sau kiểm thử: khôi phục draft và clipboard; đóng tab tạm; mở lại saved layout, khôi phục autosave như ban đầu rồi xác nhận indicator gốc còn nguyên. Không lưu indicator đang test vào layout gốc.

## Các cổng chưa được phép suy diễn là hoàn tất

- **24 giờ realtime hoạt động trên từng feed:** chưa hoàn tất; vài nến live không thay thế được. Cần thêm kiểm tra qua phiên, mất kết nối/reconnect, boundary D/W và nhiều chế độ biến động.
- **Native Bar Replay intraday:** phụ thuộc quyền của gói TradingView đang đăng nhập. Chỉ ghi PASS nếu replay thật chạy; nếu nền tảng yêu cầu nâng gói thì ghi BLOCKED, không suy ra từ Python replay.
- **Holdout mới và NAS100 cùng feed:** chưa có. Không chọn bộ lọc thắng dựa vào archive đã xem. Hai biến thể FVG đã chạy qua cả vòng đời vùng và OB trong engine nghiên cứu; chúng không đổi điều kiện hội tụ nên kết quả excursion giống nhau không chứng minh cải thiện.
- **Chi phí và hiệu quả giao dịch:** không backtest lệnh, fill, spread hoặc P&L trong indicator này.
- **Các kích thước/thiết bị chưa thử:** không coi screenshot desktop là bằng chứng mobile/4K. Nhãn vẫn có thể đè nhau ở mức zoom quá xa.

## Tái lập

```powershell
python tools/build_vsa_observer.py
python -m unittest discover -s tests -p 'test_vsa*.py'
python tools/check_vsa_v3_mutations.py
python tools/build_vsa_v3_parity.py
python tools/research_vsa_v3.py
python research/vsa-v3-20261119/probe.py
```

Native harness: nối production → `tests/vsa_observer_native.pine` → `tests/vsa_observer_setup_native.pine`, dán bản ghép vào Pine Editor. Chạy parity riêng từ `output/playwright/vsa-v3/parity.pine` trên chart chuẩn M5; các nguồn fixture không được phát hành cho người dùng thay file production.

Log/screenshot nằm ở `output/playwright/vsa-v3/`. Các file v2 và original attachment có kiểm tra hash bảo toàn. Công cụ v2 từ chối chạy với oracle v3 để tránh ghi đè bằng chứng cũ bằng kết quả khác phiên bản.
