import io
import pytest
from decimal import Decimal
import openpyxl
from datetime import date

from app.core.excel.mb_parser import MBStatementAdapter
from app.models.enums import CategoryType, PaymentMethod


@pytest.fixture
def mb_parser():
    return MBStatementAdapter()


def create_mock_excel(rows_data, sheet_name="Sao ke tai khoan"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name
    for row in rows_data:
        ws.append(row)
    
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def test_mb_parser_can_parse_with_sheet_name(mb_parser):
    content = create_mock_excel([], "Sao ke tai khoan")
    assert mb_parser.can_parse(content) is True


def test_mb_parser_can_parse_fallback_headers(mb_parser):
    content = create_mock_excel([
        ["Ngày giao dịch", "Ngày hạch toán", "Số bút toán", "Phát sinh nợ", "Phát sinh có", "Số dư", "Nội dung", "Đơn vị thụ hưởng", "Tài khoản", "Ngân hàng"]
    ], "Sheet1")
    assert mb_parser.can_parse(content) is True


def test_mb_parser_parse_transactions(mb_parser):
    rows_data = [
        # Random headers
        ["Header 1"],
        ["Header 2"],
        # Header VN
        ["Ngày giao dịch", "Ngày hạch toán", "Số bút toán", "Phát sinh nợ", "Phát sinh có", "Số dư", "Nội dung", "Đơn vị thụ hưởng", "Tài khoản", "Ngân hàng"],
        # Header EN
        ["Transaction date", "Accounting Date", "Transaction No", "Debit", "Credit", "Balance", "Details", "Beneficiary", "Account", "Bank"],
        # Expense row
        ["01/08/2026", "01/08/2026", "FT26214A1", 50000, 0, 1000000, "Thanh toan cafe", "HIGHLANDS", "123456", "VCB"],
        # Income row
        ["02/08/2026", "02/08/2026", "FT26214B2", 0, "1,500,000", 2500000, "Nhan luong", None, None, None],
        # Empty / Skip row (both empty or 0)
        ["03/08/2026", "03/08/2026", "FT26214C3", 0, 0, 2500000, "Khong phat sinh", None, None, None],
        # Both Debit and Credit have values (Error row -> should be skipped)
        ["04/08/2026", "04/08/2026", "FT26214D4", 1000, 1000, 2500000, "Loi ngan hang", None, None, None],
        # Invalid amount format
        ["05/08/2026", "05/08/2026", "FT26214E5", "abc", 0, 2500000, "Loi so tien", None, None, None],
        # Footer
        ["Tổng phát sinh trong kỳ / Total", None, None, 50000, 1500000],
        ["Chung tu nay duoc xuat tu dong..."],
    ]
    
    content = create_mock_excel(rows_data)
    parsed_rows = mb_parser.parse(content)
    
    # Expense + Income (2 rows)
    assert len(parsed_rows) == 2
    
    # Check Expense Row
    expense = parsed_rows[0]
    assert expense.amount == Decimal("50000")
    assert expense.type == CategoryType.EXPENSE
    assert expense.transaction_date == date(2026, 8, 1)
    assert "FT26214A1" in expense.description
    assert "HIGHLANDS" in expense.description
    
    # Check Income Row
    income = parsed_rows[1]
    assert income.amount == Decimal("1500000")
    assert income.type == CategoryType.INCOME
    assert income.transaction_date == date(2026, 8, 2)
    assert "FT26214B2" in income.description
    assert "Nhan luong" in income.description
