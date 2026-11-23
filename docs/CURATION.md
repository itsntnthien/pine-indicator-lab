# Phạm vi chọn lọc — 23/11/2026

Repo này chỉ dành cho **chỉ báo Pine chạy trên TradingView**, cùng tài liệu,
nguồn gốc và công cụ build/đối chứng trực tiếp liên quan.

## Giữ lại

| Nhóm | Lý do |
|---|---|
| Ba bộ Pine hiện hành | Mỗi bộ có mục đích và chuỗi build rõ |
| Artifact `dist/` | Người dùng cài trên TradingView không cần Python |
| Oracle/test Python, harness Pine | Đối chứng hành vi và kiểm tra hồi quy |
| VSA gốc và baseline v2 | Regression đang kiểm tra hash; giữ nguồn gốc và rollback |
| Helper legacy tối thiểu | Oracle và test đang import trực tiếp |
| Tài liệu quy tắc và acceptance chọn lọc | Giữ trạng thái có bằng chứng, gồm cả FAIL/NOT_RUN |
| Attribution LuxAlgo | Nguồn, phiên bản, hash và mô tả phần phái sinh |
| Hai ảnh TradingView lịch sử | Minh họa thực tế; có nguồn và giới hạn riêng |

## Loại khỏi repo

- Chart Workspace, Local Terminal và mọi frontend/backend ứng dụng biểu đồ.
- API keys, cookie, private key, cấu hình kết nối, account data, browser profile.
- CSV/parquet thị trường, SQLite, runtime, log phiên, cache và môi trường cài đặt.
- Toàn bộ Git history cũ, archive migration và các worktree/bản backup dư.
- Các repo bên ngoài đã clone, bộ sưu tập nghiên cứu rộng và source không trực
  tiếp cần để build/test ba bộ chỉ báo.

Không xóa các tài sản này khỏi workspace gốc. Bản xuất có lịch sử Git mới để
không kéo theo dữ liệu chưa rà soát từ commit cũ.

## Các điều chỉnh khi đóng gói

- README, hướng dẫn cài đặt, kiến trúc, verification, issue/PR templates và CI
  được viết cho phạm vi Pine.
- `tools/workspace.py` giữ helper cần thiết; không mang CLI migration/archive.
- Package `engine/__init__.py` tối thiểu tránh import cả calibration runner khi
  chỉ cần helper. Nội dung thuật toán Pine và oracle hiện hành được giữ nguyên.
- Artifact được build lại bằng builder hiện có. Baseline v2 giữ nguyên byte.
- Tài liệu lịch sử được thêm nhãn; liên kết tới tài sản không xuất được đổi
  thành đường dẫn văn bản và chỉ rõ phạm vi, tránh tạo link hỏng.

## Dấu vết

[PUBLICATION_MANIFEST.json](PUBLICATION_MANIFEST.json) ghi file được chọn và
SHA-256 của nguồn trước các chỉnh sửa tài liệu. Manifest này là dấu vết nguồn,
không phải báo cáo profit hoặc chứng nhận native.

Build manifest của từng Pine ghi hash hiện tại. Bằng chứng cũ chỉ áp dụng khi
hash tương ứng khớp. Một số acceptance JSON giữ các đường dẫn artifact lịch sử;
raw CSV/log ở các đường dẫn đó không có trong clone.

Trạng thái kiểm chứng mới ở [VERIFICATION.md](VERIFICATION.md). Quyền sử dụng
ở [LICENSE.md](../LICENSE.md) và [THIRD_PARTY.md](../THIRD_PARTY.md).
