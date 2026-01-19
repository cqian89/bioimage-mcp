# Test Utilities API Contracts

## DataEquivalenceHelper

### assert_arrays_equivalent
```python
def assert_arrays_equivalent(
    actual: np.ndarray,
    expected: np.ndarray,
    rtol: float = 1e-5,
    atol: float = 1e-8,
    err_msg: str = ""
) -> None:
    """
    Assert two arrays are equivalent within numerical tolerance.
    
    Args:
        actual: Array from MCP execution
        expected: Array from native execution
        rtol: Relative tolerance
        atol: Absolute tolerance
        err_msg: Custom error message
    
    Raises:
        AssertionError: If shapes don't match or values exceed tolerance
    """
```

### assert_labels_equivalent
```python
def assert_labels_equivalent(
    actual: np.ndarray,
    expected: np.ndarray,
    iou_threshold: float = 0.99
) -> float:
    """
    Assert two label images are equivalent using IoU matching.
    
    Uses Hungarian algorithm to optimally match labels, then computes
    mean IoU across matched pairs.
    
    Args:
        actual: Label image from MCP execution (0=background, 1..N=instances)
        expected: Label image from native execution
        iou_threshold: Minimum mean IoU required
    
    Returns:
        Computed mean IoU
    
    Raises:
        AssertionError: If mean IoU < threshold
    """
```

### assert_plot_valid
```python
def assert_plot_valid(
    path: Path,
    min_size: int = 1000,
    expected_width: Optional[int] = None,
    expected_height: Optional[int] = None,
    min_variance: float = 1.0
) -> None:
    """
    Assert a plot artifact is valid using semantic checks.
    
    Args:
        path: Path to PNG/JPEG file
        min_size: Minimum file size in bytes
        expected_width: Expected width (optional)
        expected_height: Expected height (optional)
        min_variance: Minimum pixel intensity variance (detects blank images)
    
    Raises:
        AssertionError: If any semantic check fails
    """
```

### assert_table_equivalent
```python
def assert_table_equivalent(
    actual: pd.DataFrame,
    expected: pd.DataFrame,
    rtol: float = 1e-5,
    check_column_order: bool = False
) -> None:
    """
    Assert two DataFrames are equivalent.
    
    Args:
        actual: DataFrame from MCP execution
        expected: DataFrame from native execution
        rtol: Relative tolerance for numeric columns
        check_column_order: If True, column order must match
    
    Raises:
        AssertionError: If columns, index, or values differ
    """
```

### assert_metadata_preserved
```python
def assert_metadata_preserved(
    actual: xr.DataArray,
    expected: xr.DataArray
) -> None:
    """
    Assert xarray metadata (coords, dims, attrs) is preserved.
    
    Raises:
        AssertionError: If dimension names, coordinates, or attrs differ
    """
```

## NativeExecutor

### Constructor
```python
class NativeExecutor:
    def __init__(self, conda_path: Optional[str] = None):
        """
        Initialize native executor.
        
        Args:
            conda_path: Path to conda/micromamba. Auto-detected if not provided.
        
        Raises:
            NativeExecutorError: If conda not found
        """
```

### run_script
```python
def run_script(
    self,
    env_name: str,
    script_path: Path,
    args: List[str],
    timeout: int = 300,
    cwd: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Execute a Python script in isolated conda environment.
    
    Args:
        env_name: Conda environment name (e.g., "bioimage-mcp-base")
        script_path: Path to Python script
        args: Command line arguments to pass
        timeout: Maximum execution time in seconds
        cwd: Working directory (optional)
    
    Returns:
        Parsed JSON from script's stdout
    
    Raises:
        EnvironmentNotFoundError: If env_name doesn't exist
        NativeExecutorError: If script fails or timeout
    """
```

### env_exists
```python
def env_exists(self, env_name: str) -> bool:
    """Check if conda environment exists."""
```

## LFS Utilities

### is_lfs_pointer
```python
def is_lfs_pointer(path: Path) -> bool:
    """
    Check if a file is a Git LFS pointer (content not fetched).
    
    Returns True if file is small and contains LFS version header.
    """
```

### skip_if_lfs_pointer
```python
def skip_if_lfs_pointer(path: Path) -> None:
    """
    Skip pytest test if file is LFS pointer.
    
    Raises:
        pytest.skip: With informative message about LFS
    """
```
