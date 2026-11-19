"""Типы метаданных таблиц для валидации Spark SQL."""

from typing import NotRequired, TypeAlias, TypedDict


class ColumnMetadata(TypedDict):
    """Тип столбца в формате Spark DDL и допустимость NULL."""

    type: str
    nullable: NotRequired[bool]


class TableMetadata(TypedDict):
    """Столбцы таблицы в порядке их объявления."""

    columns: dict[str, ColumnMetadata]


TablesMetadata: TypeAlias = dict[str, TableMetadata]  # noqa: UP040
