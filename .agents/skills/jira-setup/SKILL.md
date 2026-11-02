---
name: jira-setup
description: Khảo sát và phỏng vấn người dùng theo phương pháp Grill-me (design tree, round-based frontier) để thiết lập hoặc chuẩn hóa file config.yaml từ config.example.yaml, tự động trinh sát môi trường máy local và kiểm tra kết nối Jira. Sử dụng khi người dùng yêu cầu "setup jira", "cấu hình jira", "hướng dẫn setup config", "tạo file config.yaml", "/setup", "/jira-setup".
license: MIT
metadata:
  version: "1.0"
  author: VNPT-Dev
---

# Jira Setup Skill (Grill-Me Methodology)

Kỹ năng phỏng vấn sâu và đồng hành cấu hình hệ thống Jira Work Logger MCP theo phương pháp **Grill-me** (phát triển bởi Matt Pocock - AI Hero). Kỹ năng này không đoán mò, không để sót giả định ngầm, và tự động thu thập sự kiện môi trường cục bộ (git, đường dẫn, mạng) trước khi đặt câu hỏi cho người dùng.

---

## 1. Triết lý Grill-Me (Core Principles)

1. **Cây quyết định (Design Tree):**
   Mọi quyết định cấu hình được biểu diễn dưới dạng nhánh cây. Quyết định tầng sau phụ thuộc vào kết quả đã chốt ở tầng trước:
   - *Hạ tầng Jira* (Server/Data Center vs Cloud) ➡️ *Phương thức xác thực* (PAT vs Basic Auth vs API Token) ➡️ *Dự án mục tiêu* (`project_key`) ➡️ *Môi trường Git & Tác giả commit* ➡️ *Quy chuẩn dự án (Custom fields, Frontend services)*.

2. **Hỏi theo Vòng (Rounds) & Ranh giới quyết định (Frontier):**
   - **Frontier** là tập hợp các câu hỏi mà toàn bộ điều kiện tiên quyết đã được giải quyết.
   - Luôn hỏi **toàn bộ frontier trong một round**: Đánh số thứ tự từng câu hỏi (`❓ Q1`, `❓ Q2`,...) và luôn kèm đề xuất tối ưu (`➡️ <Đề xuất lựa chọn>`).
   - Đặt câu hỏi sao cho người dùng chỉ cần trả lời *"Đồng ý"* / *"Yes"* là đồng nghĩa với việc chọn tất cả các phương án đề xuất của vòng đó.

3. **Thu thập sự kiện (Facts) là việc của Agent, không phải của người dùng:**
   - Trước mỗi round, Agent chủ động chạy lệnh inspect hệ thống:
     - Đọc `git config user.email`, `git config user.name`.
     - Quét lịch sử git commit gần nhất để tìm các email/alias tác giả.
     - Kiểm tra các thư mục chứa repo dự án (`repo_roots`).
     - Kiểm tra file `config.yaml` hiện tại (nếu có) và `config.example.yaml`.
   - Tuyệt đối không hỏi người dùng những thông tin mà Agent có thể tự kiểm tra được.

4. **Kết thúc khi Frontier rỗng (Empty Frontier):**
   - Phiên phỏng vấn kết thúc khi mọi nhánh trên cây quyết định đều đã được làm rõ, không còn bất kỳ giả định ngầm nào.
   - Sau khi chốt: Sinh file `config.yaml`, kiểm tra cú pháp, test kết nối thực tế tới Jira và thông báo trạng thái.

---

## 2. Cấu trúc câu hỏi chuẩn mỗi Round

Định dạng bắt buộc khi trình bày câu hỏi cho người dùng:

