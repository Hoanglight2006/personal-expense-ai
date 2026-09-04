# Nhật Ký Phát Triển & Minh Chứng Sử Dụng AI

Tài liệu ghi lại chi tiết các mốc phát triển dự án **Personal Expense AI**, các công việc thực tế theo ngày tháng, nội dung prompt khi dùng AI hỗ trợ, những lỗi phát hiện từ phản hồi của AI và cách nhóm đã tự kiểm tra, sửa lại code.

---

### 📅 03/08 – 04/08/2026: Khởi tạo dự án & Khảo sát thiết kế hệ thống
* **Việc cần làm:**
  - Khởi tạo Git repository, dựng khung dự án Backend (FastAPI, SQLAlchemy) và Frontend (React, Vite).
  - Setup môi trường ảo Python `.venv`, cài đặt các thư viện cần thiết (`fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`).
  - Phân tích luồng nghiệp vụ quản lý chi tiêu cá nhân, phác thảo sơ đồ thực thể ERD ban đầu.
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Gợi ý cấu trúc thư mục chuẩn cho dự án web app quản lý chi tiêu cá nhân gồm backend FastAPI và frontend React, tách riêng routes, services, models và schemas."
  - *Kết quả AI:* AI gợi ý cấu trúc thư mục theo mô hình phân tầng (Layered Architecture). Nhóm lấy khung đó để dựng các thư mục `backend/app/api`, `backend/app/models`, `backend/app/services` và `frontend/src/components`.
* **Phát hiện lỗi và sửa:**
  - AI đưa file cấu hình `requirements.txt` không ghim phiên bản cụ thể, để `pydantic` tự do gây nguy cơ xung đột giữa Pydantic v1 và v2 với FastAPI mới. Nhóm kiểm tra và ghim rõ các phiên bản tương thích ổn định (`pydantic>=2.7.0`, `sqlalchemy>=2.0.0`).

---

### 📅 05/08 – 06/08/2026: Thiết kế CSDL (ERD) & Cài đặt Module Mã Hóa
* **Việc cần làm:**
  - Hoàn thiện sơ đồ quan hệ thực thể (ERD) gồm các bảng: `users`, `categories`, `transactions`, `budgets`, `saving_goals`, `saving_contributions`, `saving_withdrawals`.
  - Viết các model SQLAlchemy ban đầu trong thư mục `backend/app/models/`.
  - Viết module mã hóa mật khẩu bằng `bcrypt` và sinh token JWT trong `backend/app/core/security.py`.
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Thiết kế schema cơ sở dữ liệu MySQL 8.0 cho app quản lý chi tiêu cá nhân gồm bảng User, Category, Transaction, Budget và SavingGoal. Viết bằng SQLAlchemy model và cấu hình hash mật khẩu bằng passlib bcrypt."
  - *AI phản hồi:* AI sinh ra các class model và hàm hash mật khẩu. Nhưng AI để kiểu số tiền là `Float`, quan hệ bảng Category là `ondelete="CASCADE"`, và hardcode `SECRET_KEY = "supersecret"` ngay trong file code.
* **Phát hiện lỗi và sửa:**
  - **Lỗi sai số tiền:** Đổi toàn bộ các cột tiền tệ từ `Float` sang `Numeric(15, 2)` để tránh sai số dấu phẩy động trong tính toán tài chính.
  - **Lỗi mất dữ liệu:** Đổi `CASCADE` ở bảng Category sang `RESTRICT` và thêm cột `is_hidden` (Boolean) để khi ẩn danh mục không bị xóa mất lịch sử giao dịch.
  - **Lỗi bảo mật:** Tách `SECRET_KEY`, `ALGORITHM` ra file cấu hình `.env` và quản lý tập trung qua file `config.py`.

---

### 📅 07/08 – 08/08/2026: Xây dựng API Xác thực (Auth) & Dựng giao diện Login/Register
* **Việc cần làm:**
  - Viết các API: Đăng ký tài khoản (`/register`), Đăng nhập nhận JWT token (`/login`), Đổi mật khẩu trong [auth.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/auth.py).
  - Viết dependency `get_current_user` kiểm tra token hợp lệ trên mỗi request gọi lên server.
  - Dựng trang Đăng nhập (`Login.jsx`) và Đăng ký (`Register.jsx`) trên React Frontend.
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Viết endpoint /register và /login bằng FastAPI. Yêu cầu validate email hợp lệ, kiểm tra trùng lặp email trong DB, trả về access token có hạn sử dụng 7 ngày. Viết kèm form React đơn giản xử lý submit."
  - *AI phản hồi:* AI đưa code endpoint và form React mẫu sử dụng `useState`.
