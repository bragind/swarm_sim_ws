# Swarm Simulation Stand

A reproducible ROS 2-oriented simulation stand for comparing distributed control architectures for a swarm of autonomous agents.

The project contains scripts for batch execution, scenario management, metric collection, data-quality validation, result aggregation, and figure generation. The current validated experiment set uses an accelerated deterministic headless kinematic simulation mode for high-volume repeatable runs.

## What this repository provides

- Batch execution of scenario/architecture/seed matrices.
- Four baseline/control architectures: `central_a_star`, `reactive`, `rule_dec`, and `decpomdp_heuristic`.
- Six scenario classes: nominal operation, dense obstacles, communication degradation, partial agent failure, computational degradation, and combined stress.
- Final metrics in `final_metrics.csv` and optional time-series metrics in `timeseries_metrics.csv`.
- Validation, analysis, and plotting scripts.
- Ready-to-use result tables and figures under `docs/tables` and `docs/figures`.

## Repository structure

```text
swarm_sim_ws/
├── docker/                 # Container/runtime environment assets
├── docs/                   # Diagrams, generated figures, generated tables
│   ├── figures/wkr/        # Published experiment figures in the source branch
│   ├── tables/wkr/         # Published experiment tables in the source branch
│   └── SIMULATION_STAND_UML.md
├── scripts/                # Batch runner, validation, analysis, plotting utilities
├── src/                    # ROS 2 packages and simulation nodes
├── tests/                  # Test and validation assets
└── README.md
```

## Current validated result set

The published diagnostic matrix contains 720 runs:

| Metric | Value |
|---|---:|
| Total runs | 720 |
| valid_success | 697 |
| valid_failure | 23 |
| diagnostic rows | 0 |
| incomplete_or_timeout | 0 |
| runner_timeout_reached | 0 |
| Overall success rate | 96.8% |

The matrix is:

```text
6 scenarios x 4 architectures x 30 seeds = 720 runs
```

Architectures used in the published matrix:

- `central_a_star` — centralized planning baseline.
- `reactive` — reactive local control baseline.
- `rule_dec` — decentralized rule-based algorithm.
- `decpomdp_heuristic` — Dec-POMDP-style heuristic correction policy.

## Simulation mode

The current validated run set uses:

```text
headless_fast_kinematic
```

This mode is intended for fast, deterministic, repeatable algorithmic testing. It is not a replacement for a full physics-level Gazebo/DDS validation campaign. Use it as the first layer of regression, benchmarking, and scenario-based comparison.

## Quick start

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

python3 scripts/run_wkr_experiments.py   --quick   --simulation-mode headless_fast_kinematic   --parallel 1   --output ~/sim_storage/swarm_quick

python3 scripts/validate_results.py   --input ~/sim_storage/swarm_quick/final_metrics.csv   --profile quick

python3 scripts/analyze_wkr_results.py   --input ~/sim_storage/swarm_quick/final_metrics.csv   --output ~/sim_storage/swarm_quick/analysis   --profile quick

python3 scripts/plot_wkr_results.py   --input ~/sim_storage/swarm_quick/final_metrics.csv   --output ~/sim_storage/swarm_quick/figures   --profile quick
```

## Full diagnostic run

```bash
python3 scripts/run_wkr_experiments.py   --full-diagnostic   --simulation-mode headless_fast_kinematic   --parallel 1   --seeds 43:72   --output ~/sim_storage/swarm_full_diagnostic

python3 scripts/validate_results.py   --input ~/sim_storage/swarm_full_diagnostic/final_metrics.csv   --profile full

python3 scripts/analyze_wkr_results.py   --input ~/sim_storage/swarm_full_diagnostic/final_metrics.csv   --output ~/sim_storage/swarm_full_diagnostic/analysis   --profile full

python3 scripts/plot_wkr_results.py   --input ~/sim_storage/swarm_full_diagnostic/final_metrics.csv   --output ~/sim_storage/swarm_full_diagnostic/figures   --profile full
```


## Running the simulation stand inside a container

The example below shows a typical Docker-based workflow. This is useful when you want a reproducible ROS 2 environment without preparing all dependencies on the host.

### Build the container image

```bash
cd swarm_sim_ws
docker build -t swarm-sim-stand -f docker/Dockerfile .
```

### Quick run in a container

```bash
mkdir -p $HOME/sim_storage

