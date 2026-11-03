"""Read the Clausewitz text subset used here; this is not engine validation."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r'\s+|\#[^\n]*|"(?:\\.|[^"\\])*"|>=|<=|!=|[{}=<>]|[^\s{}=<>!"#]+')
OPS = {"=", ">", "<", ">=", "<=", "!="}


def parse(text):
    tokens, end = [], 0
    for match in TOKEN.finditer(text):
        if match.start() != end:
            raise ValueError(f"Invalid token at {end}")
        end = match.end()
        token = match.group()
        if not token.isspace() and not token.startswith("#"):
            tokens.append(token)
    if end != len(text):
        raise ValueError("Unparsed text")
    position = 0

    def block(nested=False):
        nonlocal position
        nodes = []
        while position < len(tokens):
            if tokens[position] == "}":
                if not nested:
                    raise ValueError("Unexpected closing brace")
                position += 1
                return nodes
            key = tokens[position]
            position += 1
            if key in OPS or key == "{":
                raise ValueError(f"Invalid key: {key}")
            if position >= len(tokens) or tokens[position] not in OPS:
                nodes.append((key.strip('"'), None, None))
                continue
            op = tokens[position]
            position += 1
            if position >= len(tokens):
                raise ValueError(f"Missing value for {key}")
            value = tokens[position]
            position += 1
            if value == "{":
                value = block(True)
            elif value == "}" or value in OPS:
                raise ValueError(f"Invalid value for {key}")
            elif value.startswith('"'):
                value = value[1:-1]
            nodes.append((key, op, value))
        if nested:
            raise ValueError("Missing closing brace")
        return nodes

    return block()


def definitions(folder):
    result = {}
    for path in sorted((ROOT / "mod/common" / folder).glob("*.txt")):
        for name, op, value in parse(path.read_text(encoding="utf-8-sig")):
            if name in result or op != "=" or not isinstance(value, list):
                raise ValueError(f"Duplicate/invalid definition {name}: {path}")
            result[name] = value
    return result


def walk(nodes):
    for key, op, value in nodes:
        yield key, op, value
        if isinstance(value, list):
            yield from walk(value)
