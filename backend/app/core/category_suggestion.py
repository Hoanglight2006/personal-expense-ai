from sqlalchemy.orm import Session
from app.models.category import Category
from app.models.enums import CategoryType


def suggest_category(
    db: Session,
    user_id: int,
    type_sugg: CategoryType | None,
    description: str | None,
) -> Category | None:
    """Suggest an active category for the user based on type and description."""
    if not type_sugg:
        return None

    query = db.query(Category).filter(
        Category.user_id == user_id,
        Category.is_active.is_(True),
    )

    if description:
        desc_lower = description.lower()
        # Find all matching categories and do basic keyword match
        categories = query.all()
        for cat in categories:
            if cat.name.lower() in desc_lower:
                return cat
            
    # Fallback to the first available category of that type
    return query.first()
