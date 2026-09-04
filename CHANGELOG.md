# Nhật Ký Phát Triển & Minh Chứng Sử Dụng AI

Tài liệu ghi lại chi tiết các mốc phát triển dự án **Personal Expense AI**, các công việc thực tế theo ngày tháng commit, nội dung prompt khi dùng AI hỗ trợ, những lỗi phát hiện từ phản hồi của AI và cách nhóm đã tự kiểm tra, sửa lại code.

---

### 📅 03/08/2026: Khởi tạo dự án và dựng khung hệ thống
* **Việc cần làm:**
  - Khởi tạo Git repository, tạo cấu trúc thư mục cho Backend (FastAPI, SQLAlchemy) và Frontend (React, Vite).
  - Cấu hình file `.gitignore`, môi trường ảo Python `.venv` và cài đặt các thư viện cơ bản.
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Gợi ý cấu trúc thư mục chuẩn cho dự án web app quản lý chi tiêu cá nhân gồm backend FastAPI và frontend React, tách riêng routes, services, models và schemas."
  - *Kết quả AI & Thực tế áp dụng:* AI gợi ý cây thư mục khá chuẩn. Nhóm lấy khung đó để dựng các thư mục `backend/app/api`, `backend/app/models`, `backend/app/services` và `frontend/src/components`.

---

