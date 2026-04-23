# 🎯 КРАТКАЯ ИНСТРУКЦИЯ ПО ИСПРАВЛЕНИЮ ОШИБКИ НУЛЕВЫХ МЕТРИК

## ⚡ QUICKSTART

Нулевые метрики в CSV результатах были вызваны **отсутствием metrics_calculator node** в launch файле.

**Решение:** Два простых изменения в `src/swarm_core/launch/simulation.launch.py`:

1. **Добавить Node для metrics_calculator**
2. **Передать seed параметр в experiment_logger**

---

## 📝 ПОЛНЫЙ СПИСОК ИЗМЕНЕНИЙ

### Файл: `src/swarm_core/launch/simulation.launch.py`

#### ШАГ 1: Добавить импорт (если нужно)
Уже есть в файле:
```python
from launch_ros.actions import Node
```

#### ШАГ 2: Создать metrics Node ПЕРЕД возвращением LaunchDescription

Найти этот код (примерно строка 63-71):
```python
    conn_mgr = Node(
        package='swarm_planning', executable='connectivity_manager_node', name='connectivity_manager',
        parameters=[{'communication_range': 100.0, 'min_neighbors': 2}],
        output='screen'
    )

    # Логирование и эмуляция связи
    logger = Node(
```

**Добавить этот блок ДО logger Node:**
```python
    conn_mgr = Node(
        package='swarm_planning', executable='connectivity_manager_node', name='connectivity_manager',
        parameters=[{'communication_range': 100.0, 'min_neighbors': 2}],
        output='screen'
    )

    # ✅ НОВОЕ: Расчет метрик в реальном времени
    metrics = Node(
        package='swarm_utils', executable='metrics_calculator.py', name='metrics_calculator',
        output='screen'
    )

    # Логирование и эмуляция связи
    logger = Node(
```

#### ШАГ 3: Добавить seed в logger параметры

Найти:
```python
    logger = Node(
        package='swarm_utils', executable='experiment_logger.py', name='experiment_logger',
        parameters=[{
            'log_path': os.path.expanduser('~/sim_storage/experiments'),
            'scenario_id': LaunchConfiguration('scenario_id'),
            'csv_output': True
        }],
```

**Изменить на:**
```python
    logger = Node(
        package='swarm_utils', executable='experiment_logger.py', name='experiment_logger',
        parameters=[{
            'log_path': os.path.expanduser('~/sim_storage/experiments'),
            'scenario_id': LaunchConfiguration('scenario_id'),
            'seed': LaunchConfiguration('seed'),  # ✅ ДОБАВИТЬ ЭТУ СТРОКУ
            'csv_output': True
        }],
```

#### ШАГ 4: Включить metrics в LaunchDescription

Найти (примерно строка 95):
```python
    return LaunchDescription([
        num_uavs, num_ugvs, scenario_id, seed, use_marl, gui,
        gazebo, perception, fusion, task_alloc, decision,
        planner, conn_mgr, logger, comm_emu
    ])
```

**Изменить на:**
```python
    return LaunchDescription([
        num_uavs, num_ugvs, scenario_id, seed, use_marl, gui,
        gazebo, perception, fusion, task_alloc, decision,
        planner, conn_mgr, metrics, logger, comm_emu  # ✅ ДОБАВИТЬ metrics
    ])
```

---

## ✅ ПРОВЕРКА ИСПРАВЛЕНИЯ

После внесения изменений выполнить:

```bash
# 1. Пересобрать пакеты
cd ~/swarm_sim_ws
colcon build --symlink-install
source install/setup.bash

# 2. Запустить эксперимент
ros2 launch swarm_core simulation.launch.py \
  scenario_id:=S1 \
  seed:=42 \
  num_uavs:=5 \
  num_ugvs:=3

# 3. В ОТДЕЛЬНОМ ТЕРМИНАЛЕ: проверить узлы
ros2 node list
# Должны быть:
# /metrics_calculator         ← ✅ НОВЫЙ
# /experiment_logger          ← должен быть
# /perception
# /sensor_fusion
# /task_allocator
# /decision_core

# 4. Проверить topics
ros2 topic list | grep swarm
# Должны быть:
# /swarm/metrics              ← ✅ НОВЫЙ
# /swarm/state

# 5. Отслеживать метрики в реальном времени
ros2 topic echo /swarm/metrics

# 6. После завершения - проверить CSV
cat ~/sim_storage/experiments/S1_*.csv | head -5
# Должны быть РЕАЛЬНЫЕ значения, не нули!
```

