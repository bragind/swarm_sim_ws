# Swarm Simulation Stand

ROS 2-ориентированный симуляционный стенд для воспроизводимого сравнения архитектур управления роем автономных агентов.

Стенд предназначен для пакетного запуска сценариев, моделирования поведения агентов, сбора метрик, проверки качества данных, анализа результатов и построения графиков. Основная валидированная серия выполнена в ускоренном детерминированном режиме `headless_fast_kinematic`, который позволяет проводить массовые headless-запуски без тяжелой физической симуляции и визуализации.

> В текущей доказательной серии используется реализованный контур `Dec-POMDP + эвристическая коррекция`. Полноценный proof-режим с обученной MARL-политикой требует отдельного обученного checkpoint и не смешивается с диагностическим режимом.

## Возможности

- Запуск матриц экспериментов `scenario_id × architecture × seed`.
- Поддержка четырех архитектур управления:
  - `central_a_star`;
  - `reactive`;
  - `rule_dec`;
  - `decpomdp_heuristic`.
- Шесть сценариев:
  - S1 — номинальная навигация;
  - S2 — плотные препятствия;
  - S3 — деградация связи;
  - S4 — частичный отказ агентов;
  - S5 — вычислительная деградация;
  - S6 — комбинированный стресс.
- Запись `final_metrics.csv` и `timeseries_metrics.csv`.
- Валидация результатов через `validate_results.py`.
- Анализ результатов через `analyze_wkr_results.py`.
- Построение графиков через `plot_wkr_results.py`.
- Готовые таблицы и графики в `docs/tables/wkr` и `docs/figures/wkr`.

## Структура репозитория

```text
swarm_sim_ws/
├── docker/                         # Docker/runtime окружение
├── docs/
│   ├── figures/wkr/                # Графики по диагностической серии
│   ├── tables/wkr/                 # Таблицы по диагностической серии
│   ├── SIMULATION_STAND_UML.md     # UML/data-flow диаграмма
│   ├── wkr_virtual_environment_topdown.png
│   └── wkr_virtual_environment_topdown.svg
├── scripts/                        # Batch-runner, validation, analysis, plotting
├── src/                            # ROS 2 пакеты и узлы стенда
├── tests/                          # Тесты и проверки
└── README.md
```

## Архитектура стенда

Стенд построен как ROS 2-oriented pipeline:

```text
run_wkr_experiments.py
    ↓
simulation.launch.py
    ↓
swarm_state_publisher
    ↓
decision_core_node
    ↓
metrics_calculator / mission_supervisor / experiment_logger
    ↓
final_metrics.csv
    ↓
validate_results.py / analyze_wkr_results.py / plot_wkr_results.py
```

Основные модули:

| Модуль | Назначение |
|---|---|
| `scripts/run_wkr_experiments.py` | Формирует матрицу сценариев, архитектур и seed; запускает серию экспериментов |
| `swarm_core/launch/simulation.launch.py` | Передает параметры запуска в ROS 2-узлы стенда |
| `config/scenarios.yaml` | Описывает сценарии S1-S6 и параметры деградации |
| `swarm_state_publisher` | Публикует агрегированное состояние роя |
| `decision_core_node` | Реализует выбор архитектуры управления |
| `communication_emulator` | Моделирует задержки, потери и деградацию связи |
| `metrics_calculator` | Считает coverage, connectivity, collisions, energy и integral score |
| `mission_supervisor` | Определяет завершение миссии, успех или неуспех |
| `experiment_logger` | Пишет финальные и временные метрики |
| `validate_results.py` | Проверяет валидность итогового набора данных |
| `analyze_wkr_results.py` | Агрегирует и сравнивает результаты |
| `plot_wkr_results.py` | Строит графики |

Подробная диаграмма приведена в [`docs/SIMULATION_STAND_UML.md`](docs/SIMULATION_STAND_UML.md).

## Результаты валидированной серии

Полная диагностическая серия:

```text
6 сценариев × 4 архитектуры × 30 seed = 720 запусков
```

Сводка валидации:

