"""Публичные исключения Spark SQL-анализатора."""

from .base import SparkSqlAnalyzerError
from .runtime import (
    AnalyzerInputError,
    CatalystIllegalArgumentError,
    CatalystRuntimeError,
    CatalystUnsupportedOperationError,
    Py4JConnectionError,
    Py4JInvocationError,
    Py4JJavaInvocationError,
    SparkEngineError,
    UnexpectedAnalyzerError,
)
from .sql import (
    AmbiguousReferenceError,
    DataTypeMismatchError,
    MissingAggregationError,
    MissingGroupByError,
    SqlSyntaxError,
    SqlValidationError,
    StructFieldNotFoundError,
    TableOrViewNotFoundError,
    UnresolvedColumnError,
    UnresolvedRoutineError,
    WrongNumberOfArgumentsError,
)

__all__ = [
    "AmbiguousReferenceError",
    "AnalyzerInputError",
    "CatalystIllegalArgumentError",
    "CatalystRuntimeError",
    "CatalystUnsupportedOperationError",
    "DataTypeMismatchError",
    "MissingAggregationError",
    "MissingGroupByError",
    "Py4JConnectionError",
    "Py4JInvocationError",
    "Py4JJavaInvocationError",
    "SparkEngineError",
    "SparkSqlAnalyzerError",
    "SqlSyntaxError",
    "SqlValidationError",
    "StructFieldNotFoundError",
    "TableOrViewNotFoundError",
    "UnexpectedAnalyzerError",
    "UnresolvedColumnError",
    "UnresolvedRoutineError",
    "WrongNumberOfArgumentsError",
]
