# Chi tiêu cá nhân — Personal Expense AI

Ứng dụng quản lý thu chi cá nhân gồm FastAPI, React và MySQL. Hệ thống hỗ trợ
Transaction CRUD, thùng rác, danh mục tùy chỉnh, ngân sách, mục tiêu tiết kiệm,
phân bổ thu nhập vào mục tiêu và nhập sao kê Excel.

## Tài liệu

- [API Transaction và Category](docs/API.md)
- [Database và migration](docs/DATABASE.md)
- [Changelog](CHANGELOG.md)
- Swagger UI khi backend đang chạy: `http://127.0.0.1:8000/docs`

## Yêu cầu

- Python 3.11 trở lên.
- Node.js tương thích Vite 8 và npm.
- MySQL 8 cho môi trường ứng dụng thực tế.

Test backend mặc định sử dụng SQLite in-memory. Test migration MySQL là test tùy
chọn và luôn tạo một database dùng một lần.

## Cấu hình môi trường

Tạo file cấu hình từ các mẫu; không commit file `.env`.

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Biến backend:

| Biến | Bắt buộc | Ý nghĩa |
|---|---:|---|
| `DATABASE_URL` | Có | SQLAlchemy URL, ví dụ `mysql+pymysql://user:password@localhost:3306/personal_expense`. |
| `SECRET_KEY` | Có | Secret ký JWT; phải là chuỗi ngẫu nhiên dài và không dùng giá trị mẫu. |
| `CORS_ORIGINS` | Có khi chạy frontend riêng | JSON array origin được phép, ví dụ `["http://localhost:5173"]`. |
| `ALGORITHM` | Không | Thuật toán JWT, mặc định `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Không | Thời hạn access token, mặc định 30 phút. |
| `FRONTEND_BASE_URL` | Không | URL frontend dùng trong luồng reset mật khẩu. |
| `SMTP_*` | Theo tính năng | Cần khi gửi email reset mật khẩu qua SMTP. |
| `MAX_IMAGE_SIZE_MB`, `MAX_EXCEL_SIZE_MB` | Không | Giới hạn upload, mặc định lần lượt 10 MB và 5 MB. |
| `OCR_PROVIDER`, `GEMINI_API_KEY`, `GEMINI_MODEL` | Theo tính năng | Cần cho OCR/AI khi chọn Gemini; không bắt buộc cho CRUD cơ bản. |

Frontend dùng `VITE_API_BASE_URL`; nếu bỏ trống, mặc định là
`http://localhost:8000/api/v1`.

Nếu username hoặc password MySQL chứa ký tự đặc biệt như `@`, `#`, `/`, `%`,
hãy URL-encode trước khi đưa vào `DATABASE_URL`.

## Chạy backend

Từ thư mục gốc:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --reload --reload-dir backend --app-dir backend --host 127.0.0.1 --port 8000
```

Backend tự tạo các bảng còn thiếu bằng SQLAlchemy metadata khi khởi động. Với
database legacy, hãy đọc [tài liệu migration](docs/DATABASE.md) trước khi chạy
ứng dụng. Health check: `GET http://127.0.0.1:8000/health`.

## Chạy frontend

Trong terminal khác:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Mở `http://localhost:5173`.

## Quy tắc nghiệp vụ chính

- Tất cả Transaction, Category, Budget và Saving Goal đều thuộc user lấy từ JWT;
  client không được truyền `user_id` để thay quyền sở hữu.
- Transaction hỗ trợ tạo, xem, sửa, đưa vào thùng rác, restore và xóa vĩnh viễn.
  Xóa vĩnh viễn chỉ hợp lệ sau khi Transaction đã ở trong thùng rác.
- Category có ba trạng thái thực tế: active, hidden (`is_active=false`) và
  soft-deleted (`deleted_at` khác null). Hidden có thể restore; deleted không có
  endpoint restore và bị loại khỏi danh sách Category.
- Không thể đổi `Category.type` khi danh mục đã từng được dùng bởi Transaction
  hoặc Budget.
- Transaction mới và Excel import chỉ được dùng Category active, chưa xóa và
  cùng loại `income`/`expense`.
- `total_balance = all_time_income - all_time_expense`.
- `saving_balance` là tổng `current_amount` của Saving Goal không cancelled.
- `available_balance = total_balance - saving_balance`. Các thao tác làm số dư
  khả dụng âm sẽ bị từ chối và được tuần tự hóa bằng khóa hàng User trên MySQL.
- `income_allocation` chỉ được tạo trong `POST /transactions` bằng
  `saving_goal_id` và `saving_goal_amount`. API contribution công khai của
  Saving Goal chỉ nhận khoản nạp thủ công `amount` và `note`.
