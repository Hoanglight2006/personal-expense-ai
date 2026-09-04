# Nhật Ký Phát Triển & Minh Chứng Sử Dụng AI

Tài liệu ghi lại chi tiết các mốc phát triển dự án **Personal Expense AI**, công việc thực tế theo ngày tháng, nội dung prompt khi dùng AI hỗ trợ (tuân thủ cấu trúc Context, Instructions, Constraints, Output Format như trong [AI_DEVELOPMENT_LOG.md](docs/AI_DEVELOPMENT_LOG.md)), những lỗi phát hiện từ phản hồi của AI và cách nhóm tự kiểm tra, hoàn thiện code.

---

### 📅 03/08 – 04/08/2026: Khởi tạo dự án & Khảo sát thiết kế hệ thống
* **Việc cần làm:**
  - Khởi tạo Git repository, dựng khung dự án Backend (FastAPI, SQLAlchemy) và Frontend (React, Vite).
  - Setup môi trường ảo Python `.venv`, cài đặt các thư viện cần thiết (`fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`).
  - Phân tích luồng nghiệp vụ quản lý chi tiêu cá nhân, phác thảo sơ đồ thực thể ERD ban đầu.
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Tôi đang bắt đầu xây dựng dự án web app quản lý chi tiêu cá nhân "Personal Expense AI", sử dụng Backend FastAPI và Frontend React (Vite).

    [Instructions]
    Gợi ý cấu trúc thư mục chuẩn cho dự án, tách bạch rõ ràng giữa routes, services, models và schemas để dễ mở rộng và kiểm thử sau này.

    [Input Data / Constraints]
    - Backend: Python 3.11+, FastAPI, SQLAlchemy, Pydantic, MySQL.
    - Frontend: React, Vite, CSS thuần.
    - Các tính năng dự kiến: Xác thực tài khoản, Quản lý danh mục, Giao dịch thu/chi, Ngân sách, Quỹ tiết kiệm và Trợ lý AI.

    [Output Format]
    Trình bày dưới dạng cây thư mục kèm chú thích ngắn gọn mục đích của từng thư mục chính.
    ```
  - *AI phản hồi:* AI gợi ý cấu trúc thư mục phân tầng (Layered Architecture). Nhóm lấy khung đó để dựng các thư mục `backend/app/api`, `backend/app/models`, `backend/app/services` và `frontend/src/components`.
* **Phát hiện lỗi và sửa:**
  - AI đưa file cấu hình `requirements.txt` không ghim phiên bản cụ thể, để `pydantic` tự do gây nguy cơ xung đột giữa Pydantic v1 và v2 với FastAPI mới. Nhóm kiểm tra và ghim rõ các phiên bản tương thích ổn định (`pydantic>=2.7.0`, `sqlalchemy>=2.0.0`).

---

### 📅 05/08 – 06/08/2026: Thiết kế CSDL (ERD) & Cài đặt Module Mã Hóa
* **Việc cần làm:**
  - Hoàn thiện sơ đồ quan hệ thực thể (ERD) gồm các bảng: `users`, `categories`, `transactions`, `budgets`, `saving_goals`, `saving_contributions`, `saving_withdrawals`.
  - Viết các model SQLAlchemy ban đầu trong thư mục `backend/app/models/`.
  - Viết module mã hóa mật khẩu bằng `bcrypt` và sinh token JWT trong `backend/app/core/security.py`.
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Tôi đang thiết kế cơ sở dữ liệu MySQL 8.0 cho app quản lý chi tiêu cá nhân bằng SQLAlchemy ORM trong FastAPI.

    [Instructions]
    Viết các model SQLAlchemy cho các bảng: User, Category, Transaction, Budget, SavingGoal. Cài đặt hàm hash mật khẩu bằng passlib bcrypt.

    [Input Data / Constraints]
    - Bảng User liên kết 1-n với các bảng còn lại.
    - Số tiền giao dịch và ngân sách cần đảm bảo độ chính xác khi tính toán tài chính.
    - Hỗ trợ lưu khóa bí mật an toàn.

    [Output Format]
    Mã nguồn Python khai báo SQLAlchemy models có type hints và hàm hash/verify password.
    ```
  - *AI phản hồi:* AI sinh ra các class model và hàm hash mật khẩu. Nhưng AI để kiểu số tiền là `Float`, quan hệ bảng Category là `ondelete="CASCADE"`, và hardcode `SECRET_KEY = "supersecret"` ngay trong file code.
