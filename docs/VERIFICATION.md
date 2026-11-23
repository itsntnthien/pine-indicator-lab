# Kiểm chứng bản đóng gói — 23/11/2026

## Kết quả thực tế của lần đóng gói

Môi trường local: Windows, Python **3.13.14**. Các lệnh chạy trong bản xuất Pine
độc lập, không phải trong workspace gốc đầy đủ.

| Kiểm tra | Kết quả | Phạm vi |
|---|---|---|
| Build ba chỉ báo | PASS | Artifact và manifest tái tạo được |
| Python regression | **86/86 PASS** | 82 test chỉ báo/đối chứng + 4 test bảo vệ bản xuất |
| VSA mutation controls | **5/5 bị phát hiện** | Cố ý làm sai pool cap, gap, same-bar, stale break và volume readiness |
| Nguồn Pine/oracle so với workspace | Giữ nguyên byte | Không sửa thuật toán để đóng gói |
| Kiểm tra artifact | SHA-256 đối chiếu input/output | Chạy bằng `tools/verify_publication.py` |
| Trình biên dịch TradingView | **Không chạy lại** | Không suy ra từ Python/build |
| Native realtime / Bar Replay / alert delivery | **Không chạy lại** | Cổng riêng, cần môi trường TradingView |
| Hiệu quả giao dịch / chạy tiền thật | **Không chứng nhận** | Ngoài phạm vi xuất repo |

Báo cáo máy đọc được: [publication verification](../evidence/publication/verification.json).
CI được cấu hình Windows/Linux tại [Verify](../.github/workflows/verify.yml);
trạng thái từng lần chạy xem ở tab Actions, không mặc định là PASS từ cấu hình.

## Đúng hash nào có bằng chứng native?

| Chỉ báo | SHA-256 của bản xuất | Bằng chứng / giới hạn |
|---|---|---|
| ICT Intraday | `6a86470dad0992b87502b973b462fc0e9a9e8822de3896bda11128993232d2dc` | Build hiện tại không claim native. Báo cáo lịch sử nêu compile/chart đã chạy nhưng E2E còn thiếu, NAS M5 có sai khác ATR sau reload |
| SMC / ICT Observer | `5b5dfcb788360bfae69fb52d9202262bdebf01a6d1b5cfd09359437722d1dee1` | Cùng hash với acceptance ngày 16/11: 8 tổ hợp, 47.414 lượt nến và 880.479 checks không khác; vẫn có giới hạn E2E |
| VSA Observer v3 | `ac3e071c3dc378e982489dd4b1420469164dd660427bbc8de112e57cd4f27842` | Acceptance ghi `DRAFT_NATIVE_RETEST_BLOCKED`; compile/visual acceptance cuối chưa chạy |

Chi tiết:

- [Intraday history](INTRADAY_VALIDATION_20261115.md).
- [SMC / ICT acceptance](../evidence/lux_custom/native-20261116.json) và
  [báo cáo](LUX_CUSTOM_VALIDATION_20261116.md). Cross-document NAS không bất biến
  tuyệt đối vì OHLC đầu vào thay đổi; Intraday Replay bị gate tài khoản.
- [VSA acceptance](../evidence/vsa_observer/v3-lux-system-acceptance.json). Một
  hash trung gian đã chạy native; sau thay đổi presentation, hash cuối chưa chạy
  lại. Ảnh lịch sử không thay cho nghiệm thu phiên bản hiện tại.

## Tái lập offline

```powershell
python -m pip install -r requirements-test.txt
python -B tools/build_intraday.py
python -B tools/build_lux_custom.py
python -B tools/build_vsa_observer.py
python -B -m unittest discover -s tests -v
python -B tools/check_vsa_v3_mutations.py
python -B tools/verify_publication.py
```

`verify_publication.py` dùng danh sách file Git theo dõi. Khi thêm file mới,
stage file trước khi kiểm tra. Nó kiểm tra phạm vi Pine, một số pattern secret,
link tài liệu, kích thước file và ba manifest build. Đây không phải audit bảo mật
toàn diện hoặc kiểm chứng quyền sở hữu của mọi nguồn.

`built_utc` của Intraday thay đổi giữa các lần build; SHA của script vẫn phải
giữ nguyên nếu source không đổi. Không so timestamp như một lỗi tái lập.

## Tái lập native cần thêm gì?

1. Dùng đúng script/hash, symbol/feed, timeframe và input.
2. Compile và Add to chart bằng TradingView; ghi lỗi/warning thực tế.
3. Chạy harness phù hợp trên cùng dữ liệu, lưu timestamp và export đầy đủ.
4. So oracle theo từng nến, phân biệt seed/warmup/feed drift với lỗi logic.
5. Kiểm tra reload, replay, nến đang hình thành, thiếu volume và các toggle UI.
6. Kiểm tra alert delivery riêng nếu đó là yêu cầu nghiệm thu.

Các CSV và log tài khoản không được đưa vào Git. CLI nghiên cứu archive/catalog
cần dữ liệu riêng ngoài repo; xem [Architecture](ARCHITECTURE.md).
