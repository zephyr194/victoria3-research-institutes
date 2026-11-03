"""Offline structural/binding checks; optionally check native references in a game install."""
import argparse
import json
from pathlib import Path
import re

from generate import outputs
from script import ROOT, definitions, parse, walk


def validate(game_dir=None):
    categories = ("buildings", "building_groups", "production_method_groups", "production_methods",
                  "script_values", "scripted_triggers", "scripted_effects", "scripted_buttons",
                  "journal_entries", "static_modifiers")
    groups = {name: definitions(name) for name in categories}
    defined = {key for group in groups.values() for key in group}
    for path in (ROOT / "mod").rglob("*.txt"):
        parse(path.read_text(encoding="utf-8-sig"))
    for name, content in outputs().items():
        if (ROOT / name).read_text() != content:
            raise ValueError(f"Stale generated artifact: {name}")
    expected_loc = set(groups["buildings"]) | set(groups["building_groups"]) | set(groups["production_method_groups"]) | set(groups["production_methods"]) | set(groups["static_modifiers"])
    expected_loc.update(k + suffix for k in groups["journal_entries"] for suffix in ("", "_reason", "_status"))
    all_nodes = [node for group in groups.values() for nodes in group.values() for node in walk(nodes)]
    for key, _, value in all_nodes:
        if key.startswith("ri_") and value in ("yes", "no") and key not in defined:
            raise ValueError(f"Undefined scripted call: {key}")
        if key == "scripted_button" and value not in groups["scripted_buttons"]:
            raise ValueError(f"Unknown button: {value}")
        if key == "remove_modifier" and value not in groups["static_modifiers"]:
            raise ValueError(f"Unknown removed modifier: {value}")
        if key == "add_modifier":
            fields = dict((k, v) for k, _, v in value)
            if fields["name"] not in groups["static_modifiers"] or fields.get("days") != "8":
                raise ValueError("Programme bonuses must name a defined modifier and expire after 8 days")
    for category in ("scripted_buttons", "journal_entries"):
        for nodes in groups[category].values():
            expected_loc.update(v for k, _, v in walk(nodes) if k in ("name", "desc") and isinstance(v, str))
    languages = []
    for path in sorted((ROOT / "mod/localization").rglob("*.yml")):
        data = path.read_bytes()
        if not data.startswith(b"\xef\xbb\xbf"):
            raise ValueError(f"Localization requires UTF-8 BOM: {path}")
        text = data.decode("utf-8-sig")
        if not text.startswith(f"l_{path.parent.name}:\n"):
            raise ValueError(f"Wrong language header: {path}")
        lines = text.splitlines()[1:]
        if any(not re.fullmatch(r' [A-Za-z0-9_]+:0 "(?:[^"\\]|\\.)*"', line) for line in lines if line):
            raise ValueError(f"Malformed localization line: {path}")
        keys = re.findall(r"^ (\w+):0 ", text, re.M)
        if len(keys) != len(set(keys)) or expected_loc - set(keys):
            raise ValueError(f"Duplicate/missing localization in {path}: {expected_loc - set(keys)}")
        if set(re.findall(r"\$(ri_\w+)\$", text)) - set(keys):
            raise ValueError(f"Missing nested localization in {path}")
        languages.append(set(keys))
    if len(languages) != 2 or languages[0] != languages[1]:
        raise ValueError("English and Simplified Chinese must cover identical keys")
    building = dict((k, v) for k, _, v in groups["buildings"]["building_ri_research_institute"])
    if not {"required_construction", "production_method_groups"} <= building.keys() or {"construction_points", "production_methods"} & building.keys():
        raise ValueError("Use actual game building fields, not the shared documentation aliases")
    for key, _, _ in building["production_method_groups"]:
        if key not in groups["production_method_groups"]:
            raise ValueError(f"Unknown PM group: {key}")
    for nodes in groups["production_method_groups"].values():
        fields = dict((k, v) for k, _, v in nodes)
        if any(k not in groups["production_methods"] for k, _, _ in fields["production_methods"]):
            raise ValueError("Unknown production method")
    group = dict((k, v) for k, _, v in groups["building_groups"][building["building_group"]])
    if group.get("is_government_funded") != "yes":
        raise ValueError("Research institutes must be government funded")
    pulses = [(name, key) for name, nodes in groups["journal_entries"].items() for key, _, _ in nodes if key == "on_weekly_pulse"]
    if pulses != [("ri_je", "on_weekly_pulse")]:
        raise ValueError("There must be exactly one programme scheduler")
    bindings = json.loads((ROOT / "evidence/bindings.json").read_text())["snapshots"]
    native_effects = {k for nodes in groups["scripted_effects"].values() for k, _, _ in walk(nodes) if k in {"set_variable", "change_variable", "add_treasury", "add_modifier", "remove_modifier"}}
    native_modifiers = {k for k, _, v in all_nodes if k.startswith(("country_", "building_employment_", "goods_input_")) and not isinstance(v, list)}
    for version, snapshot in bindings.items():
        for category, names in (("effects", native_effects), ("modifiers", native_modifiers)):
            if names - snapshot[category]["bindings"].keys():
                raise ValueError(f"Missing {category} evidence for {version}")
    if game_dir:
        validate_native_references(Path(game_dir))
    return f"Validated {len(defined)} definitions, {len(languages[0])} bilingual keys, generated matrix and two interface snapshots."


def validate_native_references(game_dir):
    if (game_dir / "game/common").is_dir():
        game_dir = game_dir / "game"
    if not (game_dir / "common/buildings").is_dir():
        raise ValueError("--game-dir must contain game/common or common/buildings")
    checks = {"building_groups": "bg_government", "technology/technologies": "empiricism", "laws": "law_isolationism"}
    for category, key in checks.items():
        files = (game_dir / "common" / category).rglob("*.txt")
        if not any(re.search(r"(?m)^\s*" + key + r"\s*=", p.read_text(encoding="utf-8-sig", errors="replace")) for p in files):
            raise ValueError(f"Native reference missing: {key}")
    icon = game_dir / "gfx/interface/icons/building_icons/building_university.dds"
    if not icon.is_file():
        raise ValueError(f"Native icon missing: {icon}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir")
    args = parser.parse_args()
    print(validate(args.game_dir))