* **Phát hiện lỗi và sửa:**
  - Lỗi sai số tiền: Đổi toàn bộ các cột tiền tệ từ `Float` sang `Numeric(15, 2)` để tránh sai số dấu phẩy động trong tính toán tài chính.
  - Lỗi mất dữ liệu: Đổi `CASCADE` ở bảng Category sang `RESTRICT` và thêm cột `is_hidden` (Boolean) để khi ẩn danh mục không bị xóa mất lịch sử giao dịch.
  - Lỗi bảo mật: Tách `SECRET_KEY`, `ALGORITHM` ra file cấu hình `.env` và quản lý tập trung qua file `config.py`.

---

### 📅 07/08 – 08/08/2026: Xây dựng API Xác thực (Auth) & Dựng giao diện Login/Register
* **Việc cần làm:**
  - Viết các API: Đăng ký tài khoản (`/register`), Đăng nhập nhận JWT token (`/login`), Đổi mật khẩu trong [auth.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/auth.py).
  - Viết dependency `get_current_user` kiểm tra token hợp lệ trên mỗi request gọi lên server.
  - Dựng trang Đăng nhập (`Login.jsx`) và Đăng ký (`Register.jsx`) trên React Frontend.
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Tôi đang phát triển module xác thực người dùng cho ứng dụng web chi tiêu cá nhân bằng FastAPI và React.

    [Instructions]
    Viết hai endpoint /register và /login bằng FastAPI:
    1. Kiểm tra email hợp lệ, kiểm tra trùng lặp email trong cơ sở dữ liệu.
    2. Mã hóa mật khẩu khi đăng ký, kiểm tra mật khẩu khi đăng nhập và trả về access token JWT có hạn 7 ngày.
    3. Viết form React đơn giản xử lý submit đăng ký và đăng nhập.

    [Input Data / Constraints]
    - Sử dụng OAuth2PasswordBearer và thư viện python-jose để tạo token.
    - Xử lý mã lỗi HTTP 400 khi email đã tồn tại, 401 khi sai mật khẩu.

    [Output Format]
    Code backend router FastAPI và component form React JSX.
    ```
  - *AI phản hồi:* AI đưa code endpoint và form React mẫu sử dụng `useState`.
* **Phát hiện lỗi và sửa:**
  - Lỗi trùng tài khoản do hoa/thường: AI không chuẩn hóa email, dẫn đến việc `User@gmail.com` và `user@gmail.com` bị tạo thành 2 tài khoản khác nhau. Nhóm thêm `email.strip().lower()` trước khi lưu và tìm kiếm trong database.
  - Lỗi mật khẩu yếu: AI không kiểm tra độ dài mật khẩu. Nhóm thêm regex bắt buộc mật khẩu tối thiểu 6 ký tự để đảm bảo an toàn.

---

### 📅 09/08 – 10/08/2026: Hoàn thiện Bảo vệ Tuyến đường (Protected Routes) & Kết nối Frontend - Backend
* **Việc cần làm:**
  - Xây dựng component `ProtectedRoute.jsx` trên React để chặn người dùng chưa đăng nhập truy cập các trang nội bộ.
  - Cấu hình lưu Access Token vào `localStorage` và tự động gắn vào Header `Authorization: Bearer <token>`.
  - Viết Axios Interceptor xử lý lỗi 401 khi token hết hạn.
  - Cấu hình CORS trên FastAPI cho phép Frontend gọi API.
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Tôi đang kết nối ứng dụng React với backend FastAPI thông qua thư viện Axios.

    [Instructions]
    Hướng dẫn cách cấu hình Axios interceptor trong React:
    1. Tự động đính kèm Bearer token từ localStorage vào header Authorization của mỗi request gửi đi.
    2. Bắt lỗi 401 Unauthorized toàn cục: nếu token hết hạn hoặc không hợp lệ thì tự động chuyển hướng người dùng về trang /login.
    3. Viết component ProtectedRoute để bảo vệ các tuyến đường yêu cầu đăng nhập.

    [Input Data / Constraints]
    - Sử dụng React Router v6.
    - Xử lý mượt mà khi người dùng tải lại trang mà vẫn giữ được trạng thái đăng nhập.

    [Output Format]
    File cấu hình Axios (api.js) và component ProtectedRoute.jsx.
    ```
  - *AI phản hồi:* AI cung cấp đoạn code cấu hình `axios.interceptors.response.use()`.