- Excel gồm hai bước: parse để preview, sau đó import các dòng đã xác nhận. Mỗi
  import phải có `idempotency_key` duy nhất theo user để chống submit lặp.

## Checklist xác minh

Từ thư mục gốc:

```powershell
pytest -q -p no:cacheprovider
Set-Location frontend
npm test -- --run
npm run lint
npm run build
Set-Location ..
git diff --check
```

Test migration MySQL không nằm trong suite mặc định; xem lệnh chạy với database
dùng một lần tại [docs/DATABASE.md](docs/DATABASE.md#test-migration-mysql-bằng-database-dùng-một-lần).

---

## 🤖 Hướng dẫn làm việc với AI Agents

Dự án sử dụng **2 AI Agents** để hỗ trợ quy trình phát triển phần mềm. Toàn bộ cấu hình AI được lưu trong thư mục `.agents`.

### 1. Công nghệ của dự án

* **Backend:** FastAPI (Python).
* **Frontend:** React.
* **Cơ sở dữ liệu:** MySQL.
* **IDE:** Antigravity IDE.
* **Quản lý mã nguồn:** Git và GitHub.

Mỗi thành viên tự cấu hình API Key trong phần cài đặt LLM của IDE. Tuyệt đối không ghi API Key, mật khẩu MySQL, token hoặc secret trực tiếp vào source code.

Các biến môi trường nhạy cảm phải được lưu trong file `.env`. Không commit hoặc push file `.env` lên GitHub.

### 2. Danh sách AI Agents

Dự án chỉ sử dụng đúng **2 Agent**:

#### `/agent-1-dev` — Full-stack Developer

Agent 1 chịu trách nhiệm phát triển toàn bộ tính năng:

* Xây dựng backend bằng FastAPI.
* Thiết kế model và thao tác dữ liệu MySQL.
* Xây dựng REST API.
* Xử lý authentication và phân quyền.
* Validation dữ liệu.
* Xây dựng giao diện bằng React.
* Quản lý state và tích hợp frontend với API.
* Xử lý loading, lỗi và trạng thái không có dữ liệu.
* Sửa lỗi sau khi nhận báo cáo từ Agent 3.
* Chạy test, lint và production build trước khi báo hoàn thành.

Agent 1 phải đọc `REQUIREMENTS.md` và kiểm tra code hiện tại trước khi sửa. Không được tự suy đoán cấu trúc dự án hoặc viết lại toàn bộ hệ thống khi không cần thiết.

#### `/agent-3-qa` — QA và Code Reviewer

Agent 3 chỉ chịu trách nhiệm kiểm thử và đánh giá:

* Review code FastAPI và React.
* Kiểm tra logic nghiệp vụ.
* Kiểm tra validation.
* Kiểm tra authentication và phân quyền.
* Kiểm tra nguy cơ SQL Injection và lộ dữ liệu.
* Kiểm tra quyền sở hữu Transaction và Category.
* Kiểm tra tích hợp frontend với backend.
* Kiểm tra Unit Test và Integration Test.
* Phát hiện regression và lỗi bảo mật.
* Đề xuất cách sửa cho Agent 1.

Agent 3 chỉ được đọc, kiểm tra và báo cáo. Agent 3 không được triển khai tính năng mới, tự sửa code, commit hoặc push.

Dự án **không sử dụng Agent 2**.

### 3. Quy trình làm việc chuẩn

Mỗi tính năng phải thực hiện theo quy trình sau:

1. Mở một chat mới và gọi `/agent-1-dev`.
2. Giao cho Agent 1 đúng một tính năng cần triển khai.
3. Agent 1 phát triển backend FastAPI, frontend React và tích hợp MySQL.
4. Lập trình viên chạy thử và kiểm tra code.
5. Khi tính năng đã hoạt động, mở một chat mới hoàn toàn.
6. Gọi `/agent-3-qa` và cung cấp các file hoặc đoạn code cần đánh giá.
7. Agent 3 review, chạy test nếu phù hợp và lập báo cáo lỗi.
8. Lập trình viên kiểm tra, chọn lọc các nhận xét hợp lý.
9. Quay lại chat của Agent 1 và gửi báo cáo QA để Agent 1 sửa lỗi.
10. Chạy lại toàn bộ test, frontend lint và production build.
11. Chỉ commit khi tính năng đã vượt qua kiểm tra.

### 4. Quy tắc sử dụng Agent

* Một tính năng tương ứng với một luồng chat.
* Không gọi Agent 1 và Agent 3 trong cùng một chat.
* Khi chuyển từ phát triển sang QA, phải mở chat mới.
* Agent 1 là Agent duy nhất được viết hoặc sửa code tính năng.
* Agent 3 chỉ review và kiểm thử.
* Không sử dụng hoặc tạo Agent 2.
* Không yêu cầu AI đọc toàn bộ repository nếu không cần thiết.
* Nên tag chính xác file cần xử lý, ví dụ `@transactions.py` hoặc `@TransactionPage.jsx`.
* Mô tả rõ hàm, API hoặc lỗi cần xử lý.
* Không sao chép code do AI tạo ra vào nhánh chính khi chưa đọc và chạy thử.
* Không cho AI tự commit, push hoặc tạo Pull Request nếu chưa được yêu cầu rõ ràng.

### 5. Bảo mật dữ liệu

* Chỉ sử dụng dữ liệu giả trong prompt, test và báo cáo mẫu.
* Không gửi thông tin tài chính hoặc thông tin cá nhân thật cho AI.
* Không đưa API Key, access token, JWT, mật khẩu MySQL hoặc secret vào chat.
* Không hardcode thông tin nhạy cảm trong FastAPI hoặc React.
* Không commit file `.env`.
* Chỉ commit `.env.example` với giá trị minh họa.
* Không ghi token hoặc mật khẩu vào log.
* Mọi API liên quan đến dữ liệu cá nhân phải giới hạn theo người dùng hiện tại.
* Người dùng không được xem, sửa hoặc xóa dữ liệu của tài khoản khác.

Ví dụ cấu hình an toàn:

```env
DATABASE_URL=mysql+pymysql://DB_USER:DB_PASSWORD@localhost:3306/personal_expense
SECRET_KEY=replace-with-a-secure-secret
```

Nếu tên người dùng hoặc mật khẩu chứa ký tự đặc biệt như `@`, `#`, `/` hoặc `%`, cần mã hóa URL trước khi đưa vào `DATABASE_URL`.

### 6. Git Workflow

#### Bảo vệ nhánh `main`

Nhánh `main` chỉ chứa code đã được kiểm thử thành công.

Không code hoặc push trực tiếp lên `main`.

#### Tạo Feature Branch

Mỗi tính năng phải được phát triển trên một nhánh riêng, được tạo từ `main`.

Ví dụ:

```bash
git switch main
git pull origin main
git switch -c feature/transaction-management
```

Tên nhánh phải mô tả tính năng, không đặt theo tên thành viên.

Ví dụ hợp lệ:

```text
feature/api-transaction
feature/ui-transaction
feature/transaction-management
fix/transaction-validation
```

#### Commit Message

Commit message sử dụng định dạng:

```text
[Loại thao tác] Mô tả ngắn gọn
```

Ví dụ:

```text
[Add] Hoàn thiện chức năng quản lý giao dịch
[Fix] Kiểm tra quyền sở hữu danh mục khi tạo giao dịch
[Test] Bổ sung kiểm thử phân quyền transaction
[Docs] Cập nhật hướng dẫn sử dụng AI Agents
```

Không sử dụng commit message không rõ nghĩa như:

```text
update
fix bug
code moi
```

#### Điều kiện trước khi commit

Chỉ commit khi:

* Backend test thành công.
* Frontend lint thành công.
* Frontend production build thành công.
* Không có API Key, mật khẩu, token hoặc secret trong diff.
* Không có `.env`, `node_modules`, cache hoặc build output trong commit.
* Lập trình viên đã đọc và kiểm tra code do AI tạo ra.

#### Gộp vào `main`

Trước khi merge, cập nhật nhánh tính năng từ `main`:

```bash
git switch feature/transaction-management
git pull origin main
```

Sau đó xử lý conflict, chạy lại toàn bộ kiểm tra và mới tạo Pull Request hoặc merge vào `main`.

Khi có conflict lớn, các thành viên phải trao đổi trực tiếp. Không tự ý ghi đè code của người khác.

### 7. Checklist trước khi hoàn thành tính năng

* [ ] Đã dùng `/agent-1-dev` để phát triển.
* [ ] Backend sử dụng FastAPI.
* [ ] Frontend sử dụng React.
* [ ] Cơ sở dữ liệu sử dụng MySQL.
* [ ] Đã chạy thử tính năng bằng dữ liệu giả.
* [ ] Đã mở chat mới và dùng `/agent-3-qa` để review.
* [ ] Đã kiểm tra và xử lý báo cáo QA.
* [ ] Backend test thành công.
* [ ] Frontend lint thành công.
* [ ] Frontend production build thành công.
* [ ] Không có dữ liệu thật hoặc secret trong source code.
* [ ] Không có `.env` hoặc `node_modules` trong commit.
* [ ] Commit message đúng quy chuẩn.
* [ ] Feature branch đã được cập nhật từ `main`.