docker run --rm -it   -v "$(pwd)":/workspace/swarm_sim_ws   -v "$HOME/sim_storage":/sim_storage   -w /workspace/swarm_sim_ws   swarm-sim-stand   bash -lc '
    source /opt/ros/humble/setup.bash &&
    colcon build --symlink-install &&
    source install/setup.bash &&
    python3 scripts/run_wkr_experiments.py       --quick       --simulation-mode headless_fast_kinematic       --parallel 1       --output /sim_storage/swarm_quick &&
    python3 scripts/validate_results.py       --input /sim_storage/swarm_quick/final_metrics.csv       --profile quick &&
    python3 scripts/analyze_wkr_results.py       --input /sim_storage/swarm_quick/final_metrics.csv       --output /sim_storage/swarm_quick/analysis       --profile quick &&
    python3 scripts/plot_wkr_results.py       --input /sim_storage/swarm_quick/final_metrics.csv       --output /sim_storage/swarm_quick/figures       --profile quick
  '
```

### Full diagnostic run in a container

```bash
docker run --rm -it   -v "$(pwd)":/workspace/swarm_sim_ws   -v "$HOME/sim_storage":/sim_storage   -w /workspace/swarm_sim_ws   swarm-sim-stand   bash -lc '
    source /opt/ros/humble/setup.bash &&
    colcon build --symlink-install &&
    source install/setup.bash &&
    python3 scripts/run_wkr_experiments.py       --full-diagnostic       --simulation-mode headless_fast_kinematic       --parallel 1       --seeds 43:72       --output /sim_storage/swarm_full_diagnostic &&
    python3 scripts/validate_results.py       --input /sim_storage/swarm_full_diagnostic/final_metrics.csv       --profile full &&
    python3 scripts/analyze_wkr_results.py       --input /sim_storage/swarm_full_diagnostic/final_metrics.csv       --output /sim_storage/swarm_full_diagnostic/analysis       --profile full &&
    python3 scripts/plot_wkr_results.py       --input /sim_storage/swarm_full_diagnostic/final_metrics.csv       --output /sim_storage/swarm_full_diagnostic/figures       --profile full
  '
```

> Results are stored on the host under `$HOME/sim_storage`, mounted into the container as `/sim_storage`.

## Result artifacts

This documentation package includes neutral copies of the published tables and recreated figures based on the same metric values:

```text
tables/
├── validation_summary.csv
├── architecture_run_distribution.csv
├── scenario_run_distribution.csv
├── success_rate_by_architecture.csv
├── success_rate_by_scenario.csv
└── success_rate_by_scenario_architecture.csv

figures/
├── fig_validation_outcomes.png
├── fig_runs_by_architecture.png
├── fig_runs_by_scenario.png
├── fig_success_rate_by_architecture.png
├── fig_success_rate_by_scenario.png
└── fig_success_rate_heatmap.png
```

## Metric interpretation

The most important metrics are:

- `success_flag` — whether the run completed according to the mission criteria.
- `coverage_ratio` — how effectively the swarm covered the target area or mission objective.
- `connectivity_coeff` — quality of swarm connectivity under normal and degraded communication.
- `collisions_count` — number of detected collisions or unsafe contacts.
- `total_energy_wh` — energy proxy accumulated during the run.
- `integral_score` — aggregate normalized performance indicator used for architecture ranking.

`success_rate` is useful as a health and validity indicator. For architecture comparison, the integral score, connectivity, energy, and collision metrics are more informative.

## Main result highlights

Across scenarios S1-S6, the `decpomdp_heuristic` architecture has the best integral score and best connectivity in the published mean-metric tables. `central_a_star` is the most energy-efficient architecture in the published best-architecture table. Scenario S6 is the most discriminative stress test: the reactive baseline drops to 23.3% success and has the weakest integral score.

## MARL/proof mode note

The current validated matrix should be treated as a deterministic diagnostic benchmark. A full learned-policy proof mode requires a trained checkpoint such as:

```text
models/marl/wkr_qmix_policy.pt
```

A test checkpoint is suitable only for plumbing/smoke checks and must not be used as evidence of learned-policy performance.

## License and usage

Use this repository as a reproducible simulation test bench for swarm-control algorithms, regression checks, and architecture comparison under controlled scenarios.
