# Симуляционный стенд роя автономных агентов

Воспроизводимый ROS 2-ориентированный симуляционный стенд для сравнения распределенных архитектур управления роем автономных агентов.

Проект содержит скрипты для пакетного запуска экспериментов, управления сценариями, сбора метрик, проверки качества данных, агрегации результатов и построения графиков. Текущий валидированный набор экспериментов использует ускоренный детерминированный headless-режим кинематического моделирования для массовых повторяемых запусков.

## Что предоставляет репозиторий

- Пакетный запуск матриц «сценарий / архитектура / seed».
- Четыре базовые архитектуры управления: `central_a_star`, `reactive`, `rule_dec` и `decpomdp_heuristic`.
- Шесть классов сценариев: штатная работа, плотные препятствия, деградация связи, частичный отказ агентов, вычислительная деградация и комбинированный стресс.
- Итоговые метрики в `final_metrics.csv` и опциональные временные ряды в `timeseries_metrics.csv`.
- Скрипты валидации, анализа и построения графиков.
- Готовые таблицы и рисунки с результатами в каталогах `docs/tables` и `docs/figures`.

## Структура репозитория

```text
swarm_sim_ws/
├── docker/                 # Файлы контейнерной/исполняемой среды
├── docs/                   # Диаграммы, сгенерированные графики и таблицы
│   ├── figures/wkr/        # Опубликованные графики экспериментов в исходной ветке
│   ├── tables/wkr/         # Опубликованные таблицы экспериментов в исходной ветке
│   └── SIMULATION_STAND_UML.md
├── scripts/                # Batch-runner, валидация, анализ и построение графиков
├── src/                    # ROS 2-пакеты и узлы симуляционного стенда
├── tests/                  # Тестовые и валидационные материалы
└── README.md
```

## Текущий валидированный набор результатов

Опубликованная диагностическая матрица содержит 720 запусков:

| Метрика | Значение |
|---|---:|
| Всего запусков | 720 |
| valid_success | 697 |
| valid_failure | 23 |
| diagnostic rows | 0 |
| incomplete_or_timeout | 0 |
| runner_timeout_reached | 0 |
| Общий коэффициент успешности | 96.8% |

Матрица экспериментов:

```text
6 сценариев x 4 архитектуры x 30 seed = 720 запусков
```

Архитектуры, использованные в опубликованной матрице:

- `central_a_star` — централизованный базовый вариант планирования.
- `reactive` — базовый вариант реактивного локального управления.
- `rule_dec` — децентрализованный алгоритм на основе правил.
- `decpomdp_heuristic` — эвристическая корректирующая политика в стиле Dec-POMDP.

## Режим моделирования

Текущий валидированный набор запусков использует режим:

```text
headless_fast_kinematic
```

Этот режим предназначен для быстрого, детерминированного и воспроизводимого алгоритмического тестирования. Он не заменяет полноценную кампанию физической валидации на уровне Gazebo/DDS. Его следует использовать как первый уровень регрессионного тестирования, бенчмаркинга и сценарного сравнения архитектур.

## Быстрый запуск

```bash
source /opt/ros/humble/setup.bash
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


## Запуск симуляционного стенда в контейнере

Ниже приведен типовой пример запуска в Docker-контейнере. Такой режим удобен, когда нужно получить воспроизводимую среду без локальной настройки зависимостей ROS 2.

### Сборка контейнерного образа

```bash
cd swarm_sim_ws
docker build -t swarm-sim-stand -f docker/Dockerfile .
```

### Быстрый запуск в контейнере

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

### Полный диагностический запуск в контейнере

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

> Результаты сохраняются на хосте в каталоге `$HOME/sim_storage`, смонтированном в контейнер как `/sim_storage`.

## Артефакты результатов

В комплект документации входят нейтральные копии опубликованных таблиц и заново построенные графики на основе тех же значений метрик:

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

## Интерпретация метрик

Основные метрики:

- `success_flag` — показывает, был ли запуск завершен в соответствии с критериями миссии.
- `coverage_ratio` — показывает, насколько эффективно рой покрыл целевую область или выполнил целевую задачу.
- `connectivity_coeff` — характеризует качество связности роя в нормальных условиях и при деградации связи.
- `collisions_count` — число обнаруженных столкновений или небезопасных контактов.
- `total_energy_wh` — прокси-оценка суммарных энергозатрат за запуск.
- `integral_score` — агрегированный нормализованный показатель эффективности, используемый для ранжирования архитектур.

`success_rate` удобно использовать как показатель работоспособности и валидности запусков. Для сравнения архитектур более информативны интегральный показатель, связность, энергозатраты и число столкновений.

## Основные результаты

В сценариях S1-S6 архитектура `decpomdp_heuristic` имеет лучший интегральный показатель и лучшую связность в опубликованных таблицах средних метрик. Архитектура `central_a_star` является наиболее энергоэффективной по опубликованной таблице лучших архитектур. Сценарий S6 является наиболее показательным стресс-тестом: базовый реактивный алгоритм падает до 23.3% успешности и показывает самый слабый интегральный результат.

## Примечание о MARL/proof-режиме

Текущую валидированную матрицу следует рассматривать как детерминированный диагностический бенчмарк. Полный proof-режим с обученной политикой требует наличия обученного checkpoint-файла, например:

```text
models/marl/wkr_qmix_policy.pt
```

Тестовый checkpoint подходит только для проверки связности пайплайна и smoke-тестов. Его нельзя использовать как подтверждение эффективности обученной политики.

## Лицензия и использование

Репозиторий предназначен для использования как воспроизводимый симуляционный стенд тестирования алгоритмов управления роем, регрессионных проверок и сравнения архитектур управления в контролируемых сценариях.
