"""Excel agent: prepares and analyzes spreadsheets sent by the client.

The Telegram flow sends a document via `analyze_upload`; text-only chat
messages just get pointed at that flow.
"""
import pandas as pd

from .models import ExcelUpload


def handle_message(telegram_user_id: int, text: str) -> str:
    return "Пришлите файл (.xlsx/.csv) — я его разберу и пришлю сводку."


def analyze_upload(upload: ExcelUpload) -> str:
    df = pd.read_excel(upload.file.path) if upload.original_name.endswith(("xlsx", "xls")) else pd.read_csv(upload.file.path)
    summary = (
        f"Строк: {len(df)}, столбцов: {len(df.columns)}\n"
        f"Столбцы: {', '.join(map(str, df.columns))}"
    )
    upload.summary = summary
    upload.save(update_fields=["summary"])
    return summary
