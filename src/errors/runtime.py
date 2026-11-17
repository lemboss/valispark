"""Исключения входных данных, Catalyst, Spark и Py4J."""

from .base import SparkSqlAnalyzerError


class AnalyzerInputError(SparkSqlAnalyzerError):
    """В анализатор переданы некорректные Python-аргументы."""


class CatalystIllegalArgumentError(SparkSqlAnalyzerError):
    """JVM вернула ``IllegalArgumentException``."""


class CatalystUnsupportedOperationError(SparkSqlAnalyzerError):
    """JVM вернула ``UnsupportedOperationException``."""


class CatalystRuntimeError(SparkSqlAnalyzerError):
    """JVM вернула ``SparkRuntimeException``."""


class SparkEngineError(SparkSqlAnalyzerError):
    """JVM вернула ``SparkException``."""


class Py4JJavaInvocationError(SparkSqlAnalyzerError):
    """Py4J передал необработанное исключение JVM."""


class Py4JInvocationError(SparkSqlAnalyzerError):
    """Py4J не смог вызвать JVM API."""


class Py4JConnectionError(Py4JInvocationError):
    """Связь между Python и JVM нарушена."""


class UnexpectedAnalyzerError(SparkSqlAnalyzerError):
    """Непредвиденная ошибка реализации анализатора."""
