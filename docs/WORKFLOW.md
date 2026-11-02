# Repository & Jira Workflow

Tài liệu quy chuẩn hướng dẫn vận hành tự động hóa quy trình làm việc với Jira VNPT và Tempo Timesheets thông qua Agent Harness và MCP Server.

---

## 1. Bản đồ hệ thống (System Architecture)

- **MCP Server (`server.py`):** Lớp giao tiếp API chuẩn FastMCP, hỗ trợ Jira Server / Data Center (v8.22.6) và REST API latest/v2.
- **Cấu hình (`config.yaml`):** Lưu trữ thông tin kết nối Jira URL, Personal Access Token (PAT), danh sách repo nội bộ và tác giả git.
- **Skills (`.agents/skills/`):** Các kỹ năng tự động hóa (`jira-worklog`, `jira-sprint-tracker`, `jira-ticket-manager`).
- **Liên kết Claude Code (`.claude/skills/`):** Symlinks tự động đồng bộ qua `scripts/link-claude-skills.py`.
- **Harness Rules (`AGENTS.md`):** Các quy tắc bất biến, phân loại task và ranh giới quyền hạn của AI Agent.

---

## 2. Quy trình làm việc hàng ngày (Daily Worklog Workflow)

### Giai đoạn 1: Thu thập dữ liệu (Inspection)
1. Xác định ngày cần xử lý (mặc định hôm nay).
2. Gọi `scan_daily_work(date)` để lấy tất cả git commit trong ngày trên các repo thuộc `/Volumes/ExternalHome/Users/gnoud/dev/workInVNPT/`.
3. Kiểm tra các ticket đang thực hiện trong Sprint thông qua `get_my_sprints(state='active')` và `get_my_tickets(status='In Progress')`.
4. Kiểm tra trạng thái hiện tại trên Tempo qua `get_tempo_worklogs(from_date, to_date)`.

### Giai đoạn 2: Lập kế hoạch phân bổ (Draft Allocation)
1. Tổng thời gian mỗi ngày làm việc tiêu chuẩn: **8.0h**.
2. Nhóm các commit theo module / service:
   - Nếu commit tương ứng với ticket đang chạy: ghép vào ticket đó.
   - Nếu commit thuộc tính năng mới chưa có ticket: lên kế hoạch tạo ticket mới với prefix `[BE]` / `[FE]`.
3. Soạn thảo nội dung comment worklog ngắn gọn, mô tả kỹ thuật rõ ràng, không chứa từ khóa AI.

### Giai đoạn 3: Phê duyệt từ người dùng (User Confirmation Gate)
- **Bắt buộc:** Trình bày bảng xem trước cho người dùng:
  ```markdown
  | Ticket | Công việc | Thời gian | Ghi chú worklog |
  | :--- | :--- | :---: | :--- |
  | NCPTWORK-4381 | Sentry integration | 4h | Tích hợp Sentry logging mobile |
  | NCPTWORK-4377 | Chuẩn hóa SafeKid Mobile | 4h | Cập nhật cấu hình môi trường mobile |
  ```
- Chờ xác nhận từ người dùng trước khi thực hiện ghi dữ liệu.

### Giai đoạn 4: Thực thi & Xác nhận (Execution & Verification)
1. Ghi nhận thời gian qua `log_work(ticket_key, time_spent, date, comment)`.
2. Kiểm tra lại bảng Tempo bằng `get_tempo_worklogs(date, date)` để đảm bảo số giờ hiển thị chính xác trên giao diện Tempo Timesheets.

---

## 3. Quy chuẩn xử lý sự cố (Error Recovery)

| Lỗi | Nguyên nhân | Biện pháp xử lý |
| :--- | :--- | :--- |
| `401 Unauthorized` | Token PAT hết hạn hoặc cấu hình sai | Kiểm tra `personal_access_token` trong `config.yaml`. |
| `OTP_REQUIRED` | Gọi vào endpoint bị chặn bởi WAF | Sử dụng endpoint `/rest/api/latest/` hoặc `/rest/agile/1.0/`. |
| `No commits found` | Email git không khớp hoặc ngày sai | Kiểm tra `git.author_email` bằng lệnh `git log -n 1 --pretty=format:"%ae"`. |
