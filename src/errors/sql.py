"""Исключения ошибок SQL, обнаруживаемых Catalyst."""

from __future__ import annotations

from .base import SparkSqlAnalyzerError


class SqlValidationError(SparkSqlAnalyzerError):
    """Базовая семантическая или синтаксическая ошибка SQL."""


class SqlSyntaxError(SqlValidationError):
    """Синтаксическая ошибка ``PARSE_SYNTAX_ERROR``."""


class TableOrViewNotFoundError(SqlValidationError):
    """Таблица или представление не существует."""


class UnresolvedColumnError(SqlValidationError):
    """Колонка не существует или не может быть разрешена."""


class UnresolvedRoutineError(SqlValidationError):
    """Функция не зарегистрирована в Catalyst."""


class AmbiguousReferenceError(SqlValidationError):
    """Ссылка на колонку неоднозначна."""


class DataTypeMismatchError(SqlValidationError):
    """Типы выражений несовместимы."""


class MissingGroupByError(SqlValidationError):
    """В агрегирующем запросе отсутствует ``GROUP BY``."""


class MissingAggregationError(SqlValidationError):
    """Выражение не входит в группировку или агрегатную функцию."""


class WrongNumberOfArgumentsError(SqlValidationError):
    """Функции передано неверное число аргументов."""


class StructFieldNotFoundError(SqlValidationError):
    """Поле отсутствует в типе ``STRUCT``."""


SQL_ERROR_TYPES: tuple[tuple[str, type[SqlValidationError]], ...] = (
    ("PARSE_SYNTAX_ERROR", SqlSyntaxError),
    ("TABLE_OR_VIEW_NOT_FOUND", TableOrViewNotFoundError),
    ("UNRESOLVED_COLUMN", UnresolvedColumnError),
    ("UNRESOLVED_ROUTINE", UnresolvedRoutineError),
    ("AMBIGUOUS_REFERENCE", AmbiguousReferenceError),
    ("DATATYPE_MISMATCH", DataTypeMismatchError),
    ("MISSING_GROUP_BY", MissingGroupByError),
    ("MISSING_AGGREGATION", MissingAggregationError),
    ("WRONG_NUM_ARGS", WrongNumberOfArgumentsError),
    ("FIELD_NOT_FOUND", StructFieldNotFoundError),
)


def sql_error_from_condition(
    condition: str,
    message: str,
    sql: str,
) -> SqlValidationError:
    """Создаёт Python-исключение по поддерживаемому Spark condition."""
    for prefix, error_type in SQL_ERROR_TYPES:
        if condition == prefix or condition.startswith(f"{prefix}."):
            return error_type(
                message,
                sql=sql,
                error_condition=condition,
            )
    raise KeyError(condition)
