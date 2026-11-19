"""Валидация входных данных без обращения к Catalyst."""

from .errors import AnalyzerInputError
from .types import ColumnMetadata, TablesMetadata


class _MetadataValidator:
    """Проверяет Python-вход и возвращает защитную копию метаданных."""

    def __init__(self, sql: str) -> None:
        self._sql = sql

    def validate_sql(self) -> None:
        if not isinstance(self._sql, str):
            raise self._input_error("sql должен быть строкой")

    def validate_tables(self, tables: TablesMetadata) -> TablesMetadata:
        if not isinstance(tables, dict):
            raise self._input_error("tables должен быть словарём")
        validated: TablesMetadata = {}
        for table_name, table in tables.items():
            if not isinstance(table_name, str) or not table_name:
                raise self._input_error("Имя таблицы должно быть непустой строкой")
            if (
                not isinstance(table, dict)
                or table.keys() != {"columns"}
                or not isinstance(table["columns"], dict)
            ):
                raise self._input_error(
                    f"Описание таблицы {table_name!r} должно содержать словарь columns"
                )
            columns: dict[str, ColumnMetadata] = {}
            for name, column in table["columns"].items():
                if not isinstance(name, str) or not name:
                    raise self._input_error(
                        f"Имя столбца таблицы {table_name!r} должно быть непустой строкой"
                    )
                if (
                    not isinstance(column, dict)
                    or column.keys() - {"type", "nullable"}
                    or not isinstance(column.get("type"), str)
                    or not column["type"].strip()
                    or not isinstance(column.get("nullable", True), bool)
                ):
                    raise self._input_error(
                        f"Некорректное описание столбца {name!r} таблицы {table_name!r}"
                    )
                columns[name] = column.copy()
            validated[table_name] = {"columns": columns}
        return validated

    def _input_error(self, message: str) -> AnalyzerInputError:
        sql = self._sql if isinstance(self._sql, str) else repr(self._sql)
        return AnalyzerInputError(message, sql=sql)
