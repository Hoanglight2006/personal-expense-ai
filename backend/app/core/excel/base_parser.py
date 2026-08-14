from abc import ABC, abstractmethod
from typing import IO

from app.schemas.transaction import BulkTransactionRow


class ExcelParser(ABC):
    """Abstract base class for Excel statement parsers."""

    @abstractmethod
    def can_parse(self, file_content: bytes) -> bool:
        """Return True if this parser can handle the given file."""
        pass

    @abstractmethod
    def parse(self, file_content: bytes) -> list[BulkTransactionRow]:
        """Parse the Excel file into a list of transaction rows."""
        pass
