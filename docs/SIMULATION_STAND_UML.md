# Simulation stand UML and data-flow diagrams

This document describes the simulation stand as a ROS 2-oriented modular test bench.

## Component/data-flow diagram

```mermaid
flowchart LR
  Runner["scripts/run_wkr_experiments.py\nfactor matrix, ROS_DOMAIN_ID, manifest.csv"]
  Launch["swarm_core/launch/simulation.launch.py\nscenario_id, architecture, seed, run_id"]
  Scenario["config/scenarios.yaml\nS1-S6"]
  World["worlds/wkr_test_field_light.world\nheadless/light simulation world"]
  State["swarm_state_publisher\n/swarm/state"]
  Decision["decision_core_node\ncentral_a_star/reactive/rule_dec/decpomdp_heuristic"]
  Alloc["task_allocator_node\n/swarm/task_allocation"]
  Comm["communication_emulator\nlatency/loss diagnostics"]
  Metrics["metrics_calculator\n/swarm/metrics_json"]
  Supervisor["mission_supervisor\n/experiment/start, /experiment/complete"]
  Logger["experiment_logger\ntimeseries_metrics.csv, final_metrics.csv"]
  Analyze["analyze_wkr_results.py\nsummary, CI, comparisons"]
  Plot["plot_wkr_results.py\nPNG/SVG figures"]
  Validate["validate_results.py\ndata quality gates"]

  Runner --> Launch
  Scenario --> Runner
  Scenario --> Launch
  World --> Launch
  Launch --> State
  Launch --> Decision
  Launch --> Alloc
  Launch --> Comm
  Launch --> Metrics
  Launch --> Supervisor
  Launch --> Logger
  State -->|SwarmState| Decision
  State -->|SwarmState| Metrics
  State -->|SwarmState| Logger
  Decision -->|architecture_info| Logger
  Comm -->|latency/loss| Metrics
  Metrics -->|periodic metrics| Supervisor
  Metrics -->|periodic metrics| Logger
  Supervisor -->|start/complete events| Metrics
  Supervisor -->|complete event| Logger
  Logger --> Analyze
  Logger --> Plot
  Logger --> Validate
```

## Main data path

1. The experiment runner forms tuples `scenario_id x architecture x seed` and starts `simulation.launch.py`.
2. The launch file passes unified parameters to the simulation nodes.
3. `swarm_state_publisher` publishes agent states.
4. `metrics_calculator` computes coverage, connectivity, energy, and collisions.
5. `mission_supervisor` completes each run using success or timeout criteria.
6. `experiment_logger` writes one final row per `run_id` and a separate time-series CSV.
7. Analysis, plotting, and validation scripts consume `final_metrics.csv` without modifying source data.
```
