## Why

The same terminal effect is accepted by the writer but rejected by a later reader when GitHub records closure before Action-route removal. This happened on [#481](https://github.com/royhsu-work/investment-strategy/issues/481#issuecomment-7188932613) and [#458](https://github.com/royhsu-work/investment-strategy/issues/458#issuecomment-7078971489), and [#478's existing prerequisite](https://github.com/royhsu-work/investment-strategy/issues/478#issuecomment-7171259065) remains unsatisfied. The authoritative scope, rejected alternatives, and feasibility evidence are in the [manual Explore on #485](https://github.com/royhsu-work/investment-strategy/issues/485#手動-leadexplore-結論可進提案).

## What Changes

- Qualify the same exact terminal retirement regardless of the relative order of its two effects. Preserve result-before-effect causality, exact Action identity, bounded cardinality, complete evidence, fresh closed/no-route observation, and no replay.
- Reuse the existing formal qualification owner across affected readers. Do not change the writer, reroute completed Issues, remove dependencies, or create a new dispatcher.
- Keep #485 on the manual OpenSpec and independent maintenance path. Use the existing native Dispatch once after deployment to prove live release of the existing #481 edge, not to advance #485. No schedule is required.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scheduled-agent-workflow`: exact terminal retirement qualification for fresh observation and prerequisite release.

## Impact

Terminal qualification, its existing caller entry points, and the existing CI quality workflow ordering needed to prove Test First. No repository Skill maintenance, investment behavior, new gate, #479 retirement, #478 architecture work, or #483 tool-layer work. Refs #485.