| Показатель | Значение |
|---|---:|
| Всего запусков | 720 |
| valid_success | 697 |
| valid_failure | 23 |
| diagnostic rows | 0 |
| incomplete_or_timeout | 0 |
| runner_timeout_reached | 0 |
| Общая успешность | 96.8 % |

Основной набор результатов находится в:

```text
docs/tables/wkr/
├── table_4_1_experiment_matrix.md
├── table_4_2_validity_summary.md
├── table_4_3_success_rate.md
├── table_4_4_mean_metrics.md
└── table_4_5_best_architecture_by_scenario.md
```

Графики находятся в:

```text
docs/figures/wkr/
├── fig_collisions_boxplot.png
├── fig_connectivity_by_architecture.png
├── fig_coverage_by_architecture.png
├── fig_energy_boxplot.png
├── fig_integral_score.png
├── fig_success_rate_by_scenario.png
└── fig_validation_summary.png
```

## Быстрый запуск

```bash
git clone -b fix/wkr-experiment-validation https://github.com/bragind/swarm_sim_ws.git
cd swarm_sim_ws

source /opt/ros/humble/setup.bash
rosdep update
rosdep install --from-paths src --ignore-src -r -y

colcon build --symlink-install
source install/setup.bash

python3 scripts/run_wkr_experiments.py \
  --quick \
  --simulation-mode headless_fast_kinematic \
  --parallel 1 \
  --output ~/sim_storage/swarm_quick

python3 scripts/validate_results.py \
  --input ~/sim_storage/swarm_quick/final_metrics.csv \
  --profile quick

python3 scripts/analyze_wkr_results.py \
  --input ~/sim_storage/swarm_quick/final_metrics.csv \
  --output ~/sim_storage/swarm_quick/analysis \
  --profile quick

python3 scripts/plot_wkr_results.py \
  --input ~/sim_storage/swarm_quick/final_metrics.csv \
  --output ~/sim_storage/swarm_quick/figures \
  --profile quick
```

## Полный диагностический запуск

```bash
python3 scripts/run_wkr_experiments.py \
  --full-diagnostic \
  --simulation-mode headless_fast_kinematic \
  --parallel 1 \
  --seeds 43:72 \
  --output ~/sim_storage/swarm_full_diagnostic

python3 scripts/validate_results.py \
  --input ~/sim_storage/swarm_full_diagnostic/final_metrics.csv \
  --profile full

python3 scripts/analyze_wkr_results.py \
  --input ~/sim_storage/swarm_full_diagnostic/final_metrics.csv \
  --output ~/sim_storage/swarm_full_diagnostic/analysis \
  --profile full

python3 scripts/plot_wkr_results.py \
  --input ~/sim_storage/swarm_full_diagnostic/final_metrics.csv \
  --output ~/sim_storage/swarm_full_diagnostic/figures \
  --profile full
```

## Запуск в Docker-контейнере

### Сборка образа

```bash
cd swarm_sim_ws
docker build -t swarm-sim-stand -f docker/Dockerfile .
```

### Быстрая диагностическая серия в контейнере

```bash
mkdir -p "$HOME/sim_storage"

docker run --rm -it \
  -v "$(pwd)":/workspace/swarm_sim_ws \
  -v "$HOME/sim_storage":/sim_storage \
  -w /workspace/swarm_sim_ws \
  swarm-sim-stand \
  bash -lc '
    source /opt/ros/humble/setup.bash &&
    colcon build --symlink-install &&
    source install/setup.bash &&
    python3 scripts/run_wkr_experiments.py \
      --quick \
      --simulation-mode headless_fast_kinematic \
      --parallel 1 \
      --output /sim_storage/swarm_quick &&
    python3 scripts/validate_results.py \
      --input /sim_storage/swarm_quick/final_metrics.csv \
      --profile quick &&
    python3 scripts/analyze_wkr_results.py \
      --input /sim_storage/swarm_quick/final_metrics.csv \
      --output /sim_storage/swarm_quick/analysis \
      --profile quick &&
    python3 scripts/plot_wkr_results.py \
      --input /sim_storage/swarm_quick/final_metrics.csv \
      --output /sim_storage/swarm_quick/figures \
      --profile quick
  '
```

