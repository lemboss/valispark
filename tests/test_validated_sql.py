"""Минимальная проверка SQL через Catalyst."""

import pytest

from src.errors import SqlSyntaxError


def test_validated_sql(open_jvm) -> None:
    sql = "SELECT 1 + 2 AS result"
    analyzer = open_jvm(sql)

    assert analyzer.validated_sql() == sql


def test_invalidated_sql(open_jvm) -> None:
    sql = "SELECTTTTT 1 + 2 AS result"
    analyzer = open_jvm(sql)

    with pytest.raises(SqlSyntaxError) as error:
        analyzer.validated_sql()

    assert error.value.error_condition == "PARSE_SYNTAX_ERROR"
