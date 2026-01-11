# Quickstart: Pandas Table Functions

This guide shows how to use the pandas-based table functions in `bioimage-mcp`.

## 1. Load a CSV Table
First, load your measurement file into a `TableRef`.

```python
# Tool: base.io.table.load
inputs = {"path": "/data/measurements.csv"}
params = {"delimiter": ","}
# Returns: TableRef (uri: "file:///data/measurements.csv", ...)
```

## 2. Filter with `query()`
Filter the data to keep only large objects.

```python
# Tool: base.pandas.DataFrame.query (accepts TableRef directly)
inputs = {"df": table_ref}
params = {"expr": "area > 500"}
# Returns: ObjectRef (filtered DataFrame)

# Optional: explicitly convert first
# Tool: base.pandas.DataFrame
# inputs = {"table": table_ref}
# Returns: ObjectRef (uri: "obj://pandas.DataFrame/...", ...)
```

## 3. GroupBy and Aggregate
Calculate the average intensity per label class.

```python
# Tool: base.pandas.DataFrame.groupby
inputs = {"df": filtered_df_ref}
params = {"by": "class_name"}
# Returns: GroupByRef

# Tool: base.pandas.GroupBy.mean
inputs = {"grouped": groupby_ref}
# Returns: ObjectRef (aggregated DataFrame)
```

## 4. Export Results
Save the final summary to a CSV (or TSV) file for downstream tools.

```python
# Tool: base.io.table.export
inputs = {"data": agg_df_ref}
params = {
    "dest_path": "/results/summary.csv",
    "sep": ","
}
# Returns: TableRef
```

## Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `PANDAS_INVALID_QUERY` | Syntax error in `query()` string. | Check column names and operators. |
| `PANDAS_MISSING_COLUMN` | Column referenced in `on` or `by` not found. | Verify column names in `TableRef` metadata. |
| `OBJECT_NOT_FOUND` | `ObjectRef` ID not found in cache. | Ensure the session is still active. |
| `IO_FORMAT_UNSUPPORTED` | File format not recognized. | Use `.csv` or `.tsv` (delimited). |
