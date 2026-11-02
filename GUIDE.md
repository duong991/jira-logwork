# Hướng Dẫn Sử Dụng Jira Work Logger MCP

MCP Server tự động quét commit từ Git repo nội bộ theo ngày, tổng hợp nội dung và tạo / cập nhật ticket Jira kèm thời gian ước lượng (estimate) & thực tế (spent).

---

## 1. Cấu hình hệ thống (`config.yaml`)

File cấu hình đặt tại: [`config.yaml`](config.yaml)

Hệ thống Jira của VNPT (`https://cntt.vnpt.vn`) là bản **Jira Server / Data Center (v8.22.6)**. Code đã được tối ưu tương thích REST API v2, văn bản plain-text description, và hỗ trợ 2 hình thức xác thực:

```yaml
jira:
  url: "https://cntt.vnpt.vn"
  project_key: "NCPTWORK"

  # Cách 1 (Khuyên dùng): Personal Access Token (PAT)
  # Tạo tại: https://cntt.vnpt.vn/secure/ViewProfile.jspa -> Personal Access Tokens -> Create token
  personal_access_token: ""

  # Cách 2: Dùng tài khoản VNPT nội bộ (nếu không tạo PAT)
  # username: "tên_đăng_nhập" # Tên tài khoản Jira/SSO VNPT (ví dụ: duongdm)
  # password: "mật_khẩu"

git:
  # Email tác giả commit (kiểm tra bằng lệnh: git log -n 1 --pretty=format:"%ae")
  author_email: "dongminhduong991@gmail.com"
  repo_roots:
    - /Volumes/ExternalHome/Users/gnoud/dev/workInVNPT
  remote_orgs:
    - vci-ncpt
    - vci-cnnt
    - duong991
  repos: []

defaults:
  issue_type: "Task"                              # Loại issue mặc định (Task, Story,...)
  frontend_services:                              # Các repo FE để đánh tiền tố [FE] thay vì [BE]
    - dx-day-web
    - smartir-dashboard
  task_type_field: ""
  task_type_options: {}
```

---

## 2. Tích hợp MCP Client

### A. Claude Code (CLI)
File cấu hình dự án đã tạo sẵn tại [`.mcp.json`](.mcp.json):
```json
{
  "mcpServers": {
    "jira-work-logger": {
      "command": "/Volumes/ExternalHome/Users/gnoud/dev/workInVNPT/jira/.venv/bin/python",
      "args": [
        "/Volumes/ExternalHome/Users/gnoud/dev/workInVNPT/jira/server.py"
      ]
    }
  }
}
```
Khởi động Claude Code trong thư mục dự án để chấp thuận:
```bash
claude
# Chọn đồng ý kích hoạt MCP server khi được hỏi
```
Kiểm tra trạng thái MCP:
```bash
claude mcp list
```

### B. Claude Desktop
Thêm vào `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "jira-work-logger": {
      "command": "/Volumes/ExternalHome/Users/gnoud/dev/workInVNPT/jira/.venv/bin/python",
      "args": [
        "/Volumes/ExternalHome/Users/gnoud/dev/workInVNPT/jira/server.py"
      ]
    }
  }
}
```
Khởi động lại ứng dụng Claude Desktop.

---

## 3. Danh sách Tools của MCP Server

| Tool | Mô tả | Tham số chính |
| :--- | :--- | :--- |
| `log_work` | Log giờ làm việc vào ticket Jira (tự động đồng bộ lên bảng Tempo Timesheets). | `ticket_key`, `time_spent`, `date` (YYYY-MM-DD, mặc định: hôm nay), `comment`. |
| `get_tempo_worklogs` | Xem tổng hợp giờ và danh sách chi tiết các worklog trên Tempo Timesheet. | `from_date`, `to_date` (định dạng `YYYY-MM-DD`, mặc định: tháng hiện tại). |
| `get_my_sprints` | Xem danh sách các Sprint có ticket gán cho bạn. | `state` (`'active'`, `'closed'`, `'all'`, mặc định: `'active'`). |
| `scan_daily_work` | Quét commit trong ngày qua tất cả các repo được cấu hình. | `date` (định dạng `YYYY-MM-DD`, mặc định: hôm nay). |
| `get_my_tickets` | Lấy tối đa 20 ticket Jira đang gán cho bạn. | `status` (ví dụ: `'In Progress'`, `'To Do'`, `'Done'`). |
| `create_jira_ticket` | Tạo ticket Jira mới với worklog & estimate. Tiêu đề tự thêm tiền tố `[BE]` / `[FE]`. | `service_name`, `title`, `summary`, `time_estimate`, `time_spent`, `task_type`, `side`. |
| `update_jira_ticket` | Cập nhật thông tin và log time vào ticket đã có. | `ticket_key`, `summary`, `description`, `time_estimate`, `time_spent`. |

> **Quy chuẩn định dạng thời gian Jira (`time_estimate` / `time_spent`):**  
> Dùng dạng `1w`, `2d`, `4h`, `30m` hoặc kết hợp `1d 4h`.

---

## 4. Kịch bản Prompt mẫu cho AI Agent

Sau khi kết nối MCP server với Claude Code hoặc Claude Desktop, bạn chỉ cần ra lệnh tự nhiên:

### Kịch bản 1: Quét commit và log công việc hôm nay
```text
Quét commit hôm nay của tôi và tạo các ticket Jira tương ứng với thời gian ước lượng và thời gian thực tế đã làm.
```

### Kịch bản 2: Quét commit ngày cụ thể trong quá khứ
```text
Gọi tool scan_daily_work với date="2026-11-01", sau đó tóm tắt các tính năng tôi đã commit và hỏi tôi trước khi tạo ticket Jira.
```

### Kịch bản 3: Xem ticket đang xử lý và log thêm giờ
```text
Lấy danh sách các ticket Jira đang In Progress của tôi, sau đó log 2h vào ticket liên quan đến backend.
```

---

## 5. Lưu ý & Xử lý sự cố

1. **Lỗi `401 Unauthorized` từ Jira:**
   - Kiểm tra `email` và `api_token` trong [`config.yaml`](config.yaml).
   - Đảm bảo API token chưa hết hạn tại [Atlassian API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens).

2. **`scan_daily_work` không tìm thấy commit:**
   - Kiểm tra `git.author_email` trong [`config.yaml`](config.yaml) có khớp với email ghi nhận trong commit hay không (`git log -n 1 --pretty=format:"%ae"`).
   - Kiểm tra repo có nằm trong thư mục con trực tiếp của `git.repo_roots` và remote URL origin có chứa chuỗi trong `git.remote_orgs` hay không.

3. **Từ chối từ khóa AI:**
   - MCP server tự động chặn tiêu đề hoặc mô tả chứa từ khóa như `claude`, `anthropic`, `co-authored-by`, `generated by ai`. Agent sẽ tự động làm sạch nội dung trước khi gửi sang Jira.
