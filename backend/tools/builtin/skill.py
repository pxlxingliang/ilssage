from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from backend.tools.registry import ToolInfo

BUILTIN_SKILLS_DIR = Path(__file__).parent / "skills"
SKILLS_DIR = Path("~/.ilssage/skills").expanduser()

DESCRIPTION = """\
Load a skill module's full instructions and domain knowledge. \
Use this when you need specialized guidance that is not in your system prompt."""


# ── Data classes ─────────────────────────────────────────

@dataclass
class SkillMeta:
    name: str
    description: str = ""


@dataclass
class Skill:
    meta: SkillMeta
    prompt: str = ""
    directory: Optional[Path] = None


# ── SKILL.md parser ───────────────────────────────────────

def _parse_skill_md(path: Path) -> Tuple[SkillMeta, str]:
    if not path.exists():
        raise FileNotFoundError(f"SKILL.md not found: {path}")
    content = path.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            import yaml
            front = yaml.safe_load(parts[1]) or {}
            prompt = parts[2].strip()
        else:
            front = {}
            prompt = content
    else:
        front = {}
        prompt = content
    meta = SkillMeta(
        name=front.get("name", path.parent.name),
        description=front.get("description", ""),
    )
    return meta, prompt


# ── Registry ─────────────────────────────────────────────

class SkillRegistry:
    def __init__(self, skills_dirs: Optional[List[str]] = None):
        self._skills: Dict[str, Skill] = {}
        self._dirs = [Path(d).expanduser() for d in (skills_dirs or [])]
        if not self._dirs:
            self._dirs = [SKILLS_DIR]

    def discover(self) -> List[str]:
        discovered: List[str] = []
        for base_dir in self._dirs:
            if not base_dir.exists():
                continue
            for skill_dir in base_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    discovered.append(skill_dir.name)
        return sorted(discovered)

    def _parse_summary(self, skill_dir: Path) -> Optional[Dict[str, Any]]:
        md_path = skill_dir / "SKILL.md"
        if not md_path.exists():
            return None
        content = md_path.read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                front = yaml.safe_load(parts[1]) or {}
            else:
                front = {}
        else:
            front = {}
        return {
            "name": front.get("name", skill_dir.name),
            "description": front.get("description", ""),
        }

    def get_summaries(self) -> List[Dict[str, Any]]:
        by_name: Dict[str, Dict[str, Any]] = {}
        for base_dir in self._dirs:
            if not base_dir.exists():
                continue
            for skill_dir in base_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                if not (skill_dir / "SKILL.md").exists():
                    continue
                summary = self._parse_summary(skill_dir)
                if not summary:
                    continue
                name = summary["name"]
                prev = by_name.get(name)
                if prev is not None:
                    logger.warning(
                        f"Skill '{name}' redefined: "
                        f"'{skill_dir}' overrides '{prev['_dir']}'"
                    )
                summary["_dir"] = str(skill_dir)
                by_name[name] = summary
        return sorted(
            ({k: v for k, v in s.items() if k != "_dir"} for s in by_name.values()),
            key=lambda s: s["name"],
        )

    def load(self, name: str) -> Optional[Skill]:
        if name in self._skills:
            return self._skills[name]

        found_dir: Optional[Path] = None
        for base_dir in self._dirs:
            skill_dir = base_dir / name
            if skill_dir.exists() and (skill_dir / "SKILL.md").exists():
                if found_dir is not None:
                    logger.warning(
                        f"Skill '{name}' redefined: "
                        f"'{skill_dir}' overrides '{found_dir}'"
                    )
                found_dir = skill_dir

        if found_dir is None:
            return None

        try:
            skill = _load_skill_from_dir(found_dir)
            self._skills[name] = skill
            return skill
        except Exception:
            return None

    def get(self, name: str) -> Optional[Skill]:
        return self._skills.get(name)


def _load_skill_from_dir(skill_dir: Path) -> Skill:
    meta, prompt = _parse_skill_md(skill_dir / "SKILL.md")
    return Skill(meta=meta, prompt=prompt, directory=skill_dir.resolve())


# ── Singleton ────────────────────────────────────────────

_skill_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry(
            skills_dirs=[str(BUILTIN_SKILLS_DIR), str(SKILLS_DIR)]
        )
    return _skill_registry


# ── Tool factory ─────────────────────────────────────────

def create_skill_tool(registry: Optional[SkillRegistry] = None) -> Optional[ToolInfo]:
    if registry is None:
        registry = get_skill_registry()
    summaries = registry.get_summaries()
    if not summaries:
        return None

    lines = []
    names = []
    for s in summaries:
        lines.append(f"  - {s['name']}: {s['description']}")
        names.append(s["name"])

    skill_list = "\n".join(lines)

    def _load_fn(name: str) -> str:
        skill = registry.load(name)
        if skill is None:
            return f"Skill '{name}' not found. Available: {', '.join(names)}"
        return (
            f"## Skill: {skill.meta.name}\n"
            f"Directory: {skill.directory}\n\n"
            f"{skill.prompt}"
        )

    return ToolInfo(
        name="load_skill",
        description=(
            f"{DESCRIPTION}\n\n"
            f"Available skills:\n{skill_list}"
        ),
        parameters={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the skill to load",
                    "enum": names,
                }
            },
            "required": ["name"],
        },
        fn=_load_fn,
    )
