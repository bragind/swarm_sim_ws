# swarm_sim_ws

## Результаты full diagnostic для ВКР

Финальный набор данных для главы 4:

- контейнер: `/home/swarm/sim_storage/wkr_full_diagnostic_fix1`
- Windows: `C:\Users\diman\sim_storage\wkr_full_diagnostic_fix1`
- русские графики: `figures_ru/`
- таблицы для главы 4: `tables_ru/`
- финальный текст разделов 4.4-4.9: `docs/EXPERIMENTS_WKR.md`

Серия содержит 720 запусков: 697 `valid_success`, 23 `valid_failure`,
0 diagnostic rows, 0 `incomplete_or_timeout`, 0 `runner_timeout_reached`.
В ВКР эти результаты следует трактовать как full diagnostic без обученной
MARL-политики. Исследуется реализованный контур `Dec-POMDP + эвристическая
коррекция`.

Full proof MARL не выполнялся, так как отсутствует обученный checkpoint
`models/marl/wkr_qmix_policy.pt`. Тестовый `models/marl/test_policy.pt`
использовался только для диагностической проверки загрузки и не является
proof-valid моделью.

## WKR final diagnostic commands

Рабочая ветка: `fix/wkr-experiment-validation`.

Quick diagnostic:

```bash
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash

python3 scripts/run_wkr_experiments.py \
  --quick \
  --simulation-mode headless_fast_kinematic \
  --parallel 1 \
  --output /home/swarm/sim_storage/wkr_quick_check
```

Full diagnostic fix1, используемый для главы 4:

```bash
python3 scripts/run_wkr_experiments.py \
  --full-diagnostic \
  --simulation-mode headless_fast_kinematic \
  --parallel 1 \
  --seeds 43:72 \
  --output /home/swarm/sim_storage/wkr_full_diagnostic_fix1

python3 scripts/validate_results.py \
  --input /home/swarm/sim_storage/wkr_full_diagnostic_fix1/final_metrics.csv \
  --profile full

python3 scripts/diagnose_full_failures.py \
  --input /home/swarm/sim_storage/wkr_full_diagnostic_fix1/final_metrics.csv \
  --output /home/swarm/sim_storage/wkr_full_diagnostic_fix1/diagnostics

python3 scripts/analyze_wkr_results.py \
  --input /home/swarm/sim_storage/wkr_full_diagnostic_fix1/final_metrics.csv \
  --output /home/swarm/sim_storage/wkr_full_diagnostic_fix1/analysis \
  --profile full

python3 scripts/plot_wkr_results.py \
  --input /home/swarm/sim_storage/wkr_full_diagnostic_fix1/final_metrics.csv \
  --output /home/swarm/sim_storage/wkr_full_diagnostic_fix1/figures \
  --profile full
```

Results:

- container: `/home/swarm/sim_storage/wkr_full_diagnostic_fix1`
- Windows: `C:\Users\diman\sim_storage\wkr_full_diagnostic_fix1`

MARL plumbing test, diagnostic only:

```bash
python3 scripts/create_test_marl_checkpoint.py
python3 scripts/run_wkr_experiments.py \
  --quick \
  --include-marl \
  --allow-test-marl-model \
  --marl-model-path models/marl/test_policy.pt \
  --simulation-mode headless_fast_kinematic \
  --parallel 1 \
  --output /home/swarm/sim_storage/wkr_quick_marl_plumbing
```

Full proof remains blocked until `models/marl/wkr_qmix_policy.pt` exists and
passes:

```bash
python3 scripts/inspect_marl_checkpoint.py \
  --model models/marl/wkr_qmix_policy.pt \
  --require-proof
```

Do not use `models/marl/test_policy.pt` for proof claims. It must remain
`trained=false` and `allowed_for_wkr_proof=false`.

## Current WKR Commands

The three WKR modes are intentionally separated. Do not edit generated CSV
files manually, and do not use `models/marl/test_policy.pt` for proof claims.

Quick diagnostic without MARL:

