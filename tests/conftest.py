"""Общие pytest fixtures."""

from collections.abc import Callable, Iterator

import pytest

from src import SparkSqlAnalyzer

AnalyzerFactory = Callable[[str], SparkSqlAnalyzer]


@pytest.fixture
def open_jvm() -> Iterator[AnalyzerFactory]:
    """Создаёт анализатор с открытой JVM и закрывает его после теста."""
    analyzers: list[SparkSqlAnalyzer] = []

    def open_analyzer(sql: str) -> SparkSqlAnalyzer:
        analyzer = SparkSqlAnalyzer(sql)
        analyzer.open_jvm()
        analyzers.append(analyzer)
        return analyzer

    yield open_analyzer

    for analyzer in reversed(analyzers):
        analyzer.close_jvm()
