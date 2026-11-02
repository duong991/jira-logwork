---
name: jira-sprint-tracker
description: Theo dõi tiến độ Sprint, thống kê ticket được gán theo trạng thái (To Do, In Progress, Open, Resolved, Done) và kiểm tra tiến độ burndown của các dự án VNPT trên Jira. Sử dụng khi người dùng hỏi "tiến độ sprint", "sprint hiện tại có những ticket nào", "xem sprint của tôi".
license: MIT
metadata:
  version: "1.0"
  author: VNPT-Dev
---

# Jira Sprint Tracker Skill

Kỹ năng theo dõi, giám sát và tổng hợp trạng thái các Sprint đang hoạt động trên hệ thống Jira VNPT (`https://cntt.vnpt.vn`).

## Công cụ sử dụng
- `get_my_sprints(state="active" | "closed" | "all")`: Xem danh sách sprint và số lượng ticket được gán.
- `get_my_tickets(status="In Progress" | "To Do" | "Open" | "Done")`: Lấy danh sách ticket cụ thể theo trạng thái.

## Quy trình làm việc

1. **Truy vấn Sprint hiện tại:**
   - Gọi `get_my_sprints(state="active")` để lấy ID và tên các Sprint đang chạy.
   - Thống kê tỷ lệ hoàn thành: số ticket đã `Resolved`/`Done` so với số ticket còn `In Progress`/`To Do`/`Open`.
2. **Chi tiết hóa các blocker hoặc rủi ro:**
   - Liệt kê các ticket đang bị tồn đọng lâu hoặc chưa được log work.
   - Hiển thị ngày bắt đầu và kết thúc của Sprint để nhắc nhở hạn chót (Deadline).
3. **Báo cáo tóm tắt:**
   - Định dạng bảng rõ ràng kèm đường dẫn trực tiếp tới từng ticket trên Jira (`https://cntt.vnpt.vn/browse/{KEY}`).