```bash
colcon build
source install/setup.bash
python3 scripts/run_wkr_experiments.py \
  --quick \
  --simulation-mode headless_fast_kinematic \
  --parallel 1 \
  --output ~/sim_storage/wkr_quick
python3 scripts/validate_results.py --input ~/sim_storage/wkr_quick/final_metrics.csv --profile quick
python3 scripts/analyze_wkr_results.py --input ~/sim_storage/wkr_quick/final_metrics.csv --output ~/sim_storage/wkr_quick/analysis --profile quick
python3 scripts/plot_wkr_results.py --input ~/sim_storage/wkr_quick/final_metrics.csv --output ~/sim_storage/wkr_quick/figures --profile quick
```

Full diagnostic without MARL:

```bash
python3 scripts/run_wkr_experiments.py \
  --full-diagnostic \
  --simulation-mode headless_fast_kinematic \
  --parallel 1 \
  --seeds 43:72 \
  --output /home/swarm/sim_storage/wkr_full_diagnostic

python3 scripts/validate_results.py \
  --input /home/swarm/sim_storage/wkr_full_diagnostic/final_metrics.csv \
  --profile full

python3 scripts/analyze_wkr_results.py \
  --input /home/swarm/sim_storage/wkr_full_diagnostic/final_metrics.csv \
  --output /home/swarm/sim_storage/wkr_full_diagnostic/analysis \
  --profile full

python3 scripts/plot_wkr_results.py \
  --input /home/swarm/sim_storage/wkr_full_diagnostic/final_metrics.csv \
  --output /home/swarm/sim_storage/wkr_full_diagnostic/figures \
  --profile full
```

This matrix is 6 scenarios x 4 architectures x 30 seeds = 720 runs:
`central_a_star`, `reactive`, `rule_dec`, `decpomdp_heuristic`.

Quick MARL plumbing test:

```bash
python3 scripts/create_test_marl_checkpoint.py
python3 scripts/run_wkr_experiments.py --quick --include-marl --allow-test-marl-model --marl-model-path models/marl/test_policy.pt --output ~/sim_storage/wkr_quick_marl_plumbing
```

Train and inspect a real MARL checkpoint:

```bash
python3 scripts/train_wkr_marl.py \
  --scenarios S1,S2,S3,S4,S5,S6 \
  --episodes 1000 \
  --seeds 43:72 \
  --output models/marl/wkr_qmix_policy.pt \
  --num-agents 8

python3 scripts/inspect_marl_checkpoint.py \
  --model models/marl/wkr_qmix_policy.pt \
  --require-proof
```

MARL smoke proof:

```bash
python3 scripts/run_wkr_experiments.py \
  --full-proof \
  --scenarios S1 \
  --architectures reactive,marl_decpomdp \
  --seeds 43:45 \
  --require-marl-model \
  --marl-model-path models/marl/wkr_qmix_policy.pt \
  --simulation-mode headless_fast_kinematic \
  --parallel 1 \
  --output /home/swarm/sim_storage/wkr_marl_smoke

python3 scripts/validate_results.py \
  --input /home/swarm/sim_storage/wkr_marl_smoke/final_metrics.csv \
  --profile full \
  --proof-mode
```

Full proof experiment:

```bash
python3 scripts/run_wkr_experiments.py \
  --full-proof \
  --require-marl-model \
  --marl-model-path models/marl/wkr_qmix_policy.pt \
  --simulation-mode headless_fast_kinematic \
  --parallel 1 \
  --seeds 43:72 \
  --output /home/swarm/sim_storage/wkr_full_proof

python3 scripts/validate_results.py \
  --input /home/swarm/sim_storage/wkr_full_proof/final_metrics.csv \
  --profile full \
  --proof-mode

python3 scripts/analyze_wkr_results.py \
  --input /home/swarm/sim_storage/wkr_full_proof/final_metrics.csv \
  --output /home/swarm/sim_storage/wkr_full_proof/analysis \
  --profile full \
  --proof-mode

python3 scripts/plot_wkr_results.py \
  --input /home/swarm/sim_storage/wkr_full_proof/final_metrics.csv \
  --output /home/swarm/sim_storage/wkr_full_proof/figures \
  --profile full \
  --proof-mode
```

