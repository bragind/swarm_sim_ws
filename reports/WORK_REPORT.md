# Work Report: Swarm Simulation Stand Validation Package

## Objective

Prepare a clean, reproducible documentation and reporting package for a ROS 2-oriented swarm simulation stand. The package describes how to run the stand, how modules interact, which metrics are collected, and what the published diagnostic result set shows.

## Completed work

1. Reviewed the repository structure and separated the simulation stand description from academic wording.
2. Normalized the documentation language so the project is presented as an engineering simulation stand.
3. Reused the published tables from `docs/tables/wkr` and converted them into neutral table names.
4. Recreated the main figures from the published mean metrics table.
5. Prepared an updated README with quick-start, full diagnostic run, metric interpretation, and result highlights.
6. Prepared a UML/data-flow description of the simulation pipeline.

## Experiment matrix

The published matrix contains six scenarios, four architectures, and thirty seeds per scenario/architecture pair:

```text
6 x 4 x 30 = 720 runs
```

Scenario classes:

- S1: nominal navigation.
- S2: dense obstacle environment.
- S3: communication degradation.
- S4: partial agent failure.
- S5: computational degradation.
- S6: combined stress.

Architectures:

- Central-A*.
- Reactive control.
- Decentralized rule-based.
- Dec-POMDP + heuristic correction.

## Validation summary

| Metric | Value |
|---|---:|
| Total runs | 720 |
| valid_success | 697 |
| valid_failure | 23 |
| diagnostic rows | 0 |
| incomplete_or_timeout | 0 |
| runner_timeout_reached | 0 |
| Overall success rate | 96.8% |

The result set is clean from the point of view of runner timeouts and malformed diagnostic rows.

## Main observations from the published metrics

1. All architectures are stable in S1-S5 by success rate.
2. In S6, the reactive baseline drops to 23.3% success, while the other architectures remain at 100%.
3. `Dec-POMDP + heuristic correction` has the best integral score in all six scenarios.
4. `Dec-POMDP + heuristic correction` also has the best connectivity in all six scenarios.
5. `Central-A*` is the most energy-efficient architecture in the best-architecture table.
6. S6 is the key stress scenario because it combines obstacles, communication degradation, failures, and computational degradation.

## Generated figures

- `fig_validation_outcomes.png` — valid success/failure distribution.
- `fig_success_rate_by_scenario.png` — success rate by scenario and architecture.
- `fig_connectivity_by_architecture.png` — mean connectivity by scenario and architecture.
- `fig_coverage_by_architecture.png` — mean coverage ratio by scenario and architecture.
- `fig_collisions_by_architecture.png` — mean collision count by scenario and architecture.
- `fig_energy_by_architecture.png` — mean energy by scenario and architecture.
- `fig_integral_score.png` — mean integral score by scenario and architecture.

## Engineering interpretation

The current package should be interpreted as a deterministic benchmark for validating the simulation pipeline, data collection path, and comparative behavior of control architectures. It is suitable for regression testing and algorithmic comparison in the headless kinematic mode. A separate physics-level validation stage is still needed for claims that depend on realistic dynamics, middleware timing, or sensor/actuator effects.

## Deliverables

```text
README.md
reports/WORK_REPORT.md
docs/SIMULATION_STAND_UML.md
tables/*.csv
tables/*.md
figures/*.png
```
