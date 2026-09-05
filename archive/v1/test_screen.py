import json
import unittest

from screen import RESULTS, enumerate_timings, enumerate_topologies, hard_filter


class ScreeningTests(unittest.TestCase):
    def test_search_space_is_stable(self):
        topologies, reasons = enumerate_topologies()
        self.assertEqual(reasons["raw_generated"], 288)
        self.assertEqual(len(topologies), 8)
        self.assertEqual(len(enumerate_timings()), 120)

    def test_every_survivor_satisfies_hard_constraints(self):
        topologies, _ = enumerate_topologies()
        for topology in topologies:
            self.assertEqual(hard_filter(topology), (True, "pass"))
            self.assertLessEqual(len({s.mask for s in topology.switches()}), 4)

    def test_reportable_results_exist(self):
        summary = json.loads((RESULTS / "summary.json").read_text())
        robustness = json.loads((RESULTS / "robustness.json").read_text())
        self.assertEqual(summary["total_transient_runs"], 17_280)
        self.assertEqual(len(summary["top10"]), 10)
        self.assertEqual(len(robustness["robust_top10"]), 10)
        self.assertTrue(robustness["all_scenarios_same_winner_topology"])


if __name__ == "__main__":
    unittest.main()