* **Phát hiện lỗi và sửa:**
  - Đoạn code AI dùng `window.location.href = '/login'` trực tiếp mà quên xóa token hỏng trong `localStorage`, dẫn đến tình trạng vòng lặp redirect vô hạn nếu trang login vẫn cố đọc token cũ. Nhóm sửa lại: xóa `localStorage.removeItem('token')` trước khi redirect.
  - Cấu hình lại `CORSMiddleware` ở backend chỉ cho phép origin của frontend dev (`http://localhost:5173`), không để `allow_origins=["*"]` bừa bãi.

---

### 📅 11/08 – 12/08/2026: Phân hệ Quản lý Danh mục (Categories) & Nạp dữ liệu mặc định
* **Việc cần làm:**
  - Xây dựng API CRUD Danh mục trong [categories.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/categories.py).
  - Viết script nạp sẵn 12 danh mục mặc định chuẩn (Ăn uống, Đi lại, Nhà ở, Mua sắm, Lương, Thưởng...).
  - Xây dựng chức năng Ẩn/Hiện danh mục (`is_hidden`) để bảo vệ các giao dịch lịch sử.
  - Dựng giao diện quản lý danh mục trên Frontend.
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Tôi đang làm module quản lý danh mục thu chi (Categories) trong ứng dụng FastAPI.

    [Instructions]
    Viết API CRUD cho Category gồm:
    1. Tạo, xem danh sách, cập nhật tên và biểu tượng icon.
    2. Hỗ trợ cả hai loại thu nhập (INCOME) và chi tiêu (EXPENSE).
    3. Tạo hàm nạp sẵn bộ danh mục mặc định cho tài khoản mới (Ăn uống, Đi lại, Lương, Thưởng...).
    4. Tính năng ẩn danh mục (is_hidden) thay vì xóa cứng.

    [Input Data / Constraints]
    - Mỗi danh mục thuộc sở hữu của một người dùng (user_id).
    - Không cho phép người dùng sửa hoặc xóa danh mục của người khác.

    [Output Format]
    Code router FastAPI và Pydantic schema tương ứng.
    ```
  - *AI phản hồi:* AI đưa các hàm CRUD cơ bản và hàm seed category mặc định.
* **Phát hiện lỗi và sửa:**
  - AI viết query cập nhật danh mục nhưng không kiểm tra quyền sở hữu (`user_id`), khiến User A có thể sửa nhầm danh mục của User B nếu đoán được `category_id`. Nhóm bổ sung điều kiện `filter(Category.user_id == current_user.id)` vào tất cả các câu lệnh update/delete để chặn lỗi IDOR.

---

### 📅 13/08 – 14/08/2026: Quản lý Giao dịch Thu/Chi (Transactions) & Cơ chế Thùng rác
* **Việc cần làm:**
  - Xây dựng API CRUD Giao dịch trong [transactions.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/transactions.py): phân trang, tìm kiếm, lọc theo ngày tháng, danh mục, loại thu/chi.
  - Thêm tính năng Nhân bản giao dịch (`Duplicate`) để tạo nhanh các khoản chi định kỳ.
  - Xây dựng Thùng rác (Recycle Bin): Xóa mềm (`is_deleted = True`), Khôi phục (`Restore`), Xóa vĩnh viễn (`Permanent Delete`).
  - Dựng bảng hiển thị giao dịch và modal thêm mới trên Frontend.
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Với vai trò là một Business Analyst (BA) chuyên sâu về mảng Fintech, tôi đang xây dựng phân hệ Quản lý Giao dịch Thu/Chi cho ứng dụng Personal Expense AI.

    [Instructions]
    Hãy phân tích nghiệp vụ và liệt kê chi tiết:
    1. Những yêu cầu còn thiếu trong luồng CRUD Giao dịch và Thùng rác (Recycle Bin).
    2. Các trường hợp biên (Edge cases) có thể xảy ra trong thực tế.
    3. Tiêu chí chấp nhận (Acceptance Criteria) theo chuẩn Gherkin (Given - When - Then).
    4. Các câu hỏi nghiệp vụ cần làm rõ với khách hàng / Stakeholders.

    [Input Data / Constraints]
    - Hỗ trợ 2 loại: Thu nhập (Income) và Chi tiêu (Expense).
    - Mỗi giao dịch bắt buộc có: Số tiền, Ngày giao dịch, Danh mục (Category), Hình thức thanh toán (Tiền mặt / Chuyển khoản).
    - Bất biến số dư: Số dư khả dụng = Tổng thu - Tổng chi - Tiền đã tích lũy vào mục tiêu tiết kiệm (Số dư này tuyệt đối không được âm).
    - Thùng rác hỗ trợ: Chuyển vào thùng rác (Soft-delete), Khôi phục (Restore), Xóa vĩnh viễn (Permanent delete).

    [Output Format]
    Trình bày Markdown rõ ràng, có tiêu đề và bảng biểu trực quan.
    ```
  - *AI phản hồi:*
    - Yêu cầu còn thiếu: Bổ sung tính năng nhân bản giao dịch (Duplicate) để tạo nhanh chi phí định kỳ và nhập sao kê hàng loạt từ Excel.
    - Trường hợp biên quan trọng:
      * Người dùng xóa khoản Thu nhập 10 triệu, nhưng trước đó đã tiêu hết 8 triệu và gửi tiết kiệm 2 triệu $\rightarrow$ Xóa xong ví sẽ bị âm tiền.
      * Người dùng khôi phục giao dịch từ thùng rác nhưng danh mục cũ đã bị xóa vĩnh viễn trước đó.
    - Acceptance Criteria (Gherkin):
      * Given: Ví có số dư khả dụng là 1.000.000 đ và có 1 khoản thu nhập 5.000.000 đ.
      * When: Người dùng bấm xóa khoản thu nhập 5.000.000 đ.
      * Then: Hệ thống chặn lại, trả về mã lỗi `400 Bad Request` kèm thông báo: "Không thể xóa nguồn thu vì thao tác này sẽ làm số dư khả dụng bị âm."
