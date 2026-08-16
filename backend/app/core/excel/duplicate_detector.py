from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def is_duplicate_transaction(
    db: Session,
    user_id: int,
    amount: Decimal,
    transaction_date: str | object,
    description: str | None,
) -> bool:
    """Check if a similar transaction already exists for this user."""
    # This is a simple fingerprint. MB parser prepends the ref number to the description
    # e.g. "[FT2332...] Transfer ...". 
    # If the ref number is present, it's highly specific.
    # Otherwise, it matches exact amount, date, and description.
    
    query = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.is_deleted.is_(False),
        Transaction.amount == amount,
        Transaction.transaction_date == transaction_date,
    )
    
    if description:
        # Check if the reference number is in the description
        if description.startswith("[") and "]" in description:
            ref_no = description[1:description.find("]")]
            query = query.filter(Transaction.description.contains(ref_no))
        else:
            query = query.filter(Transaction.description == description)
    else:
        query = query.filter((Transaction.description.is_(None)) | (Transaction.description == ""))

    existing = query.first()
    return existing is not None
