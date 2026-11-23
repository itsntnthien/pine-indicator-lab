> **Tài liệu lịch sử.** Các kết quả dưới đây thuộc lượt phát triển được ghi ngày trong tài liệu. Trạng thái đóng gói hiện tại ở VERIFICATION.md (`VERIFICATION.md`, tài sản lịch sử ngoài bản chọn lọc). Đường dẫn ghi dạng văn bản tới kho dữ liệu/log ngoài bản chọn lọc không có trong clone.

# ICT Intraday v1 — bản thử nghiệm đã triển khai

Ngày 2026-11-13. Đặc tả được người dùng xác nhận qua phỏng vấn và yêu cầu triển khai. Tài liệu này thay thế đề xuất break–retest trong `NEW_INDICATOR_SPEC.md`.

**Cập nhật 2026-11-15: đã compile native và chạy trên hai feed M5/M15/H1/H4; E2E chưa đạt.** Đã sửa lỗi tên biến Pine và thang giá layout, kiểm tra 529 setup native, tái sử dụng 8.128 nến OANDA cũ cho hồi quy. NAS M5 có 7 giá trị ATR khác sau reload chưa giải thích được; CSV parity, Bar Replay và alert delivery còn thiếu do giới hạn phiên tài khoản. Xem [báo cáo kiểm chứng](INTRADAY_VALIDATION_20261115.md).

## Mã nguồn và build

- [config.pine](../src/intraday/config.pine): cấu hình, kiểu dữ liệu, RR và làm tròn giá.
- [context.pine](../src/intraday/context.pine): pivot, hướng, OB/FVG/nền cung cầu trong ngữ cảnh H1/H4/D1/W1; toàn bộ payload HTF được offset đồng nhất.
- [zones.pine](../src/intraday/zones.pine): vùng độc lập, giới hạn swing, vòng đời, phép chạm/quét và chọn TP.
- [setup.pine](../src/intraday/setup.pine): cửa sổ xác nhận, cực trị nhịp, snapshot, open observation, alert và dữ liệu kiểm chứng.
- [ui.pine](../src/intraday/ui.pine): gộp hình theo giao nhau, nhãn thành phần, bảng tiếng Việt và mức giá đã khóa.
- [reference.py](../src/intraday/reference.py): oracle tuần tự Python; dùng lại `true_ranges` từ harness cũ, bổ sung ATR Wilder và hợp đồng mới. Không chạy lệnh, không tính P/L.

```powershell
python -B tools/build_intraday.py
python -B -m unittest discover -s tests -p 'test_intraday*.py' -v
python -B -m unittest discover -s tests -v
```

Bản ghép: [ICT_INTRADAY_EXPERIMENTAL.pine](../dist/intraday/ICT_INTRADAY_EXPERIMENTAL.pine). Manifest cùng thư mục ghi hash fragment/output và build token; build offline tự nó không thực hiện compile native. Kết quả native gắn đúng hash nằm trong `evidence/intraday/verification.json`. `dist/` không theo dõi Git; chạy build để tái tạo. Không đổi các source tham chiếu, không chọn một ứng viên cũ làm release.

## Hợp đồng đã thực hiện

Feed chỉ phát entry trên `OANDA:XAUUSD`, `FOREXCOM:NAS100` và chart nến giá tiêu chuẩn. M5 dùng H1; M15 dùng H4. H1/H4 chỉ quan sát; khung thấp hơn chart không được gắn nhãn thành confirmed HTF. D1/W1 chỉ tham khảo. Hướng của khung còn lại trái nhau chỉ cảnh báo, không chặn luồng đang dùng.

Pivot 2/2 giữ anchor sớm nhất khi đồng giá trong cửa sổ: pivot high lớn hơn hai nến trái và không thấp hơn hai nến phải; pivot low đối xứng. Hướng theo close phá swing đã biết từ trước; pivot mới xác nhận không được dùng để tạo break hồi tố trong cùng nến. Nếu cả hai phía cùng bị phá do các mức tham chiếu bất thường, đưa hướng về chưa rõ. Chưa rõ hướng hoặc chưa có ATR thì không tạo setup.

Mỗi HTF giữ tối đa ba mức BSL/SSL mỗi phía và SR cùng nguồn swing. SR rộng ±0,2 ATR14 HTF tại lúc tạo. OB là toàn bộ high–low nến ngược màu gần nhất trong mười nến trước close phá swing; không có origin hợp lệ thì không tạo OB. FVG dùng gap ba nến đã đóng, ngưỡng max(0,1 ATR14, mintick). Cung/cầu lấy nền dài nhất hợp lệ 1–3 nến thân ≤50% biên, tổng nền ≤ATR trước departure; thân departure ≥ATR đó và close ngoài nền. Không yêu cầu displacement bổ sung cho OB.

