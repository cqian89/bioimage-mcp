# Data Model: Pandas Table Artifacts

## 1. TableRef
Represents a file-backed tabular dataset.

```json
{
  "type": "TableRef",
  "uri": "file:///path/to/table.csv",
  "format": "csv",
  "columns": ["id", "area", "intensity", "label"],
  "row_count": 1250,
  "delimiter": ",",
  "schema_id": "bioimage.schema.measurements.v1"
}
```

- **format**: `csv`, `tsv`.
- **columns**: List of string column names for quick discovery without reading the file.
- **row_count**: Optional integer.
- **delimiter**: Required if format is `csv` or `tsv`.

## 2. ObjectRef (Pandas DataFrame)
Represents an in-memory pandas DataFrame held in the tool's `OBJECT_CACHE`.

```json
{
  "type": "ObjectRef",
  "uri": "obj://pandas.DataFrame/uuid-1234",
  "python_class": "pandas.core.frame.DataFrame",
  "storage_type": "memory",
  "metadata": {
    "columns": ["id", "area"],
    "shape": [1250, 2]
  }
}
```

## 3. GroupByRef
A specialized `ObjectRef` representing the result of a `groupby` operation.

```json
{
  "type": "GroupByRef",
  "uri": "obj://pandas.core.groupby.DataFrameGroupBy/uuid-5678",
  "python_class": "pandas.core.groupby.generic.DataFrameGroupBy",
  "storage_type": "memory",
  "metadata": {
    "grouped_by": ["label"],
    "groups_count": 5
  }
}
```

## 4. Column Metadata Schema
Used for describing individual columns in a `TableRef` or `ObjectRef`.

| Field | Type | Description |
|-------|------|-------------|
| name | string | The column header |
| dtype | string | Pandas dtype (e.g., `int64`, `float64`, `category`) |
| unit | string | (Optional) Physical units (e.g., `um^2`) |
| description | string | (Optional) Human-readable explanation |
