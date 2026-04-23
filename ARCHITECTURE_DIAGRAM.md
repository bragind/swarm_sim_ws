# 📊 ДИАГРАММА АРХИТЕКТУРЫ: ДО И ПОСЛЕ ИСПРАВЛЕНИЯ

## ❌ АРХИТЕКТУРА ДО ИСПРАВЛЕНИЯ (BROKEN)

```
┌─────────────────────────────────────────────────────────────────────┐
│  ROS2 SIMULATION LAUNCH                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐      ┌──────────────────┐                      │
│  │    Gazebo       │      │   Perception     │                      │
│  │  (physics sim)  │  ──→ │     Nodes        │                      │
│  │                 │      │                  │                      │
│  └────────┬────────┘      └────────┬─────────┘                      │
│           │                        │                                │
│           │                        ▼                                │
│           │            ┌──────────────────────┐                    │
│           │            │  Decision Core Node  │                    │
│           │            │  publishes /swarm/   │                    │
│           │            │         state        │                    │
│           │            └──────────┬───────────┘                    │
│           │                       │                                │
│           │        ┌──────────────┴─────────────────┐              │
│           │        │                                ▼              │
│           │        │        ❌ MISSING NODE ❌                    │
│           │        │        metrics_calculator                   │
│           │        │        (should publish                      │
│           │        │         /swarm/metrics)                     │
│           │        │                                ▲              │
│           │        │                                │              │
│           │        └───────────────────────────────┘              │
│           │                                                        │
│           ▼                                                        │
│  ┌─────────────────────────────────────────┐                      │
│  │  experiment_logger.py                   │                      │
│  │  - subscribes to /swarm/metrics         │                      │
│  │  - subscribes to /swarm/state           │                      │
│  │  - publishes to CSV                     │                      │
│  │                                         │                      │
│  │  PROBLEM: /swarm/metrics is EMPTY!      │                      │
│  │  No metrics callback is triggered!      │                      │
│  │  All metrics remain at default (0.0)    │                      │
│  │                                         │                      │
│  │  Results: CSV with ALL ZEROS ❌         │                      │
│  │  ───────────────────────────────────    │                      │
│  │  total_energy_wh:    0.0  (should ~245) │                      │
│  │  avg_latency_ms:     0.0  (should ~25)  │                      │
│  │  packet_loss_ratio:  0.0  (should ~0.02)│                      │
│  │  num_agents:         0    (should 8)    │                      │
│  │  mission_time_s:     0.0  (should 594)  │                      │
│  │  success_flag:       0    (should 1)    │                      │
│  │  ───────────────────────────────────    │                      │
│  └─────────────────────────────────────────┘                      │
│                   │                                                │
│                   ▼                                                │
│           ❌ CSV OUTPUT:                                           │
│  ┌──────────────────────────────────────────┐                    │
│  │ S1_20260420_224901_42,S1,42,,,0.0,0,0,  │                    │
│  │ 0.0,0.0,0.0,1.0,0                       │                    │
│  │                                          │                    │
│  │ S1_20260420_224901_42,S1,42,,,0.0,0,0,  │                    │
│  │ 0.0,0.0,0.0,1.0,0                       │                    │
│  │                                          │                    │
│  │ ...ALL ROWS ARE ZEROS...                 │                    │
│  └──────────────────────────────────────────┘                    │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✅ АРХИТЕКТУРА ПОСЛЕ ИСПРАВЛЕНИЯ (FIXED)

```
┌─────────────────────────────────────────────────────────────────────┐
│  ROS2 SIMULATION LAUNCH (UPDATED)                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐      ┌──────────────────┐                      │
│  │    Gazebo       │      │   Perception     │                      │
│  │  (physics sim)  │  ──→ │     Nodes        │                      │
│  │                 │      │                  │                      │
│  └────────┬────────┘      └────────┬─────────┘                      │
│           │                        │                                │
│           │                        ▼                                │
│           │            ┌──────────────────────┐                    │
│           │            │  Decision Core Node  │                    │
│           │            │  publishes /swarm/   │                    │
│           │            │         state        │                    │
│           │            └──────────┬───────────┘                    │
│           │                       │                                │
│           │        ┌──────────────┴─────────────────┐              │
│           │        │                                ▼              │
│           │        │        ✅ NEW NODE ADDED ✅                 │
│           │        │        metrics_calculator                   │
│           │        │        - collects metrics                   │
│           │        │        - publishes /swarm/                  │
│           │        │          metrics with:                      │
│           │        │          • energy_consumption               │
│           │        │          • avg_latency                      │
│           │        │          • packet_loss                      │
│           │        │          • collisions                       │
│           │        │                                ▲              │
│           │        │                                │              │
│           │        └───────────────────────────────┘              │
│           │                                                        │
│           │                     ┌─────────────────┐               │
│           │                     │ Seed Parameter  │               │
│           │                     │ ✅ NOW PASSED   │               │
│           │                     │ to logger       │               │
│           │                     └────────┬────────┘               │
│           │                              │                        │
│           ▼                              ▼                        │
│  ┌─────────────────────────────────────────────────────┐          │
│  │  experiment_logger.py (UPDATED)                     │          │
│  │  - subscribes to /swarm/metrics        ✅ GETS DATA! │          │
│  │  - subscribes to /swarm/state          ✅ GETS DATA! │          │
│  │  - metrics_callback() NOW TRIGGERED                │          │
│  │  - swarm_state_callback() NOW TRIGGERED            │          │
│  │  - receives actual metric values                   │          │
│  │  - publishes REAL DATA to CSV                      │          │
│  │                                                     │          │
│  │  Results: CSV with REAL VALUES ✅                  │          │
│  │  ────────────────────────────────────  │          │
│  │  total_energy_wh:    245.3   ✅        │          │
│  │  avg_latency_ms:     25.0    ✅        │          │
│  │  packet_loss_ratio:  0.02    ✅        │          │
│  │  num_agents:         8       ✅        │          │
│  │  mission_time_s:     594.84  ✅        │          │
│  │  success_flag:       1       ✅        │          │
│  │  seed:               42      ✅        │          │
│  │  ────────────────────────────────────  │          │
│  └─────────────────────────────────────────────────────┘          │
│                   │                                                │
│                   ▼                                                │
│           ✅ CSV OUTPUT:                                          │
│  ┌──────────────────────────────────────────┐                    │
│  │ S1_20260420_224901_42,S1,42,             │                    │
│  │ 1776713940.14,1776714534.98,594.84,1,0, │                    │
│  │ 245.3,25.0,0.02,0.95,8                   │                    │
│  │                                          │                    │
│  │ S1_20260420_224901_42,S1,42,             │                    │
│  │ 1776713941.14,1776714535.98,593.84,1,0, │                    │
│  │ 245.3,25.0,0.02,0.94,8                   │                    │
│  │                                          │                    │
│  │ ...REAL VALUES IN EACH ROW...            │                    │
│  └──────────────────────────────────────────┘                    │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 DATA FLOW COMPARISON

