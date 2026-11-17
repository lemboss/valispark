"""Базовые исключения SQL-анализатора."""

from __future__ import annotations

import re

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def clean_error_message(message: str) -> str:
    """Удаляет ANSI-разметку и лишние пробелы из текста ошибки."""
    return _ANSI_ESCAPE.sub("", message).strip()


class SparkSqlAnalyzerError(Exception):
    """Базовая ошибка проверки Spark SQL."""

    def __init__(
        self,
        message: str,
        *,
        sql: str,
        error_condition: str = "",
    ) -> None:
        self.message = clean_error_message(message)
        self.sql = sql
        self.error_condition = error_condition
        super().__init__(self._formatted_message())

    def _formatted_message(self) -> str:
        if self.error_condition:
            prefix = f"[{self.error_condition}]"
            if not self.message.startswith(prefix):
                return f"{prefix} {self.message}"
        return self.message
