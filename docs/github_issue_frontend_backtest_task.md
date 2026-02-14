# Task: Fix portfolio rebalance visibility, weight display, and backtest behavior

## Background
Current system still has user-visible inconsistencies between monitoring views and expected portfolio behavior.

## Problems to fix
1. Portfolio monitoring page does not clearly reflect portfolio rebalancing changes over time.
2. Weight display is missing or not reliably shown in relevant views.
3. Backtest flow still needs refinement and stability improvements (input handling, diagnostics, and result consistency).

## Expected outcome
- Rebalance changes are visible and verifiable in the portfolio UI.
- Weights are displayed consistently and match backend calculation output.
- Backtest runs reliably across supported methods, with clear precheck/validation messaging and accurate output rendering.

## Acceptance criteria
- UI shows position/weight changes after rebalance without manual refresh confusion.
- Weight values are present, non-empty, and consistent with backend payload.
- Backtest methods run end-to-end or show actionable error details.
- Add/adjust tests for monitoring payload correctness and backtest API behavior.