### Полная диагностическая серия в контейнере

```bash
docker run --rm -it \
  -v "$(pwd)":/workspace/swarm_sim_ws \
  -v "$HOME/sim_storage":/sim_storage \
  -w /workspace/swarm_sim_ws \
  swarm-sim-stand \
  bash -lc '
    source /opt/ros/humble/setup.bash &&
    colcon build --symlink-install &&
    source install/setup.bash &&
    python3 scripts/run_wkr_experiments.py \
      --full-diagnostic \
      --simulation-mode headless_fast_kinematic \
      --parallel 1 \
      --seeds 43:72 \
      --output /sim_storage/swarm_full_diagnostic &&
    python3 scripts/validate_results.py \
      --input /sim_storage/swarm_full_diagnostic/final_metrics.csv \
      --profile full &&
    python3 scripts/analyze_wkr_results.py \
      --input /sim_storage/swarm_full_diagnostic/final_metrics.csv \
      --output /sim_storage/swarm_full_diagnostic/analysis \
      --profile full &&
    python3 scripts/plot_wkr_results.py \
      --input /sim_storage/swarm_full_diagnostic/final_metrics.csv \
      --output /sim_storage/swarm_full_diagnostic/figures \
      --profile full
  '
```

Результаты будут сохранены на хосте в `$HOME/sim_storage`.

## Интерпретация метрик

| Метрика | Смысл |
|---|---|
| `success_flag` | Факт успешного завершения миссии |
| `coverage_ratio` | Степень покрытия целевой области |
| `connectivity_coeff` | Сохранение связности роя |
| `collisions_count` | Число столкновений или небезопасных сближений |
| `total_energy_wh` | Оценка суммарного энергопотребления |
| `avg_latency_ms` | Средняя задержка обмена |
| `packet_loss_ratio` | Доля потерь сообщений |
| `integral_score` | Агрегированная метрика эффективности |

Метрика успешности используется как контрольная метрика работоспособности стенда. Для сравнения архитектур более информативны `connectivity_coeff`, `collisions_count`, `total_energy_wh` и `integral_score`.

## Основные выводы по результатам

- Серия из 720 запусков валидна: отсутствуют diagnostic rows, incomplete/timeout и runner timeout.
- В сценариях S1-S5 все архитектуры показывают 100% успешности.
- В сценарии S6 реактивная архитектура падает до 23.3% успешности.
- `decpomdp_heuristic` показывает лучший `integral_score` и лучшую связность во всех сценариях.
- `central_a_star` показывает лучшее энергопотребление во всех сценариях.
- S6 является главным стресс-тестом стенда, так как объединяет препятствия, деградацию связи, отказы и вычислительную деградацию.

## Ограничения

1. Основная серия выполнена в режиме `headless_fast_kinematic`, а не в полном Gazebo/DDS-контуре.
2. В серии не использовалась обученная MARL-политика.
3. Тестовый MARL checkpoint может применяться только для smoke/plumbing-проверки.
4. Метрика времени выполнения миссии не используется как основной показатель из-за требований к надежной синхронизации start/complete-событий.
5. Сырые сенсорные потоки не моделируются: используется агрегированное состояние среды.

## MARL proof mode

Полный proof-режим требует обученного checkpoint:

```text
models/marl/wkr_qmix_policy.pt
```

Проверка checkpoint:

```bash
python3 scripts/inspect_marl_checkpoint.py \
  --model models/marl/wkr_qmix_policy.pt \
  --require-proof
```

Запуск proof-эксперимента:

```bash
python3 scripts/run_wkr_experiments.py \
  --full-proof \
  --require-marl-model \
  --marl-model-path models/marl/wkr_qmix_policy.pt \
  --simulation-mode headless_fast_kinematic \
  --parallel 1 \
  --seeds 43:72 \
  --output ~/sim_storage/swarm_full_proof
```

## Назначение

Репозиторий можно использовать как воспроизводимый стенд для проверки алгоритмов управления роем, регрессионного тестирования, сравнения архитектур управления и подготовки следующего этапа — физически более детальной Gazebo/DDS-валидации.
