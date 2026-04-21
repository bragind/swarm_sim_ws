#!/usr/bin/env python3
import pandas as pd
import sys

def analyze_csv(csv_path):
    df = pd.read_csv(csv_path)
    print(f"📊 Всего записей: {len(df)}")
    print(f"📈 Успешных прогонов (success_flag=1): {df['success_flag'].sum()} из {len(df)} ({100*df['success_flag'].mean():.1f}%)")
    print(f"⏱️  Среднее время миссии: {df['mission_time_s'].mean():.2f} ± {df['mission_time_s'].std():.2f} с")
    print(f"🔗 Средний коэффициент связности: {df['connectivity_coeff'].mean():.3f}")
    print(f"💥 Среднее число столкновений: {df['collisions_count'].mean():.2f}")
    print(f"⚡ Среднее энергопотребление: {df['total_energy_wh'].mean():.2f} Вт·ч")
    
    # Группировка по сценариям
    if 'scenario_id' in df.columns:
        print("\n📋 По сценариям:")
        for sc in df['scenario_id'].unique():
            sub = df[df['scenario_id'] == sc]
            print(f"  {sc}: n={len(sub)}, успех={sub['success_flag'].sum()}/{len(sub)} ({100*sub['success_flag'].mean():.1f}%), время={sub['mission_time_s'].mean():.1f}±{sub['mission_time_s'].std():.1f}с")

if __name__ == '__main__':
    csv_path = sys.argv[1] if len(sys.argv) > 1 else '/root/sim_storage/exp_results_final.csv'
    analyze_csv(csv_path)
