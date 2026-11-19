"""Проверки валидации входных данных без JVM."""

from typing import cast

import pytest

from src.errors import AnalyzerInputError
from src.metadata import _MetadataValidator
from src.types import TablesMetadata


def test_valid_metadata_preserves_optional_nullable() -> None:
    validator = _MetadataValidator("SELECT * FROM t")
    tables: TablesMetadata = {
        "t": {
            "columns": {
                "id": {"type": " INT ", "nullable": False},
                "name": {"type": "STRING"},
                "notes": {"type": "STRING", "nullable": True},
            }
        },
        "empty": {"columns": {}},
    }

    assert validator.validate_tables({}) == {}
    validated = validator.validate_tables(tables)
    assert validated == tables
    assert list(validated["t"]["columns"]) == ["id", "name", "notes"]
    assert "nullable" not in validated["t"]["columns"]["name"]
    assert validator.validate_sql() is None


def test_validated_metadata_is_independent_of_input() -> None:
    tables: TablesMetadata = {
        "t": {"columns": {"id": {"type": "INT", "nullable": False}}}
    }
    validated = _MetadataValidator("SELECT * FROM t").validate_tables(tables)

    tables["t"]["columns"]["id"]["nullable"] = True
    tables["t"]["columns"]["name"] = {"type": "STRING"}
    tables["t"]["columns"] = {}
    tables.clear()

    assert validated == {"t": {"columns": {"id": {"type": "INT", "nullable": False}}}}


@pytest.mark.parametrize(
    ("tables", "message"),
    [
        ([], "tables должен быть словарём"),
        ({"": {"columns": {}}}, "Имя таблицы должно быть непустой строкой"),
        ({1: {"columns": {}}}, "Имя таблицы должно быть непустой строкой"),
        ({"t": []}, "Описание таблицы 't' должно содержать словарь columns"),
        ({"t": {}}, "Описание таблицы 't' должно содержать словарь columns"),
        (
            {"t": {"columns": []}},
            "Описание таблицы 't' должно содержать словарь columns",
        ),
        (
            {"t": {"columns": {}, "extra": True}},
            "Описание таблицы 't' должно содержать словарь columns",
        ),
        (
            {"t": {"columns": {"": {"type": "INT"}}}},
            "Имя столбца таблицы 't' должно быть непустой строкой",
        ),
        (
            {"t": {"columns": {1: {"type": "INT"}}}},
            "Имя столбца таблицы 't' должно быть непустой строкой",
        ),
    ],
)
def test_invalid_table_metadata(tables: object, message: str) -> None:
    sql = "SELECT * FROM t"
    with pytest.raises(AnalyzerInputError) as error:
        _MetadataValidator(sql).validate_tables(cast(TablesMetadata, tables))

    assert str(error.value) == message
    assert error.value.sql == sql


@pytest.mark.parametrize(
    "column",
    [
        "INT",
        {},
        {"type": 1},
        {"type": ""},
        {"type": "  "},
        {"type": "INT", "extra": True},
        {"type": "INT", "nullable": 1},
        {"type": "INT", "nullable": None},
    ],
)
def test_invalid_column_metadata(column: object) -> None:
    sql = "SELECT id FROM t"
    tables = cast(TablesMetadata, {"t": {"columns": {"id": column}}})
    with pytest.raises(AnalyzerInputError) as error:
        _MetadataValidator(sql).validate_tables(tables)

    assert str(error.value) == "Некорректное описание столбца 'id' таблицы 't'"
    assert error.value.sql == sql


@pytest.mark.parametrize("sql", [None, 123, b"SELECT 1"])
def test_invalid_sql_is_checked_on_request(sql: object) -> None:
    validator = _MetadataValidator(cast(str, sql))
    assert validator.validate_tables({}) == {}

    with pytest.raises(AnalyzerInputError) as error:
        validator.validate_sql()

    assert str(error.value) == "sql должен быть строкой"
    assert error.value.sql == repr(sql)
