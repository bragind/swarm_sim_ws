#!/usr/bin/env python3
"""
Генерация графиков для диссертации (Рис. 4.3–4.7).
Выход: PNG 300 DPI + SVG для LaTeX.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats

# Настройки для ГОСТ/академического стиля
plt.rcParams.update({
    'font.size': 11,
    'font.family': 'DejaVu Sans',
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.figsize': (10, 6),
    'figure.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.format': 'png'
})

def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # Фильтрация ошибок парсинга
    df = df[df['error'].isna() | (df['error'] == '')]
    df['scenario'] = df['scenario_id'].astype('category')
    return df

def plot_mission_time(df: pd.DataFrame, output_dir: Path):
    """Рис. 4.3: Время выполнения миссии по сценариям"""
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x='scenario', y='mission_time_s', 
                palette='Set2', showfliers=False, width=0.6)
    plt.xlabel('Сценарий', fontsize=12)
    plt.ylabel('Время миссии, с', fontsize=12)
    plt.title('Зависимость времени выполнения миссии от сценария', fontsize=13, pad=15)
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Добавление статистики
    for i, scenario in enumerate(df['scenario'].cat.categories):
        sub = df[df['scenario'] == scenario]['mission_time_s'].dropna()
        if len(sub) > 0:
            plt.text(i, sub.max() * 1.05, 
                    f'n={len(sub)}\nμ={sub.mean():.1f}±{sub.std():.1f}',
                    ha='center', fontsize=9, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    for ext in ['png', 'svg']:
        plt.savefig(output_dir / f'fig_mission_time.{ext}', dpi=300 if ext=='png' else None)
    plt.close()
    print(f"✅ Рис. 4.3 сохранён: fig_mission_time.png/svg")

def plot_connectivity_degradation(df: pd.DataFrame, output_dir: Path):
    """Рис. 4.4: Устойчивость связности при потере пакетов"""
    # Фильтруем сценарий с деградацией связи (предполагаем, что это S3)
    s3 = df[df['scenario_id'] == 'S3'].copy()
    if s3.empty:
        print("⚠️  Нет данных для сценария деградации связи (S3)")
        return
    
    plt.figure(figsize=(10, 6))
    
    # Группировка по уровню потерь (если есть в данных) или используем среднее
    if 'packet_loss_ratio' in s3.columns and s3['packet_loss_ratio'].notna().any():
        s3['loss_bin'] = pd.cut(s3['packet_loss_ratio'], 
                               bins=[-0.01, 0.05, 0.10, 0.15, 0.20, 0.26], 
                               labels=['0–5%', '5–10%', '10–15%', '15–20%', '20–25%'])
        sns.lineplot(data=s3, x='loss_bin', y='connectivity_coeff', 
                     marker='o', ci=95, linewidth=2, markersize=8)
        plt.xlabel('Вероятность потери пакета', fontsize=12)
    else:
        # Если нет детализации по потерям, показываем среднее по сценарию
        plt.bar(['S3'], [s3['connectivity_coeff'].mean()], yerr=[s3['connectivity_coeff'].std()],
                capsize=8, color='skyblue', edgecolor='black')
        plt.xlabel('Сценарий', fontsize=12)
    
    plt.ylabel('Коэффициент связности роя', fontsize=12)
    plt.title('Устойчивость связности при деградации канала связи', fontsize=13, pad=15)
    plt.ylim(0, 1.05)
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    
    for ext in ['png', 'svg']:
        plt.savefig(output_dir / f'fig_connectivity.{ext}', dpi=300 if ext=='png' else None)
    plt.close()
    print(f"✅ Рис. 4.4 сохранён: fig_connectivity.png/svg")

def plot_success_rate(df: pd.DataFrame, output_dir: Path):
    """Рис. 4.5: Доля успешных миссий по сценариям"""
    plt.figure(figsize=(10, 6))
    
    success_rates = df.groupby('scenario')['success_flag'].agg(['mean', 'count', 'std'])
    success_rates['ci95'] = 1.96 * success_rates['std'] / np.sqrt(success_rates['count'])
    
    plt.bar(success_rates.index.astype(str), 
            success_rates['mean'] * 100,
            yerr=success_rates['ci95'] * 100,
            capsize=8, color='lightgreen', edgecolor='black', linewidth=1.5)
    
    plt.xlabel('Сценарий', fontsize=12)
    plt.ylabel('Доля успешных миссий, %', fontsize=12)
    plt.title('Надёжность выполнения миссий в различных условиях', fontsize=13, pad=15)
    plt.ylim(0, 105)
    plt.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Подписи значений
    for i, (idx, row) in enumerate(success_rates.iterrows()):
        plt.text(i, row['mean']*100 + 5, f'{row["mean"]*100:.1f}%', 
                ha='center', fontsize=11, fontweight='bold')
    
    for ext in ['png', 'svg']:
        plt.savefig(output_dir / f'fig_success_rate.{ext}', dpi=300 if ext=='png' else None)
    plt.close()
    print(f"✅ Рис. 4.5 сохранён: fig_success_rate.png/svg")

def generate_statistics_report(df: pd.DataFrame, output_dir: Path):
    """Генерация текстового отчёта со статистикой для диссертации"""
    report = []
    report.append("📊 СТАТИСТИЧЕСКИЙ ОТЧЁТ ПО ЭКСПЕРИМЕНТАМ")
    report.append("=" * 60)
    report.append(f"Дата генерации: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    report.append(f"Всего проанализировано прогонов: {len(df)}\n")
    
    # Групповая статистика по сценариям
    for scenario in sorted(df['scenario_id'].dropna().unique()):
        sub = df[df['scenario_id'] == scenario]
        report.append(f"🔹 Сценарий {scenario} (n={len(sub)}):")
        
        if sub['mission_time_s'].notna().any():
            t = sub['mission_time_s'].dropna()
            report.append(f"   • Время миссии: {t.mean():.2f} ± {t.std():.2f} с (95% ДИ: [{t.mean()-1.96*t.std()/np.sqrt(len(t)):.2f}; {t.mean()+1.96*t.std()/np.sqrt(len(t)):.2f}])")
        
        if 'success_flag' in sub.columns:
            success_rate = sub['success_flag'].mean() * 100
            ci = 1.96 * np.sqrt(success_rate * (100 - success_rate) / len(sub))
            report.append(f"   • Успешность: {success_rate:.1f}% ± {ci:.1f}% (95% ДИ)")
        
        if 'connectivity_coeff' in sub.columns and sub['connectivity_coeff'].notna().any():
            c = sub['connectivity_coeff'].dropna()
            report.append(f"   • Связность: {c.mean():.3f} ± {c.std():.3f}")
        
        report.append("")
    
    # Проверка гипотез (пример для H1.1: время миссии в базовом сценарии < 60 с)
    report.append("🔍 ПРОВЕРКА ГИПОТЕЗ:")
    s1 = df[df['scenario_id'] == 'S1']['mission_time_s'].dropna()
    if len(s1) >= 2:
        t_stat, p_val = stats.ttest_1samp(s1, 60.0, alternative='less')
        report.append(f"   H₁,₁: Время миссии в S1 < 60 с → t={t_stat:.3f}, p={p_val:.4f} {'✅ ПОДТВЕРЖДЕНО' if p_val < 0.05 else '❌ НЕ ПОДТВЕРЖДЕНО'}")
    
    # Сохранение отчёта
    report_path = output_dir / 'statistics_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    print(f"✅ Статистический отчёт: {report_path}")
    
    return '\n'.join(report)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True, help='Путь к exp_results.csv')
    parser.add_argument('--output', default='figures', help='Папка для графиков')
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("📊 Загрузка данных...")
    df = load_data(args.csv)
    
    print("📈 Генерация графиков...")
    plot_mission_time(df, output_dir)
    plot_connectivity_degradation(df, output_dir)
    plot_success_rate(df, output_dir)
    
    print("📝 Генерация статистического отчёта...")
    report = generate_statistics_report(df, output_dir)
    print("\n" + report)
    
    print(f"\n✨ Готово! Файлы для диссертации:")
    for f in output_dir.glob('*'):
        print(f"  • {f.name}")

if __name__ == '__main__':
    main()