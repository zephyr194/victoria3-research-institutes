"""Execute the shipped country scripts against a small mock world.

Does not emulate engine loading, POP economics, scope propagation or UI.
"""
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from script import definitions


class Runtime:
    def __init__(self, treasury=1000000, occupancy="0.5", literacy="0.5"):
        self.variables = {}
        self.treasury = Decimal(treasury)
        self.buildings = [{"is_building_type": "building_ri_research_institute", "occupancy": Decimal(occupancy)}]
        self.literacy = Decimal(literacy)
        self.at_war = False
        self.isolationism = False
        self.modifiers = {}
        self.effects = definitions("scripted_effects")
        self.triggers = definitions("scripted_triggers")
        self.values = definitions("script_values")
        self.buttons = definitions("scripted_buttons")
        self.call("ri_initialize")

    def value(self, item):
        if isinstance(item, list):
            result = Decimal(0)
            for key, _, value in item:
                if key == "if":
                    fields = dict((k, v) for k, _, v in value)
                    if self.condition(fields["limit"]):
                        result = self.math(result, [(k, op, v) for k, op, v in value if k != "limit"])
                else:
                    result = self.math(result, [(key, "=", value)])
            return result
        if item.startswith("var:"):
            return self.variables[item[4:]]
        if item == "gold_reserves":
            return self.treasury
        if item == "literacy_rate":
            return self.literacy
        if item in self.values:
            return self.value(self.values[item])
        return Decimal(item)

    def math(self, current, nodes):
        for key, _, value in nodes:
            value = self.value(value)
            if key == "value": current = value
            elif key == "add": current += value
            elif key == "subtract": current -= value
            elif key == "multiply": current *= value
            else: raise ValueError(f"Unsupported math {key}")
        return current

    def condition(self, nodes, building=None):
        def check(key, op, value):
            if key == "AND": return self.condition(value, building)
            if key == "NOT": return not self.condition(value, building)
            if key == "OR": return any(check(k, o, v) for k, o, v in value)
            if key == "always": return value == "yes"
            if key == "is_player": return value == "yes"
            if key == "has_variable": return value in self.variables
            if key == "has_modifier": return value in self.modifiers
            if key == "is_at_war": return self.at_war == (value == "yes")
            if key == "has_law":
                if value != "law_type:law_isolationism": raise ValueError(value)
                return self.isolationism
            if key == "any_scope_building":
                return any(self.condition(value, b) for b in self.buildings)
            if key == "is_building_type": return building[key] == value
            if key in self.triggers:
                return self.condition(self.triggers[key], building) == (value == "yes")
            if key.startswith("var:") and key[4:] not in self.variables: return False
            left = building["occupancy"] if key == "occupancy" else self.value(key)
            right = self.value(value)
            if op == "=": return left == right
            if op == "!=": return left != right
            if op == ">": return left > right
            if op == "<": return left < right
            if op == ">=": return left >= right
            if op == "<=": return left <= right
            raise ValueError(f"Unsupported condition {key}")
        return all(check(k, o, v) for k, o, v in nodes)

    def execute(self, nodes):
        matched_chain = False
        for key, _, value in nodes:
            if key in ("if", "else_if", "else"):
                if key == "if": matched_chain = False
                fields = dict((k, v) for k, _, v in value)
                matched = not matched_chain and (key == "else" or self.condition(fields["limit"]))
                if matched:
                    self.execute([(k, op, v) for k, op, v in value if k != "limit"])
                    matched_chain = True
            elif key == "set_variable":
                fields = dict((k, v) for k, _, v in value)
                self.variables[fields["name"]] = self.value(fields["value"])
            elif key == "change_variable":
                fields = dict((k, v) for k, _, v in value)
                name = fields.pop("name")
                self.variables[name] = self.math(self.variables[name], [(k, "=", v) for k, v in fields.items()])
            elif key == "add_treasury": self.treasury += self.value(value)
            elif key == "remove_modifier": self.modifiers.pop(value, None)
            elif key == "add_modifier":
                fields = dict((k, v) for k, _, v in value)
                self.modifiers[fields["name"]] = int(fields["days"])
            elif key in self.effects: self.call(key)
            else: raise ValueError(f"Unsupported effect {key}")

    def call(self, key):
        self.execute(self.effects[key])

    def click(self, key):
        fields = dict((k, v) for k, _, v in self.buttons[key])
        if self.condition(fields["visible"]) and self.condition(fields["possible"]):
            self.execute(fields["effect"])
            return True
        return False

    def tick(self, count=1):
        for _ in range(count):
            self.advance_days(7)
            self.call("ri_weekly_tick")

    def advance_days(self, days):
        self.modifiers = {k: v - days for k, v in self.modifiers.items() if v > days}
