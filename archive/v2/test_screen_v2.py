import unittest

from screen_v2 import (
    CONTROL_MASKS,
    KAPPA_RANGE,
    MAX_TOTAL_CAP_FF,
    MAX_VGS_SOURCE_SENSITIVITY,
    compression_ratio,
    enumerate_candidates,
    evaluate,
    robustness_envelope,
    source_tracking_gain,
    v1_series_cap_tracking,
)


class V2ScreeningTests(unittest.TestCase):
    def test_control_budget_and_comp_write_separation(self):
        self.assertLessEqual(len(CONTROL_MASKS), 5)
        self.assertFalse(
            any(mask[1] == "1" and mask[3] == "1" for mask in CONTROL_MASKS.values())
        )

    def test_direct_gs_storage_improves_source_tracking(self):
        gain = source_tracking_gain(160, 80)
        self.assertLessEqual(abs(1.0 - gain), MAX_VGS_SOURCE_SENSITIVITY)
        self.assertGreater(gain, 0.95)

    def test_every_passing_candidate_satisfies_new_hard_constraints(self):
        passing = []
        for candidate in enumerate_candidates():
            metrics = evaluate(candidate)
            if metrics["functional"]:
                passing.append((candidate, metrics))
        self.assertTrue(passing)
        for candidate, metrics in passing:
            self.assertGreaterEqual(metrics["compression_ratio"], KAPPA_RANGE[0])
            self.assertLessEqual(metrics["compression_ratio"], KAPPA_RANGE[1])
            self.assertLessEqual(
                metrics["vgs_source_sensitivity_pct"],
                100 * MAX_VGS_SOURCE_SENSITIVITY,
            )
            self.assertLessEqual(metrics["total_cap_ff"], MAX_TOTAL_CAP_FF)

    def test_compression_is_intentionally_below_unity(self):
        self.assertAlmostEqual(compression_ratio(160, 80), 80 / 243)
        self.assertLess(compression_ratio(160, 80), 1.0)

    def test_recommended_cap_pairs_survive_mismatch_and_parasitic_corners(self):
        for c_st, c_data in ((160, 60), (160, 80)):
            envelope = robustness_envelope(c_st, c_data)
            self.assertEqual(envelope["corner_count"], 16)
            self.assertLessEqual(envelope["worst_vgs_source_sensitivity_pct"], 5.0)

    def test_v1_series_cap_winner_is_rejected_by_new_stability_gate(self):
        comparison = v1_series_cap_tracking()
        self.assertFalse(comparison["passes_v2_5pct_gate"])
        self.assertGreater(comparison["vgs_source_sensitivity_pct"], 5.0)


if __name__ == "__main__":
    unittest.main()
