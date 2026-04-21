#!/usr/bin/env python3
import pandas as pd
import sys

def aggregate_runs(csv_path):
    df = pd.read_csv(csv_path)
    # Группируем по run_id
    grouped = df.groupby('run_id')
    results = []
    for run_id, group in grouped:
        if len(group) == 0:
            continue
        # Последняя строка содержит финальные метрики (кроме времени)
        last = group.iloc[-1].copy()
        # Вычисляем время миссии как разницу между start_time последней и первой записи
        first_time = group.iloc[0]['start_time']
        last_time = last['start_time']
        last['mission_time_s'] = last_time - first_time if pd.notna(first_time) and pd.notna(last_time) else 0.0
        last['end_time'] = last_time  # заполняем end_time
        results.append(last)
    
    agg_df = pd.DataFrame(results)
    # Сохраняем агрегированный файл
    agg_csv = csv_path.replace('.csv', '_aggregated.csv')
    agg_df.to_csv(agg_csv, index=False)
    print(f"✅ Агрегировано {len(agg_df)} прогонов в {agg_csv}")
    return agg_df

def analyze(df):
    print(f"📊 Всего прогонов: {len(df)}")
    success = df['success_flag'].sum()
    total = len(df)
    print(f"📈 Успешных: {success} из {total} ({100*success/total:.1f}%)")
    print(f"⏱️  Среднее время миссии: {df['mission_time_s'].mean():.2f} ± {df['mission_time_s'].std():.2f} с")
    print(f"🔗 Средний коэффициент связности: {df['connectivity_coeff'].mean():.3f}")
    print(f"💥 Среднее число столкновений: {df['collisions_count'].mean():.2f}")
    print(f"⚡ Среднее энергопотребление: {df['total_energy_wh'].mean():.2f} Вт·ч")
    
    if 'scenario_id' in df.columns:
        print("\n📋 По сценариям:")
        for sc in df['scenario_id'].unique():
            sub = df[df['scenario_id'] == sc]
            print(f"  {sc}: n={len(sub)}, успех={sub['success_flag'].sum()}/{len(sub)} ({100*sub['success_flag'].mean():.1f}%), время={sub['mission_time_s'].mean():.1f}±{sub['mission_time_s'].std():.1f}с")

if __name__ == '__main__':
    csv_path = sys.argv[1] if len(sys.argv) > 1 else '/root/sim_storage/exp_results_final.csv'
    agg_df = aggregate_runs(csv_path)
    analyze(agg_df)
