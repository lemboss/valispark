# Spark SQL Validator

[Русский](#русский) | [English](#english)

## Русский

Валидация Spark SQL и ссылок на таблицы через Catalyst без создания
`SparkSession` и без выполнения запроса.

Анализатор запускает локальную JVM через Py4J. Стандартный Catalyst
`Analyzer` с `CatalogManager` разрешает имена таблиц и проверяет логический
план. V2-каталог доступен только для чтения и предоставляет только схемы
таблиц.

```text
SQL
 ↓
CatalystSqlParser.parsePlan
 ↓
LogicalPlan
 ↓
Analyzer(CatalogManager).executeAndCheck
```

Проверка завершается на этапе анализа. Данные не читаются, оптимизатор
не запускается, физический план не строится и Spark job не стартует.

### Требования

- Python 3.12;
- Java, совместимая с PySpark 3.5;
- `uv`.

Установка зависимостей:

```bash
uv sync --dev
```

### Использование

Конструктор `Valispark(sql, *, tables: TablesMetadata)` требует
именованный аргумент `tables`. Для запросов без `FROM` можно передать
`tables={}`.

`Valispark` имеет три публичных метода:

- `prepare_query()` запускает JVM и инициализирует компоненты Catalyst для запроса;
- `validated_sql()`;
- `close_jvm()`.

```python
from src import Valispark

sql = "SELECT 1 + 2 AS result"
analyzer = Valispark(sql, tables={})

analyzer.prepare_query()
try:
    validated_sql = analyzer.validated_sql()
finally:
    analyzer.close_jvm()

assert validated_sql == sql
```

Метаданные передаются обычными словарями. Публичный тип `TablesMetadata`
сопоставляет имена таблиц в формате `table` или `schema.table` с записями
`TableMetadata`. В каждой записи `columns` сопоставляет имена колонок с их
`ColumnMetadata`, где `type` задаётся строкой Spark DDL, а необязательное
поле `nullable` принимает `bool`. Типы `TableMetadata` и `ColumnMetadata`
объявлены как `TypedDict`. Все три типа доступны из `src`.

```python
from src import TablesMetadata, Valispark

tables: TablesMetadata = {
    "sales.orders": {
        "columns": {
            "order_id": {"type": "BIGINT", "nullable": False},
            "amount": {"type": "DECIMAL(12,2)"},
        },
    },
}
sql = "SELECT SUM(amount) FROM sales.orders"
analyzer = Valispark(sql, tables=tables)
analyzer.prepare_query()
try:
    assert analyzer.validated_sql() == sql
finally:
    analyzer.close_jvm()
```

`validated_sql()` возвращает исходную строку без изменений. При ошибке метод
выбрасывает типизированное исключение.

```python
from src import Valispark
from src.errors import SqlSyntaxError

analyzer = Valispark("SELECTTT 1", tables={})
analyzer.prepare_query()

try:
    analyzer.validated_sql()
except SqlSyntaxError as error:
    assert error.error_condition == "PARSE_SYNTAX_ERROR"
finally:
    analyzer.close_jvm()
```

### Ошибки

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

### Ограничения

- Имена в формате `catalog.schema.table` и работа с несколькими каталогами
  не поддерживаются.
- Действуют правила неявного преобразования типов Spark. Например,
  `1 + "1"` проходит анализ, поскольку Spark приводит строку к числовому
  типу.
- Проверка охватывает разбор и анализ SQL. Ошибки, зависящие от данных или
  возникающие при выполнении, остаются за рамками проверки.

### Структура

```text
.
├── src/
│   ├── errors/
│   │   ├── base.py
│   │   ├── runtime.py
│   │   ├── sql.py
│   │   └── translator.py
│   ├── catalog.py
│   ├── metadata.py
│   ├── types.py
│   └── valispark.py
└── tests/
    ├── conftest.py
    ├── test_metadata.py
    └── test_validated_sql.py
```

### Тесты

```bash
uv run pytest -q
```

### Форматирование

```bash
uv run ruff check src tests
uv run black --check src tests
uv run isort --check-only src tests
```

## English

Validate Spark SQL and table references through Catalyst without creating a
`SparkSession` or executing the query.

The validator starts a local JVM through Py4J. Catalyst's standard
`Analyzer` uses `CatalogManager` to resolve table names and check the logical
plan. The V2 catalog is read-only and provides only table schemas.

```text
SQL
 ↓
CatalystSqlParser.parsePlan
 ↓
LogicalPlan
 ↓
Analyzer(CatalogManager).executeAndCheck
```

Validation ends at the analysis stage. It reads no data, runs no optimizer,
builds no physical plan, and starts no Spark job.

### Requirements

- Python 3.12
- Java compatible with PySpark 3.5
- `uv`

Install the dependencies with the following command.

```bash
uv sync --dev
```

### Usage

The `Valispark(sql, *, tables: TablesMetadata)` constructor requires the
`tables` keyword argument. For queries without a `FROM` clause, pass
`tables={}`.

`Valispark` exposes three public methods.

- `prepare_query()` starts the JVM and initializes the Catalyst components for the query.
- `validated_sql()`
- `close_jvm()`

```python
from src import Valispark

sql = "SELECT 1 + 2 AS result"
analyzer = Valispark(sql, tables={})

analyzer.prepare_query()
try:
    validated_sql = analyzer.validated_sql()
finally:
    analyzer.close_jvm()

assert validated_sql == sql
```

Pass metadata as regular dictionaries. The public `TablesMetadata` type maps
table names in the form `table` or `schema.table` to `TableMetadata` entries.
In each entry, `columns` maps column names to their `ColumnMetadata`, where
`type` is a Spark DDL string and the optional `nullable` field accepts a
`bool`. Both `TableMetadata` and `ColumnMetadata` are declared as
`TypedDict` types. All three types are available from `src`.

```python
from src import TablesMetadata, Valispark

tables: TablesMetadata = {
    "sales.orders": {
        "columns": {
            "order_id": {"type": "BIGINT", "nullable": False},
            "amount": {"type": "DECIMAL(12,2)"},
        },
    },
}
sql = "SELECT SUM(amount) FROM sales.orders"
analyzer = Valispark(sql, tables=tables)
analyzer.prepare_query()
try:
    assert analyzer.validated_sql() == sql
finally:
    analyzer.close_jvm()
```

`validated_sql()` returns the original string unchanged. If validation fails,
the method raises a typed exception.

```python
from src import Valispark
from src.errors import SqlSyntaxError

analyzer = Valispark("SELECTTT 1", tables={})
analyzer.prepare_query()

try:
    analyzer.validated_sql()
except SqlSyntaxError as error:
    assert error.error_condition == "PARSE_SYNTAX_ERROR"
finally:
    analyzer.close_jvm()
```

### Errors

Public error classes are available from `src.errors`.

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

Each error object has three fields.

- `message` is the error text with ANSI formatting removed.
- `sql` is the SQL being validated.
- `error_condition` is the Spark error condition.

### Limitations

- Names in the form `catalog.schema.table` and use of multiple catalogs
  are unsupported.
- Spark's implicit type coercion rules apply. For example, `1 + "1"` passes
  analysis because Spark coerces the string to a numeric type.
- Validation covers SQL parsing and analysis. Data-dependent errors and
  errors that occur during execution are outside the scope of validation.

### Project structure

```text
.
├── src/
│   ├── errors/
│   │   ├── base.py
│   │   ├── runtime.py
│   │   ├── sql.py
│   │   └── translator.py
│   ├── catalog.py
│   ├── metadata.py
│   ├── types.py
│   └── valispark.py
└── tests/
    ├── conftest.py
    ├── test_metadata.py
    └── test_validated_sql.py
```

### Tests

```bash
uv run pytest -q
```

### Formatting

```bash
uv run ruff check src tests
uv run black --check src tests
uv run isort --check-only src tests
```