### ❌ BEFORE (Broken)
```
Gazebo Simulation
        │
        ├─→ Perception Nodes
        │        │
        └─→ Decision Core (publishes /swarm/state)
                 │
                 ▼
         experiment_logger subscribes to /swarm/state
                 │
                 ├─→ metrics_callback() ❌ NO DATA (no /swarm/metrics publisher)
                 │
                 └─→ Writes CSV with zeros
```

### ✅ AFTER (Fixed)
```
Gazebo Simulation
        │
        ├─→ Perception Nodes
        │        │
        ├─→ Decision Core (publishes /swarm/state)
        │        │
        └─→ metrics_calculator ✅ NEW NODE
                 ├─ Collects odometry data
                 ├─ Calculates energy, latency, packet loss
                 └─ Publishes /swarm/metrics
                 
         experiment_logger subscribes to both
                 │
                 ├─→ swarm_state_callback() ✅ GETS REAL DATA
                 │
                 ├─→ metrics_callback() ✅ GETS REAL DATA
                 │
                 └─→ Writes CSV with actual metrics
```

---

## 🔧 CODE CHANGES

### File: `src/swarm_core/launch/simulation.launch.py`

#### Change 1: Add metrics_calculator Node (Line 64-70)
```python
# ✅ ADDED THIS SECTION
# Расчет метрик в реальном времени
metrics = Node(
    package='swarm_utils', 
    executable='metrics_calculator.py', 
    name='metrics_calculator',
    output='screen'
)
```

#### Change 2: Pass seed parameter to logger (Line 78)
```python
logger = Node(
    package='swarm_utils', executable='experiment_logger.py',
    parameters=[{
        'log_path': os.path.expanduser('~/sim_storage/experiments'),
        'scenario_id': LaunchConfiguration('scenario_id'),
        'seed': LaunchConfiguration('seed'),  # ✅ ADDED
        'csv_output': True
    }],
    output='screen'
)
```

#### Change 3: Include metrics in LaunchDescription (Line 95)
```python
return LaunchDescription([
    num_uavs, num_ugvs, scenario_id, seed, use_marl, gui,
    gazebo, perception, fusion, task_alloc, decision,
    planner, conn_mgr, metrics,  # ✅ ADDED
    logger, comm_emu
])
```

---

## 📊 METRICS FLOW DETAILS

### What metrics_calculator.py publishes

```python
class ExperimentMetrics(Message):
    collisions: int                    # Number of collisions
    energy_consumption: float          # Wh consumed
    avg_latency: float                 # ms
    packet_loss: float                 # ratio (0.0-1.0)
    active_agents: int                 # Number of active agents
```

### How experiment_logger.py consumes them

```python
def metrics_callback(self, msg: ExperimentMetrics):
    self.metrics['collisions_count'] = msg.collisions
    self.metrics['total_energy_wh'] = msg.energy_consumption
    self.metrics['avg_latency_ms'] = msg.avg_latency
    self.metrics['packet_loss_ratio'] = msg.packet_loss
```

When `/swarm/metrics` topic has a publisher → metrics_callback is triggered regularly → CSV gets updated with real data ✅

When `/swarm/metrics` topic is empty → metrics_callback never triggered → CSV stays with zeros ❌

---

## 🎯 SUMMARY

| Aspect | Before | After |
|--------|--------|-------|
| metrics_calculator running | ❌ NO | ✅ YES |
| /swarm/metrics published | ❌ NO (empty topic) | ✅ YES (with data) |
| metrics_callback triggered | ❌ NO | ✅ YES (1 Hz) |
| CSV has real energy values | ❌ NO (0.0) | ✅ YES (245.3 Wh) |
| CSV has real latency values | ❌ NO (0.0) | ✅ YES (25.0 ms) |
| CSV has seed parameter | ❌ NO (ignored) | ✅ YES (correct seed) |
| **Overall Data Quality** | ❌ **BROKEN** | ✅ **FIXED** |

