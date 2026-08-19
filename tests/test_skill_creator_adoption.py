import hashlib
import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "agents" / "skills" / "skill-creator"

UPSTREAM_BLOBS = {
    "LICENSE.txt": "4f881c52d1f72f4cfb720e339e2d35c3058d01a9",
    "SKILL.md": "65b3a402dbd09b8e83f9d637c6b553875189085c",
    "agents/analyzer.md": "14e41d6068635f4dd3fb878fd1626312395dda63",
    "agents/comparator.md": "80e00eb45db3ee53a132fc2ba97fd59a7339e563",
    "agents/grader.md": "558ab05c0a9a8bb062ef4c51823d4d76c3acf7c4",
    "assets/eval_review.html": "938ff32aed9bffabf723bd5492d720f4736c8e4d",
    "eval-viewer/generate_review.py": "7fa5978631fed1ed545591dbb2b0eb21ce3f3d08",
    "eval-viewer/viewer.html": "6d8e96348a02e66c3363d2ff3b3ae58ac11e6382",
    "references/schemas.md": "b6eeaa2d4a34c1653069585c6c5603da39a5bdbe",
    "scripts/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "scripts/aggregate_benchmark.py": "3e66e8c105be9bab9f0e9c61f0d1482619401580",
    "scripts/generate_report.py": "959e30a0014ec165c41a2bb7420b7dfe1416bbac",
    "scripts/improve_description.py": "06bcec76122446986e3610c20a39c466de36f495",
    "scripts/package_skill.py": "f48eac444656ddc41204aac1760a217951ce609e",
    "scripts/quick_validate.py": "ed8e1dddce77b16af13c6f36b3fe86c4ac7c590c",
    "scripts/run_eval.py": "e58c70bea39d5b252a1e819f242bbdcdf20e8b87",
    "scripts/run_loop.py": "30a263d674ef19de11c756d6f7537f91a421909e",
    "scripts/utils.py": "51b6a07dd57174197a937034b7eecebd5768ff8a",
}
UPSTREAM_FILES = set(UPSTREAM_BLOBS)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    payload = f"blob {len(data)}\0".encode() + data
    return hashlib.sha1(payload, usedforsecurity=False).hexdigest()


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("skill_creator_quick_validate", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_skill_creator_package_and_provenance() -> None:
    assert SKILL_ROOT.is_dir()
    actual = {
        str(path.relative_to(SKILL_ROOT))
        for path in SKILL_ROOT.rglob("*")
        if path.is_file()
    }
    assert UPSTREAM_FILES <= actual

    for relative_path, expected_sha in UPSTREAM_BLOBS.items():
        assert _git_blob_sha(SKILL_ROOT / relative_path) == expected_sha

    upstream = (SKILL_ROOT / "UPSTREAM.md").read_text()
    assert "0a64e398ec6bb34a494f0c347e8ccae53a862f8e" in upstream
    assert "3cf9a8db32597ba3e24b584a3d696f4e11c7d7b6" in upstream
    assert "## Added" in upstream
    deleted = upstream.split("## Deleted", 1)[1].split("## Modified", 1)[0]
    modified = upstream.split("## Modified", 1)[1]
    assert "none" in deleted.lower()
    assert "none" in modified.lower()
    assert "references/repository-governance.md" in upstream
    assert (SKILL_ROOT / "LICENSE.txt").exists()


def test_upstream_quick_validate_accepts_adopted_skill() -> None:
    module = _load_module(SKILL_ROOT / "scripts" / "quick_validate.py")
    validate = cast(Callable[[Path], tuple[bool, str]], module.validate_skill)
    valid, message = validate(SKILL_ROOT)
    assert valid, message


def test_repository_governance_is_local_to_adopted_skill() -> None:
    assert not (ROOT / "agents" / "skills" / "skill-maintenance.md").exists()
    local = SKILL_ROOT / "references" / "repository-governance.md"
    text = local.read_text()
    assert "agents/AGENTS.md" in text
    assert "agents/roles/" in text
    assert "mapped" in text.lower()


def test_mapped_actions_conditionally_compose_skill_creator() -> None:
    paths = [
        "agents/skills/openspec-explore/SKILL.md",
        "agents/skills/openspec-change/SKILL.md",
        "agents/skills/openspec-review/SKILL.md",
        "agents/skills/implementation/SKILL.md",
        "agents/skills/implementation-review/SKILL.md",
    ]
    for path in paths:
        text = (ROOT / path).read_text()
        assert "agents/skills/skill-creator/SKILL.md" in text
        assert "repository Skills" in text or "Skill artifacts" in text

    agents = (ROOT / "agents" / "AGENTS.md").read_text()
    assert "action:skill-creator" not in agents
