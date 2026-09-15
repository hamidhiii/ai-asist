"""Excel agent: prepares and analyzes spreadsheets sent by the client.

The Telegram flow sends a document via `analyze_upload`; text-only chat
messages just get pointed at that flow.
"""
import pandas as pd

from .models import ExcelUpload


def handle_message(telegram_user_id: int, text: str, note: str | None = None) -> str:
    return "Пришлите файл (.xlsx/.csv) — я его разберу и пришлю сводку."


def _summarize_dataframe(df: pd.DataFrame) -> str:
    lines = [
        f"Строк: {len(df)}, столбцов: {len(df.columns)}",
        f"Столбцы: {', '.join(map(str, df.columns))}",
    ]

    numeric_df = df.select_dtypes(include="number")
    if not numeric_df.empty:
        lines.append("Статистика по числовым столбцам:")
        for col in numeric_df.columns:
            series = numeric_df[col].dropna()
            if series.empty:
                continue
            lines.append(
                f"  {col}: сумма={series.sum():.2f}, среднее={series.mean():.2f}, "
                f"min={series.min():.2f}, max={series.max():.2f}"
            )

    return "\n".join(lines)


def analyze_upload(upload: ExcelUpload) -> str:
    is_excel = upload.original_name.lower().endswith(("xlsx", "xls"))

    if is_excel:
        sheets = pd.read_excel(upload.file.path, sheet_name=None)
    else:
        sheets = {"CSV": pd.read_csv(upload.file.path)}

    if len(sheets) == 1:
        ((_, df),) = sheets.items()
        summary = _summarize_dataframe(df)
    else:
        parts = []
        for sheet_name, df in sheets.items():
            parts.append(f"Лист «{sheet_name}»:\n{_summarize_dataframe(df)}")
        summary = "\n\n".join(parts)

    upload.summary = summary
    upload.save(update_fields=["summary"])
    return summary
