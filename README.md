# 🚀 Jira Logwork MCP Server

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol-green.svg)](https://modelcontextprotocol.io/)
[![Jira](https://img.shields.io/badge/Jira-Server%20%7C%20Data%20Center%20%7C%20Cloud-0052CC.svg)](https://www.atlassian.com/software/jira)
[![Tempo](https://img.shields.io/badge/Timesheets-Tempo%20Supported-orange.svg)](https://www.tempo.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Jira Logwork MCP Server** là máy chủ MCP (Model Context Protocol) chuyên dụng giúp các AI Coding Agent (Claude Code, Claude Desktop, DeepSeek Harness, Cursor) tự động hóa toàn diện quy trình:
1. **Quét git commits** trong ngày qua nhiều repository.
2. **Khớp nội dung với Jira tickets** trong Sprint đang hoạt động.
3. **Phân bổ thời gian công chuẩn (8.0h/ngày)** và tạo/cập nhật ticket chuẩn tiền tố `[BE]` / `[FE]`.
4. **Logwork trực tiếp lên Tempo Timesheets & Jira** với cơ chế bảo mật nghiêm ngặt.

---

## ✨ Tính năng nổi bật (Key Highlights)

- 🏢 **Hỗ trợ toàn diện cả Jira Server / Data Center & Jira Cloud:**
  - Tương thích Jira Server / Data Center v8.22+ (REST API v2 / latest, plain-text descriptions).
  - Hỗ trợ Jira Cloud (REST API v3, Atlassian Document Format).
  - Cơ chế xác thực linh hoạt: **Personal Access Token (PAT)**, **Basic Auth (Username / Password SSO nội bộ)**, hoặc **Atlassian Cloud API Token**.
- ⏱️ **Tích hợp sâu Tempo Timesheets:**
  - `log_work`: Ghi nhận giờ làm việc tự động đồng bộ sang bảng Timesheet của Tempo.
  - `get_tempo_worklogs`: Báo cáo chi tiết số giờ đã chấm công theo ngày/tháng để đối soát.
- 🏃 **Quản lý Sprint & Phân loại Ticket:**
  - Tự động nhận diện Sprint đang active (`get_my_sprints`) và tự động gán ticket vào Sprint mục tiêu.
  - Hỗ trợ custom fields nâng cao (như các trường bắt buộc của VNPT: Công đoạn, Mã SPDA cascading 2 cấp).
- 🔍 **Quét Git đa kho chứa & đa danh tính (Multi-repo & Multi-author):**
  - Tự động lọc các repo công việc theo tổ chức (`remote_orgs`) hoặc danh sách chỉ định (`repos`).
  - Hỗ trợ danh sách nhiều email/alias của lập trình viên (`author_emails`).
- 🤖 **Bộ kỹ năng AI Agent tích hợp sẵn (.agents/skills & .claude/skills):**
  - `jira-worklog`: Vòng đời 5 bước quét commit, dự thảo bảng giờ và logwork.
  - `jira-sprint-tracker`: Theo dõi tiến độ Sprint và trạng thái ticket.
  - `jira-ticket-manager`: Tạo và biên tập ticket theo quy chuẩn kỹ thuật.
  - `jira-setup`: Trợ lý phỏng vấn thiết lập `config.yaml` dựa trên phương pháp **Grill-Me** (AI Hero).
- 🛡️ **Nguyên tắc an toàn (Hard Invariants):**
  - **Preview First:** Luôn yêu cầu người dùng xác nhận bảng phân bổ thời gian trước khi ghi dữ liệu.
  - **No AI Authorship:** Loại bỏ tuyệt đối mọi chuỗi ký tự nhắc đến AI/Claude trong tiêu đề và nội dung gửi lên Jira.
  - **Credential Safety:** [`config.yaml`](config.yaml) được bảo vệ nghiêm ngặt qua `.gitignore`.

---

## 🛠️ Danh mục MCP Tools

| Tool | Mô tả chức năng | Tham số chính |
| :--- | :--- | :--- |
| `scan_daily_work` | Quét commit trong ngày trên toàn bộ work repos, bỏ qua merge và commit trùng lặp. | `date` (`YYYY-MM-DD`, mặc định: hôm nay). |
| `log_work` | Ghi thời gian làm việc vào ticket Jira (đồng bộ tức thì lên bảng Tempo Timesheets). | `ticket_key`, `time_spent`, `date`, `comment`. |
| `get_tempo_worklogs` | Tra cứu tổng số giờ và chi tiết các mục worklog đã ghi trên Tempo Timesheet. | `from_date`, `to_date` (`YYYY-MM-DD`). |
| `get_my_sprints` | Liệt kê các Sprint và danh sách ticket được gán cho người dùng. | `state` (`'active'`, `'closed'`, `'all'`). |
| `get_my_tickets` | Lấy tối đa 20 ticket Jira đang gán cho người dùng theo trạng thái. | `status` (ví dụ: `'In Progress'`, `'To Do'`, `'Done'`). |
| `create_jira_ticket` | Tạo ticket Jira mới chuẩn tiền tố `[BE]`/`[FE]`, gán Sprint, due date và estimate. | `service_name`, `title`, `summary`, `time_estimate`, `time_spent`, `task_type`, `side`, `sprint_id`, `due_date`. |
| `update_jira_ticket` | Chỉnh sửa tóm tắt, mô tả, cập nhật estimate và log thêm giờ vào ticket sẵn có. | `ticket_key`, `summary`, `description`, `time_estimate`, `time_spent`. |

---

## 🚀 Cài đặt & Khởi động nhanh (Quickstart)

### 1. Chuẩn bị môi trường

```bash
# Clone repository
git clone https://github.com/duong991/jira-logwork.git
cd jira-logwork

# Khởi tạo môi trường ảo Python
python3 -m venv .venv
source .venv/bin/activate

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
```

### 2. Thiết lập cấu hình (`config.yaml`)

Bạn có 2 cách để thiết lập file cấu hình:

#### Cách A (Khuyên dùng): Dùng trợ lý phỏng vấn Grill-Me
Mở Agent và gõ:
```text
/jira-setup
```
Agent sẽ tự động trinh sát môi trường máy bạn (git emails, đường dẫn repos), phỏng vấn theo từng vòng (Rounds & Frontier) và hỗ trợ hoàn thiện `config.yaml`.

#### Cách B: Tạo thủ công từ file mẫu
```bash
cp config.example.yaml config.yaml
```
Chỉnh sửa [`config.yaml`](config.yaml) với thông tin Jira của bạn:
- **Jira Server / DC:** Nhập `url`, `project_key` và `personal_access_token` (PAT).
- **Jira Cloud:** Nhập `url`, `project_key`, `email` và `api_token`.
- **Git:** Cấu hình `author_emails` và `repo_roots` / `repos`.

---

## 🔌 Tích hợp với MCP Client

### A. Claude Code (CLI)

File [`.mcp.json`](.mcp.json) đã được tạo sẵn tại thư mục gốc của dự án:
```json
{
  "mcpServers": {
    "jira-work-logger": {
      "command": "/path/to/jira-logwork/.venv/bin/python",
      "args": [
        "/path/to/jira-logwork/server.py"
      ]
    }
  }
}
```

Chạy lệnh `claude` tại thư mục dự án và chọn **Approve** khi được hỏi.

### B. Claude Desktop

Thêm cấu hình sau vào file cấu hình Claude Desktop:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "jira-work-logger": {
      "command": "/absolute/path/to/jira-logwork/.venv/bin/python",
      "args": [
        "/absolute/path/to/jira-logwork/server.py"
      ]
    }
  }
}
```

---

## 💡 Kịch bản tương tác mẫu (Sample Prompts)

- **Logwork hôm nay:**
  > *"Quét commit hôm nay của tôi, đề xuất kế hoạch phân bổ 8h công và hỏi tôi trước khi log vào Jira & Tempo."*
- **Tra cứu Sprint:**
  > *"Xem Sprint hiện tại có những ticket nào đang mở của tôi?"*
- **Kiểm tra công Tempo:**
  > *"Kiểm tra tổng số giờ tôi đã log trên Tempo trong tháng này."*
- **Tạo ticket mới:**
  > *"Tạo ticket backend cho repo safekid-backend với công việc tối ưu API xác thực, estimate 4h."*

---

## 📂 Cấu trúc Repository

```text
jira-logwork/
├── .agents/skills/              # Kỹ năng định nghĩa cho coding agents
│   ├── jira-worklog/            # Skill logwork hàng ngày
│   ├── jira-sprint-tracker/     # Skill tra cứu Sprint
│   ├── jira-ticket-manager/     # Skill quản trị ticket
│   └── jira-setup/              # Skill phỏng vấn cấu hình Grill-Me
├── .claude/skills/              # Symlinks phục vụ Claude Code
├── docs/                        # Tài liệu hướng dẫn & quy chuẩn
│   ├── WORKFLOW.md              # Quy trình vận hành chi tiết
│   └── TOOL_REGISTRY.md         # Bảng tra cứu công cụ
├── scripts/                     # Scripts tiện ích
│   └── link-claude-skills.py    # Tự động đồng bộ skills
├── config.example.yaml          # File cấu hình mẫu chuẩn hoá
├── server.py                    # FastMCP Server triển khai các công cụ
├── requirements.txt             # Danh sách dependencies
├── AGENTS.md                    # Chỉ dẫn hệ thống cho AI Agents
├── GUIDE.md                     # Cẩm nang hướng dẫn sử dụng tiếng Việt
└── README.md                    # Tài liệu giới thiệu dự án
```

---

## 📜 Giấy phép (License)

Dự án phát hành theo giấy phép [MIT License](LICENSE).
Phát triển và tối ưu bởi [Đồng Minh Dương](https://github.com/duong991).
Dựa trên nền tảng ban đầu của [jira-work-logger](https://github.com/AbdAlrahmanAlQaroot/jira-work-logger).
