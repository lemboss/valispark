"""Проверки анализа SQL через Catalyst с каталогом таблиц."""

import pytest

from src import TablesMetadata, Valispark
from src.errors import (
    AnalyzerInputError,
    SqlSyntaxError,
    TableOrViewNotFoundError,
    UnresolvedColumnError,
)

TABLES: TablesMetadata = {
    "employees": {
        "columns": {
            "id": {"type": "BIGINT", "nullable": False},
            "manager_id": {"type": "BIGINT", "nullable": True},
        }
    },
    "hr.payroll": {
        "columns": {
            "employee_id": {"type": "BIGINT"},
            "salary": {"type": "DECIMAL(12, 2)"},
            "details": {"type": "STRUCT<bonuses: ARRAY<DECIMAL(12, 2)>>"},
        }
    },
}


def test_tables_argument_is_required() -> None:
    with pytest.raises(TypeError, match="tables"):
        Valispark("SELECT 1")


@pytest.mark.parametrize("sql", ["SELECT 1 + 2 AS result", 'SELECT 1 + "1"'])
def test_validated_sql_without_tables(prepare_query, sql: str) -> None:
    analyzer = prepare_query(sql, tables={})

    assert analyzer.validated_sql() == sql


def test_invalidated_sql(prepare_query) -> None:
    sql = "SELECTTTTT 1 + 2 AS result"
    analyzer = prepare_query(sql, tables={})

    with pytest.raises(SqlSyntaxError) as error:
        analyzer.validated_sql()

    assert error.value.error_condition == "PARSE_SYNTAX_ERROR"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT employees.id FROM employees",
        "SELECT hr.payroll.salary + details.bonuses[0] FROM hr.payroll",
        (
            "SELECT e.id, p.salary FROM employees AS e "
            "JOIN hr.payroll AS p ON e.id = p.employee_id"
        ),
        (
            "SELECT e.id, m.id FROM employees AS e "
            "JOIN employees AS m ON e.manager_id = m.id"
        ),
    ],
    ids=["unqualified-table", "schema-table-ddl", "join-with-aliases", "self-join"],
)
def test_validated_sql_with_tables(prepare_query, sql: str) -> None:
    analyzer = prepare_query(sql, tables=TABLES)

    assert analyzer.validated_sql() == sql


def test_unknown_table(prepare_query) -> None:
    analyzer = prepare_query("SELECT * FROM hr.missing", tables=TABLES)

    with pytest.raises(TableOrViewNotFoundError):
        analyzer.validated_sql()


def test_unknown_column(prepare_query) -> None:
    analyzer = prepare_query("SELECT e.missing FROM employees AS e", tables=TABLES)

    with pytest.raises(UnresolvedColumnError):
        analyzer.validated_sql()


def test_analyzers_on_shared_jvm_have_isolated_catalogs(prepare_query) -> None:
    sql = "SELECT id FROM employees"
    first = prepare_query(sql, tables=TABLES)
    second = prepare_query(
        sql, tables={"employees": {"columns": {"name": {"type": "STRING"}}}}
    )

    assert first._runtime.gateway is second._runtime.gateway
    assert first._runtime.catalog is not second._runtime.catalog
    assert first.validated_sql() == sql
    with pytest.raises(UnresolvedColumnError):
        second.validated_sql()


def test_column_resolution_is_case_sensitive(prepare_query) -> None:
    analyzer = prepare_query("SELECT ID FROM employees", tables=TABLES)

    with pytest.raises(UnresolvedColumnError):
        analyzer.validated_sql()


@pytest.mark.parametrize(
    "tables",
    [
        pytest.param(None, id="none"),
        pytest.param([], id="tables-container"),
        pytest.param({"employees": []}, id="table-container"),
        pytest.param({"employees": {}}, id="missing-columns"),
        pytest.param(
            {"employees": {**TABLES["employees"], "extra": True}}, id="table-key"
        ),
        pytest.param({"employees": {"columns": []}}, id="columns-container"),
        pytest.param(
            {"employees": {"columns": {"id": "BIGINT"}}}, id="column-container"
        ),
        pytest.param({"employees": {"columns": {"id": {}}}}, id="missing-type"),
        pytest.param(
            {"employees": {"columns": {"id": {"type": "BIGINT", "extra": True}}}},
            id="column-key",
        ),
        pytest.param(
            {"employees": {"columns": {"id": {"type": "BIGINT", "nullable": 1}}}},
            id="nullable-type",
        ),
        pytest.param({"employees": {"columns": {"id": {"type": 1}}}}, id="type-value"),
        pytest.param(
            {"catalog.hr.employees": TABLES["employees"]},
            id="three-part-table-name",
        ),
        pytest.param(
            {
                "employees": TABLES["employees"],
                "default.employees": TABLES["employees"],
            },
            id="duplicate-normalized-table-name",
        ),
        pytest.param(
            {"employees": {"columns": {"id": {"type": "NOT_A_SPARK_TYPE"}}}},
            id="invalid-ddl",
        ),
    ],
)
def test_invalid_tables_metadata(prepare_query, tables: TablesMetadata) -> None:
    with pytest.raises(AnalyzerInputError):
        prepare_query("SELECT 1", tables=tables).validated_sql()