### 📅 07/08/2026: Thiết kế cơ sở dữ liệu (ERD) và viết đặc tả yêu cầu
* **Việc cần làm:**
  - Viết tài liệu yêu cầu hệ thống [REQUIREMENTS.md](file:///d:/clone/personal-expense-ai/REQUIREMENTS.md).
  - Thiết kế sơ đồ quan hệ thực thể (ERD) gồm các bảng: `users`, `categories`, `transactions`, `budgets`, `saving_goals`, `saving_contributions`, `saving_withdrawals`.
  - Viết model SQLAlchemy ban đầu trong thư mục `backend/app/models/`.
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Thiết kế schema cơ sở dữ liệu MySQL 8.0 cho app quản lý chi tiêu cá nhân. Cần có bảng User, Category, Transaction (thu/chi), Budget (ngân sách tháng theo danh mục) và SavingGoal (tiết kiệm). Viết bằng mã SQLAlchemy model."
  - *AI phản hồi:* AI sinh ra các class model cơ bản nhưng đặt kiểu dữ liệu số tiền là `Float`, và ở bảng `Transaction` thiết lập khóa ngoại liên kết với `Category` là `ondelete="CASCADE"`.
* **Phát hiện lỗi & Tự sửa lại:**
  - **Lỗi 1 (Sai số tiền tệ):** Kiểu `Float` trong lập trình bị lỗi sai số dấu phẩy động (ví dụ `0.1 + 0.2 != 0.3`). Nhóm đổi toàn bộ các cột tiền tệ sang `Numeric(15, 2)` để tính toán chuẩn xác đến từng đồng.
  - **Lỗi 2 (Nguy cơ mất dữ liệu):** Để `CASCADE` ở danh mục rất nguy hiểm, người dùng lỡ tay xóa một danh mục là toàn bộ lịch sử chi tiêu thuộc danh mục đó bị xóa sạch theo. Nhóm đổi sang `ondelete="RESTRICT"` và thêm cột `is_hidden` (Boolean) vào bảng `Category` để khi người dùng không muốn dùng danh mục đó nữa thì chỉ ẩn đi, dữ liệu giao dịch cũ vẫn được giữ nguyên.

---

### 📅 11/08/2026: Module Xác thực tài khoản (Auth) & Phân quyền JWT
* **Việc cần làm:**
  - Viết các API đăng ký (`/register`), đăng nhập (`/login`) và đổi mật khẩu trong [auth.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/auth.py).
  - Sử dụng `passlib` với thuật toán `bcrypt` để băm mật khẩu. Sinh mã JWT token khi đăng nhập thành công.
  - Viết middleware `get_current_user` để bảo vệ các router nội bộ.
  - Xây dựng component `ProtectedRoute.jsx` trên React để chặn người dùng chưa đăng nhập.
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Viết hàm đăng ký và đăng nhập bằng FastAPI sử dụng JWT token thuật toán HS256 và băm mật khẩu bằng Bcrypt. Viết thêm hàm dependency get_current_user để lấy user từ header Authorization: Bearer <token>."
  - *AI phản hồi:* AI đưa đoạn code tạo token bằng `pyjwt` và verify bằng `passlib.context.CryptContext`. Tuy nhiên mã khóa bí mật `SECRET_KEY = "mysecretkey"` bị hardcode trực tiếp trong file code, và hàm đăng ký không kiểm tra định dạng email hay khoảng trắng.
* **Phát hiện lỗi & Tự sửa lại:**
  - Chuyển toàn bộ `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` ra file cấu hình `.env` để bảo mật.
  - Sửa hàm đăng ký: Thêm `email.strip().lower()` để tránh việc gõ chữ hoa chữ thường tạo ra nhiều tài khoản trùng nhau; thêm regex kiểm tra độ dài mật khẩu tối thiểu 6 ký tự.
  - Ở React frontend: Viết thêm Axios response interceptor bắt mã lỗi 401 để khi token hết hạn thì tự động xóa token trong `localStorage` và điều hướng người dùng về trang đăng nhập, tránh màn hình bị treo trắng.

---

### 📅 14/08/2026: Phân hệ Danh mục, Giao dịch thu/chi & Thùng rác (Recycle Bin)
* **Việc cần làm:**
  - Xây dựng CRUD Danh mục ([categories.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/categories.py)): Nạp sẵn 12 danh mục mặc định, hỗ trợ ẩn/hiện danh mục.
  - Xây dựng CRUD Giao dịch ([transactions.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/transactions.py)): Phân trang, tìm kiếm, lọc theo ngày tháng, danh mục, loại thu/chi.
  - Thêm tính năng Nhân bản giao dịch (`Duplicate`) để tạo nhanh các khoản chi định kỳ.
  - Xây dựng cơ chế Thùng rác: Xóa mềm (`is_deleted = True`), Khôi phục (`Restore`) và Xóa vĩnh viễn (`Permanent Delete`).
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Tôi đang làm tính năng Thùng rác (Recycle Bin) cho phần quản lý giao dịch thu/chi cá nhân (gồm xóa mềm is_deleted, khôi phục và xóa vĩnh viễn). Hãy liệt kê những trường hợp biên (edge cases) có thể xảy ra trong thực tế làm sai lệch số dư ví và sinh code mẫu cho API restore transaction."
  - *AI phản hồi:* AI chỉ ra trường hợp biên: Nếu xóa một khoản thu nhập 5 triệu trong khi người dùng đã tiêu hết tiền thì số dư ví sẽ bị âm. AI viết code khôi phục bằng cách gán lại `txn.is_deleted = False`.
* **Phát hiện lỗi & Tự sửa lại:**
  - **Lỗi AI bỏ sót:** AI không xử lý trường hợp khi người dùng khôi phục một giao dịch từ thùng rác, nhưng Danh mục (`Category`) của giao dịch đó trước đó đã bị người dùng xóa vĩnh viễn $\rightarrow$ gọi API khôi phục sẽ bị văng lỗi Foreign Key Exception ở database.
  - **Nhóm tự sửa:** Trong hàm khôi phục, nhóm viết thêm kiểm tra: nếu danh mục cũ không còn tồn tại hoặc đang bị xóa, tự động gán giao dịch đó về danh mục mặc định "Khác" và gửi thông báo cho người dùng.
  - Thêm kiểm tra quyền sở hữu (`user_id`): Đảm bảo người dùng chỉ được xem/sửa/xóa giao dịch của chính mình, tránh lỗi bảo mật IDOR.

---

### 📅 17/08/2026: Phân hệ Ngân sách (Budgets) & Cảnh báo bội chi
* ***Việc cần làm:**
  - Xây dựng API và giao diện Quản lý Ngân sách ([budgets.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/budgets.py)): Người dùng đặt hạn mức chi tiêu theo từng danh mục trong tháng (ví dụ: Ăn uống tháng 8 là 3 triệu).
  - Tính toán tiến độ chi tiêu thực tế, đổi màu thanh cảnh báo (xanh $\rightarrow$ vàng $\rightarrow$ đỏ khi vượt quá 100%).
  - Cập nhật trang thông tin cá nhân Profile ([profile.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/profile.py)).
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Viết câu truy vấn SQLAlchemy tính tổng số tiền đã chi tiêu (type='expense') của một danh mục trong tháng và năm hiện tại của user, so sánh với hạn mức budget đã đặt để trả về tỷ lệ phần trăm đã dùng."
  - *AI phản hồi:* AI đưa câu query dùng `func.sum(Transaction.amount)` nhóm theo `category_id`.
* **Phát hiện lỗi & Tự sửa lại:**
  - **Lỗi query:** Đoạn code AI sinh ra không lọc điều kiện `is_deleted == False`, dẫn đến việc các giao dịch đã nằm trong Thùng rác vẫn bị tính dồn vào tổng chi tiêu ngân sách, làm sai lệch cảnh báo bội chi.
  - **Nhóm tự sửa:** Thêm `Transaction.is_deleted.is_(False)` vào query.
  - Thêm ràng buộc duy nhất trong database: `UniqueConstraint("user_id", "category_id", "month", "year")` để chặn việc người dùng vô tình tạo 2 bản ghi ngân sách cho cùng một danh mục trong cùng một tháng.

---

### 📅 18/08/2026: Mục tiêu tiết kiệm, Rút tiền & Khóa dòng chống âm ví (Pessimistic Lock)
* **Việc cần làm:**
  - Xây dựng phân hệ Quỹ tiết kiệm ([saving_goals.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/saving_goals.py)): Cho phép tạo mục tiêu tiết kiệm, nạp tiền thủ công (`MANUAL`) hoặc trích tự động khi ghi nhận thu nhập (`INCOME_ALLOCATION`).
  - Hỗ trợ rút tiền tiết kiệm một phần hoặc toàn bộ, hoàn tiền lại vào số dư khả dụng và ghi log lịch sử rút.
  - Viết cơ chế khóa dòng người dùng `SELECT ... FOR UPDATE` trong SQLAlchemy để xử lý xung đột đồng thời (Race-condition).
  - Thêm cơ chế `idempotency_key` chống trừ tiền hoặc nạp tiền 2 lần khi người dùng bấm liên tục hoặc mạng gián đoạn.
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
* **Phát hiện lỗi nghiêm trọng & Tự viết lại:**
  - **Lỗi logic cực nặng của AI:** Khi xóa một khoản thu nhập đã trích tiền vào quỹ tiết kiệm, số tiền đã trích đó sẽ phải được giải phóng ngược lại (`released_savings`) vì nguồn thu không còn nữa. AI chỉ lấy số dư hiện tại trừ đi toàn bộ số tiền `txn.amount`, khiến người dùng bị báo lỗi oan không xóa được dù thực tế số dư sau khi hoàn tiền tiết kiệm vẫn đủ. Ngoài ra AI không dùng khóa dòng nên nếu bấm xóa 2 lần cùng lúc sẽ bị race condition.
  - **Nhóm tự code lại hoàn chỉnh:** Tự viết hàm `_ensure_projected_balance()` trong [transactions.py](file:///d:/clone/personal-expense-ai/backend/app/api/routes/transactions.py) có tính toán chuẩn xác phần tiền tiết kiệm giải phóng:
    ```python
    # Tính toán chính xác phần tiền tiết kiệm được hoàn lại
    released_savings = sum(
        (Decimal(str(goal.current_amount)) - projected_goal_amounts[goal.id]
         for goal in linked_goals if goal.status != GoalStatus.CANCELLED),
        Decimal("0")
    )
    # Khóa hàng User và kiểm tra số dư dự kiến
    _ensure_projected_balance(
        db,
        current_user.id,
        -_balance_effect(txn.type, Decimal(str(txn.amount))) + released_savings,
        "Không thể xóa nguồn thu vì thao tác này sẽ làm số dư khả dụng bị âm."
    )
    ```
  - Thêm mã khóa `(saving_goal_id, idempotency_key)` khi rút tiền để client gửi lại request trùng lặp không bị trừ tiền lần hai.

---

### 📅 19/08/2026: Trích xuất sao kê ngân hàng Excel & Sửa lỗi Parser MB Bank
* **Việc cần làm:**
  - Viết module đọc file sao kê Excel ngân hàng ([excel_service.py](file:///d:/clone/personal-expense-ai/backend/app/services/excel_service.py)) và parser riêng cho sao kê MB Bank ([mb_parser.py](file:///d:/clone/personal-expense-ai/backend/app/services/mb_parser.py)).
  - Cho phép người dùng tải file `.xlsx` lên, xem trước bảng dữ liệu (Preview) và chọn danh mục trước khi nạp vào hệ thống.
* **Minh chứng sử dụng AI:**
  - *Prompt:* "Viết biểu thức chính quy (Regex) trong Python để trích xuất số tiền và dấu biến động (+ hoặc -) từ cột diễn giải sao kê ngân hàng có dạng: 'GD: +1,500,000VND ngay 15/08' hoặc '-250,000 VND tai Highlands Coffee'."
  - *AI phản hồi:* AI đưa regex: `r"([+-]?\d+)\s*(?:VND|d)?"`
* **Phát hiện lỗi & Tự sửa lại:**
  - **Lỗi Regex:** Dữ liệu thực tế từ file Excel ngân hàng Việt Nam luôn có dấu phẩy `,` phân cách hàng nghìn (ví dụ `1,500,000`). Regex của AI gặp dấu phẩy thì dừng lại ngay, chỉ bắt được mỗi số `1` (thay vì 1.5 triệu thì thành 1 đồng!).
  - **Nhóm sửa:** Viết lại pattern: `r"([+-]?[\d,]+)\s*(?:VND|đ|d)?"`, sau đó dùng `.replace(",", "")` rồi mới ép sang kiểu `Decimal`. Kiểm tra và bổ sung xử lý trường hợp file bị trống dòng hoặc sai định dạng ngày tháng để không làm crash cả tiến trình import.

---

## 🎯 TỔNG KẾT BÀI HỌC KINH NGHIỆM KHI SỬ DỤNG AI

1. **Không copy nguyên văn code AI ở các phần xử lý tiền bạc:** AI thường mắc lỗi tính toán làm tròn (dùng `float` thay vì `Decimal`), quên các khoản trích lũy phụ và không để ý đến các trường hợp race condition khi có nhiều request đồng thời.
2. **AI rất mạnh ở khâu gợi ý trường hợp biên (Edge Cases):** Khi được đóng vai Business Analyst, AI liệt kê được nhiều góc nhìn thực tế (như người dùng xóa thu nhập khi đã tiêu hết tiền, hoặc nhập sao kê trùng lặp), giúp nhóm lường trước các kịch bản để tự viết code kiểm tra chặt chẽ hơn.
3. **Phải luôn kiểm thử lại regex và dữ liệu thực tế:** Các đoạn code regex hoặc xử lý chuỗi do AI tạo ra thường dựa trên dữ liệu mẫu lý tưởng của phương Tây, khi gặp định dạng thực tế ở Việt Nam (dấu phẩy phân cách tiền tệ, định dạng ngày DD/MM/YYYY) thì rất dễ bị lỗi nếu không test kỹ.
