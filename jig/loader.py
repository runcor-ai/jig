"""Command loader: every command, built-in or user-defined, is a plugin of the same format.

A command is defined by files next to each other in a command directory:

    <name>.yaml          definition (parameters, tool policy, schema reference, validators)
    <name>.md            prompt template ($placeholders) - required for agent commands
    <name>.schema.json   output JSON schema (or give `output_schema:` inline in the yaml)

Directories, in load order (later ones override earlier ones with the same name):
    1. jig/commands/          built-in standard library
    2. ~/.jig/commands/       user commands      (override with $JIG_USER_COMMANDS)
    3. <project>/commands/        project commands

Definition fields (all optional except `purpose`):
    purpose        one-line description
    version        string
    target         {type: text | artifact | artifact_or_text | none, required: bool}
    parameters     name -> {type, default, enum?, items?, description}
                   types: string | integer | number | boolean | list | object | path
                   (path: file inside the project, inserted into the prompt as untrusted data)
    artifact       create | use | optional | none        (default: optional)
    requires       stages of the artifact that must have completed, e.g. [specify]
    mode           agent | procedure                      (procedure = built-in runner, e.g. run_tests)
    procedure      name of a built-in procedure when mode is procedure
    tool_policy    name of a policy in jig config, or inline {tools, allow, deny} (default: none)
    prompt         template file (default: <name>.md)
    output_schema  schema file (default: <name>.schema.json) or an inline schema mapping
    validators     names of built-in validators run after schema validation
    postprocess    names of built-in post-processing hooks
    idempotent     safe to retry on validation failure (default: true for agent commands)
    timeout_s      per-call agent timeout
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import yaml

BUILTIN_DIR = Path(__file__).resolve().parent / "commands"
# Placeholders every template may use besides its own parameters (see jig/prompts.py).
CONTEXT_PLACEHOLDERS = {"command", "artifact_id", "target", "parameters", "spec", "build_spec", "tests",
                        "expected_ids",
                        "context", "workspace_state"}
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
TARGET_TYPES = {"text", "artifact", "artifact_or_text", "none"}
PARAM_TYPES = {"string", "integer", "number", "boolean", "list", "object", "path"}
ARTIFACT_MODES = {"create", "use", "optional", "none"}
RESERVED_PARAMS = {"approval_required", "max_attempts"}


class CommandDefError(ValueError):
    """A command definition is invalid. Message lists every problem with its file."""


@dataclass
class Command:
    name: str
    spec: dict
    source: str                     # builtin | user | project
    path: Path                      # the .yaml file
    prompt: str | None = None
    schema: dict = field(default_factory=dict)
    overrides: str | None = None    # source of the definition this one replaced

    def get(self, key: str, default: Any = None) -> Any:
        return self.spec.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.spec[key]


def command_dirs(project_dir: Path) -> list[tuple[str, Path]]:
    user = Path(os.environ.get("JIG_USER_COMMANDS") or Path.home() / ".jig" / "commands")
    return [("builtin", BUILTIN_DIR), ("user", user), ("project", Path(project_dir) / "commands")]


def _normalize(name: str, raw: dict) -> dict:
    spec = dict(raw)
    spec.setdefault("version", "0")
    spec["target"] = {"type": "artifact_or_text", "required": True, **(spec.get("target") or {})}
    spec["parameters"] = spec.get("parameters") or {}
    spec.setdefault("artifact", "optional")
    spec["requires"] = list(spec.get("requires") or [])
    spec.setdefault("mode", "agent")
    spec.setdefault("tool_policy", "none")
    spec["validators"] = list(spec.get("validators") or [])
    spec["postprocess"] = list(spec.get("postprocess") or [])
    spec.setdefault("idempotent", spec["mode"] == "agent")
    return spec


def _check(name: str, spec: dict, path: Path, prompt: str | None, schema: Any,
           validators: set[str], procedures: set[str], postprocess: set[str]) -> list[str]:
    p = []
    if not NAME_RE.match(name):
        p.append(f"name '{name}' must be lowercase letters, digits or underscores")
    if not spec.get("purpose"):
        p.append("missing 'purpose'")
    if spec["target"]["type"] not in TARGET_TYPES:
        p.append(f"target.type must be one of {sorted(TARGET_TYPES)}")
    if spec["artifact"] not in ARTIFACT_MODES:
        p.append(f"artifact must be one of {sorted(ARTIFACT_MODES)}")
    if spec["artifact"] == "use" and spec["target"]["type"] != "artifact":
        p.append("artifact: use requires target.type: artifact")
    for pname, ps in spec["parameters"].items():
        if pname in RESERVED_PARAMS:
            p.append(f"parameter '{pname}' is reserved")
        if not isinstance(ps, dict) or ps.get("type") not in PARAM_TYPES:
            p.append(f"parameter '{pname}' needs type in {sorted(PARAM_TYPES)}")
    if spec["mode"] not in ("agent", "procedure"):
        p.append("mode must be agent or procedure")
    if spec["mode"] == "agent" and prompt is None:
        p.append(f"agent command needs a prompt template ({spec.get('prompt') or name + '.md'})")
    if prompt is not None:
        p += template_problems(prompt, set(spec["parameters"]), spec.get("prompt") or f"{name}.md")
    if spec["mode"] == "procedure" and spec.get("procedure") not in procedures:
        p.append(f"unknown procedure '{spec.get('procedure')}'; built-in procedures: {sorted(procedures)}")
    pol = spec["tool_policy"]
    if not isinstance(pol, (str, dict)) or (isinstance(pol, dict) and not isinstance(pol.get("tools", []), list)):
        p.append("tool_policy must be a policy name or {tools: [...], allow: [...], deny: [...]}")
    for v in spec["validators"]:
        if v not in validators:
            p.append(f"unknown validator '{v}'; available: {sorted(validators)}")
    for h in spec["postprocess"]:
        if h not in postprocess:
            p.append(f"unknown postprocess hook '{h}'; available: {sorted(postprocess)}")
    if not isinstance(schema, dict):
        p.append("output schema missing or not a JSON object")
    else:
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as e:
            p.append(f"output schema invalid: {e.message}")
    return [f"{path}: {m}" for m in p]


def template_problems(text: str, params: set[str], fname: str) -> list[str]:
    """Every $name / ${name} must be a declared parameter or a context placeholder ($$ is a literal $)."""
    import string
    t = string.Template(text)
    known = params | CONTEXT_PLACEHOLDERS
    out = []
    unknown = sorted({n for n in t.get_identifiers() if n not in known})
    if unknown:
        out.append(f"{fname} uses undefined placeholder(s) {', '.join('$' + n for n in unknown)}; "
                   f"declare them under parameters or use one of: {', '.join(sorted(known))}")
    # A brace placeholder that never became a name ("${unclosed", "${bad-name}") is a typo. A bare "$" before
    # something that is not a name (e.g. "costs $5") renders unchanged, so it is allowed.
    # (the "invalid" group is empty and starts right after the "$")
    braces = [m for m in t.pattern.finditer(text)
              if m.group("invalid") is not None and text[m.start("invalid"):m.start("invalid") + 1] == "{"]
    if braces:
        lines = sorted({text.count("\n", 0, m.start()) + 1 for m in braces})
        snippets = [text[m.start():m.start() + 20].split("\n")[0] for m in braces]
        out.append(f"{fname} has a malformed ${{...}} placeholder at line(s) {lines}: {snippets[:3]} "
                   f"(write $$ for a literal $)")
    return out


def _load_one(path: Path) -> tuple[str, dict, str | None, Any]:
    name = path.stem
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise CommandDefError(f"{path}: definition must be a mapping")
    name = raw.pop("name", name)
    spec = _normalize(name, raw)
    prompt_file = path.parent / (spec.get("prompt") or f"{name}.md")
    prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.is_file() else None
    sch = spec.get("output_schema")
    if isinstance(sch, dict):
        schema = sch
    else:
        sfile = path.parent / (sch or f"{name}.schema.json")
        schema = json.loads(sfile.read_text(encoding="utf-8")) if sfile.is_file() else (
            {"type": "object"} if spec["mode"] == "procedure" and not sch else None)
    return name, spec, prompt, schema


def load_commands(project_dir: Path, dirs: list[tuple[str, Path]] | None = None) -> dict[str, Command]:
    from .procedures import PROCEDURES, POSTPROCESS
    from .validators import VALIDATORS
    commands: dict[str, Command] = {}
    problems: list[str] = []
    for source, d in (dirs or command_dirs(project_dir)):
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.yaml")):
            try:
                name, spec, prompt, schema = _load_one(path)
            except (yaml.YAMLError, json.JSONDecodeError, OSError) as e:
                problems.append(f"{path}: {e}")
                continue
            except CommandDefError as e:
                problems.append(str(e))
                continue
            errs = _check(name, spec, path, prompt, schema, set(VALIDATORS), set(PROCEDURES), set(POSTPROCESS))
            if errs:
                problems += errs
                continue
            prev = commands.get(name)
            commands[name] = Command(name, spec, source, path, prompt, schema,
                                     overrides=prev.source if prev else None)
    if problems:
        raise CommandDefError("invalid command definition(s):\n  " + "\n  ".join(problems))
    return commands
