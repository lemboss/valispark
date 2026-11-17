"""Преобразование исключений Catalyst, Spark и Py4J в публичные ошибки."""

from __future__ import annotations

import re
from contextlib import suppress

from py4j.protocol import Py4JError, Py4JJavaError, Py4JNetworkError
from pyspark.errors import (
    IllegalArgumentException,
    PySparkException,
    SparkRuntimeException,
    UnsupportedOperationException,
)

from .base import SparkSqlAnalyzerError
from .runtime import (
    CatalystIllegalArgumentError,
    CatalystRuntimeError,
    CatalystUnsupportedOperationError,
    Py4JConnectionError,
    Py4JInvocationError,
    Py4JJavaInvocationError,
    SparkEngineError,
    UnexpectedAnalyzerError,
)
from .sql import sql_error_from_condition

_ERROR_CONDITION = re.compile(r"\[([A-Z][A-Z0-9_.]+)]")
_JAVA_ERROR_TYPES: tuple[tuple[str, type[SparkSqlAnalyzerError]], ...] = (
    ("IllegalArgumentException", CatalystIllegalArgumentError),
    ("UnsupportedOperationException", CatalystUnsupportedOperationError),
    ("SparkRuntimeException", CatalystRuntimeError),
    ("SparkException", SparkEngineError),
)


def translate_error(exc: Exception, *, sql: str) -> SparkSqlAnalyzerError:
    """Преобразует внутреннее исключение в публичную ошибку анализатора."""
    if isinstance(exc, SparkSqlAnalyzerError):
        return exc

    message = _error_message(exc)
    condition = _error_condition(exc, message)
    if condition:
        with suppress(KeyError):
            return sql_error_from_condition(condition, message, sql)

    if isinstance(exc, Py4JNetworkError):
        return Py4JConnectionError(message, sql=sql)
    if isinstance(exc, IllegalArgumentException):
        return CatalystIllegalArgumentError(message, sql=sql)
    if isinstance(exc, UnsupportedOperationException):
        return CatalystUnsupportedOperationError(message, sql=sql)
    if isinstance(exc, SparkRuntimeException):
        return CatalystRuntimeError(message, sql=sql)
    if isinstance(exc, Py4JJavaError):
        return _translate_java_error(exc, message=message, sql=sql)
    if isinstance(exc, Py4JError):
        return Py4JInvocationError(message, sql=sql)
    if isinstance(exc, PySparkException):
        return CatalystRuntimeError(message, sql=sql)
    return UnexpectedAnalyzerError(message, sql=sql)


def _translate_java_error(
    exc: Py4JJavaError,
    *,
    message: str,
    sql: str,
) -> SparkSqlAnalyzerError:
    java_class = _java_class_name(exc)
    for suffix, error_type in _JAVA_ERROR_TYPES:
        if java_class.endswith(suffix):
            return error_type(message, sql=sql)
    return Py4JJavaInvocationError(message, sql=sql)


def _error_message(exc: Exception) -> str:
    """Возвращает сообщение JVM без служебного Py4J stack trace."""
    if isinstance(exc, Py4JJavaError):
        try:
            message = exc.java_exception.getMessage()
            return str(message or exc.java_exception.toString())
        except (AttributeError, Py4JError, TypeError):
            return str(exc)
    return str(exc)


def _error_condition(exc: Exception, message: str) -> str:
    """Извлекает Spark error condition из Python/JVM исключения."""
    condition = _condition_from_object(exc)
    if condition:
        return condition

    if isinstance(exc, Py4JJavaError):
        condition = _condition_from_object(exc.java_exception)
        if condition:
            return condition

    match = _ERROR_CONDITION.search(message)
    return match.group(1) if match else ""


def _condition_from_object(exc: object) -> str:
    for method_name in ("getCondition", "getErrorClass"):
        try:
            condition = getattr(exc, method_name)()
            if condition:
                return str(condition)
        except (AttributeError, Py4JError, TypeError):
            continue
    return ""


def _java_class_name(exc: Py4JJavaError) -> str:
    try:
        return str(exc.java_exception.getClass().getName())
    except (AttributeError, Py4JError, TypeError):
        return ""
