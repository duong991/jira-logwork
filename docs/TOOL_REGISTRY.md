# MCP Tool Registry

Danh mục và quy chuẩn sử dụng 7 công cụ được cung cấp bởi `jira-work-logger` MCP server.

---

### 1. `log_work`
- **Mục đích:** Ghi nhận giờ làm việc vào ticket Jira và tự động đồng bộ lên Tempo Timesheets.
- **Tham số:**
  - `ticket_key` (str, bắt buộc): Mã ticket (ví dụ: `'NCPTWORK-4381'`).
  - `time_spent` (str, bắt buộc): Định dạng thời gian Jira (`'2h'`, `'4h'`, `'1d'`, `'30m'`, `'1d 4h'`).
  - `date` (str, tùy chọn): Ngày làm việc dạng `YYYY-MM-DD` (mặc định: hôm nay).
  - `comment` (str, tùy chọn): Mô tả tóm tắt công việc đã làm.

---

### 2. `get_tempo_worklogs`
- **Mục đích:** Tra cứu tổng số giờ và chi tiết các lần log work trên bảng Tempo Timesheets.
- **Tham số:**
  - `from_date` (str, tùy chọn): Ngày bắt đầu `YYYY-MM-DD` (mặc định: ngày 1 đầu tháng).
  - `to_date` (str, tùy chọn): Ngày kết thúc `YYYY-MM-DD` (mặc định: cuối tháng).

---

### 3. `get_my_sprints`
- **Mục đích:** Xem danh sách Sprint đang hoạt động hoặc đã đóng kèm số lượng ticket được giao cho người dùng.
- **Tham số:**
  - `state` (str, tùy chọn): `'active'`, `'closed'`, hoặc `'all'` (mặc định: `'active'`).

---

### 4. `get_my_tickets`
- **Mục đích:** Lấy tối đa 20 ticket được giao cho bạn theo trạng thái cụ thể.
- **Tham số:**
  - `status` (str, tùy chọn): Trạng thái Jira (ví dụ: `'In Progress'`, `'To Do'`, `'Open'`, `'Done'`).

---

### 5. `scan_daily_work`
- **Mục đích:** Quét toàn bộ commit git của bạn trong ngày trên tất cả các repo công việc được cấu hình.
- **Tham số:**
  - `date` (str, tùy chọn): Ngày quét `YYYY-MM-DD` (mặc định: hôm nay).

---

### 6. `create_jira_ticket`
- **Mục đích:** Tạo mới ticket Jira gán cho người dùng với tiền tố `[BE]` / `[FE]`.
- **Tham số:**
  - `service_name` (str): Tên module / repo.
  - `title` (str): Tiêu đề công việc.
  - `summary` (str): Mô tả chi tiết.
  - `time_estimate` (str): Thời gian ước lượng (e.g. `'3h'`).
  - `time_spent` (str): Thời gian đã thực hiện (tùy chọn).
  - `side` (str): `'BE'`, `'FE'` hoặc `'BE-FE'`.

---

### 7. `update_jira_ticket`
- **Mục đích:** Cập nhật tiêu đề, mô tả hoặc ước lượng thời gian của ticket đã có.
- **Tham số:**
  - `ticket_key` (str): Mã ticket (ví dụ: `'NCPTWORK-4381'`).
  - `summary` (str, tùy chọn): Tiêu đề mới.
  - `description` (str, tùy chọn): Mô tả mới.
  - `time_estimate` (str, tùy chọn): Thời gian ước lượng mới.
  - `time_spent` (str, tùy chọn): Thời gian log thêm.