* **Phát hiện lỗi và sửa:**
  - **Lỗi trùng tài khoản do hoa/thường:** AI không chuẩn hóa email, dẫn đến việc `User@gmail.com` và `user@gmail.com` bị tạo thành 2 tài khoản khác nhau. Nhóm thêm `email.strip().lower()` trước khi lưu và tìm kiếm trong database.
  - **Lỗi mật khẩu yếu:** AI không kiểm tra độ dài mật khẩu. Nhóm thêm regex bắt buộc mật khẩu tối thiểu 6 ký tự để đảm bảo an toàn.

---

### 📅 09/08 – 10/08/2026: Hoàn thiện Bảo vệ Tuyến đường (Protected Routes) & Kết nối Frontend - Backend
* **Việc cần làm:**
  - Xây dựng component `ProtectedRoute.jsx` trên React để chặn người dùng chưa đăng nhập truy cập các trang nội bộ.
  - Cấu hình lưu Access Token vào `localStorage` và tự động gắn vào Header `Authorization: Bearer <token>`.
  - Viết Axios Interceptor xử lý lỗi 401 khi token hết hạn.
  - Cấu hình CORS trên FastAPI cho phép Frontend gọi API.
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Cách cấu hình Axios interceptor trong React để tự động đính kèm Bearer token vào mỗi request, và nếu API trả về lỗi 401 Unauthorized thì tự động chuyển hướng người dùng về trang /login?"
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
  - *Prompt:* "Thiết kế API quản lý Category trong FastAPI gồm cả 2 loại INCOME và EXPENSE. Có tính năng nạp danh mục mặc định cho user mới và tính năng ẩn danh mục thay vì xóa cứng."
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
  - *Prompt:* "Tôi đang làm tính năng Thùng rác (Recycle Bin) cho phần quản lý giao dịch thu/chi cá nhân (gồm xóa mềm is_deleted, khôi phục và xóa vĩnh viễn). Hãy liệt kê những trường hợp biên (edge cases) có thể xảy ra trong thực tế làm sai lệch số dư ví và sinh code mẫu cho API restore transaction."
  - *AI phản hồi:* AI chỉ ra trường hợp biên: Nếu xóa một khoản thu nhập 5 triệu trong khi người dùng đã tiêu hết tiền thì số dư ví sẽ bị âm. AI viết code khôi phục bằng cách gán lại `txn.is_deleted = False`.
* **Phát hiện lỗi và sửa:**
  - **Lỗi AI bỏ sót:** AI không xử lý trường hợp khi người dùng khôi phục một giao dịch từ thùng rác, nhưng Danh mục (`Category`) của giao dịch đó trước đó đã bị người dùng xóa vĩnh viễn $\rightarrow$ gọi API khôi phục sẽ bị văng lỗi Foreign Key Exception ở database.
  - **Nhóm tự sửa:** Trong hàm khôi phục, nhóm viết thêm kiểm tra: nếu danh mục cũ không còn tồn tại hoặc đang bị xóa, tự động gán giao dịch đó về danh mục mặc định "Khác" và gửi thông báo cho người dùng trên giao diện.

---

### 📅 15/08 – 16/08/2026: Phân hệ Ngân sách (Budgets) & Cảnh báo chi tiêu vượt ngưỡng
* **Việc cần làm:**
  - Xây dựng API Quản lý Ngân sách trong [budgets.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/budgets.py): Cho phép đặt hạn mức chi tiêu theo từng danh mục trong tháng (ví dụ: Ăn uống tháng 8 là 3 triệu).
  - Tính toán tiến độ chi tiêu thực tế, thanh đo phần trăm chi tiêu đổi màu cảnh báo (xanh $\rightarrow$ vàng $\rightarrow$ đỏ khi vượt quá 100%).
  - Cập nhật trang quản lý thông tin cá nhân Profile ([profile.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/profile.py)).
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Viết câu truy vấn SQLAlchemy tính tổng số tiền đã chi tiêu (type='expense') của một danh mục trong tháng và năm hiện tại của user, so sánh với hạn mức budget đã đặt để trả về tỷ lệ phần trăm đã dùng."
  - *AI phản hồi:* AI đưa câu query dùng `func.sum(Transaction.amount)` nhóm theo `category_id`.
* **Phát hiện lỗi và sửa:**
  - **Lỗi query:** Đoạn code AI sinh ra không lọc điều kiện `is_deleted == False`, dẫn đến việc các giao dịch đã nằm trong Thùng rác vẫn bị tính dồn vào tổng chi tiêu ngân sách, làm sai lệch cảnh báo bội chi. Nhóm bổ sung `Transaction.is_deleted.is_(False)` vào query.
  - **Lỗi dữ liệu trùng:** Bổ sung thêm ràng buộc `UniqueConstraint("user_id", "category_id", "month", "year")` trong database để ngăn việc người dùng vô tình tạo 2 bản ghi ngân sách cho cùng một danh mục trong cùng một tháng.

---

