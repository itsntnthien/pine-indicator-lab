# Kiến trúc chỉ báo

## Bốn lớp của repo

1. **Pine source:** module chia theo trách nhiệm, ghép thành một script hợp lệ.
2. **Artifact:** file `dist/` để đưa vào Pine Editor; manifest ghi hash và đầu vào.
3. **Oracle:** Python tuần tự để kiểm tra quy tắc, thời điểm và vòng đời.
4. **Verification:** regression, parser, synthetic fixtures, mutation và harness
   Pine đối chiếu trên TradingView.

Python không thay thế Pine runtime. Không có frontend web, server chart hay
ứng dụng thay thế TradingView trong repo này.

## Các chuỗi build

| Bộ | Thứ tự và phần dùng chung |
|---|---|
| Intraday | `config → context → zones → setup → ui` |
| SMC / ICT | `lux config → intraday context → intraday zones (phần ingestion) → structure → regions → assessment → ui` |
| VSA v3 | `config → core → setup → ui → render` |

SMC / ICT chỉ lấy phần nạp vùng từ Intraday; builder cắt trước `f_contact`, không
đưa entry/target engine vào observer. Mỗi builder kiểm tra header Pine và một số
điều kiện cấm trước khi ghi artifact.

Các hash đầu vào tính trên byte file. `.gitattributes` giữ nguyên byte để clone
Windows/Linux không tự đổi newline và làm lệch fingerprint hoặc baseline.

## Hợp đồng thời gian

- Phân biệt **nến nguồn**, **thời điểm xác nhận** và **thời điểm hiển thị**.
- HTF phải sẵn sàng tại thời điểm xử lý LTF; dữ liệu tương lai bị chặn trong oracle.
- Event được chốt theo nến đã đóng. Các fixture kiểm tra prefix, reload, seed và
  thay đổi giá trị ngoài cửa sổ quan sát.
- VSA không coi ba nến cách nhau bởi gap phiên là ba nến liên tục của một FVG.
- VSA tách số vùng/pool giữ để tính toán khỏi số đối tượng được vẽ.

Quy tắc chi tiết của từng thuật toán ở tài liệu riêng, không suy ra chỉ từ tên
SMC/ICT/VSA. Tham số và định nghĩa giữa các chỉ báo có thể khác nhau.

## Python oracle và helper tương thích

`src/*/reference.py` giữ engine Python hiện có. Intraday dùng hàm `true_ranges`
từ đường dẫn legacy trong `references/`; bộ kiểm tra dùng thêm type và resampler.
Repo chỉ giữ các module phụ thuộc này, không nhập cả dự án legacy.

`tools/workspace.py` được thu gọn thành các helper path/hash/catalog. Lệnh quản
lý migration/archive của workspace gốc không có trong bản xuất này.

## Công cụ nào chạy được khi clone sạch?

| Công cụ | Đầu vào |
|---|---|
| `build_intraday.py`, `build_lux_custom.py`, `build_vsa_observer.py` | Source đã có trong repo |
| `unittest discover -s tests` | Fixture tổng hợp và baseline đã có |
| `check_vsa_v3_mutations.py` | Oracle và regression suite đã có |
| `verify_publication.py` | Các file được Git theo dõi và manifest |
| `check_intraday_parity.py`, `check_lux_native.py` | Cần export native do người dùng cung cấp |
| `indicator_readiness.py`, `check_intraday_legacy.py`, `check_lux_custom.py` khi chạy CLI | Cần catalog/dataset riêng của workspace gốc |
| `research_vsa_v3.py` khi chạy CLI | Cần archive nghiên cứu riêng; các hàm thuần vẫn được unit test |
| Các công cụ VSA v2 | Được đóng băng; từ chối dùng oracle v3 theo thiết kế |

Không dựng dataset giả để biến một cổng chưa chạy thành PASS. Kho dữ liệu thị
trường và bộ sưu tập source bên ngoài không được đóng gói.
