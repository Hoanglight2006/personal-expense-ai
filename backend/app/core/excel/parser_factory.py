from app.core.excel.base_parser import ExcelParser
from app.core.excel.mb_parser import MBStatementAdapter


def get_excel_parser(file_content: bytes) -> ExcelParser | None:
    """Factory to get the right Excel parser based on file content."""
    mb_parser = MBStatementAdapter()
    if mb_parser.can_parse(file_content):
        return mb_parser
    # Add other bank parsers here in the future
    return None
