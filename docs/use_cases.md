# 📖 ĐẶC TẢ USE CASE & BIỂU ĐỒ TRÌNH TỰ HỆ THỐNG (USE CASE SPECIFICATION)

> **CƠ QUAN CHỦ QUẢN**: TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN VÀ TRUYỀN THÔNG (ICTU) — KHOA CNTT  
> **ĐỀ TÀI**: HỆ THỐNG QUẢN LÝ CHI TIÊU CÁ NHÂN CÓ TÍCH HỢP AI (PERSONAL EXPENSE AI)  
> **NHÓM THỰC HIỆN**: NHÓM 04 (Lê Tâm An - Backend & Dương Đình Hoàng - Frontend)  
> **GIẢNG VIÊN HƯỚNG DẪN**: ThS. Nguyễn Thị Tuyển  
> **TÀI LIỆU CĂN CỨ**: [REQUIREMENTS.md](file:///d:/code%20vscode/presonal-expense/personal-expense-ai/REQUIREMENTS.md), [kn2.docx](file:///d:/code%20vscode/presonal-expense/personal-expense-ai/kn2.docx) và [docs/requirements.md](file:///d:/code%20vscode/presonal-expense/personal-expense-ai/docs/requirements.md)

---

## 👥 1. XÁC ĐỊNH TÁC NHÂN HỆ THỐNG (ACTORS)

Theo Mục 2.3 của [kn2.docx](file:///d:/code%20vscode/presonal-expense/personal-expense-ai/kn2.docx), hệ thống tương tác với các tác nhân sau:

| Tác nhân (Actor) | Phân loại | Vai trò & Trách nhiệm trong hệ thống |
|---|---|---|
| **Người dùng cá nhân (End User)** | Tác nhân chính (Primary Actor) | Là người đã đăng nhập, trực tiếp nhập liệu thu chi, thiết lập ngân sách, nạp/rút tiền tiết kiệm, xem báo cáo trực quan và đặt câu hỏi cho trợ lý AI. |
| **Quản trị viên hệ thống (Administrator)** | Tác nhân quản trị (Administrative Actor) | Quản trị tài khoản người dùng, xử lý sự cố đăng nhập/khóa tài khoản, cấp lại mật khẩu tạm thời và giám sát tài nguyên gọi AI Gemini (theo chuẩn Zero-Knowledge không xem chi tiết chi tiêu riêng tư). |
| **Dịch vụ AI Đám mây (Cloud AI / Gemini)** | Tác nhân hỗ trợ (Secondary Actor) | Cung cấp dịch vụ mô hình ngôn ngữ lớn (LLM) và thị giác máy tính: phân tích thói quen, gợi ý ngân sách, trả lời câu hỏi chat và OCR hóa đơn. |
| **Hệ thống Máy chủ (PCServer / Backend)** | Tác nhân hệ thống | Tiếp nhận yêu cầu, xác thực JWT, kiểm soát giao dịch ACID, khóa dòng bi quan (`SELECT ... FOR UPDATE`) và ẩn danh hóa dữ liệu trước khi gửi sang AI. |

---

## 🗺️ 2. BIỂU ĐỒ USE CASE TỔNG QUÁT & PHÂN RÃ

### 2.1. Biểu đồ Use Case Tổng quát (Mục 2.4 kn2.docx)

```mermaid
graph TB
    User((👤 Người dùng))
    Admin((🛡️ Quản trị viên))
    AI((🤖 Cloud AI Gemini))

    subgraph System ["HỆ THỐNG QUẢN LÝ CHI TIÊU CÁ NHÂN CÓ TÍCH HỢP AI"]
        UC_Account["1. Quản lý tài khoản cá nhân"]
        UC_Category["2. Quản lý danh mục"]
        UC_Txn["3. Quản lý giao dịch & Thùng rác"]
        UC_Budget["4. Quản lý ngân sách"]
        UC_Goal["5. Quản lý mục tiêu tiết kiệm"]
        UC_Stats["6. Xem thống kê chi tiêu"]
        UC_AI["7. Sử dụng trợ lý AI FinAI"]
        UC_Admin_Users["8. Quản trị tài khoản & Sự cố người dùng"]
        UC_Admin_Stats["9. Giám sát hệ thống & AI Telemetry"]
    end

    User --> UC_Account
    User --> UC_Category
    User --> UC_Txn
    User --> UC_Budget
    User --> UC_Goal
    User --> UC_Stats
    User --> UC_AI

    Admin --> UC_Admin_Users
    Admin --> UC_Admin_Stats

    UC_AI -.->|<<interact>>| AI
    UC_Admin_Stats -.->|<<monitor>>| AI
```

---

### 2.2. Biểu đồ Use Case Phân rã 7 Phân hệ (Mục 2.5 kn2.docx)

```mermaid
graph LR
    subgraph UC_Detail ["CÁC USE CASE PHÂN RÃ CHI TIẾT"]
        direction TB
        subgraph G1 ["2.5.1. Quản lý tài khoản"]
            UC01["Đăng ký tài khoản"]
            UC02["Đăng nhập & Nhận JWT"]
            UC03["Quản lý thông tin & Đổi mật khẩu"]
        end

        subgraph G2 ["2.5.2. Quản lý danh mục"]
            UC04["Thêm danh mục mới"]
            UC05["Sửa đổi danh mục"]
            UC06["Ẩn/Hiện & Xóa mềm danh mục"]
        end

        subgraph G3 ["2.5.3. Quản lý giao dịch"]
            UC07["Thêm giao dịch thu/chi"]
            UC08["Nhân bản giao dịch"]
            UC09["Chuyển thùng rác & Khôi phục"]
            UC10["Tìm kiếm & Lọc giao dịch"]
        end

        subgraph G4 ["2.5.4. Quản lý ngân sách"]
            UC12["Thiết lập hạn mức ngân sách"]
            UC13["Giám sát & Cảnh báo bội chi"]
        end

        subgraph G5 ["2.5.5. Quản lý mục tiêu tiết kiệm"]
            UC14["Tạo mục tiêu tiết kiệm"]
            UC15["Nạp tiền vào quỹ tiết kiệm"]
            UC16["Rút tiền từ quỹ tiết kiệm (FIFO)"]
            UC17["Hủy mục tiêu hoàn tiền ví"]
        end

        subgraph G6 ["2.5.6. Xem thống kê chi tiêu"]
            UC18["Xem tổng quan số dư khả dụng"]
            UC19["Xem biểu đồ cơ cấu danh mục"]
            UC20["Xem biểu đồ xu hướng thu chi SVG"]
        end

        subgraph G7 ["2.5.7. Sử dụng trợ lý AI"]
            UC21["AI Sinh báo cáo chi tiêu tháng"]
            UC22["AI Gợi ý hạn mức ngân sách"]
            UC23["Trò chuyện với Chatbot FinAI"]
            UC24["AI OCR Quét hóa đơn mua sắm"]
        end
    end
```

---

## 🔄 3. BIỂU ĐỒ TRÌNH TỰ TIÊU BIỂU (SEQUENCE DIAGRAMS)

Theo quy định tại **Mục 3.1 của [kn2.docx](file:///d:/code%20vscode/presonal-expense/personal-expense-ai/kn2.docx)**, hệ thống được nhóm thành các nhóm nghiệp vụ chính và lựa chọn các biểu đồ trình tự tiêu biểu nhất cho từng nhóm:

### 3.1.1. Nhóm Xác thực tài khoản (Đăng nhập hệ thống)
*Người dùng nhập thông tin qua Form, Controller kiểm tra tính hợp lệ và truy vấn CSDL; nếu đúng mật khẩu, hệ thống tạo Access Token và chuyển hướng vào Dashboard, ngược lại sẽ báo lỗi.*

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as PCClient (React)
    participant AuthCtrl as AuthController (FastAPI)
    participant DB as MySQL Database

    User->>UI: Nhập email/username và mật khẩu, nhấn "Đăng nhập"
    UI->>AuthCtrl: POST /api/auth/login {email, password}
    AuthCtrl->>DB: SELECT * FROM users WHERE email = :email
    DB-->>AuthCtrl: Trả về bản ghi user (chứa password_hash)
    
    alt Sai mật khẩu hoặc không tìm thấy email
        AuthCtrl-->>UI: HTTP 401 Unauthorized ("Thông tin đăng nhập không chính xác")
        UI-->>User: Hiển thị thông báo lỗi trên form
    else Mật khẩu hợp lệ (Bcrypt verify thành công)
        AuthCtrl->>AuthCtrl: Sinh JWT Token (HS256, hạn 7 ngày)
        AuthCtrl-->>UI: HTTP 200 OK {access_token, user_info}
        UI->>UI: Lưu token vào localStorage
        UI-->>User: Điều hướng tự động vào màn hình Dashboard
    end
```

---

### 3.1.2. Nhóm Quản lý danh mục (Thêm mới & Cập nhật danh mục)
*Người dùng nhập thông tin danh mục mới; Controller kiểm tra tính hợp lệ rồi gửi lệnh INSERT lưu vào bảng categories trong CSDL và hiển thị thông báo thành công.*

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as PCClient (React)
    participant CatCtrl as CategoryController (FastAPI)
    participant DB as MySQL Database

    User->>UI: Nhập tên danh mục, chọn loại (income/expense), icon, màu sắc
    UI->>CatCtrl: POST /api/categories (Header: Bearer Token)
    CatCtrl->>CatCtrl: Chuẩn hóa tên (name_normalized)
    CatCtrl->>DB: SELECT id FROM categories WHERE user_id = :uid AND name_normalized = :norm
    
    alt Tên danh mục đã tồn tại
        DB-->>CatCtrl: Đã có bản ghi
        CatCtrl-->>UI: HTTP 400 Bad Request ("Danh mục đã tồn tại")
        UI-->>User: Báo lỗi trùng lặp trên giao diện
    else Tên danh mục hợp lệ
        DB-->>CatCtrl: Không trùng
        CatCtrl->>DB: INSERT INTO categories (user_id, name, name_normalized, type, icon, color)
        DB-->>CatCtrl: Ghi bản ghi thành công
        CatCtrl-->>UI: HTTP 201 Created {category_data}
        UI-->>User: Cập nhật danh sách danh mục & Thông báo thành công
    end
```

---

### 3.1.3. Nhóm Giao dịch và Khôi phục (Thêm giao dịch & Kiểm soát số dư)
*Khi người dùng mở form, hệ thống truy vấn CSDL để lấy danh mục; người dùng điền thông tin, Controller kiểm tra an toàn số dư và thực thi INSERT INTO transactions.*

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as PCClient (React)
    participant TxnCtrl as TransactionController (FastAPI)
    participant DB as MySQL Database

    User->>UI: Nhập giao dịch (Số tiền, Ngày, Loại, Danh mục, Phương thức)
    UI->>TxnCtrl: POST /api/transactions
    TxnCtrl->>DB: BEGIN TRANSACTION
    TxnCtrl->>DB: SELECT id FROM users WHERE id = :uid FOR UPDATE
    DB-->>TxnCtrl: Khóa hàng user thành công

    TxnCtrl->>DB: Tính toán Available Balance hiện tại
    DB-->>TxnCtrl: Available Balance = 2,500,000 đ

    alt Là giao dịch chi tiêu (Expense) và Số tiền chi > Available Balance
        TxnCtrl->>DB: ROLLBACK
        TxnCtrl-->>UI: HTTP 400 Bad Request ("Số dư khả dụng không đủ để thực hiện giao dịch")
        UI-->>User: Báo lỗi cảnh báo thiếu số dư
    else Hợp lệ thỏa mãn bất biến số dư
        TxnCtrl->>DB: INSERT INTO transactions (user_id, category_id, type, amount, date, ...)
        DB-->>TxnCtrl: Ghi thành công
        TxnCtrl->>DB: COMMIT TRANSACTION
        TxnCtrl-->>UI: HTTP 201 Created {transaction_data}
        UI-->>User: Hiển thị giao dịch mới trong danh sách & Cập nhật số dư ví
    end
```

---

### 3.1.4. Nhóm Ngân sách (Thiết lập & Cảnh báo bội chi)
*Người dùng nhập hạn mức và tháng áp dụng, Controller kiểm tra tính hợp lệ rồi lưu vào bảng budgets; tự động đối chiếu tổng chi với hạn mức để kích hoạt cảnh báo.*

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as PCClient (React)
    participant BgtCtrl as BudgetController (FastAPI)
    participant DB as MySQL Database

    User->>UI: Chọn danh mục, nhập hạn mức (amount) cho tháng M/Y
    UI->>BgtCtrl: POST /api/budgets {category_id, amount, month, year}
    BgtCtrl->>DB: Kiểm tra UQ(user_id, category_id, month, year)
    
    alt Đã tồn tại hạn mức cho danh mục trong tháng
        BgtCtrl->>DB: UPDATE budgets SET amount = :new_amount WHERE ...
    else Chưa tồn tại
        BgtCtrl->>DB: INSERT INTO budgets (user_id, category_id, amount, month, year)
    end
    DB-->>BgtCtrl: Lưu hạn mức thành công

    BgtCtrl->>DB: SELECT SUM(amount) FROM transactions WHERE category_id = :cid AND month = :m AND is_deleted = 0
    DB-->>BgtCtrl: Tổng chi thực tế = 4,200,000 đ / Hạn mức = 5,000,000 đ (84%)
    
    BgtCtrl-->>UI: HTTP 200 OK {budget_data, spent: 4200000, percent: 84%, status: "warning"}
    UI-->>User: Hiển thị thanh tiến độ màu vàng cam (Cảnh báo sắp chạm ngưỡng)
```

---

### 3.1.5. Nhóm Mục tiêu tiết kiệm (Nạp tiền & Rút tiền có sổ Ledger FIFO)
*Nạp tiền: INSERT vào saving_contributions và UPDATE saving_goals. Rút tiền: Kiểm tra số dư quỹ, ghi saving_withdrawals và phân bổ khấu trừ FIFO vào saving_withdrawal_allocations.*

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as PCClient (React)
    participant GoalCtrl as SavingGoalController (FastAPI)
    participant DB as MySQL Database

    User->>UI: Chọn mục tiêu, nhấn "Rút tiền", nhập số tiền cần rút
    UI->>GoalCtrl: POST /api/saving-goals/{id}/withdraw {amount, note}
    GoalCtrl->>DB: BEGIN TRANSACTION
    GoalCtrl->>DB: SELECT * FROM users WHERE id = :uid FOR UPDATE
    GoalCtrl->>DB: SELECT * FROM saving_goals WHERE id = :gid FOR UPDATE
    DB-->>GoalCtrl: Trả về thông tin quỹ (current_amount = 3,000,000 đ)

    alt Số tiền rút > current_amount trong quỹ
        GoalCtrl->>DB: ROLLBACK
        GoalCtrl-->>UI: HTTP 400 Bad Request ("Số tiền rút vượt quá số dư đang có trong quỹ")
        UI-->>User: Báo lỗi số dư quỹ không đủ
    else Thỏa mãn điều kiện rút
        GoalCtrl->>DB: INSERT INTO saving_withdrawals (saving_goal_id, amount, note)
        GoalCtrl->>DB: Truy vấn các saving_contributions chưa tiêu thụ theo thứ tự thời gian (FIFO)
        GoalCtrl->>DB: INSERT INTO saving_withdrawal_allocations (withdrawal_id, contribution_id, amount)
        GoalCtrl->>DB: UPDATE saving_goals SET current_amount = current_amount - :amount
        GoalCtrl->>DB: COMMIT TRANSACTION
        GoalCtrl-->>UI: HTTP 200 OK {goal_updated, balance_released}
        UI-->>User: Cập nhật tiến độ quỹ & Hoàn trả số tiền rút về Số dư khả dụng
    end
```

---

### 3.1.6. Nhóm Thống kê chi tiêu & Biểu đồ SVG
*Khi người dùng truy cập trang tổng quan, Controller truy vấn CSDL để tính toán tổng số dư, tổng thu, tổng chi và trả dữ liệu về để Frontend tự vẽ biểu đồ SVG sắc nét.*

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as PCClient (React SVG Hub)
    participant StatsCtrl as StatsController (FastAPI)
    participant DB as MySQL Database

    User->>UI: Mở trang Dashboard (hoặc chọn chu kỳ 3, 6, 12 tháng)
    UI->>StatsCtrl: GET /api/transactions/summary?period=current_month
    StatsCtrl->>DB: SELECT SUM(income), SUM(expense) FROM transactions WHERE user_id = :uid AND is_deleted = 0
    StatsCtrl->>DB: SELECT SUM(current_amount) FROM saving_goals WHERE user_id = :uid AND status != 'cancelled'
    StatsCtrl->>DB: SELECT category_name, SUM(amount) FROM transactions GROUP BY category_id
    DB-->>StatsCtrl: Trả về tập dữ liệu thô
    
    StatsCtrl->>StatsCtrl: Tính Available Balance = Tổng thu - Tổng chi - Tiết kiệm
    StatsCtrl-->>UI: HTTP 200 OK {total_income, total_expense, available_balance, by_category, trends}
    
    UI->>UI: Tự tính scale tọa độ và render thẻ SVG (<rect>, <line>, <text>, <circle>)
    UI-->>User: Hiển thị Metric Cards, Biểu đồ Donut phân bổ và Biểu đồ cột đôi thu/chi
```

---

### 3.1.7. Nhóm Trợ lý AI (Sinh báo cáo tháng & Gemini OCR Hóa đơn)
*Hệ thống tổng hợp dữ liệu sạch, đưa vào System/User Prompt chuẩn 5 thành phần, gọi Gemini API và hiển thị kết quả cho người dùng.*

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as PCClient (React)
    participant AICtrl as AIController (FastAPI)
    participant DB as MySQL Database
    participant Gemini as Google Cloud Gemini API

    User->>UI: Nhấn "Sinh báo cáo tài chính AI" cho tháng 09/2026
    UI->>AICtrl: POST /api/ai/monthly-report {month: 9, year: 2026}
    AICtrl->>DB: Truy vấn tổng thu, tổng chi, chi tiết theo danh mục trong tháng
    DB-->>AICtrl: Dữ liệu tài chính tháng đã tổng hợp
    
    AICtrl->>AICtrl: Ẩn danh hóa dữ liệu (Loại bỏ tên, email, số tài khoản)
    AICtrl->>AICtrl: Xây dựng System Prompt (Role Financial Planner) & User Prompt 5 thành phần
    
    AICtrl->>Gemini: POST /v1beta/models/gemini-1.5-flash:generateContent {prompt}
    
    alt Gemini Timeout hoặc Lỗi kết nối mạng
        AICtrl->>AICtrl: Kích hoạt Fallback Rule Engine nội bộ
        AICtrl-->>UI: HTTP 200 OK {report_markdown: "[Báo cáo nội bộ dự phòng]...", is_fallback: true}
    else Gemini phản hồi thành công
        Gemini-->>AICtrl: Văn bản nhận xét (100-150 từ, khoản chi lớn nhất, gợi ý điều chỉnh)
        AICtrl->>DB: INSERT INTO ai_reports (user_id, month, year, report_type, content)
        AICtrl-->>UI: HTTP 200 OK {report_markdown: "...", is_fallback: false}
    end
    UI-->>User: Hiển thị báo cáo phân tích tài chính AI trực quan trên giao diện
```

---

### 3.8. Biểu đồ Trình tự Phân hệ Quản trị viên (Admin Subsystem)

#### Use Case 8: Quản trị tài khoản & Xử lý sự cố người dùng (Lock / Unlock & Reset Password)
```mermaid
sequenceDiagram
    autonumber
    actor Admin as 🛡️ Quản trị viên (Admin)
    participant UI as Giao diện Quản trị (AdminUsersPage)
    participant Ctrl as Bộ điều khiển Admin (AdminRouter)
    participant DB as CSDL MySQL 8 (InnoDB)

    Admin->>UI: Tìm kiếm tài khoản và chọn thao tác (Khóa / Mở khóa / Reset Pass)
    UI->>Ctrl: PATCH /api/v1/admin/users/{id}/status {is_locked}
    Ctrl->>Ctrl: Kiểm tra quyền get_current_admin (role == "admin")
    alt Cố tình tự khóa chính mình
        Ctrl-->>UI: HTTP 400 Bad Request ("Không thể tự khóa tài khoản của chính mình")
    else Khóa/Mở khóa hợp lệ
        Ctrl->>DB: UPDATE users SET is_locked = :val WHERE id = :id
        DB-->>Ctrl: Bản ghi được cập nhật
        Ctrl-->>UI: HTTP 200 OK {id, is_locked, role, ...}
        UI-->>Admin: Hiển thị badge trạng thái mới và thông báo Toast
    end
```

---

## 🏗️ 4. BIỂU ĐỒ TRIỂN KHAI HỆ THỐNG (DEPLOYMENT DIAGRAM)

Theo đặc tả chi tiết tại **Mục 3.4 của [kn2.docx](file:///d:/code%20vscode/presonal-expense/personal-expense-ai/kn2.docx)**:

```mermaid
graph TD
    subgraph PCClient ["💻 1. Nút PCClient (Máy khách người dùng)"]
        Browser["Trình duyệt Web (Chrome / Edge / Firefox)"]
        ReactApp["Giao diện người dùng (React 19 + Vite 8)<br/>- Thành phần UI & SVG Charts<br/>- FinAI Mascot 3D Animation<br/>- Axios Client (Gửi Bearer JWT)"]
        Browser --- ReactApp
    end

    subgraph PCServer ["🖥️ 2. Nút PCServer (Máy chủ ứng dụng)"]
        FastAPIServer["Máy chủ Backend (FastAPI - Python 3.11)<br/>- Bộ định tuyến REST API (/api/*)<br/>- Middleware xác thực JWT<br/>- Dependency Injection (get_current_user)<br/>- Khóa dòng SELECT ... FOR UPDATE"]
        
        DataAccessor["Tầng truy cập dữ liệu (SQLAlchemy 2.0 ORM)"]
        
        AIServiceModule["Thành phần giao tiếp AI<br/>- Ẩn danh hóa dữ liệu (Data Minimization)<br/>- Module OCR Gemini Vision Base64<br/>- Trình phân tích Regex & Fallback Engine"]
        
        MySQLServer[("Cơ sở dữ liệu MySQL 8.0<br/>- InnoDB Engine (ACID)<br/>- 10 bảng quan hệ & Composite FK<br/>- UTF-8 mb4 unicode")]

        FastAPIServer --> DataAccessor
        FastAPIServer --> AIServiceModule
        DataAccessor --> MySQLServer
    end

    subgraph CloudAIService ["☁️ 3. Nút Cloud AI Service (Đám mây Google)"]
        GeminiAPI["Google Gemini AI Platform<br/>- Model: gemini-1.5-flash<br/>- Model: gemini-1.5-flash-vision<br/>- Phân tích văn bản & OCR hình ảnh"]
    end

    ReactApp ===|Giao thức HTTP/HTTPS (Port 5173 -> 8000)| FastAPIServer
    AIServiceModule ===|Giao thức HTTPS (Google AI Studio REST API)| GeminiAPI
```

### Mô tả các nút và lý do lựa chọn kiến trúc:
1. **PCClient**: Cung cấp giao diện Web SPA gọn nhẹ, chạy trực tiếp trên trình duyệt của người dùng. Chịu trách nhiệm render giao diện, quản lý form và tương tác thời gian thực.
2. **PCServer**: Chịu trách nhiệm toàn bộ xử lý nghiệp vụ tài chính, bảo vệ mật khẩu, điều khiển giao dịch ACID và bảo vệ bất biến số dư ví.
3. **Cloud AI Service**: Dịch vụ đám mây xử lý các tác vụ trí tuệ nhân tạo chuyên sâu (sinh báo cáo, đọc hóa đơn thị giác) mà không đòi hỏi tài nguyên phần cứng GPU đắt đỏ trên máy chủ cục bộ.
4. **Lý do lựa chọn mô hình 2 tầng kết hợp Cloud AI**: Phù hợp với điều kiện triển khai thực tế của nhóm sinh viên; tách biệt rõ ràng giữa Client - Server giúp hệ thống bảo mật, dễ nâng cấp và tận dụng sức mạnh AI hiện đại một cách linh hoạt.
