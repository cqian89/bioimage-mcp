import sqlite3

def setup_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE functions(
            fn_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            tags_json TEXT
        )
    """)
    
    data = [
        ("f1", "Cell Segmenter", "Segments cells in images", '["segmentation", "cell", "microscopy"]'),
        ("f2", "Image Filter", "Gaussian blur filter", '["filter", "processing"]'),
        ("f3", "Nuclei Counter", "Counts nuclei in cell images", '["nuclei", "counting", "analysis"]'),
        ("f4", "Cell Tracking", "Tracks cells over time", '["tracking", "time-lapse"]'),
        ("f5", "Nothing", "Irrelevant tool", '[]'),
    ]
    
    conn.executemany("INSERT INTO functions VALUES (?, ?, ?, ?)", data)
    return conn

def search(conn, keywords):
    W_NAME = 3
    W_DESC = 2
    W_TAG = 1
    
    score_parts = []
    coverage_parts = []
    
    # We need separate param lists to match SQL structure
    score_params = []
    coverage_params = []
    
    for kw in keywords:
        term = f"%{kw}%"
        
        # Score Logic
        s_name = f"(CASE WHEN name LIKE ? THEN {W_NAME} ELSE 0 END)"
        s_desc = f"(CASE WHEN description LIKE ? THEN {W_DESC} ELSE 0 END)"
        s_tags = f"(CASE WHEN tags_json LIKE ? THEN {W_TAG} ELSE 0 END)"
        
        score_parts.append(f"({s_name} + {s_desc} + {s_tags})")
        score_params.extend([term, term, term])
        
        # Coverage Logic
        c_part = f"(CASE WHEN (name LIKE ? OR description LIKE ? OR tags_json LIKE ?) THEN 1 ELSE 0 END)"
        coverage_parts.append(c_part)
        coverage_params.extend([term, term, term])

    score_expr = " + ".join(score_parts)
    coverage_expr = " + ".join(coverage_parts)
    
    # Important: Concatenate params in the same order as expressions appear in SQL
    all_params = score_params + coverage_params
    
    sql = f"""
        SELECT 
            fn_id, name, description,
            ({score_expr}) as score,
            ({coverage_expr}) as coverage
        FROM functions
        WHERE ({coverage_expr}) > 0
        ORDER BY coverage DESC, score DESC, fn_id ASC
    """
    
    # Note: I used the calculated coverage expression in WHERE clause too. 
    # SQLite allows aliases in WHERE in some cases, or we can use HAVING, 
    # but repeating expression is safer or use a subquery. 
    # To keep params aligned, if I repeat expression in WHERE, I need to add params again!
    # OR use a CTE/Subquery.
    
    # Let's use a wrapper query to avoid repeating logic/params
    wrapper_sql = f"""
        SELECT * FROM (
            SELECT 
                fn_id, name, description,
                ({score_expr}) as score,
                ({coverage_expr}) as coverage
            FROM functions
        )
        WHERE coverage > 0
        ORDER BY coverage DESC, score DESC, fn_id ASC
    """
    
    cursor = conn.execute(wrapper_sql, all_params)
    for row in cursor:
        print(row)

conn = setup_db()
print("--- Search: ['cell', 'segment'] ---")
search(conn, ["cell", "segment"])
