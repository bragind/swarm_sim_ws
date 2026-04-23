# 🔴 АНАЛИЗ ПРОБЛЕМЫ НУЛЕВЫХ МЕТРИК в swarm_sim_ws

## 📊 Проблема
Все метрики в CSV/JSON результатах содержат нули:
```csv
mission_time_s,0.0
success_flag,0
collisions_count,0
total_energy_wh,0.0
avg_latency_ms,0.0
packet_loss_ratio,0.0
num_agents,0  # Должно быть 8
```

Но в JSON финального результата:
```json
{
  "mission_time_s": 594.8,
  "num_agents": 8,
  ...
}
```

---

## 🔍 ГЛАВНАЯ ПРИЧИНА: MISSING METRICS_CALCULATOR NODE

### Архитектура потока данных метрик

```
Симуляция (Gazebo)
    ↓
Узлы восприятия (perception_node.py)
    ↓
Узлы решения (decision_core_node.py) → публикует /swarm/state
    ↓
metrics_calculator.py → должен публиковать /swarm/metrics ❌ НЕ ЗАПУСКАЕТСЯ!
    ↓
experiment_logger.py → подписывается на /swarm/metrics (не получает данные!)
    ↓
CSV/JSON файлы (с нулевыми метриками)
```

### 📋 Соответствие в launch файле

**Файл**: `src/swarm_core/launch/simulation.launch.py` (строки 74-95)

**ЧТО ЗАПУСКАЕТСЯ:**
```python
logger = Node(
    package='swarm_utils', 
    executable='experiment_logger.py',  # ✅ ЕСТЬ
    ...
)

comm_emu = Node(
    package='swarm_utils', 
    executable='communication_emulator.py',  # ✅ ЕСТЬ
    ...
)
```

**ЧТО НЕ ЗАПУСКАЕТСЯ:**
```python
# ❌ metrics_calculator.py НЕ В СПИСКЕ!
```

---

## 🔴 ДЕТАЛЬНЫЙ АНАЛИЗ КАЖДОГО НУЛЕВОГО ЗНАЧЕНИЯ

### 1. **total_energy_wh = 0.0** ❌

**Причина**: Callback `metrics_callback()` никогда не вызывается
- `experiment_logger.py` подписывается на `/swarm/metrics`
- `metrics_calculator.py` публикует на `/swarm/metrics`
- Но `metrics_calculator.py` не запущен!
- Результат: `self.metrics['total_energy_wh'] = 0.0` (default value)

**Источник метрик в коде:**
```python
# experiment_logger.py, line 79
def metrics_callback(self, msg: ExperimentMetrics):
    self.metrics['collisions_count'] = msg.collisions
    self.metrics['total_energy_wh'] = msg.energy_consumption  # ← Никогда не получает данные
    self.metrics['avg_latency_ms'] = msg.avg_latency
    self.metrics['packet_loss_ratio'] = msg.packet_loss
```

### 2. **avg_latency_ms = 0.0** ❌
Та же причина - `metrics_calculator.py` не запущен

### 3. **packet_loss_ratio = 0.0** ❌
Та же причина - `metrics_calculator.py` не запущен

### 4. **num_agents = 0** ❌ (в CSV)

**Частичная причина**: `num_agents` устанавливается при первом `/swarm/state` сообщении
```python
# experiment_logger.py, line 68
def swarm_state_callback(self, msg: SwarmState):
    if self.start_time is None:
        self.start_time = self.get_clock().now().nanoseconds / 1e9
        self.metrics['start_time'] = self.start_time
        self.metrics['num_agents'] = len(msg.agents)  # ← Зависит от /swarm/state
```

Но в JSON это значение есть (8), значит:
- Callback вызвался один раз
- Но в CSV - он записан как 0 потому что либо:
  - CSV создается ДО первого сообщения `/swarm/state`, либо
  - CSV расписывается периодически (каждую 1 сек) и переписывает значение

### 5. **collisions_count = 0** ❌
Та же причина - `metrics_callback()` не вызывается (нет `/swarm/metrics`)

### 6. **mission_time_s = 0.0** (в CSV)

**Причина**: Неправильное логирование или вычисление
```python
# experiment_logger.py, line 119-120
if self.start_time is not None:
    current_time = self.get_clock().now().nanoseconds / 1e9
    self.metrics['mission_time_s'] = current_time - self.start_time
```

При логировании в CSV - вычисляется корректно (594.8 сек в JSON)
Но CSV может быть перезаписан ДО finalize с нулевым значением, или
логирование периодическое может перезаписать?

### 7. **success_flag = 0** ❌