* **Phát hiện lỗi và sửa:**
  - Lỗi AI bỏ sót: AI không xử lý trường hợp khi người dùng khôi phục một giao dịch từ thùng rác, nhưng Danh mục (`Category`) của giao dịch đó trước đó đã bị người dùng xóa vĩnh viễn $\rightarrow$ gọi API khôi phục sẽ bị văng lỗi Foreign Key Exception ở database.
  - Nhóm tự sửa: Trong hàm khôi phục, nhóm viết thêm kiểm tra: nếu danh mục cũ không còn tồn tại hoặc đang bị xóa, tự động gán giao dịch đó về danh mục mặc định "Khác" và gửi thông báo cho người dùng trên giao diện.

---

### 📅 15/08 – 16/08/2026: Phân hệ Ngân sách (Budgets) & Cảnh báo chi tiêu vượt ngưỡng
* **Việc cần làm:**
  - Xây dựng API Quản lý Ngân sách trong [budgets.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/budgets.py): Cho phép đặt hạn mức chi tiêu theo từng danh mục trong tháng (ví dụ: Ăn uống tháng 8 là 3 triệu).
  - Tính toán tiến độ chi tiêu thực tế, thanh đo phần trăm chi tiêu đổi màu cảnh báo (xanh $\rightarrow$ vàng $\rightarrow$ đỏ khi vượt quá 100%).
  - Cập nhật trang quản lý thông tin cá nhân Profile ([profile.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/profile.py)).
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Với vai trò là Business Analyst & Product Owner, tôi đang thiết kế phân hệ Ngân sách chi tiêu tháng (Budgets) và Mục tiêu tích lũy tài chính (Saving Goals).

    [Instructions]
    Hãy phân tích nghiệp vụ và liệt kê:
    1. Những yêu cầu còn thiếu về luồng tiền giữa Ngân sách, Mục tiêu tiết kiệm và Giao dịch hàng ngày.
    2. Các Edge cases liên quan đến nạp tiền, rút tiền và phân bổ thu nhập.
    3. Acceptance criteria cho tính năng cảnh báo bội chi và nạp tiền tiết kiệm.
    4. Câu hỏi cần hỏi khách hàng về quy tắc hoàn tiền khi hủy mục tiêu tiết kiệm.

    [Input Data / Constraints]
    - Ngân sách: Hạn mức theo từng danh mục trong 1 tháng (VD: Ăn uống tháng 09/2026 là 5.000.000 đ).
    - Tiết kiệm: Cho phép nạp tiền thủ công (MANUAL) hoặc tự động trích tiền khi tạo giao dịch thu nhập (INCOME_ALLOCATION). Cho phép rút một phần hoặc toàn bộ.

    [Output Format]
    Trình bày Markdown trực quan, ngắn gọn, đi thẳng vào các trường hợp thực tế.
    ```
  - *AI phản hồi:*
    - Yêu cầu còn thiếu: Phân biệt rõ giữa Hủy mục tiêu (`CANCELLED` - hoàn tiền về ví) và Hoàn thành mục tiêu (`COMPLETED` - đã đạt mục tiêu mua sắm).
    - Edge cases: Người dùng đặt 2 mức ngân sách trùng nhau cho cùng 1 danh mục trong cùng 1 tháng; hoặc người dùng rút số tiền tiết kiệm vượt quá số dư đang có trong quỹ tích lũy.
* **Phát hiện lỗi và sửa:**
  - Lỗi query: Đoạn code AI sinh ra không lọc điều kiện `is_deleted == False`, dẫn đến việc các giao dịch đã nằm trong Thùng rác vẫn bị tính dồn vào tổng chi tiêu ngân sách, làm sai lệch cảnh báo bội chi. Nhóm bổ sung `Transaction.is_deleted.is_(False)` vào query.
  - Lỗi dữ liệu trùng: Bổ sung thêm ràng buộc `UniqueConstraint("user_id", "category_id", "month", "year")` trong database để ngăn việc người dùng vô tình tạo 2 bản ghi ngân sách cho cùng một danh mục trong cùng một tháng.

---

### 📅 17/08 – 18/08/2026: Mục tiêu tiết kiệm, Rút tiền & Khóa dòng chống âm ví (Pessimistic Lock)
* **Việc cần làm:**
  - Xây dựng phân hệ Quỹ tiết kiệm ([saving_goals.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/saving_goals.py)): Tạo mục tiêu, nạp tiền thủ công (`MANUAL`) hoặc trích tự động khi tạo giao dịch thu nhập (`INCOME_ALLOCATION`).
  - Hỗ trợ rút tiền tiết kiệm một phần hoặc toàn bộ, hoàn tiền lại vào số dư khả dụng và ghi log lịch sử rút.
  - Viết cơ chế khóa dòng người dùng `SELECT ... FOR UPDATE` trong SQLAlchemy để xử lý xung đột đồng thời (Race-condition).
  - Thêm cơ chế `idempotency_key` chống trừ tiền hoặc nạp tiền 2 lần khi client retry mạng.
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Bạn là một Senior Backend Developer chuyên về FastAPI, SQLAlchemy và MySQL 8.0 (InnoDB).

    [Instructions]
    Viết hàm xóa giao dịch thu nhập (chuyển vào thùng rác) đảm bảo an toàn tuyệt đối:
    - Khóa dòng dữ liệu người dùng để chống lỗi Race-condition (nhiều request xóa/rút tiền cùng lúc).
    - Đảm bảo số dư khả dụng (Available Balance) không bao giờ bị âm.

    [Input Data / Constraints]
    - Dữ liệu: User, Transaction, SavingGoal, SavingContribution.
    - Sử dụng khóa hàng: SELECT ... FOR UPDATE.
    - Mã lỗi trả về khi không đủ số dư: HTTP 400 Bad Request.

    [Output Format]
    Code Python chuẩn PEP 8 có type hints và xử lý ngoại lệ rõ ràng.
    ```
  - *Code ban đầu do AI sinh ra:*
    ```python
    def trash_transaction(transaction_id: int, db: Session, current_user: User):
        db.query(User).filter(User.id == current_user.id).with_for_update().first()
        txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        
        avail_balance = get_user_available_balance(db, current_user.id)
        if txn.type == "income" and avail_balance - txn.amount < 0:
            raise HTTPException(status_code=400, detail="Không đủ số dư để xóa giao dịch này")
        
        txn.is_deleted = True
        db.commit()
    ```
