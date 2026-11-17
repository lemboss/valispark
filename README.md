# Spark SQL Validator

Валидация Spark SQL через Catalyst `SimpleAnalyzer` без создания
`SparkSession` и без выполнения запроса.

Анализатор запускает локальную JVM через Py4J и выполняет только построение и
проверку логического плана:

```text
SQL
 ↓
CatalystSqlParser.parsePlan
 ↓
LogicalPlan
 ↓
SimpleAnalyzer.executeAndCheck
```

Физический план и Spark job не создаются, данные не читаются.

## Требования

- Python 3.12;
- Java, совместимая с PySpark 3.5;
- `uv`.

Установка зависимостей:

```bash
uv sync --dev
```

## Использование

`SparkSqlAnalyzer` имеет три публичных метода:

- `open_jvm()`;
- `validated_sql()`;
- `close_jvm()`.

```python
from src import SparkSqlAnalyzer

sql = "SELECT 1 + 2 AS result"
analyzer = SparkSqlAnalyzer(sql)

analyzer.open_jvm()
try:
    validated_sql = analyzer.validated_sql()
finally:
    analyzer.close_jvm()

assert validated_sql == sql
```

`validated_sql()` возвращает исходную строку без изменений. При ошибке метод
выбрасывает типизированное исключение.

```python
from src import SparkSqlAnalyzer
from src.errors import SqlSyntaxError

analyzer = SparkSqlAnalyzer("SELECTTT 1")
analyzer.open_jvm()

try:
    analyzer.validated_sql()
except SqlSyntaxError as error:
    assert error.error_condition == "PARSE_SYNTAX_ERROR"
finally:
    analyzer.close_jvm()
```

## Ошибки

Публичные ошибки находятся в `src.errors`:

```python
from src.errors import (
    AmbiguousReferenceError,
    DataTypeMismatchError,
    MissingAggregationError,
    MissingGroupByError,
    SqlSyntaxError,
    TableOrViewNotFoundError,
    UnresolvedColumnError,
    WrongNumberOfArgumentsError,
)
```

Объект ошибки содержит:

- `message` — текст ошибки без ANSI-разметки;
- `sql` — проверяемый SQL;
- `error_condition` — Spark error condition.

## Ограничения

- `SparkSession` и Spark Catalog не создаются.
- Анализатор не принимает метаданные физических таблиц.
- Запросы к таблицам завершаются `TABLE_OR_VIEW_NOT_FOUND`, потому что
  `SimpleAnalyzer` не знает их схемы.
- Полноценная проверка колонок, `JOIN` и агрегаций с физическими таблицами
  требует отдельного Catalyst catalog или JVM-helper с `LocalRelation`.
- Неизвестная функция может привести к `CatalystUnsupportedOperationError`
  из-за ограничений `SimpleAnalyzer` и его `FakeV2SessionCatalog`.

## Структура

```text
.
├── src/
│   ├── errors/
│   │   ├── base.py
│   │   ├── runtime.py
│   │   ├── sql.py
│   │   └── translator.py
│   └── spark_sql_analyzer.py
└── tests/
    ├── conftest.py
    └── test_validated_sql.py
```

## TODO

Добавить тесты на:

1. обычную таблицу;
2. schema-qualified имя;
3. алиасы;
4. несколько таблиц;
5. `JOIN`;
6. self-join;
7. неоднозначные колонки;
8. сложные типы `ARRAY`, `MAP`, `STRUCT`;
9. повторяющиеся таблицы в разных схемах;
10. CTE с именем, совпадающим с физической таблицей;
11. вложенные подзапросы.

## Тесты

```bash
uv run pytest -q
```

## Форматирование

```bash
uv run ruff check src tests
uv run black --check src tests
uv run isort --check-only src tests
```