```markdown
❓ **Q1** - **<Tiêu đề câu hỏi>**: <Mô tả chi tiết bối cảnh, các phương án lựa chọn A, B, C>

➡️ **Đề xuất:** <Lựa chọn khuyên dùng kèm lý do ngắn gọn>

---

❓ **Q2** - **<Tiêu đề câu hỏi>**: <Mô tả chi tiết bối cảnh, các phương án lựa chọn A, B, C>

➡️ **Đề xuất:** <Lựa chọn khuyên dùng kèm lý do ngắn gọn>
```

---

## 3. Lộ trình phỏng vấn chuẩn (Standard Grilling Pipeline)

### Vòng 1: Hạ tầng Jira & Dự án mục tiêu
- **Trinh sát tự động:** Kiểm tra `config.yaml` cũ (nếu có), kiểm tra `config.example.yaml`.
- **Câu hỏi Frontier:**
  - `Q1`: Jira Endpoint URL (Jira Server/Data Center nội bộ VNPT `https://cntt.vnpt.vn` hay Jira Cloud `https://*.atlassian.net` hay Jira On-Premise khác?).
  - `Q2`: Project Key chính để tạo ticket và logwork (ví dụ: `NCPTWORK`, `PROJ`,...).

### Vòng 2: Phương thức xác thực (Phụ thuộc vào Vòng 1)
- **Nếu là Jira Server / Data Center (như VNPT `cntt.vnpt.vn`):**
  - `Q1`: Chọn Personal Access Token (PAT - khuyên dùng) hay Username/Password SSO/AD nội bộ?
  - Hướng dẫn chi tiết người dùng lấy PAT tại giao diện: `Profile -> Personal Access Tokens -> Create token`.
- **Nếu là Jira Cloud (`atlassian.net`):**
  - `Q1`: Email tài khoản Atlassian và API Token tạo tại `https://id.atlassian.com/manage-profile/security/api-tokens`.

### Vòng 3: Cấu hình Git & Nhận diện Commit
- **Trinh sát tự động:**
  - Chạy `git config user.email`, `git config user.name`.
  - Quét `git log -n 20 --pretty=format:"%ae|%an"` trên các repo lân cận để lập danh sách tác giả tiềm năng.
  - Quét các thư mục cha để phát hiện các git clone đang tồn tại.
- **Câu hỏi Frontier:**
  - `Q1`: Danh sách `author_emails` để quét commit (trình bày danh sách email/alias đã phát hiện được).
  - `Q2`: Thư mục gốc chứa các repo (`repo_roots`) và danh sách tổ chức Git (`remote_orgs`) hoặc chỉ định danh sách repo cụ thể (`repos`).

### Vòng 4: Quy chuẩn dự án & Custom Fields
- **Trinh sát tự động:** Kiểm tra các dịch vụ frontend trong workspace để phân loại `[FE]` / `[BE]`.
- **Câu hỏi Frontier:**
  - `Q1`: Danh sách dịch vụ frontend (`frontend_services`) cần gắn nhãn `[FE]`.
  - `Q2`: Các trường tùy chỉnh bắt buộc (Đối với VNPT `NCPTWORK`: trường Công đoạn `customfield_13000` và Mã SPDA `customfield_13100`).

---

## 4. Thực thi và Nghiệm thu (Finalize & Health Check)

1. **Hiển thị bản xem trước (Preview):** Trình bày nội dung `config.yaml` dự kiến (che mờ ký tự mật khẩu/token).
2. **Ghi file:** Ghi cấu hình vào `config.yaml` (đảm bảo file đã nằm trong `.gitignore`).
3. **Kiểm tra sức khỏe hệ thống (Health Check):**
   - Chạy lệnh Python nạp file `config.yaml` với `yaml.safe_load`.
   - Kiểm tra kết nối Jira qua API `/myself` để xác nhận token/tài khoản hợp lệ.
   - Thử nghiệm quét nhanh commit hôm nay bằng `scan_daily_work`.
4. **Bàn giao:** Hướng dẫn các câu lệnh tiếp theo (`/logwork`, `/setup`, kiểm tra MCP server).