Quick uses `headless_fast_kinematic` and is diagnostic only. Proof MARL requires
`models/marl/wkr_qmix_policy.pt` with `trained = true` and
`allowed_for_wkr_proof = true`.

## WKR experiment validation workflow

Основная воспроизводимая матрица экспериментов описана в `docs/EXPERIMENTS_WKR.md`.

```bash
colcon build --symlink-install
source install/setup.bash
python3 scripts/run_wkr_experiments.py --quick --output ~/sim_storage/wkr_quick
python3 scripts/validate_results.py --input ~/sim_storage/wkr_quick/final_metrics.csv
python3 scripts/analyze_wkr_results.py --input ~/sim_storage/wkr_quick/final_metrics.csv --output ~/sim_storage/wkr_quick/analysis
python3 scripts/plot_wkr_results.py --input ~/sim_storage/wkr_quick/final_metrics.csv --output ~/sim_storage/wkr_quick/figures
```

Full-запуск:

```bash
python3 scripts/run_wkr_experiments.py --full --parallel 1 --output ~/sim_storage/wkr_full
```

Финальные метрики пишутся в `final_metrics.csv` по правилу: одна строка на один `run_id`. Периодические значения пишутся отдельно в `timeseries_metrics.csv`. Запуск `marl_decpomdp` не считается валидным MARL-экспериментом, если модель не загружена.
A test bench for distributed control system algorithms
# 1. Клонирование и настройка
cd ~/
mkdir -p swarm_sim_ws/src
cd swarm_sim_ws

# 2. Скопируйте все файлы в соответствующие директории
# (структура описана в разделе 1)

# 3. Установка зависимостей
source /opt/ros/humble/setup.bash
rosdep update
rosdep install --from-paths src --ignore-src -r -y

# 4. Сборка
colcon build --symlink-install

# 5. Запуск единичного эксперимента
ros2 launch swarm_core simulation.launch.py \
    scenario_id:=S1 \
    seed:=42 \
    num_uavs:=5 \
    num_ugvs:=3 \
    use_marl:=true

# 6. Запуск всех экспериментов (batch mode)
./scripts/run_all_experiments.sh

# 7. Анализ результатов
python3 src/swarm_utils/scripts/analyze_exp.py \
    --csv_path ~/sim_storage/experiments/exp_results.csv

# 8. Диагностика batch/logging (Docker)
# Важно: не смешивайте запуск от разных пользователей.
# - Если запуск делался от root, рабочие пути обычно под /root/...
# - Если запуск делался от swarm, рабочие пути обычно под /home/swarm/...

# 8.1 Проверка окружения (в контейнере)
whoami
echo $HOME
source /opt/ros/humble/setup.bash
source /home/swarm/ws/install/setup.bash

# 8.2 Проверка, что пакеты видны в ROS 2
ros2 pkg prefix swarm_core
ros2 pkg prefix swarm_perception
ros2 pkg prefix swarm_decision
ros2 pkg prefix swarm_utils

# Если Package not found:
# 1) не используйте sudo для colcon build
# 2) пересоберите и заново source install/setup.bash
# cd /home/swarm/ws
# colcon build --symlink-install
# source /home/swarm/ws/install/setup.bash

# 8.3 Запуск batch
cd /home/swarm/ws/scripts
bash run_all_experiments.sh

# 8.4 Где искать логи
ls -lah /home/swarm/sim_storage/experiments
ls -lah /root/sim_storage/experiments

# 8.5 Быстрый поиск критических ошибок в .log
grep -RniE "ERROR|FATAL|Traceback|not found|timeout" /home/swarm/sim_storage/experiments/*.log

# 8.6 Анализ логов
# Текущий анализатор:
python3 /home/swarm/ws/scripts/analyze_experiments.py \
    --log_dir /home/swarm/sim_storage/experiments \
    --output /home/swarm/sim_storage/exp_results.csv

# Примечание:
# analyze_experiments.py парсит текстовые метрики (success, mission_time, energy, ...)
# из .log. Если в launch-логах этих строк нет, success_flag останется 0.