Vùng chỉ bắt đầu được dùng sau HTF close xác lập. Mất hiệu lực khi HTF close xuyên biên xa hoặc đủ 100 nến HTF từ xác nhận. Liquidity dạng đường mất hiệu lực khi HTF close xuyên mức. Một nguồn đã tạo setup không tạo setup thứ hai; nó vẫn có thể là mức cấu trúc tham khảo/TP đến khi mất hiệu lực. ID nguồn gắn feed, HTF, loại, hướng, anchor/sự kiện tạo và thời điểm xác lập.

Giá có thể quét/test ngay trong nến HTF đang chạy. Sweep là nến LTF đi qua mức, vượt ít nhất một tick và đóng lấy lại ít nhất một tick. Với vùng, cần biên nến LTF giao vùng rồi close ra khỏi biên gần về hướng giao dịch. Không áp màu thân/râu, không cần MSS LTF và không chờ retest. Tín hiệu chỉ đi thuận hướng HTF của cặp.

Gọi nến bắt đầu nhịp là N: cho xác nhận tại N, N+1, N+2 hoặc N+3. Sang N+4 chưa xác nhận thì kết thúc nhịp; muốn thử lại phải có nến không còn giao vùng, sau đó quay lại. Nhịp đang chờ cũng bị hủy khi hướng không phù hợp. Khi dữ liệu thiếu/ATR chưa sẵn sàng, không âm thầm thay bằng 0 để tạo vùng/tín hiệu.

Cực trị nhịp lấy từ các nến LTF đã quan sát từ N đến nến xác nhận, không lấy high/low HTF cuối cùng trong tương lai. Nhiều nguồn cùng xác nhận cùng nến/cùng hướng tạo một setup, SL bao ngoài tất cả cực trị liên quan. Đệm SL là max(0,1 ATR14 LTF tại xác nhận, một tick), long làm tròn xuống, short lên. Nguồn tham gia được đánh dấu đã dùng; nguồn chỉ chồng hình nhưng chưa xác nhận không bị tiêu thụ.

TP là biên gần/mức HTF đối diện hợp lệ gần nhất theo hướng lệnh; không tự tạo TP fixed-R khi thiếu mục tiêu. Snapshot khóa source IDs, hướng, close tham chiếu, ATR, cực trị, SL, TP và thời gian xác nhận. RR tạm theo close và RR theo open nến sau là hai quan sát riêng. RR dưới input mặc định 1,5R chỉ cảnh báo; chưa có TP thì RR không xác định.

Open nến kế tiếp được ghi riêng và không phải fill broker. Nếu open qua SL hoặc tới/vượt TP, giữ setup và báo giá bất lợi; RR khi risk/reward không còn dương được để chưa xác định. Không gắn nhãn WIN/LOSS, không ngầm giả định một giao dịch đã được thực thi.

## Thời gian và realtime

Pine lấy payload của nến HTF trước bằng offset `[1]` cùng `lookahead_on`; giá trị vùng/hướng khả dụng tại đầu kỳ HTF tiếp theo. Nhịp LTF dùng snapshot HTF có sẵn tại đầu nến đó. Đây là biên thời gian dùng chung với oracle: chỉ nạp các nến HTF có `end <= LTF.open_time`. HTF kết thúc đúng lúc LTF đóng được áp dụng từ nến LTF kế tiếp, không sửa lại quyết định vừa chốt.

