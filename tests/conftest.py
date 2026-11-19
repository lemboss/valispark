"""Общие pytest fixtures."""

from collections.abc import Iterator
from typing import Any, Protocol

import pytest
from pyspark.java_gateway import launch_gateway

from src import TablesMetadata, Valispark
from src.valispark import _close_gateway


class AnalyzerFactory(Protocol):
    def __call__(self, sql: str, *, tables: TablesMetadata) -> Valispark: ...


@pytest.fixture(scope="session")
def jvm() -> Iterator[Any]:
    """Запускает один JVM gateway для тестовой сессии."""
    gateway = launch_gateway()
    try:
        yield gateway
    finally:
        _close_gateway(gateway)


@pytest.fixture
def prepare_query(jvm: Any) -> Iterator[AnalyzerFactory]:
    """Создаёт анализатор с отдельным каталогом на общей JVM."""
    analyzers: list[Valispark] = []

    def prepare_analyzer(sql: str, *, tables: TablesMetadata) -> Valispark:
        analyzer = Valispark(sql, tables=tables)
        analyzers.append(analyzer)
        return analyzer._prepare_with_gateway(jvm)

    try:
        yield prepare_analyzer
    finally:
        for analyzer in reversed(analyzers):
            analyzer.close_jvm()
