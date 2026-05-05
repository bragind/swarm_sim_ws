# UML-диаграмма стенда симуляции

```mermaid
flowchart LR
  Runner["scripts/run_wkr_experiments.py<br/>factor matrix, ROS_DOMAIN_ID, manifest.csv"]
  Launch["swarm_core/launch/simulation.launch.py<br/>scenario_id, architecture, seed, run_id"]
  Scenario["config/scenarios.yaml<br/>S1-S6"]
  World["worlds/wkr_test_field_light.world<br/>headless Gazebo/light SDF"]

  State["swarm_state_publisher<br/>/swarm/state"]
  Decision["decision_core_node<br/>central_a_star/reactive/rule_dec/marl_decpomdp"]
  Alloc["task_allocator_node<br/>/swarm/task_allocation"]
  Comm["communication_emulator<br/>latency/loss diagnostics"]
  Metrics["metrics_calculator<br/>/swarm/metrics_json"]
  Supervisor["mission_supervisor<br/>/experiment/start, /experiment/complete"]
  Logger["experiment_logger<br/>timeseries_metrics.csv, final_metrics.csv"]
  Analyze["analyze_wkr_results.py<br/>summary, CI, comparisons"]
  Plot["plot_wkr_results.py<br/>SVG/PNG figures"]
  Validate["validate_results.py<br/>data quality gates"]

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

## Основной поток данных

1. Runner формирует пары `scenario_id x architecture x seed` и запускает `simulation.launch.py`.
2. Launch передает единые параметры всем узлам стенда.
3. `swarm_state_publisher` публикует состояние агентов, `metrics_calculator` считает coverage/connectivity/energy/collisions.
4. `mission_supervisor` завершает run по критериям успеха или timeout.
5. `experiment_logger` пишет одну финальную строку на `run_id` и отдельный timeseries CSV.
6. Analyze/plot/validate работают только с `final_metrics.csv`, не меняя исходные данные.
