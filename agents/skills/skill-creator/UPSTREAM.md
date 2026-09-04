# Anthropic skill-creator upstream provenance

This directory adopts the original Anthropic `skill-creator` package as the reusable repository baseline.

## Immutable upstream baseline

- Repository: `anthropics/skills`
- Upstream path: `skills/skill-creator/`
- Commit: `0a64e398ec6bb34a494f0c347e8ccae53a862f8e`
- Subtree: `3cf9a8db32597ba3e24b584a3d696f4e11c7d7b6`

The upstream-origin files listed below are expected to remain byte-for-byte identical to that pinned subtree during the initial adoption. Their Git blob SHA is the deterministic integrity basis for later comparison.

| Upstream path | Git blob SHA |
| --- | --- |
| `LICENSE.txt` | `4f881c52d1f72f4cfb720e339e2d35c3058d01a9` |
| `SKILL.md` | `65b3a402dbd09b8e83f9d637c6b553875189085c` |
| `agents/analyzer.md` | `14e41d6068635f4dd3fb878fd1626312395dda63` |
| `agents/comparator.md` | `80e00eb45db3ee53a132fc2ba97fd59a7339e563` |
| `agents/grader.md` | `558ab05c0a9a8bb062ef4c51823d4d76c3acf7c4` |
| `assets/eval_review.html` | `938ff32aed9bffabf723bd5492d720f4736c8e4d` |
| `eval-viewer/generate_review.py` | `7fa5978631fed1ed545591dbb2b0eb21ce3f3d08` |
| `eval-viewer/viewer.html` | `6d8e96348a02e66c3363d2ff3b3ae58ac11e6382` |
| `references/schemas.md` | `b6eeaa2d4a34c1653069585c6c5603da39a5bdbe` |
| `scripts/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` |
| `scripts/aggregate_benchmark.py` | `3e66e8c105be9bab9f0e9c61f0d1482619401580` |
| `scripts/generate_report.py` | `959e30a0014ec165c41a2bb7420b7dfe1416bbac` |
| `scripts/improve_description.py` | `06bcec76122446986e3610c20a39c466de36f495` |
| `scripts/package_skill.py` | `f48eac444656ddc41204aac1760a217951ce609e` |
| `scripts/quick_validate.py` | `ed8e1dddce77b16af13c6f36b3fe86c4ac7c590c` |
| `scripts/run_eval.py` | `e58c70bea39d5b252a1e819f242bbdcdf20e8b87` |
| `scripts/run_loop.py` | `30a263d674ef19de11c756d6f7537f91a421909e` |
| `scripts/utils.py` | `51b6a07dd57174197a937034b7eecebd5768ff8a` |

## Added

| Repository path | Reason | Maintenance implication |
| --- | --- | --- |
| `UPSTREAM.md` | Repository-owned immutable provenance and explicit local delta ledger are required so future refreshes can distinguish original upstream content from intentional repository additions without modifying upstream-origin files. | Preserve/re-evaluate this ledger on every governed upstream refresh. |
| `references/repository-governance.md` | Repository-specific integration and authority constraints must remain separate from the unchanged Anthropic baseline while being progressively loadable by governed Skill work. These constraints belong with the adopted Skill integration rather than global runtime or role authority because they specialize how this reusable Skill is consumed in this repository. | Re-evaluate against current `agents/AGENTS.md`, role, and mapped-action owners whenever Skill governance changes. |

## Deleted

none — the initial adoption intentionally omits no upstream file or capability from the pinned subtree.

## Modified

none — the initial adoption intentionally patches no upstream-origin file. Repository-specific integration is represented only by the Added files above.

## Refresh rule

A future upstream update must use another immutable revision and explicitly reassess this complete Added / Deleted / Modified ledger. Mutable upstream `main` is never runtime authority.