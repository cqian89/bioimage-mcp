# Trackpy API Coverage Report

This report tracks the exposure of trackpy v0.7 functions via the Bioimage-MCP API.
It satisfies requirement **TRACK-03** (Full API coverage).

## Summary

- **Total Functions Scanned:** 137
- **Functions Exposed:** 130
- **Functions Excluded:** 7
- **Coverage Score:** 100.0%

## Thresholds

- [x] `total_exposed >= 100`
- [x] `coverage_pct >= 90.0`

## Exclusions

| Function ID | Reason |
|-------------|--------|
| `trackpy.disable_numba` | Configuration utility, not analysis tool |
| `trackpy.enable_numba` | Configuration utility, not analysis tool |
| `trackpy.feature.refine` | Deprecated, use trackpy.refine |
| `trackpy.handle_logging` | Logging configuration |
| `trackpy.ignore_logging` | Logging configuration |
| `trackpy.quiet` | Logging configuration |
| `trackpy.try_numba_jit` | Internal utility, not for users |

## Exposed Functions

<details>
<summary>Click to see all exposed functions</summary>

- `trackpy.annotate`
- `trackpy.annotate3d`
- `trackpy.artificial.draw_array`
- `trackpy.artificial.draw_cluster`
- `trackpy.artificial.draw_feature`
- `trackpy.artificial.draw_features_brightfield`
- `trackpy.artificial.draw_point`
- `trackpy.artificial.draw_spots`
- `trackpy.artificial.feat_brightfield`
- `trackpy.artificial.feat_disc`
- `trackpy.artificial.feat_gauss`
- `trackpy.artificial.feat_hat`
- `trackpy.artificial.feat_ring`
- `trackpy.artificial.feat_step`
- `trackpy.artificial.gen_connected_locations`
- `trackpy.artificial.gen_nonoverlapping_locations`
- `trackpy.artificial.gen_random_locations`
- `trackpy.artificial.rot_2d`
- `trackpy.artificial.rot_3d`
- `trackpy.bandpass`
- `trackpy.batch`
- `trackpy.cluster`
- `trackpy.compute_drift`
- `trackpy.diag.dependencies`
- `trackpy.diag.performance_report`
- `trackpy.diagonal_size`
- `trackpy.direction_corr`
- `trackpy.emsd`
- `trackpy.estimate_mass`
- `trackpy.estimate_size`
- `trackpy.feature.batch`
- `trackpy.feature.characterize`
- `trackpy.feature.estimate_mass`
- `trackpy.feature.estimate_size`
- `trackpy.feature.local_maxima`
- `trackpy.feature.locate`
- `trackpy.feature.minmass_v03_change`
- `trackpy.feature.minmass_v04_change`
- `trackpy.filter`
- `trackpy.filter_clusters`
- `trackpy.filter_stubs`
- `trackpy.filtering.filter`
- `trackpy.filtering.filter_clusters`
- `trackpy.filtering.filter_stubs`
- `trackpy.find_link`
- `trackpy.find_link_iter`
- `trackpy.grey_dilation`
- `trackpy.imsd`
- `trackpy.invert_image`
- `trackpy.is_typical`
- `trackpy.link`
- `trackpy.link_df`
- `trackpy.link_df_iter`
- `trackpy.link_iter`
- `trackpy.link_partial`
- `trackpy.local_maxima`
- `trackpy.locate`
- `trackpy.locate_brightfield_ring`
- `trackpy.masks.binary_mask`
- `trackpy.masks.cosmask`
- `trackpy.masks.r_squared_mask`
- `trackpy.masks.sinmask`
- `trackpy.masks.theta_mask`
- `trackpy.mass_ecc`
- `trackpy.mass_size`
- `trackpy.minmass_v03_change`
- `trackpy.minmass_v04_change`
- `trackpy.motion.compute_drift`
- `trackpy.motion.diagonal_size`
- `trackpy.motion.direction_corr`
- `trackpy.motion.emsd`
- `trackpy.motion.imsd`
- `trackpy.motion.is_diffusive`
- `trackpy.motion.is_localized`
- `trackpy.motion.is_typical`
- `trackpy.motion.min_rolling_theta_entropy`
- `trackpy.motion.msd`
- `trackpy.motion.proximity`
- `trackpy.motion.relate_frames`
- `trackpy.motion.shannon_entropy`
- `trackpy.motion.subtract_drift`
- `trackpy.motion.theta_entropy`
- `trackpy.motion.vanhove`
- `trackpy.motion.velocity_corr`
- `trackpy.msd`
- `trackpy.pair_correlation_2d`
- `trackpy.pair_correlation_3d`
- `trackpy.percentile_threshold`
- `trackpy.plot_density_profile`
- `trackpy.plot_displacements`
- `trackpy.plot_traj`
- `trackpy.plot_traj3d`
- `trackpy.plots.annotate`
- `trackpy.plots.annotate3d`
- `trackpy.plots.mass_ecc`
- `trackpy.plots.mass_size`
- `trackpy.plots.plot_density_profile`
- `trackpy.plots.plot_displacements`
- `trackpy.plots.plot_traj`
- `trackpy.plots.plot_traj3d`
- `trackpy.plots.ptraj`
- `trackpy.plots.ptraj3d`
- `trackpy.plots.scatter`
- `trackpy.plots.scatter3d`
- `trackpy.plots.subpx_bias`
- `trackpy.predict.instrumented`
- `trackpy.predict.null_predict`
- `trackpy.predict.predictor`
- `trackpy.preprocessing.bandpass`
- `trackpy.preprocessing.boxcar`
- `trackpy.preprocessing.convert_to_int`
- `trackpy.preprocessing.invert_image`
- `trackpy.preprocessing.legacy_bandpass`
- `trackpy.preprocessing.legacy_bandpass_fftw`
- `trackpy.preprocessing.lowpass`
- `trackpy.preprocessing.scale_to_gamut`
- `trackpy.preprocessing.scalefactor_to_gamut`
- `trackpy.proximity`
- `trackpy.ptraj`
- `trackpy.ptraj3d`
- `trackpy.reconnect_traj_patch`
- `trackpy.refine_com`
- `trackpy.refine_leastsq`
- `trackpy.relate_frames`
- `trackpy.scatter`
- `trackpy.scatter3d`
- `trackpy.subpx_bias`
- `trackpy.subtract_drift`
- `trackpy.vanhove`
- `trackpy.velocity_corr`

</details>

---
*Generated automatically during phase 05-02.*