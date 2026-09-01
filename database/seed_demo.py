"""Seed demo dataset for Personal Expense AI system.

Usage:
    python backend/seed_demo.py
    # or inside backend folder:
    python seed_demo.py

This script creates or resets a comprehensive demo account:
    - Email: demo@example.com
    - Password: Password123@
    - 12 default categories
    - 40+ realistic income & expense transactions spanning 6 months
    - Monthly budgets with realistic spending tracking
    - Saving goals with contributions & income allocations
"""

import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# Ensure project root and backend are on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.saving_goal import SavingGoal
from app.models.saving_contribution import SavingContribution
from app.models.enums import CategoryType, PaymentMethod, GoalStatus, ContributionSource
from app.core.security import get_password_hash
from app.core.category_defaults import add_missing_default_categories


def seed_demo_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("🌱 Bắt đầu tạo dữ liệu mẫu cho Personal Expense AI...")

        demo_email = "demo@example.com"
        demo_username = "demouser"
        demo_password = "Password123@"

        # 1. Clean existing demo user if exists
        existing_user = db.query(User).filter(User.email == demo_email).first()
        if existing_user:
            print(f"🔄 Đang làm mới tài khoản demo hiện tại ({demo_email})...")
            db.delete(existing_user)
            db.commit()

        # 2. Create User
        demo_user = User(
            username=demo_username,
            email=demo_email,
            password_hash=get_password_hash(demo_password),
            avatar_url="/static/avatars/default_avatar.png"
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        print(f"✓ Tạo thành công User Demo: {demo_email} (Mật khẩu: {demo_password})")

        # 3. Create Default Categories
        add_missing_default_categories(db, demo_user.id)
        db.commit()
        categories = db.query(Category).filter(Category.user_id == demo_user.id).all()
        cat_map = {c.name: c for c in categories}
        print(f"✓ Khởi tạo {len(categories)} danh mục thu chi chuẩn.")

        # 4. Create Saving Goals
        today = date.today()
        current_year = today.year
        current_month = today.month

        goal_macbook = SavingGoal(
            user_id=demo_user.id,
            name="Mua Macbook Pro M3",
            target_amount=Decimal("45000000.00"),
            current_amount=Decimal("0.00"),
            deadline=today + timedelta(days=120),
            status=GoalStatus.ACTIVE,
        )
        goal_emergency = SavingGoal(
            user_id=demo_user.id,
            name="Quỹ Khẩn Cấp Dự Phòng",
            target_amount=Decimal("60000000.00"),
            current_amount=Decimal("0.00"),
            deadline=today + timedelta(days=365),
            status=GoalStatus.ACTIVE,
        )
        db.add_all([goal_macbook, goal_emergency])
        db.commit()
        db.refresh(goal_macbook)
        db.refresh(goal_emergency)

        # 5. Generate Multi-Month Realistic Transactions
        transactions = []
        contributions = []

        # Helper to get date in past months
        def get_date_in_month(months_ago, day):
            # approximate month offset
            y = current_year
            m = current_month - months_ago
            while m <= 0:
                m += 12
                y -= 1
            max_day = min(day, 28)
            return date(y, m, max_day)

        # Monthly income and expense template
        # 6 months of data: from (current - 5) to current month
        for months_ago in range(5, -1, -1):
            m_date = lambda d: get_date_in_month(months_ago, d)
            
            # --- Incomes ---
            # 1. Salary (Lương mùng 5 hàng tháng)
            salary_amount = Decimal("32000000.00")
            salary_txn = Transaction(
                user_id=demo_user.id,
                category_id=cat_map["Lương"].id,
                type=CategoryType.INCOME,
                amount=salary_amount,
                description=f"Lương tháng {m_date(5).strftime('%m/%Y')}",
                transaction_date=m_date(5),
                payment_method=PaymentMethod.BANK_TRANSFER
            )
            db.add(salary_txn)
            db.flush()

            # Allocate 3M from salary to Macbook goal each month
            alloc_amount = Decimal("3000000.00")
            contrib = SavingContribution(
                saving_goal_id=goal_macbook.id,
                transaction_id=salary_txn.id,
                amount=alloc_amount,
                source=ContributionSource.INCOME_ALLOCATION,
                note=f"Trích lương tháng {m_date(5).strftime('%m/%Y')} vào quỹ Macbook"
            )
            db.add(contrib)
            goal_macbook.current_amount += alloc_amount

            # 2. Bonus / Freelance / Investment (occasional)
            if months_ago in (4, 2, 0):
                bonus_txn = Transaction(
                    user_id=demo_user.id,
                    category_id=cat_map["Thưởng"].id,
                    type=CategoryType.INCOME,
                    amount=Decimal("5500000.00"),
                    description=f"Thưởng KPI & dự án tháng {m_date(15).strftime('%m/%Y')}",
                    transaction_date=m_date(15),
                    payment_method=PaymentMethod.BANK_TRANSFER
                )
                db.add(bonus_txn)
                db.flush()

                # Manual deposit to Emergency fund
                manual_deposit = Decimal("2500000.00")
                contrib_em = SavingContribution(
                    saving_goal_id=goal_emergency.id,
                    transaction_id=None,
                    amount=manual_deposit,
                    source=ContributionSource.MANUAL,
                    note=f"Nạp tích lũy quỹ khẩn cấp tháng {m_date(15).strftime('%m/%Y')}"
                )
                db.add(contrib_em)
                goal_emergency.current_amount += manual_deposit

            # --- Expenses ---
            # 1. Nhà ở / Tiền thuê nhà + điện nước
            db.add(Transaction(
                user_id=demo_user.id,
                category_id=cat_map["Nhà ở"].id,
                type=CategoryType.EXPENSE,
                amount=Decimal("6500000.00"),
                description="Tiền thuê căn hộ & phí dịch vụ",
                transaction_date=m_date(6),
                payment_method=PaymentMethod.BANK_TRANSFER
            ))
            db.add(Transaction(
                user_id=demo_user.id,
                category_id=cat_map["Nhà ở"].id,
                type=CategoryType.EXPENSE,
                amount=Decimal("850000.00"),
                description="Hóa đơn tiền điện & nước sinh hoạt",
                transaction_date=m_date(12),
                payment_method=PaymentMethod.BANK_TRANSFER
            ))

            # 2. Ăn uống
            db.add(Transaction(
                user_id=demo_user.id,
                category_id=cat_map["Ăn uống"].id,
                type=CategoryType.EXPENSE,
                amount=Decimal("1250000.00"),
                description="Đi siêu thị WinMart mua thực phẩm tuần 1",
                transaction_date=m_date(7),
                payment_method=PaymentMethod.BANK_TRANSFER
            ))
            db.add(Transaction(
                user_id=demo_user.id,
                category_id=cat_map["Ăn uống"].id,
                type=CategoryType.EXPENSE,
                amount=Decimal("1420000.00"),
                description="Đi siêu thị thực phẩm tuần 2 + ăn trưa văn phòng",
                transaction_date=m_date(14),
                payment_method=PaymentMethod.BANK_TRANSFER
            ))
            db.add(Transaction(
                user_id=demo_user.id,
                category_id=cat_map["Ăn uống"].id,
                type=CategoryType.EXPENSE,
                amount=Decimal("780000.00"),
                description="Ăn tối liên hoan cuối tuần với bạn bè",
                transaction_date=m_date(21),
                payment_method=PaymentMethod.CASH
            ))

            # 3. Đi lại / Xăng xe / Grab
            db.add(Transaction(
                user_id=demo_user.id,
                category_id=cat_map["Đi lại"].id,
                type=CategoryType.EXPENSE,
                amount=Decimal("450000.00"),
                description="Đổ xăng xe máy & phí gửi xe",
                transaction_date=m_date(8),
                payment_method=PaymentMethod.CASH
            ))
            db.add(Transaction(
                user_id=demo_user.id,
                category_id=cat_map["Đi lại"].id,
                type=CategoryType.EXPENSE,
                amount=Decimal("320000.00"),
                description="Đặt xe GrabCar đi gặp đối tác",
                transaction_date=m_date(19),
                payment_method=PaymentMethod.BANK_TRANSFER
            ))

            # 4. Mua sắm
            db.add(Transaction(
                user_id=demo_user.id,
                category_id=cat_map["Mua sắm"].id,
                type=CategoryType.EXPENSE,
                amount=Decimal("1150000.00"),
                description="Mua sắm đồ gia dụng & quần áo Shopee",
                transaction_date=m_date(11),
                payment_method=PaymentMethod.BANK_TRANSFER
            ))

            # 5. Giải trí / Cafe
            db.add(Transaction(
                user_id=demo_user.id,
                category_id=cat_map["Giải trí"].id,
                type=CategoryType.EXPENSE,
                amount=Decimal("260000.00"),
                description="Gói dịch vụ Netflix & Spotify hàng tháng",
                transaction_date=m_date(10),
                payment_method=PaymentMethod.BANK_TRANSFER
            ))
            db.add(Transaction(
                user_id=demo_user.id,
                category_id=cat_map["Giải trí"].id,
                type=CategoryType.EXPENSE,
                amount=Decimal("350000.00"),
                description="Cà phê làm việc & xem phim rạp CGV",
                transaction_date=m_date(24),
                payment_method=PaymentMethod.CASH
            ))

            # 6. Sức khỏe & Giáo dục (thỉnh thoảng)
            if months_ago % 2 == 0:
                db.add(Transaction(
                    user_id=demo_user.id,
                    category_id=cat_map["Sức khỏe"].id,
                    type=CategoryType.EXPENSE,
                    amount=Decimal("750000.00"),
                    description="Gói tập gym & vitamin bổ sung",
                    transaction_date=m_date(16),
                    payment_method=PaymentMethod.BANK_TRANSFER
                ))
            if months_ago in (1, 3):
                db.add(Transaction(
                    user_id=demo_user.id,
                    category_id=cat_map["Giáo dục"].id,
                    type=CategoryType.EXPENSE,
                    amount=Decimal("1200000.00"),
                    description="Khóa học trực tuyến Udemy & sách chuyên ngành",
                    transaction_date=m_date(18),
                    payment_method=PaymentMethod.BANK_TRANSFER
                ))

        db.commit()
        total_txns = db.query(Transaction).filter(Transaction.user_id == demo_user.id).count()
        print(f"✓ Tạo thành công {total_txns} giao dịch thu/chi trải dài 6 tháng gần nhất.")
        print(f"✓ Cập nhật tiến độ mục tiêu: Macbook ({goal_macbook.current_amount:,.0f} đ), Quỹ khẩn cấp ({goal_emergency.current_amount:,.0f} đ).")

        # 6. Create Monthly Budgets for Current & Previous Months
        for m_offset in (0, 1):
            t_date = get_date_in_month(m_offset, 1)
            b_month = t_date.month
            b_year = t_date.year

            # Budget for Ăn uống
            db.add(Budget(
                user_id=demo_user.id,
                category_id=cat_map["Ăn uống"].id,
                amount=Decimal("5000000.00"),
                month=b_month,
                year=b_year
            ))
            # Budget for Mua sắm
            db.add(Budget(
                user_id=demo_user.id,
                category_id=cat_map["Mua sắm"].id,
                amount=Decimal("3000000.00"),
                month=b_month,
                year=b_year
            ))
            # Budget for Giải trí
            db.add(Budget(
                user_id=demo_user.id,
                category_id=cat_map["Giải trí"].id,
                amount=Decimal("1500000.00"),
                month=b_month,
                year=b_year
            ))
            # Budget for Đi lại
            db.add(Budget(
                user_id=demo_user.id,
                category_id=cat_map["Đi lại"].id,
                amount=Decimal("1200000.00"),
                month=b_month,
                year=b_year
            ))

        db.commit()
        print("✓ Khởi tạo thành công các định mức Ngân sách tháng.")

        print("\n🎉 HOÀN TẤT NẠP DỮ LIỆU MẪU THÀNH CÔNG!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🔑 THÔNG TIN ĐĂNG NHẬP DEMO:")
        print(f"   📧 Email:    {demo_email}")
        print(f"   🔒 Mật khẩu: {demo_password}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("💡 Giờ bạn có thể mở http://localhost:5173 và đăng nhập ngay để trải nghiệm đồ án với đầy đủ biểu đồ sống động!\n")

    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi khi nạp dữ liệu mẫu: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
