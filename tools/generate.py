"""Generate the small tier/focus matrix; hand-authored state logic stays separate."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOCI = ("production", "military", "society")
TIERS = ((1, "0.05", 10), (2, "0.10", 25), (3, "0.20", 50))


def outputs():
    modifiers, apply, buttons = [], ["ri_apply_research = {"], []
    for index, focus in enumerate(FOCI, 1):
        for tier, speed, bureaucracy in TIERS:
            key = f"ri_{focus}_{tier}"
            modifiers.append(f"{key} = {{\n    country_{focus}_tech_research_speed_mult = {speed}\n    country_bureaucracy_add = -{bureaucracy}\n}}\n")
            apply.append(f"    if = {{\n        limit = {{ var:ri_focus = {index} var:ri_tier = {tier} }}\n        add_modifier = {{ name = {key} days = 8 }}\n    }}")
        buttons.append(f"""ri_focus_{focus}_button = {{
    name = ri_focus_{focus}_button
    desc = ri_focus_{focus}_button_desc
    visible = {{ var:ri_tier > 0 NOT = {{ var:ri_focus = {index} }} }}
    possible = {{ ri_can_change_focus = yes NOT = {{ var:ri_focus = {index} }} }}
    ai_chance = {{ base = 0 }}
    effect = {{
        if = {{
            limit = {{ ri_can_change_focus = yes NOT = {{ var:ri_focus = {index} }} }}
            ri_clear_research = yes
            set_variable = {{ name = ri_focus value = {index} }}
            set_variable = {{ name = ri_focus_cooldown value = 13 }}
        }}
    }}
}}
""")
    apply.append("}")
    modifiers.append("ri_exchange_network = {\n    country_tech_spread_mult = 0.25\n    country_influence_add = -25\n}\n")
    return {
        "mod/common/static_modifiers/ri_generated.txt": "\n".join(modifiers),
        "mod/common/scripted_effects/ri_generated.txt": "\n".join(apply) + "\n",
        "mod/common/scripted_buttons/ri_generated.txt": "\n".join(buttons),
    }


if __name__ == "__main__":
    for name, content in outputs().items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print("Generated research focus/tier definitions.")