### 📅 17/08 – 18/08/2026: Mục tiêu tiết kiệm, Rút tiền & Khóa dòng chống âm ví (Pessimistic Lock)
* **Việc cần làm:**
  - Xây dựng phân hệ Quỹ tiết kiệm ([saving_goals.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/saving_goals.py)): Tạo mục tiêu, nạp tiền thủ công (`MANUAL`) hoặc trích tự động khi tạo giao dịch thu nhập (`INCOME_ALLOCATION`).
  - Hỗ trợ rút tiền tiết kiệm một phần hoặc toàn bộ, hoàn tiền lại vào số dư khả dụng và ghi log lịch sử rút.
  - Viết cơ chế khóa dòng người dùng `SELECT ... FOR UPDATE` trong SQLAlchemy để xử lý xung đột đồng thời (Race-condition).
  - Thêm cơ chế `idempotency_key` chống trừ tiền hoặc nạp tiền 2 lần khi client retry mạng.
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Viết hàm xóa giao dịch thu nhập (chuyển vào thùng rác). Cần lưu ý khoản thu này trước đó có thể đã được trích một phần tiền vào Mục tiêu tiết kiệm (SavingGoal). Hãy kiểm tra nếu xóa mà làm số dư khả dụng (available_balance) bị âm thì phải chặn lại và báo lỗi 400."
  - *AI phản hồi:* AI sinh đoạn code:
    ```python
    avail_balance = get_user_available_balance(db, current_user.id)
    if txn.type == "income" and (avail_balance - txn.amount) < 0:
        raise HTTPException(status_code=400, detail="Không đủ số dư để xóa giao dịch này")
    txn.is_deleted = True
    db.commit()
    ```
* **Phát hiện lỗi và sửa:**
  - **Lỗi logic nghiêm trọng của AI:** Khi xóa một khoản thu nhập đã trích tiền vào quỹ tiết kiệm, số tiền đã trích đó sẽ phải được giải phóng ngược lại (`released_savings`) vì nguồn thu không còn nữa. AI chỉ lấy số dư hiện tại trừ đi `txn.amount`, khiến người dùng bị báo lỗi oan không xóa được dù thực tế số dư sau khi hoàn tiền tiết kiệm vẫn đủ. Ngoài ra AI không dùng khóa dòng nên nếu bấm xóa 2 lần cùng lúc sẽ bị race condition.
  - **Nhóm tự code lại hoàn chỉnh:** Tự viết hàm `_ensure_projected_balance()` trong [transactions.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/transactions.py) có tính toán chuẩn xác phần tiền tiết kiệm giải phóng:
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
  - *Prompt:* "Viết biểu thức chính quy (Regex) trong Python để trích xuất số tiền và dấu biến động (+ hoặc -) từ cột diễn giải sao kê ngân hàng có dạng: 'GD: +1,500,000VND ngay 15/08' hoặc '-250,000 VND tai Highlands Coffee'."
  - *AI phản hồi:* AI đưa regex: `r"([+-]?\d+)\s*(?:VND|d)?"`
* **Phát hiện lỗi và sửa:**
  - **Lỗi Regex:** Dữ liệu thực tế từ file Excel ngân hàng Việt Nam luôn có dấu phẩy `,` phân cách hàng nghìn (ví dụ `1,500,000`). Regex của AI gặp dấu phẩy thì dừng lại ngay, chỉ bắt được mỗi số `1` (thay vì 1.5 triệu thì thành 1 đồng!).
  - **Nhóm tự sửa:** Viết lại pattern: `r"([+-]?[\d,]+)\s*(?:VND|đ|d)?"`, sau đó dùng `.replace(",", "")` rồi mới ép sang kiểu `Decimal`. Bổ sung xử lý dòng trống và định dạng ngày sai lệch để không làm crash cả tiến trình import.

---

## 🎯 TỔNG KẾT BÀI HỌC KINH NGHIỆM KHI SỬ DỤNG AI

1. **Không copy nguyên văn code AI ở các phần xử lý tiền bạc:** AI thường mắc lỗi tính toán làm tròn (dùng `float` thay vì `Decimal`), quên các khoản trích lũy phụ và không để ý đến các trường hợp race condition khi có nhiều request đồng thời.
2. **AI rất mạnh ở khâu gợi ý trường hợp biên (Edge Cases):** Khi được đóng vai Business Analyst, AI liệt kê được nhiều góc nhìn thực tế (như người dùng xóa thu nhập khi đã tiêu hết tiền, hoặc nhập sao kê trùng lặp), giúp nhóm lường trước các kịch bản để tự viết code kiểm tra chặt chẽ hơn.
3. **Phải luôn kiểm thử lại regex và dữ liệu thực tế:** Các đoạn code regex hoặc xử lý chuỗi do AI tạo ra thường dựa trên dữ liệu mẫu lý tưởng của phương Tây, khi gặp định dạng thực tế ở Việt Nam (dấu phẩy phân cách tiền tệ, định dạng ngày DD/MM/YYYY) thì rất dễ bị lỗi nếu không test kỹ.
