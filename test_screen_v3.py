import unittest
import numpy as np

from screen_v3 import Structure, audit, capacitance, rc_decay, structures, transfer, transition


class ChargeConservationTests(unittest.TestCase):
    def test_rc_decay_is_real_passive_and_matches_ode(self):
        cap = np.array([[243., -80.], [-80., 82.]]) * 1e-15
        conductance = np.diag([2e-14, 4e-12])
        full = rc_decay(cap, conductance, 1/60)
        half = rc_decay(cap, conductance, 1/120)
        self.assertTrue(np.isrealobj(full))
        self.assertTrue(np.allclose(full, half @ half, atol=1e-12))
        dt = 1e-8
        derivative = (rc_decay(cap, conductance, dt)-np.eye(2))/dt
        self.assertTrue(np.allclose(derivative, -np.linalg.solve(cap, conductance), atol=2e-5))
        self.assertGreaterEqual(np.linalg.eigvalsh(cap-full.T @ cap @ full).min(), -1e-26)

    def circuit(self, anchor="S", track=False):
        return Structure((("G", "S"), ("G", "X")), anchor, track, "X", False, False, False)

    def test_old_v2_loses_threshold_even_with_ideal_caps(self):
        result = transfer(self.circuit("R"), (160., 80.))
        self.assertAlmostEqual(result["kappa"], 1/3, places=10)
        self.assertAlmostEqual(result["vth_residual"], -1/3, places=10)
        self.assertEqual(audit(self.circuit("R"))["decision"], "VTH_lost_across_phases")

    def test_source_anchor_retains_threshold_for_different_ratios(self):
        for st, data in ((20., 640.), (640., 20.), (80., 160.)):
            for track in (False, True):
                result = transfer(self.circuit(track=track), (st, data))
                self.assertAlmostEqual(result["kappa"], data/(st+data), places=10)
                self.assertAlmostEqual(result["vth_residual"], 0., places=10)
                self.assertAlmostEqual(result["source_sensitivity"], 0., places=10)

    def test_parasitic_transfer_matches_independent_closed_form(self):
        st, data, cg, cx = 160., 80., 3., 2.
        result = transfer(self.circuit(), (st, data), (cg, 20., cx))
        effective = cg + data*cx/(data+cx)
        self.assertAlmostEqual(abs(result["source_sensitivity"]), effective/(st+effective), places=10)
        self.assertAlmostEqual(result["vth_residual"], -cg/(st+data+cg), places=10)

    def test_floating_gate_charge_is_conserved_when_source_moves(self):
        matrix = capacitance((("G", "S"), ("G", "X")), (160., 80.), (3., 20., 2.))
        before = np.arange(9.).reshape(3, 3)
        after = transition(matrix, before, {"S": np.array([2., 0., 0.])})
        self.assertTrue(np.allclose((matrix@(after-before))[[0, 2]], 0., atol=1e-10))

    def test_search_includes_one_cap_and_user_does_not_set_cap_area(self):
        all_s = list(structures())
        self.assertEqual(len(all_s), 3024)
        self.assertTrue(any(len(s.caps) == 1 for s in all_s))
        r = transfer(self.circuit(), (5120., 160.), (3., 20., 2.))
        self.assertGreater(r["kappa"], 0)

    def test_switch_groups_count_polarity_and_split_controls(self):
        self.assertEqual(self.circuit().groups, 4)
        self.assertEqual(self.circuit(track=True).groups, 5)
        s = Structure((("G", "S"), ("G", "X")), "S", True, "X", False, False, True)
        self.assertEqual(s.groups, 5)  # p-LTPS PWR shares SCLAMP waveform


if __name__ == "__main__":
    unittest.main()
