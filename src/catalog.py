"""Каталог схем таблиц для разрешения имён в Catalyst."""

from typing import Any

from py4j.java_gateway import is_instance_of
from py4j.protocol import Py4JJavaError
from pyspark.errors import ParseException

from .errors import AnalyzerInputError
from .types import TablesMetadata

_DEFAULT_NAMESPACE = "default"


class _SchemaTable:
    """Представляет schema-only таблицу через JVM-интерфейс Spark Table."""

    class Java:
        implements = ("org.apache.spark.sql.connector.catalog.Table",)

    def __init__(self, gateway: Any, name: str, schema: Any) -> None:
        jvm = gateway.jvm
        self._gateway = gateway
        self._name = name
        self._schema = schema
        catalog = jvm.org.apache.spark.sql.connector.catalog
        self._columns = catalog.CatalogV2Util.structTypeToV2Columns(schema)
        self._partitioning = gateway.new_array(
            jvm.org.apache.spark.sql.connector.expressions.Transform, 0
        )
        self._properties = jvm.java.util.Collections.emptyMap()
        self._capabilities = jvm.java.util.Collections.emptySet()

    def name(self) -> str:
        return self._name

    def schema(self) -> Any:
        return self._schema

    # Py4J передаёт Python и вызовы default-методов интерфейса.
    def columns(self) -> Any:
        return self._columns

    def partitioning(self) -> Any:
        return self._partitioning

    def properties(self) -> Any:
        return self._properties

    def capabilities(self) -> Any:
        return self._capabilities

    # Catalyst сравнивает V2-отношения при разрешении повторных ссылок на таблицу.
    def equals(self, other: Any) -> bool:
        return (
            other is not None
            and is_instance_of(self._gateway, other, self.Java.implements[0])
            and self._name == other.name()
            and bool(self._schema.equals(other.schema()))
        )

    def hashCode(self) -> int:
        return hash(self._name) & 0x7FFFFFFF

    def toString(self) -> str:
        return self._name


class _SchemaCatalog:
    """Предоставляет Catalyst read-only V2-каталог переданных схем."""

    class Java:
        implements = ("org.apache.spark.sql.connector.catalog.TableCatalog",)

    def __init__(
        self, gateway: Any, tables: dict[tuple[str, str], _SchemaTable]
    ) -> None:
        jvm = gateway.jvm
        self._gateway = gateway
        self._tables = tables
        self._catalog_package = jvm.org.apache.spark.sql.connector.catalog
        self._catalog_name = self._catalog_package.CatalogManager.SESSION_CATALOG_NAME()
        self._namespace = gateway.new_array(jvm.java.lang.String, 1)
        self._namespace[0] = _DEFAULT_NAMESPACE
        self._capabilities = jvm.java.util.Collections.emptySet()

    def name(self) -> str:
        return self._catalog_name

    def defaultNamespace(self) -> Any:
        return self._namespace

    def initialize(self, name: str, options: Any) -> None:
        pass

    def capabilities(self) -> Any:
        return self._capabilities

    def listTables(self, namespace: Any) -> Any:
        identifier = self._catalog_package.Identifier
        namespace_key = tuple(namespace)
        names = [name for schema, name in self._tables if (schema,) == namespace_key]
        result = self._gateway.new_array(identifier, len(names))
        for index, name in enumerate(names):
            result[index] = identifier.of(namespace, name)
        return result

    def loadTable(self, identifier: Any, *options: Any) -> _SchemaTable | None:
        namespace = identifier.namespace()
        if len(namespace) != 1:
            return None
        return self._tables.get((namespace[0], identifier.name()))

    def tableExists(self, identifier: Any) -> bool:
        return self.loadTable(identifier) is not None

    def invalidateTable(self, identifier: Any) -> None:
        pass

    def useNullableQuerySchema(self) -> bool:
        return True

    def _reject_write(self, *args: Any) -> None:
        raise NotImplementedError("Каталог доступен только для чтения")

    createTable = _reject_write
    alterTable = _reject_write
    dropTable = _reject_write
    purgeTable = _reject_write
    renameTable = _reject_write


class _SchemaCatalogBuilder:
    """Преобразует проверенные метаданные в JVM-таблицы и V2-каталог."""

    def __init__(self, gateway: Any, parser: Any, sql: str) -> None:
        self._gateway = gateway
        self._parser = parser
        self._sql = sql

    def build(self, tables: TablesMetadata) -> _SchemaCatalog:
        gateway = self._gateway
        types = gateway.jvm.org.apache.spark.sql.types
        schema_tables: dict[tuple[str, str], _SchemaTable] = {}
        for table_name, table in tables.items():
            try:
                parts = self._parser.parseMultipartIdentifier(table_name)
            except (ParseException, Py4JJavaError) as exc:
                raise self._input_error(
                    f"Некорректное имя таблицы {table_name!r}"
                ) from exc
            if parts.size() == 1:
                key = (_DEFAULT_NAMESPACE, parts.apply(0))
            elif parts.size() == 2:
                key = (parts.apply(0), parts.apply(1))
            else:
                raise self._input_error(
                    f"Имя таблицы {table_name!r} должно иметь вид table или schema.table"
                )
            if key in schema_tables:
                raise self._input_error(f"Повторяющееся имя таблицы {table_name!r}")

            fields = gateway.jvm.java.util.ArrayList()
            for name, column in table["columns"].items():
                try:
                    data_type = types.DataType.fromDDL(column["type"])
                except (ParseException, Py4JJavaError) as exc:
                    raise self._input_error(
                        f"Некорректный тип столбца {name!r} таблицы {table_name!r}: "
                        f"{column['type']!r}"
                    ) from exc
                fields.add(
                    types.DataTypes.createStructField(
                        name, data_type, column.get("nullable", True)
                    )
                )
            schema = types.DataTypes.createStructType(fields)
            schema_tables[key] = _SchemaTable(gateway, table_name, schema)
        return _SchemaCatalog(gateway, schema_tables)

    def _input_error(self, message: str) -> AnalyzerInputError:
        sql = self._sql if isinstance(self._sql, str) else repr(self._sql)
        return AnalyzerInputError(message, sql=sql)
