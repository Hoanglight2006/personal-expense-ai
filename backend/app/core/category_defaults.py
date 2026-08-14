from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import category_name_key


DEFAULT_CATEGORIES = (
    ("Ăn uống", "food", "#E76452", "expense"),
    ("Đi lại", "transport", "#4F8CC9", "expense"),
    ("Mua sắm", "shopping", "#9A6AC4", "expense"),
    ("Nhà ở", "home", "#D87542", "expense"),
    ("Sức khỏe", "health", "#DE5555", "expense"),
    ("Giáo dục", "education", "#4F72BE", "expense"),
    ("Giải trí", "entertainment", "#7D5BB2", "expense"),
    ("Lương", "salary", "#4B9D67", "income"),
    ("Thưởng", "bonus", "#E9A22F", "income"),
    ("Quà tặng", "gift", "#DD5C77", "income"),
    ("Đầu tư", "investment", "#719F4E", "income"),
    ("Khác", "other", "#D69A23", "expense"),
)


def add_missing_default_categories(db: Session, user_id: int) -> list[Category]:
    """Stage missing presets without restoring or replacing existing categories."""
    existing_names = {
        row[0]
        for row in db.query(Category.name_normalized)
        .filter(Category.user_id == user_id)
        .all()
    }
    created: list[Category] = []
    for name, icon, color, cat_type in DEFAULT_CATEGORIES:
        normalized_name = category_name_key(name)
        if normalized_name in existing_names:
            continue
        category = Category(
            user_id=user_id,
            name=name,
            name_normalized=normalized_name,
            icon=icon,
            color=color,
            type=cat_type,
            is_default=True,
        )
        db.add(category)
        created.append(category)
        existing_names.add(normalized_name)
    return created
