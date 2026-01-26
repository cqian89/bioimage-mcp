# User Acceptance Tests - Phase 8: Statistical Analysis

## Test 1: Stats Tool Discovery
**Action:** List tools with filter `scipy.stats`.
**Expected:** Should show `scipy.stats` functions like `describe_table`, `ttest_ind_table`, `f_oneway_table`, `ks_2samp_table`, and distribution methods like `norm.pdf`, `norm.cdf`, `poisson.pmf`.
**Status:** Passed

## Test 2: Wrapper Schema Verification
**Action:** Describe tool `scipy.stats.ttest_ind_table`.
**Expected:** Inputs should include `table_a` (TableRef), `table_b` (TableRef), and `equal_var` (bool). Output should be `ScalarRef` (JSON).
**Status:** Passed

## Test 3: Distribution Schema Verification
**Action:** Describe tool `scipy.stats.norm.pdf`.
**Expected:** Inputs should include `x` (number/array), `loc` (mean), `scale` (std). Output should be `ScalarRef` (JSON) or similar.
**Status:** Passed

## Test 4: Execution (Distribution)
**Action:** Run `scipy.stats.norm.pdf` with `x=[0]`.
**Expected:** Result should be `~0.3989`.
**Status:** Passed
