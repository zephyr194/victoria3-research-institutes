import unittest
from decimal import Decimal
from runtime import Runtime


class ResearchTests(unittest.TestCase):
    def active(self, **kwargs):
        runtime = Runtime(**kwargs)
        self.assertTrue(runtime.click("ri_charter_button"))
        runtime.tick()
        return runtime

    def test_charter_gates_and_no_free_research(self):
        for params in ({"treasury": 24999}, {"occupancy": "0.499"}, {"literacy": "0.099"}):
            with self.subTest(params=params):
                runtime = Runtime(**params)
                before = runtime.treasury
                runtime.call("ri_charter")
                self.assertEqual(runtime.treasury, before)
                self.assertEqual(runtime.variables["ri_tier"], 0)
        runtime = Runtime(treasury=25000, literacy="0.1")
        self.assertTrue(runtime.click("ri_charter_button"))
        self.assertEqual(runtime.treasury, 0)
        self.assertEqual(runtime.modifiers, {})
        self.assertFalse(runtime.click("ri_charter_button"))
        runtime.tick()
        self.assertEqual(runtime.variables["ri_block_reason"], 2)
        self.assertEqual(runtime.variables["ri_paid_weeks"], 0)

    def test_payment_boundary_and_auto_recovery(self):
        runtime = self.active(treasury=26000)
        self.assertEqual(runtime.treasury, 0)
        self.assertIn("ri_production_1", runtime.modifiers)
        runtime.tick()
        self.assertEqual(runtime.modifiers, {})
        self.assertEqual(runtime.variables["ri_paid_weeks"], 1)
        runtime.treasury = Decimal(1000)
        runtime.tick()
        self.assertIn("ri_production_1", runtime.modifiers)
        self.assertEqual(runtime.variables["ri_paid_weeks"], 2)

    def test_repeated_initialize_preserves_save(self):
        runtime = self.active()
        before = dict(runtime.variables)
        runtime.call("ri_initialize")
        self.assertEqual(runtime.variables, before)

    def test_experience_upgrade_literacy_and_weekly_prices(self):
        runtime = self.active(treasury=2000000)
        self.assertFalse(runtime.click("ri_expand_2_button"))
        runtime.tick(25)
        runtime.literacy = Decimal("0.299")
        self.assertFalse(runtime.click("ri_expand_2_button"))
        runtime.literacy = Decimal("0.3")
        self.assertTrue(runtime.click("ri_expand_2_button"))
        balance = runtime.treasury
        runtime.tick(52)
        self.assertEqual(runtime.treasury, balance - 52 * 3000)
        self.assertFalse(runtime.click("ri_expand_3_button"))
        runtime.literacy = Decimal("0.5")
        self.assertTrue(runtime.click("ri_expand_3_button"))
        balance = runtime.treasury
        runtime.tick()
        self.assertEqual(runtime.treasury, balance - 8000)
        self.assertEqual(set(runtime.modifiers), {"ri_production_3"})
        self.assertTrue(runtime.click("ri_downgrade_button"))
        self.assertEqual(runtime.modifiers, {})
        runtime.tick()
        self.assertEqual(set(runtime.modifiers), {"ri_production_2"})

    def test_all_focus_tier_combinations_and_no_stacking(self):
        runtime = self.active()
        for tier in (1, 2, 3):
            runtime.variables["ri_tier"] = tier
            for index, focus in enumerate(("production", "military", "society"), 1):
                runtime.variables["ri_focus"] = index
                runtime.tick()
                self.assertEqual(set(runtime.modifiers), {f"ri_{focus}_{tier}"})

    def test_focus_switch_guard_and_cooldown(self):
        runtime = self.active()
        self.assertTrue(runtime.click("ri_focus_military_button"))
        self.assertEqual(runtime.modifiers, {})
        self.assertFalse(runtime.click("ri_focus_society_button"))
        runtime.tick(12)
        self.assertFalse(runtime.click("ri_focus_society_button"))
        runtime.tick()
        self.assertTrue(runtime.click("ri_focus_society_button"))

    def test_staffing_gate_checks_type_and_any_institute(self):
        runtime = self.active()
        runtime.buildings = [{"is_building_type": "building_university", "occupancy": Decimal(1)}]
        balance = runtime.treasury
        runtime.tick()
        self.assertEqual(runtime.variables["ri_block_reason"], 1)
        self.assertEqual(runtime.treasury, balance)
        self.assertEqual(runtime.modifiers, {})
        runtime.buildings.append({"is_building_type": "building_ri_research_institute", "occupancy": Decimal("0.5")})
        runtime.tick()
        self.assertIn("ri_production_1", runtime.modifiers)

    def test_pause_resume_and_building_independence(self):
        runtime = self.active()
        self.assertTrue(runtime.click("ri_pause_button"))
        self.assertEqual(runtime.modifiers, {})
        balance = runtime.treasury
        weeks = runtime.variables["ri_paid_weeks"]
        runtime.tick(10)
        self.assertEqual(runtime.treasury, balance)
        self.assertEqual(runtime.variables["ri_paid_weeks"], weeks)
        self.assertTrue(runtime.click("ri_resume_button"))
        self.assertEqual(runtime.modifiers, {})
        runtime.tick()
        self.assertIn("ri_production_1", runtime.modifiers)
        self.assertTrue(runtime.buildings)

    def test_exchange_cost_duration_and_cooldown(self):
        runtime = self.active()
        balance = runtime.treasury
        self.assertTrue(runtime.click("ri_exchange_button"))
        self.assertEqual(runtime.treasury, balance - 10000)
        self.assertFalse(runtime.click("ri_exchange_button"))
        self.assertNotIn("ri_exchange_network", runtime.modifiers)
        runtime.tick(26)
        self.assertEqual(runtime.treasury, balance - 10000 - 26 * 1500)
        self.assertEqual(runtime.variables["ri_exchange_weeks"], 0)
        self.assertIn("ri_exchange_network", runtime.modifiers)
        runtime.tick()
        self.assertNotIn("ri_exchange_network", runtime.modifiers)
        self.assertFalse(runtime.click("ri_exchange_button"))
        runtime.tick(51)
        self.assertTrue(runtime.click("ri_exchange_button"))

    def test_exchange_war_isolation_and_literacy(self):
        for attribute, value in (("at_war", True), ("isolationism", True), ("literacy", Decimal("0.199"))):
            with self.subTest(attribute=attribute):
                runtime = self.active()
                setattr(runtime, attribute, value)
                balance = runtime.treasury
                runtime.call("ri_start_exchange")
                self.assertEqual(runtime.treasury, balance)
                self.assertEqual(runtime.variables["ri_exchange_weeks"], 0)
        for attribute in ("at_war", "isolationism"):
            runtime = self.active()
            runtime.click("ri_exchange_button")
            runtime.tick()
            setattr(runtime, attribute, True)
            runtime.tick()
            self.assertNotIn("ri_exchange_network", runtime.modifiers)
            self.assertEqual(runtime.variables["ri_exchange_weeks"], 0)
            self.assertEqual(runtime.variables["ri_exchange_interrupted"], 1)

    def test_exchange_shortfall_keeps_affordable_core(self):
        runtime = self.active()
        runtime.click("ri_exchange_button")
        runtime.treasury = Decimal(1499)
        runtime.tick()
        self.assertEqual(runtime.treasury, 499)
        self.assertIn("ri_production_1", runtime.modifiers)
        self.assertNotIn("ri_exchange_network", runtime.modifiers)
        self.assertEqual(runtime.variables["ri_exchange_weeks"], 0)

    def test_cancellation_and_pause_have_no_refund(self):
        for button in ("ri_cancel_exchange_button", "ri_pause_button"):
            runtime = self.active()
            runtime.click("ri_exchange_button")
            runtime.tick()
            balance = runtime.treasury
            cooldown = runtime.variables["ri_exchange_cooldown"]
            self.assertTrue(runtime.click(button))
            self.assertNotIn("ri_exchange_network", runtime.modifiers)
            self.assertEqual(runtime.variables["ri_exchange_weeks"], 0)
            self.assertEqual(runtime.variables["ri_exchange_cooldown"], cooldown)
            self.assertEqual(runtime.treasury, balance)

    def test_modifiers_expire_if_scheduler_stops(self):
        runtime = self.active()
        runtime.click("ri_exchange_button")
        runtime.tick()
        runtime.advance_days(8)
        self.assertEqual(runtime.modifiers, {})


if __name__ == "__main__":
    unittest.main()
