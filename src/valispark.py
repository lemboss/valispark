"""Валидация Spark SQL через Catalyst без создания SparkSession."""

from contextlib import suppress
from dataclasses import dataclass
from subprocess import TimeoutExpired
from typing import Any, Self

from py4j.protocol import Py4JError
from pyspark.java_gateway import ensure_callback_server_started, launch_gateway

from .catalog import _SchemaCatalog, _SchemaCatalogBuilder
from .errors import SparkSqlAnalyzerError
from .errors.translator import translate_error
from .metadata import _MetadataValidator
from .types import TablesMetadata


def _close_gateway(gateway: Any) -> None:
    """Освобождает переданный JVM gateway."""
    process = gateway.proc
    with suppress(Py4JError, OSError):
        if process is not None:
            gateway.shutdown()
        else:
            gateway.close()
    if process is not None and process.stdin is not None:
        # PythonGatewayServer завершает JVM после EOF на stdin.
        with suppress(OSError):
            process.stdin.close()
        with suppress(OSError, TimeoutExpired):
            process.wait(timeout=5)


@dataclass(frozen=True, slots=True)
class _CatalystRuntime:
    """Удерживает JVM-компоненты и Py4J-каталог одного анализатора."""

    gateway: Any
    owns_gateway: bool
    parser: Any
    analyzer: Any
    tracker_class: Any
    tracker_default: Any
    catalog: _SchemaCatalog


class Valispark:
    """Проверяет один SQL-запрос через Catalyst с переданными схемами таблиц."""

    def __init__(self, sql: str, *, tables: TablesMetadata) -> None:
        self._sql = sql
        self._validator = _MetadataValidator(sql)
        self._tables = self._validator.validate_tables(tables)

    def prepare_query(self) -> Self:
        """Запускает JVM gateway и инициализирует компоненты Catalyst один раз."""
        if hasattr(self, "_runtime"):
            return self

        try:
            gateway = launch_gateway()
        except Exception as exc:
            raise translate_error(exc, sql=self._sql) from exc

        return self._prepare_with_gateway(gateway, owns_gateway=True)

    def _prepare_with_gateway(
        self, gateway: Any, *, owns_gateway: bool = False
    ) -> Self:
        """Открывает отдельный каталог Catalyst на переданном gateway."""
        if hasattr(self, "_runtime"):
            return self

        try:
            self._initialize_catalyst(gateway, owns_gateway=owns_gateway)
        except SparkSqlAnalyzerError:
            if owns_gateway:
                _close_gateway(gateway)
            raise
        except Exception as exc:
            if owns_gateway:
                _close_gateway(gateway)
            raise translate_error(exc, sql=self._sql) from exc
        return self

    def _initialize_catalyst(self, gateway: Any, *, owns_gateway: bool) -> None:
        """Инициализирует компоненты Catalyst для переданного JVM gateway."""
        jvm = gateway.jvm
        parser_class = getattr(
            jvm.org.apache.spark.sql.catalyst.parser,
            "CatalystSqlParser$",
        )
        parser = getattr(parser_class, "MODULE$")

        catalog = _SchemaCatalogBuilder(gateway, parser, self._sql).build(self._tables)
        ensure_callback_server_started(gateway)

        spark_sql = jvm.org.apache.spark.sql
        catalyst = spark_sql.catalyst
        session_catalog = catalyst.catalog.SessionCatalog(
            catalyst.catalog.InMemoryCatalog(
                jvm.org.apache.spark.SparkConf(False),
                jvm.org.apache.hadoop.conf.Configuration(),
            ),
            catalyst.analysis.FunctionRegistry.builtin().clone(),
            catalyst.analysis.TableFunctionRegistry.builtin().clone(),
        )
        analyzer = catalyst.analysis.Analyzer(
            spark_sql.connector.catalog.CatalogManager(catalog, session_catalog)
        )

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
            owns_gateway=owns_gateway,
            parser=parser,
            analyzer=analyzer,
            tracker_class=tracker_class,
            tracker_default=tracker_default,
            catalog=catalog,
        )

    def close_jvm(self) -> None:
        """Удаляет runtime Catalyst и закрывает принадлежащий ему JVM gateway."""
        try:
            runtime = self._runtime
        except AttributeError:
            return

        del self._runtime
        if runtime.owns_gateway:
            _close_gateway(runtime.gateway)

    def validated_sql(self) -> str:
        """Возвращает исходный SQL или выбрасывает типизированную ошибку."""
        self._validator.validate_sql()
        if not hasattr(self, "_runtime"):
            raise RuntimeError(
                "JVM gateway не открыт: вызовите prepare_query() перед validated_sql()"
            )

        try:
            # Без SparkSession Catalyst использует SQLConf текущего JVM-потока.
            sql_conf = self._runtime.gateway.jvm.org.apache.spark.sql.internal.SQLConf
            sql_conf.get().setConfString("spark.sql.caseSensitive", "true")
            logical_plan = self._runtime.parser.parsePlan(self._sql)
            tracker = self._runtime.tracker_class(self._runtime.tracker_default)
            self._runtime.analyzer.executeAndCheck(logical_plan, tracker)
            return self._sql
        except SparkSqlAnalyzerError:
            raise
        except Exception as exc:
            raise translate_error(exc, sql=self._sql) from exc