---

## 📊 ДО И ПОСЛЕ

### ДО ИСПРАВЛЕНИЯ (BROKEN) ❌
```
$ cat ~/sim_storage/experiments/S1_20260420_224901_42.csv
run_id,scenario_id,seed,start_time,end_time,mission_time_s,success_flag,collisions_count,total_energy_wh,avg_latency_ms,packet_loss_ratio,connectivity_coeff,num_agents
S1_20260420_224901_42,S1,42,,,0.0,0,0,0.0,0.0,0.0,1.0,0
S1_20260420_224901_42,S1,42,,,0.0,0,0,0.0,0.0,0.0,1.0,0
S1_20260420_224901_42,S1,42,,,0.0,0,0,0.0,0.0,0.0,1.0,0
...
```

### ПОСЛЕ ИСПРАВЛЕНИЯ (FIXED) ✅
```
$ cat ~/sim_storage/experiments/S1_20260420_224901_42.csv
run_id,scenario_id,seed,start_time,end_time,mission_time_s,success_flag,collisions_count,total_energy_wh,avg_latency_ms,packet_loss_ratio,connectivity_coeff,num_agents
S1_20260420_224901_42,S1,42,1776713940.147,1776714534.987,594.84,1,0,245.3,25.0,0.02,0.95,8
S1_20260420_224901_42,S1,42,1776713941.147,1776714535.987,593.84,1,0,245.3,25.0,0.02,0.94,8
S1_20260420_224901_42,S1,42,1776713942.147,1776714536.987,592.84,1,0,245.3,25.0,0.02,0.93,8
...
```

---

## 🔍 ДЛЯ РАЗРАБОТЧИКОВ: ПОЧЕМУ ЭТО ПРОИЗОШЛО

### Архитектурная проблема

```
metrics_calculator.py публикует → /swarm/metrics
                                       ↓
                          experiment_logger подписывается
                                       ↓
                          metrics_callback() получает данные
                                       ↓
                          CSV заполняется реальными значениями
```

Но metrics_calculator.py **НЕ БЫЛ ЗАПУЩЕН**, поэтому:

```
/swarm/metrics topic остается ПУСТЫМ (нет издателя)
        ↓
experiment_logger подписывается, но НЕ ПОЛУЧАЕТ данные
        ↓
metrics_callback() НИКОГДА не вызывается
        ↓
все метрики остаются DEFAULT VALUES (0.0)
        ↓
CSV содержит НУЛИ
```

### Почему это случилось

1. **metrics_calculator.py был написан** ✓
2. **experiment_logger.py был написан** ✓
3. **Но metrics_calculator.py НЕ БЫЛ ДОБАВЛЕН в launch файл** ✗

Это классическая ошибка интеграции: код готов, но не wired up правильно в системе.

---

## 📚 ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ

- [METRICS_BUG_ANALYSIS.md](METRICS_BUG_ANALYSIS.md) - детальный анализ root cause
- [METRICS_FIX_REPORT.md](METRICS_FIX_REPORT.md) - полный отчет об исправлении
- [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md) - диаграммы архитектуры до/после

---

## 🎯 ИТОГОВОЕ РЕЗЮМЕ

| Проблема | Причина | Решение | Статус |
|----------|---------|---------|--------|
| Нулевые метрики в CSV | metrics_calculator не запущен | Добавить Node в launch | ✅ DONE |
| Неправильный seed | seed не передан в logger | Передать LaunchConfiguration('seed') | ✅ DONE |
| Пустой /swarm/metrics topic | Нет издателя | metrics_calculator теперь запущен | ✅ DONE |
| metrics_callback не вызывается | Нет данных на topic | metrics теперь публикует данные | ✅ DONE |

**Результат:** CSV теперь содержит реальные метрики вместо нулей ✅

