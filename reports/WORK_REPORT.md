# Work Report: validation package for the swarm simulation stand

## Objective

Prepare a clean, reproducible documentation and reporting package for a ROS 2-oriented simulation stand of autonomous swarm agents. The package describes how to run the stand, how the modules interact, which metrics are collected, and what the published diagnostic experiment set shows.

## Completed work

1. The repository structure was reviewed and the simulation-stand description was separated from academic wording.
2. The documentation language was normalized so that the project is presented as an engineering simulation stand.
3. An updated README was prepared with both local and container-based execution.
4. A set of summary tables for the diagnostic matrix was generated.
5. A set of figures was prepared to visualize run distribution and success rates.
6. A UML/data-flow description of the simulation pipeline was prepared.

## Experiment matrix

The published matrix contains six scenarios, four architectures, and thirty seed values for each scenario/architecture pair:

```text
6 x 4 x 30 = 720 runs
```

Scenario classes:

- S1: nominal navigation.
- S2: dense-obstacle environment.
- S3: communication degradation.
- S4: partial agent failure.
- S5: computational degradation.
- S6: combined stress.

Architectures:

- Central-A*.
- Reactive control.
- Rule-based decentralized control.
- Dec-POMDP with heuristic correction.

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

From the perspective of runner timeouts and malformed diagnostic rows, the result set is clean.

## Tables

- `../tables/validation_summary.csv`
- `../tables/architecture_run_distribution.csv`
- `../tables/scenario_run_distribution.csv`
- `../tables/success_rate_by_architecture.csv`
- `../tables/success_rate_by_scenario.csv`
- `../tables/success_rate_by_scenario_architecture.csv`

## Figures

### 1. Validation outcomes

![Validation outcomes](../figures/fig_validation_outcomes.png)

The chart shows that the vast majority of runs ended as valid successes, while valid failures occupy only a small fraction of the full matrix.

### 2. Runs per architecture

![Runs per architecture](../figures/fig_runs_by_architecture.png)

Each architecture was executed the same number of times, which makes direct comparison fair.

### 3. Runs per scenario

![Runs per scenario](../figures/fig_runs_by_scenario.png)

Each scenario was executed the same number of times. This makes the experiment matrix balanced.

### 4. Success rate by architecture

![Success rate by architecture](../figures/fig_success_rate_by_architecture.png)

Three architectures achieve 100% success in the published diagnostic matrix. The reactive baseline shows a lower aggregate success rate due to its behavior in the S6 stress scenario.

### 5. Success rate by scenario

![Success rate by scenario](../figures/fig_success_rate_by_scenario.png)

Scenarios S1-S5 do not cause validation problems. The main drop is observed in S6, which acts as the primary stress test of the stand.

### 6. Scenario/architecture success heatmap

![Success rate heatmap](../figures/fig_success_rate_heatmap.png)

The heatmap makes it clear that the only problematic pair is the combination of scenario S6 and the reactive architecture. All other scenario/architecture pairs show full success.

## Main observations

1. All architectures are stable in scenarios S1-S5.
2. In scenario S6, the reactive baseline drops to 23.3% success, while the other architectures remain at 100%.
3. The diagnostic matrix is balanced: each architecture and each scenario has the same number of runs.
4. The result set is clean in terms of runner timeouts and malformed diagnostic rows.
5. Scenario S6 is the key stress scenario because it combines obstacles, communication degradation, failures, and computational degradation.

## Engineering interpretation

The current package should be treated as a deterministic benchmark for checking the simulation pipeline, the data-collection contour, and the comparative behavior of control architectures. It is suitable for regression testing and algorithmic comparison in headless kinematic mode. Claims that depend on realistic dynamics, middleware timing, sensor behavior, and actuator behavior require a separate stage of more physically faithful validation.

## Delivered materials

```text
README.md
README_RU.md
reports/WORK_REPORT.md
reports/WORK_REPORT_RU.md
docs/SIMULATION_STAND_UML.md
tables/*.csv
figures/*.png
```
