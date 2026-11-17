"""Валидация Spark SQL через Catalyst без создания SparkSession."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Self

from py4j.protocol import Py4JError
from pyspark.java_gateway import launch_gateway

from .errors import AnalyzerInputError, SparkSqlAnalyzerError
from .errors.translator import translate_error


@dataclass(frozen=True, slots=True)
class _CatalystRuntime:
    gateway: Any
    parser: Any
    analyzer: Any
    tracker_class: Any
    tracker_default: Any


class SparkSqlAnalyzer:
    """Проверяет один SQL-запрос встроенным Catalyst ``SimpleAnalyzer``."""

    def __init__(self, sql: str) -> None:
        self._sql = sql

    def open_jvm(self) -> Self:
        """Запускает JVM gateway и инициализирует компоненты Catalyst один раз."""
        if hasattr(self, "_runtime"):
            return self

        try:
            gateway = launch_gateway()
        except Exception as exc:
            raise translate_error(exc, sql=self._sql) from exc

        try:
            self._initialize_catalyst(gateway)
        except Exception as exc:
            self._close_gateway(gateway)
            raise translate_error(exc, sql=self._sql) from exc
        return self

    def _initialize_catalyst(self, gateway: Any) -> None:
        """Инициализирует компоненты Catalyst для переданного JVM gateway."""
        jvm = gateway.jvm
        parser_class = getattr(
            jvm.org.apache.spark.sql.catalyst.parser,
            "CatalystSqlParser$",
        )
        parser = getattr(parser_class, "MODULE$")

        analyzer_class = getattr(
            jvm.org.apache.spark.sql.catalyst.analysis,
            "SimpleAnalyzer$",
        )
        analyzer = getattr(analyzer_class, "MODULE$")

        tracker_package = jvm.org.apache.spark.sql.catalyst
        tracker_class = tracker_package.QueryPlanningTracker
        tracker_companion_class = getattr(
            tracker_package,
            "QueryPlanningTracker$",
        )
        tracker_companion = getattr(tracker_companion_class, "MODULE$")
        tracker_default = getattr(
            tracker_companion,
            "$lessinit$greater$default$1",
        )()
        self._runtime = _CatalystRuntime(
            gateway=gateway,
            parser=parser,
            analyzer=analyzer,
            tracker_class=tracker_class,
            tracker_default=tracker_default,
        )

    def close_jvm(self) -> None:
        """Закрывает JVM gateway и удаляет runtime-объект Catalyst."""
        try:
            runtime = self._runtime
        except AttributeError:
            return

        del self._runtime
        self._close_gateway(runtime.gateway)

    def _close_gateway(self, gateway: Any) -> None:
        """Освобождает переданный JVM gateway."""
        with suppress(Py4JError, OSError):
            if getattr(gateway, "proc", False):
                gateway.shutdown()
            else:
                gateway.close()

    def validated_sql(self) -> str:
        """Возвращает исходный SQL или выбрасывает типизированную ошибку."""
        self._validate_input()
        if not hasattr(self, "_runtime"):
            raise RuntimeError(
                "JVM gateway не открыт: вызовите open_jvm() перед validated_sql()"
            )

        try:
            logical_plan = self._runtime.parser.parsePlan(self._sql)
            tracker = self._runtime.tracker_class(self._runtime.tracker_default)
            self._runtime.analyzer.executeAndCheck(logical_plan, tracker)
            return self._sql
        except SparkSqlAnalyzerError:
            raise
        except Exception as exc:
            raise translate_error(exc, sql=self._sql) from exc

    def _validate_input(self) -> None:
        """Проверяет вход непосредственно перед анализом SQL."""
        if not isinstance(self._sql, str):
            raise AnalyzerInputError(
                "sql должен быть строкой",
                sql=repr(self._sql),
            )
