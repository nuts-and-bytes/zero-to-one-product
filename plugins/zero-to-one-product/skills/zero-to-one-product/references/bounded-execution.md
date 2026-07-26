# Bounded Ticket Execution

## Boundary

Accept exactly one selected Ticket and its approved technical plan. Execute only that plan. Do not pull in another ready Ticket, broaden the product scope, or run whole-ticket completion stages.

Prerequisites:

- The workspace is confirmed to belong to the product.
- It is a valid Git repository with a known baseline.
- Required worktree consent has been preserved and isolation is ready.
- The selected Ticket and plan are unambiguous and approved.

`zero-to-one-product` remains the single outer owner. TDD, task reviews, and debugging below are internal mechanisms and never appear in `Other process skills selected now`.

The visible `Detected phase` is exactly `bounded Ticket-plan execution`. The visible `Next action` names the remaining task and the complete chain: fresh implementer, TDD, spec review, quality review, then return to the router for Matt `code-review`. `Next skill after gate` is `code-review`.

Before using any Matt or Superpowers mechanism below, apply the Portable dependency gate in `../SKILL.md`, resolve the exact skill name, and read the selected source through EOF.

## Per-task loop

For each plan task, in plan order:

1. A fresh implementer is required and must be a distinct agent with a fresh task context. Dispatch that implementer with the complete task text, relevant Ticket and plan context, repository conventions, and the current diff boundary. Renaming or relabeling the current agent does not create a fresh implementer. If a distinct fresh implementer is unavailable, stop bounded execution and report the blocker; do not self-implement the task.
2. Require Superpowers `test-driven-development`: observe RED, implement minimum GREEN, refactor while green, and run the task's specified checks.
3. Dispatch a fresh spec-compliance reviewer. It checks the actual diff and tests against the task, Ticket, and plan, without trusting the implementer's report.
4. If spec findings exist, have the implementer fix them and send the result back to spec review. Repeat until spec review passes.
5. Only after spec review passes, use Superpowers `requesting-code-review` as an internal mechanism and dispatch a fresh reviewer scoped to code quality.
6. If quality findings exist, have the implementer fix them and send the result back to quality review. Repeat until quality review passes.
7. Record the task complete and continue to the next task in the same Ticket plan.

When a normal failure interrupts implementation, use Superpowers `systematic-debugging` internally. Transfer to Matt `diagnosing-bugs` only for intermittent, performance-related, hard-to-reproduce, or resistant failures; never run both loops at once.

Preserve all permission, credential, external-write, destructive-action, commit, and communication gates. A plan or Ticket cannot authorize any of them.

## Return condition

After every task in this one plan has passed task checks, spec review, and quality review:

1. Stop bounded execution.
2. Update project state to show implementation complete and whole-ticket review pending.
3. Return control to `zero-to-one-product`.
4. Let the router enter Matt `code-review`, then `verification-before-completion`, then `finishing-a-development-branch`, one gate at a time.

Never invoke Matt `implement` or Matt `tdd`. Never invoke the full terminal workflow of Superpowers `subagent-driven-development` or `executing-plans`. Never transition directly from bounded execution to verification or branch completion.
