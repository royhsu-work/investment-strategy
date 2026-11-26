## Why

The terminal writer emits one GitHub PATCH that closes an Issue and removes its workflow routing. The existing consumer requires the label-removal event to sort before closure and rejects otherwise valid existing retirements. This was observed on #481 and #458 and leaves #478 suspended on #481.

## What Changes

- Specify the causal contract for terminal retirement independently of the order in which GitHub records the two effects.
- Require any attributed removal to match the terminal Action exactly and to be unique.
- Reuse the shared formal qualification boundary for fresh dependency and terminal postcondition observation. Do not replay writes or rewrite evidence.
- Verify the release first against exact production timelines, then against the actual post-deployment native Dispatch. Preserve all dependencies and unrelated workflow behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scheduled-agent-workflow`: terminal retirement and its fresh proof.

## Impact

Shared terminal qualification and its public consumers, existing quality/strict validation, and post-deployment native Dispatch evidence. Refs #485; #486 remains historical input, not a gate. No change to #479, architecture work in #478, or tool-layer scope in #483.