Trạng thái thuật toán dùng biến thông thường để được rollback đúng trong realtime. Chỉ các khóa chống gửi alert lặp dùng `varip`; chúng không tham gia quyết định tín hiệu lịch sử. Quan sát open được tính lại trên mỗi tick của nến tiếp theo để không mất trạng thái sau rollback. Đã đối chiếu mô hình này với [TradingView Execution model](https://www.tradingview.com/pine-script-docs/language/execution-model/) qua HTTP 200; vẫn cần kiểm chứng native.

Nhắc tới vùng là thông báo đang hình thành, có thể xuất hiện trước khi có setup. Alert xác nhận chỉ sau close LTF; cảnh báo open là event kế tiếp. Nạp lại hoặc tạo lại alert là một phiên alert mới, không phải hệ thống chống trùng broker liên phiên.

## Hiển thị và cách nạp

Các vùng cùng hướng/khung được gộp hình qua phần chồng nhau; tên thành phần vẫn hiện như `SSL|SR|OB`. Đây là phép gộp hiển thị, không phải vùng mới để tính entry. Mặc định vẽ 12 nhóm gần giá (chỉnh 2–24); các vùng ngoài hạn hiển thị vẫn được tính. Đổi hiển thị không đổi thuật toán.

Giữ tối đa 180 nhãn chi tiết setup/open để giới hạn tài nguyên; marker BUY/SELL và các plot audit vẫn tồn tại trên lịch sử chart được nạp. Bảng thể hiện setup gần nhất có thời gian; đường SL/TP là snapshot gần nhất, không có nghĩa vị thế đang mở. Thời gian trên bảng là giờ Việt Nam.

Nhãn phiên là tham chiếu địa phương: Tokyo 09–18, London 08–17, New York 08–17 từ thứ Hai đến thứ Sáu, dùng timezone IANA. Đây không phải lịch giờ giao dịch/ngày lễ của broker và không lọc entry.

Khi có phiên TradingView cho phép thao tác:

1. Tạo indicator mới trong Pine Editor, dán toàn bộ file ghép và Add to chart; không dán từng fragment.
   Kiểm tra indicator được ghim cùng thang giá với nến; nếu layout để `No scale`, dùng menu **Pin to scale → Pin to right scale** khi nến đang dùng thang phải. Không chọn tạo thang mới. Đối chiếu đường SL/TP với giá ghi trong bảng.
2. Kiểm tra compiler và runtime lần lượt OANDA:XAUUSD M5/M15, FOREXCOM:NAS100 M5/M15. Xác nhận đúng ticker thực tế, không tự thay bằng NQ hay feed NAS khác.
3. Để nhận đủ nội dung động: tạo alert loại **Any alert() function call**, bật thông báo ứng dụng trong hộp tạo alert TradingView. Chỉ báo không tự tạo hoặc đăng ký thông báo thay người dùng.
4. Không đồng thời tạo thêm alert BUY/SELL tĩnh cho cùng mục đích nếu không muốn nhận thông báo trùng từ hai alert riêng. Sau khi đổi mã/input, tạo lại alert tương ứng vì alert cũ không tự theo bản mã mới.
5. Kiểm tra H1/H4 chỉ quan sát, D1/W1 không chặn; thử chart nến không tiêu chuẩn phải không phát entry.

## Đối chiếu native với oracle

[check_intraday_parity.py](../tools/check_intraday_parity.py) nhận CSV TradingView của chart LTF và HTF, đều gắn **cùng bản build**. Không suy timestamp close bằng cộng phút: CSV phải chứa `Audit close epoch` do Pine xuất. Các trường audit khác xác nhận build token, feed, tick size, timeframe, nến tiêu chuẩn và index nguồn.

Phải export đầy đủ lịch sử được nạp, bắt đầu source index 0. Thiếu phần đầu hoặc HTF security có lịch sử seed khác export HTF thì checker báo lỗi/mismatch; không bỏ qua warmup tùy ý để tìm một đoạn khớp. Dữ liệu zero-event được ghi `INSUFFICIENT_EVENTS`, không PASS setup parity. CSV từ bản chỉ báo cũ không đủ các trường này và không được dùng để chứng nhận bản mới.

```powershell
python -B tools/check_intraday_parity.py --ltf PATH_TO_M5.csv --htf PATH_TO_H1.csv --feed OANDA:XAUUSD --minutes 5 --output evidence/intraday/oanda-m5-parity.json
```

Thay cặp M15/H4 và `--minutes 15` tương ứng; kiểm tra độc lập cho FOREXCOM:NAS100. Dung sai số là max(1e-8, một tick × 1e-6). Checker đối chiếu ATR LTF/HTF, index nguồn HTF, hướng, signal, cực trị, SL/TP và open kế tiếp; nó không xác minh đầy đủ danh sách source IDs. Bật `Log kiểm chứng` để đối chiếu thêm `SETUP|...|sources` và `OPEN|...`, cùng replay/alert delivery thật. PASS CSV không thay thế các gate còn lại.

## Bằng chứng và điều kiện chưa đạt

verification.json (`../evidence/intraday/verification.json`, tài sản lịch sử ngoài bản chọn lọc) ghi hash, kết quả offline/native và các gate còn thiếu. Fixtures tổng hợp, hồi quy bằng giá OANDA cũ và kiểm tra log Pine là ba loại bằng chứng riêng, không thay thế numerical parity hoặc đánh giá hiệu quả giao dịch. Chưa nạp dữ liệu holdout hoặc dùng kết quả ngoài mẫu để điều chỉnh các hệ số.

Chỉ đạt nghiệm thu khi cả bốn tổ hợp feed/entry có compile/runtime, numerical parity, reload/Bar Replay và alert realtime đã được quan sát; phải có cả BUY/SELL trong tập đối chứng. Compile/runtime đã được quan sát; các gate còn lại và sai khác reload được ghi trong báo cáo kiểm chứng. Chưa xác minh P/L, spread, slippage, phí, spec CFD tại Exness hoặc The5ers; không tính lot, gửi lệnh hay thực thi quy định quỹ.