* **Phát hiện lỗi và sửa:**
  - Lỗi logic của AI: Khi xóa một khoản thu nhập đã trích tiền vào quỹ tiết kiệm, số tiền đã trích đó sẽ phải được giải phóng ngược lại (`released_savings`) vì nguồn thu không còn nữa. AI chỉ lấy số dư hiện tại trừ đi `txn.amount`, khiến người dùng bị báo lỗi oan không xóa được dù thực tế số dư sau khi hoàn tiền tiết kiệm vẫn đủ. Ngoài ra AI không khóa đúng phạm vi hàng dữ liệu, gây nguy cơ race-condition khi bấm xóa liên tục.
  - Nhóm tự sửa: Tự viết hàm `_ensure_projected_balance()` trong [transactions.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/transactions.py) có tính toán chuẩn xác phần tiền tiết kiệm giải phóng:
    ```python
    released_savings = sum(
        (Decimal(str(goal.current_amount)) - projected_goal_amounts[goal.id]
         for goal in linked_goals if goal.status != GoalStatus.CANCELLED),
        Decimal("0")
    )
    _ensure_projected_balance(
        db,
        current_user.id,
        -_balance_effect(txn.type, Decimal(str(txn.amount))) + released_savings,
        "Không thể xóa nguồn thu vì thao tác này sẽ làm số dư khả dụng bị âm."
    )
    ```
  - Thêm mã khóa `(saving_goal_id, idempotency_key)` khi rút tiền để client gửi lại request trùng lặp không bị trừ tiền lần hai.

