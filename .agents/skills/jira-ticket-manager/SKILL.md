---
name: jira-ticket-manager
description: Tạo và cập nhật ticket Jira tuân thủ quy chuẩn VNPT (prefix [BE]/[FE], time estimate, mô tả công việc, worklog). Sử dụng khi người dùng yêu cầu "tạo ticket jira", "cập nhật ticket", "sửa mô tả ticket".
license: MIT
metadata:
  version: "1.0"
  author: VNPT-Dev
---

# Jira Ticket Manager Skill

Kỹ năng tạo mới và cập nhật ticket trên Jira VNPT (`https://cntt.vnpt.vn`) tuân thủ đúng quy chuẩn đặt tên và phân loại của dự án NCPTWORK.

## Quy chuẩn & Trường bắt buộc VNPT (Hard Invariants)

Khi tạo ticket trong dự án `NCPTWORK`, hệ thống **bắt buộc luôn luôn phải thiết lập** các trường sau:

1. **Mã SPDA (`customfield_13100`):** Cập nhật đủ 2 cấp:
   - Cấp 1 (Parent): **`ATTT`** (`id: 13100`)
   - Cấp 2 (Child): **`Chung/CPCATTTT`** (`id: 13270`)
2. **Công đoạn (`customfield_13000`):**
   - Giá trị: **`Nghiên cứu, phát triển, nâng cấp`** (`id: 13000`)
3. **Hạn hoàn thành (`duedate`):** Bắt buộc nhập (mặc định lấy ngày cuối cùng của tháng làm việc).
4. **Sprint (`customfield_10105`):** Gán vào Sprint đang hoạt động (ví dụ: `SAFEKIDS Sprint 19` - ID: 48756).
5. **Tiền tố bắt buộc:**
   - `[BE] <service-name>: <mô tả>` cho các module Backend.
   - `[FE] <service-name>: <mô tả>` cho các giao diện người dùng Web / Mobile.
   - `[BE-FE] <service-name>: <mô tả>` cho các công việc full-stack.
6. **Quy tắc văn phong:**
   - Rõ ràng, mô tả đúng mục tiêu kỹ thuật.
   - Tuyệt đối không đề cập đến AI / Claude authorship.

## Công cụ sử dụng
- `create_jira_ticket(service_name, title, summary, time_estimate, time_spent, task_type, side, sprint_id, due_date)`
- `update_jira_ticket(ticket_key, summary, description, time_estimate, time_spent)`

## Quy trình làm việc

1. **Thu thập thông tin ticket:**
   - Tên service/module (ví dụ: `SafeKid-Mobile`, `SafeKid-Backend`, `VNPT_KPI`, `EDM`).
   - Tiêu đề ngắn gọn và mô tả chi tiết.
   - Thời gian ước lượng (`time_estimate`, e.g. `4h`, `1d`).
2. **Xác nhận với người dùng:**
   - Trình bày bản nháp ticket đầy đủ trước khi gửi.
3. **Thực thi:**
   - Gọi tool `create_jira_ticket` hoặc `update_jira_ticket`.
   - Trả về URL trực tiếp tới ticket vừa tạo hoặc cập nhật.
