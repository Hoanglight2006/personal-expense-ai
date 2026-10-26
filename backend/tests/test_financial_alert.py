"""Tests for FinancialAlertService and EmailService."""

from datetime import date
from decimal import Decimal
import pytest
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import CategoryType, PaymentMethod, UserRole
from app.models.transaction import Transaction
from app.models.user import User
from app.services.email_service import EmailService
from app.services.financial_alert_service import FinancialAlertService
from tests.test_auth import random_string


def test_financial_alert_service_unverified_user_no_email(client, db):
    user = User(
        username=f"unver_{random_string()}",
        email=f"unver_{random_string()}@test.com",
        password_hash="fakehash",
        is_verified=False,
    )
    db.add(user)
    db.commit()

    alert_service = FinancialAlertService(db, user)
    sent = alert_service.check_and_send_budget_alerts()
    assert sent == []


def test_financial_alert_service_verified_user_sends_alert(client, db, monkeypatch):
    sent_calls = []

    def mock_send(to_email, category_name, budget_amount, spent_amount, percentage_used, status):
        sent_calls.append({
            "to_email": to_email,
            "category_name": category_name,
            "spent": spent_amount,
            "status": status,
        })
        return True

    monkeypatch.setattr(EmailService, "send_financial_alert", mock_send)

    user = User(
        username=f"ver_{random_string()}",
        email=f"ver_{random_string()}@test.com",
        password_hash="fakehash",
        is_verified=True,
    )
    db.add(user)
    db.commit()

    cat = Category(
        user_id=user.id,
        name="Ăn uống",
        name_normalized="an uong",
        type=CategoryType.EXPENSE,
        is_active=True,
    )
    db.add(cat)
    db.commit()

    today = date.today()
    # Create budget of 1,000,000
    budget = Budget(
        user_id=user.id,
        category_id=cat.id,
        amount=Decimal("1000000.00"),
        month=today.month,
        year=today.year,
    )
    db.add(budget)

    # Create expense of 900,000 (90% -> warning)
    txn = Transaction(
        user_id=user.id,
        category_id=cat.id,
        amount=Decimal("900000.00"),
        type=CategoryType.EXPENSE,
        transaction_date=today,
        payment_method=PaymentMethod.CASH,
    )
    db.add(txn)
    db.commit()

    alert_service = FinancialAlertService(db, user)
    sent = alert_service.check_and_send_budget_alerts(category_id=cat.id)

    assert len(sent) == 1
    assert sent[0]["category_name"] == "Ăn uống"
    assert sent[0]["status"] == "warning"
    assert len(sent_calls) == 1
    assert sent_calls[0]["to_email"] == user.email