---

### 📅 19/08/2026: Đọc sao kê ngân hàng Excel, Sửa Parser MB Bank & Kiểm thử tổng thể
* **Việc cần làm:**
  - Viết module đọc file sao kê Excel ngân hàng ([excel_service.py](file:///d:/clone/personal-expense-ai/backend/app/services/excel_service.py)) và parser riêng cho sao kê MB Bank ([mb_parser.py](file:///d:/clone/personal-expense-ai/backend/app/services/mb_parser.py)).
  - Cho phép tải file `.xlsx`, xem trước bảng dữ liệu (Preview) và chọn danh mục trước khi nạp vào hệ thống.
  - Chạy toàn bộ test suite kiểm thử đơn vị và tích hợp (162 tests backend, 57 tests frontend).
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Tôi đang xây dựng parser đọc file sao kê tài khoản ngân hàng Excel (MB Bank, Vietcombank) trong ứng dụng quản lý chi tiêu bằng Python.

    [Instructions]
    Viết hàm trích xuất số tiền và dấu biến động (+ hoặc -) từ cột diễn giải giao dịch bằng biểu thức chính quy (Regex).

    [Input Data / Constraints]
    - Chuỗi mẫu: "GD: +1,500,000VND ngay 15/08" hoặc "-250,000 VND tai Highlands Coffee".
    - Định dạng số tiền Việt Nam có dấu phẩy ngăn cách hàng nghìn.
    - Chuyển đổi an toàn sang kiểu số học, không làm crash nếu gặp dòng trống.

    [Output Format]
    Hàm Python hoàn chỉnh kèm regex pattern.
    ```
  - *AI phản hồi:* AI đưa regex: `r"([+-]?\d+)\s*(?:VND|d)?"`
* **Phát hiện lỗi và sửa:**
  - Lỗi Regex: Dữ liệu thực tế từ file Excel ngân hàng Việt Nam luôn có dấu phẩy `,` phân cách hàng nghìn (ví dụ `1,500,000`). Regex của AI gặp dấu phẩy thì dừng lại ngay, chỉ bắt được mỗi số `1` (thay vì 1.5 triệu thì thành 1 đồng).
  - Nhóm tự sửa: Viết lại pattern: `r"([+-]?[\d,]+)\s*(?:VND|đ|d)?"`, sau đó dùng `.replace(",", "")` rồi mới ép sang kiểu `Decimal`. Bổ sung xử lý dòng trống và định dạng ngày sai lệch để không làm crash cả tiến trình import.

---

### 📅 20/08 – 24/08/2026: Tích hợp AI OCR Quét Hóa Đơn Bằng Google Gemini Vision
* **Việc cần làm:**
  - Xây dựng module nhận diện biên lai hóa đơn qua Gemini 1.5 Flash Vision, tự động trích xuất số tiền, ngày giao dịch, người bán và danh mục gợi ý.
  - Xây dựng modal xem trước kết quả trên giao diện [TransactionFormModal.jsx](file:///d:/clone/personal-expense-ai/frontend/src/components/TransactionFormModal.jsx) để người dùng rà soát trước khi lưu.
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Bạn là một AI Engineer phát triển module OCR nhận diện hóa đơn cho ứng dụng quản lý chi tiêu cá nhân bằng Google Gemini 1.5 Flash Vision.

    [Instructions]
    Thiết kế System Prompt và hàm Python để phân tích hình ảnh hóa đơn/biên lai chuyển tiền:
    - Tự động trích xuất: Tổng số tiền (amount), Ngày giao dịch (transaction_date), Tên người bán/mô tả (description), và Gợi ý danh mục phù hợp nhất (category).

    [Input Data / Constraints]
    - Danh mục hệ thống gồm: "Ăn uống", "Đi lại", "Mua sắm", "Nhà ở", "Sức khỏe", "Giáo dục", "Giải trí", "Khác".
    - Định dạng ngày: YYYY-MM-DD.
    - Số tiền: Số nguyên dương (VND).
    - Nếu ảnh mờ hoặc không phải hóa đơn, trả về lỗi rõ ràng, không được bịa số liệu.

    [Examples]
    Input: Ảnh hóa đơn Highlands Coffee ngày 12/09/2026 tổng 85.000 đ.
    Output: {"amount": 85000, "transaction_date": "2026-09-12", "description": "Highlands Coffee", "suggested_category": "Ăn uống"}

    [Output Format]
    Mô hình AI bắt buộc trả về định dạng JSON thuần túy (không kèm text markdown thừa).
    ```
  - *AI phản hồi:* AI cung cấp prompt trích xuất JSON và hàm xử lý `extract_receipt_data()` gọi Gemini Vision API.
* **Phát hiện lỗi và sửa:**
  - Lỗi định dạng JSON: Khi ảnh mờ hoặc chụp lệch góc, AI thỉnh thoảng trả về text giải thích kèm theo khối markdown thay vì JSON thuần. Nhóm thêm tầng Regex bóc tách chuỗi JSON thuần và fallback an toàn nếu không thể parse.
  - Tối ưu giao diện: Thêm modal xem trước dữ liệu trích xuất để người dùng chủ động kiểm tra và chỉnh sửa số tiền, ngày tháng trước khi lưu vào CSDL.

---

### 📅 25/08 – 30/08/2026: Xây Dựng Trợ Lý Ảo FinAI Mascot & Chatbot Tư Vấn Tài Chính
* **Việc cần làm:**
  - Thiết kế nhân vật Mascot trợ lý ảo tài chính FinAI hình đồng xu (`CoinAssistant.jsx`) có hiệu ứng chuyển động nổi trên màn hình.
  - Tích hợp cửa sổ Chatbot tương tác trực tiếp với Google Gemini AI để giải đáp thắc mắc chi tiêu và đưa ra lời khuyên tài chính.
  - Cung cấp các nút gợi ý câu hỏi nhanh (Quick Prompt Chips) như: "Tháng này tôi tiêu nhiều nhất vào đâu?", "Tôi có thể tiết kiệm thêm tiền thế nào?".
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Bạn là một Frontend & UI/UX Specialist làm việc với React 19 và Vanilla CSS.

    [Instructions]
    Tạo component Trợ lý ảo FinAI Mascot hình đồng xu 3D nổi bật:
    - Chuyển động lơ lửng bằng CSS Keyframes 100% GPU Hardware Accelerated.
    - Nhấn vào nhân vật sẽ mở cửa sổ Chatbot Intercom-style kết nối với Gemini AI.
    - Có hàng nút bấm gợi ý câu hỏi nhanh (Quick Prompt Chips) như: "Tháng này tôi tiêu nhiều nhất vào đâu?", "Tôi có thể tiết kiệm thêm tiền thế nào?".

    [Constraints]
    - Responsive hoàn hảo trên cả máy tính, tablet và mobile.
    - Khi mở bàn phím ảo trên điện thoại (Mobile Keyboard), cửa sổ chat không bị tràn màn hình (sử dụng 100dvh).

    [Output Format]
    Component React JSX và file CSS module hóa tương ứng.
    ```
  - *AI phản hồi:* AI sinh ra các component `CoinAssistant.jsx`, `ChatPopup.jsx` và các keyframe `@keyframes float`.
* **Phát hiện lỗi và sửa:**
  - Lỗi giao diện trên di động: Cửa sổ chat bị tràn màn hình khi bàn phím ảo hiển thị trên mobile. Nhóm sửa lại chiều cao sử dụng đơn vị `100dvh` và cố định vùng hiển thị tin nhắn có thanh cuộn riêng biệt.
  - Tối ưu trải nghiệm: Bổ sung nút thu nhỏ/ẩn Mascot khi người dùng cần không gian thao tác trên bảng số liệu, và cấu hình bong bóng thoại tự động ẩn sau 6 giây để không gây rối mắt.

---

### 📅 31/08 – 03/09/2026: Tách Nhỏ CSS, Nạp Dữ Liệu Mẫu & Hoàn Thiện Kiểm Thử
* **Việc cần làm:**
  - Bóc tách file `index.css` lớn thành 28 file CSS nhỏ độc lập theo từng component/page, giữ nguyên giao diện và hiệu năng.
  - Xây dựng script Python `seed_demo.py` khởi tạo tài khoản demo `demo@example.com` với 74 giao dịch trải dài 6 tháng phục vụ chạy thử và nghiệm thu.
  - Chạy toàn bộ hệ thống kiểm thử tự động (Unit & Integration Tests) trên cả Frontend và Backend.
* **Minh chứng sử dụng AI:**
  - *Prompt:*
    ```text
    [Context]
    Tôi đang hoàn thiện dự án Personal Expense AI và cần tạo dữ liệu mẫu thực tế để phục vụ kiểm thử và trình diễn sản phẩm.

    [Instructions]
    Viết script Python seed_demo.py khởi tạo tài khoản demo demo@example.com với 74 giao dịch trải dài 6 tháng gần nhất:
    - Gán danh mục thu chi thực tế, tạo các mức ngân sách tháng và mục tiêu tiết kiệm.
    - Chạy được ổn định trên cả hệ điều hành Windows và Linux.

    [Input Data / Constraints]
    - Xử lý lỗi hiển thị tiếng Việt UTF-8 trên terminal Windows.
    - Đảm bảo tính toán số dư ví logic: các khoản thu lương/thưởng xuất hiện trước các khoản chi để số dư khả dụng không bị âm.
    - Mật khẩu tài khoản demo được mã hóa bằng bcrypt tương thích với hệ thống hiện tại.

    [Output Format]
    File script Python chạy độc lập.
    ```
  - *AI phản hồi:* AI cung cấp script nạp dữ liệu mẫu với các giao dịch ngẫu nhiên.
* **Phát hiện lỗi và sửa:**
  - Lỗi encoding UTF-8: Khi chạy trên Windows console, các ký tự tiếng Việt có dấu trong danh mục và mô tả giao dịch bị lỗi `UnicodeEncodeError`. Nhóm cấu hình lại stdout stream sang UTF-8.
  - Lỗi logic số dư: Dữ liệu giao dịch ngẫu nhiên của AI tạo ra tình huống tổng chi lớn hơn tổng thu ở một số tháng đầu, làm vi phạm bất biến số dư ví. Nhóm tinh chỉnh lại thuật toán seed để đảm bảo các khoản thu lương/thưởng luôn xuất hiện trước và số dư khả dụng luôn dương.

---

## 🎯 TỔNG KẾT BÀI HỌC KINH NGHIỆM KHI SỬ DỤNG AI

1. **Không copy nguyên văn code AI ở các phần xử lý tiền bạc:** AI thường mắc lỗi tính toán làm tròn (dùng `float` thay vì `Decimal`), quên các khoản trích lũy phụ và không để ý đến các trường hợp race condition khi có nhiều request đồng thời.
2. **AI rất mạnh ở khâu gợi ý trường hợp biên (Edge Cases):** Khi được đóng vai Business Analyst, AI liệt kê được nhiều góc nhìn thực tế (như người dùng xóa thu nhập khi đã tiêu hết tiền, hoặc nhập sao kê trùng lặp), giúp nhóm lường trước các kịch bản để tự viết code kiểm tra chặt chẽ hơn.
3. **Phải luôn kiểm thử lại regex và dữ liệu thực tế:** Các đoạn code regex hoặc xử lý chuỗi do AI tạo ra thường dựa trên dữ liệu mẫu lý tưởng của phương Tây, khi gặp định dạng thực tế ở Việt Nam (dấu phẩy phân cách tiền tệ, định dạng ngày DD/MM/YYYY) thì rất dễ bị lỗi nếu không test kỹ.