**Причина 1**: Timeout на 120 секунд с `success=False`
```python
# experiment_logger.py, line 94-96
def on_timeout(self):
    self.get_logger().warn('Timeout reached, finalizing experiment...')
    self.finalize_experiment(success=False)  # ← success=False!
```

**Причина 2**: Нет издателя для `/experiment/complete`
- Ничто не публикует на `/experiment/complete`
- Поэтому полагаются на timeout
- И timeout = False success

---

## 🛠️ РЕШЕНИЕ

### СРОЧНО ТРЕБУЕТСЯ:

#### 1. **Добавить metrics_calculator в launch** (CRITICAL)

**Файл**: `src/swarm_core/launch/simulation.launch.py`

**Добавить Node:**
```python
metrics = Node(
    package='swarm_utils',
    executable='metrics_calculator.py',
    name='metrics_calculator',
    output='screen'
)

return LaunchDescription([
    num_uavs, num_ugvs, scenario_id, seed, use_marl, gui,
    gazebo, perception, fusion, task_alloc, decision,
    planner, conn_mgr, logger, comm_emu,
    metrics  # ← ДОБАВИТЬ СЮДА
])
```

#### 2. **Передать seed параметр в experiment_logger** (HIGH)

**Текущее состояние:**
```python
logger = Node(
    package='swarm_utils', executable='experiment_logger.py',
    parameters=[{
        'log_path': os.path.expanduser('~/sim_storage/experiments'),
        'scenario_id': LaunchConfiguration('scenario_id'),
        'csv_output': True
        # ← seed НЕ передается!
    }],
    ...
)
```

**Исправить на:**
```python
logger = Node(
    package='swarm_utils', executable='experiment_logger.py',
    parameters=[{
        'log_path': os.path.expanduser('~/sim_storage/experiments'),
        'scenario_id': LaunchConfiguration('scenario_id'),
        'seed': LaunchConfiguration('seed'),  # ← ДОБАВИТЬ
        'csv_output': True
    }],
    ...
)
```

#### 3. **Добавить издателя для /experiment/complete** (MEDIUM)

Нужен узел, который:
- Отслеживает завершение миссии
- Публикует Bool true на `/experiment/complete`
- Позволяет graceful shutdown

---

## 📈 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ ПОСЛЕ ИСПРАВЛЕНИЙ

```csv
run_id,scenario_id,seed,start_time,end_time,mission_time_s,success_flag,collisions_count,total_energy_wh,avg_latency_ms,packet_loss_ratio,connectivity_coeff,num_agents
S1_20260420_224901_42,S1,42,1776713940.15,1776714534.99,594.84,1,0,245.3,25.0,0.02,0.95,8
```

Вместо:
```csv
S1_20260420_224901_42,S1,42,,,0.0,0,0,0.0,0.0,0.0,1.0,0
```

---

## 📍 ЗАТРОНУТЫЕ ФАЙЛЫ

| Файл | Проблема | Исправление |
|------|----------|-------------|
| `src/swarm_core/launch/simulation.launch.py` | metrics_calculator не запущен, seed не передан | Добавить Node для metrics_calculator, передать seed в logger |
| `src/swarm_utils/swarm_utils/metrics_calculator.py` | Не запускается | Нуждается в запуске из launch |
| `src/swarm_utils/swarm_utils/experiment_logger.py` | Ждет /swarm/metrics с пустого topic | Нужен работающий metrics_calculator |

---

## 🔬 КАК ПРОВЕРИТЬ ИСПРАВЛЕНИЕ

```bash
# В контейнере/машине:
ros2 topic list
# Должны быть видны:
# /swarm/metrics  ← должна быть!
# /swarm/state    ← должна быть!

# Слушать метрики в реальном времени:
ros2 topic echo /swarm/metrics

# Слушать состояние:
ros2 topic echo /swarm/state
```

---

## 📝 ДОПОЛНИТЕЛЬНЫЕ ЗАМЕЧАНИЯ

### Почему JSON содержит некоторые корректные значения?
JSON создается в `finalize_experiment()`, которая вызывается при:
- `/experiment/complete` сигнал (не реализовано)
- Timeout 120 секунд (текущее поведение)

Поэтому mission_time_s = 594.8 (разница между end_time и start_time) хранится в финальном JSON.

Но CSV писался периодически (каждую 1 сек) с неполными данными, и эти значения остались 0.0.

### Проблема эпизодического логирования
`log_periodic()` вызывается каждую 1 секунду и пишет ТЕКУЩЕЕ состояние метрик.
Если метрики не обновляются (нет callbacks), CSV содержит старые/дефолтные значения.
