#!/usr/bin/env python3
"""Визуализация виртуального полигона ВКР: вид сверху (top-down)."""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

# Настройка шрифта для корректного отображения кириллицы
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False


def pose_xy(text):
    """Извлекает координаты x, y из строки pose SDF."""
    parts = [float(x) for x in (text or '0 0 0 0 0 0').split()]
    return parts[0], parts[1]


def box_size(link):
    """Извлекает размеры прямоугольного препятствия (dx, dy) из link."""
    size = link.find('.//box/size')
    if size is None:
        return None
    vals = [float(x) for x in size.text.split()]
    return vals[0], vals[1]


def sphere_radius(link):
    """Извлекает радиус сферического препятствия из link."""
    radius = link.find('.//sphere/radius')
    return float(radius.text) if radius is not None else None


def main():
    # Автоматическое определение пути к проекту
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parent
    
    parser = argparse.ArgumentParser(
        description='Генерация топ-даун визуализации'
    )
    parser.add_argument(
        '--world',
        default=PROJECT_ROOT / 'src' / 'swarm_core' / 'worlds' / 'wkr_test_field_light.world',
        help='Путь к SDF-файлу мира'
    )
    parser.add_argument(
        '--output',
        default=PROJECT_ROOT / 'docs' / 'wkr_virtual_environment_topdown',
        help='Путь и базовое имя для выходных файлов'
    )
    args = parser.parse_args()

    world_path = Path(args.world)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    tree = ET.parse(world_path)
    root = tree.getroot()

    fig, ax = plt.subplots(figsize=(9, 9))
    
    # === Заголовки и подписи осей ) ===
    ax.set_title('Виртуальный полигон: вид сверху')
    ax.set_xlim(-65, 65)
    ax.set_ylim(-65, 65)
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, alpha=0.25)
    ax.set_xlabel('x, м')
    ax.set_ylabel('y, м')

    # === Зона выполнения миссии  ===
    ax.add_patch(
        Rectangle(
            (-60, -60), 120, 120,
            facecolor='#dce7df',
            edgecolor='#4f6f5f',
            lw=1.5,
            label='Зона миссии'
        )
    )

    # === Стартовые позиции агентов ===
    starts = [(-18, 0), (-13, 10), (-5, 16), (5, 16), (13, 10), (18, 0), (8, -12), (-8, -12)]
    for i, (x, y) in enumerate(starts):
        facecolor = '#1f77b4' if i < 5 else '#2ca02c'
        ax.add_patch(
            Circle((x, y), 1.2, facecolor=facecolor, edgecolor='white', lw=0.8)
        )
        # "А" 
        ax.text(x + 1.5, y + 1.5, f'А{i}', fontsize=8)

    # === Обработка моделей из SDF-мира ===
    for model in root.findall('.//model'):
        name = model.attrib.get('name', '')
        x, y = pose_xy(model.findtext('pose'))
        link = model.find('link')
        if link is None:
            continue

        if name == 'mission_area_120x120' or name == 'zona_missii_120x120':
            continue

        # Запретная зона 
        if 'restricted_zone' in name or 'zapretnaya_zona' in name:
            ax.add_patch(
                Rectangle(
                    (x - 9, y - 7), 18, 14,
                    facecolor='#cf3b31',
                    alpha=0.35,
                    edgecolor='#8a1f18',
                    label='Запретная зона'
                )
            )
            ax.text(x, y, 'Запрещено', ha='center', va='center', fontsize=8)
            continue

        # Зона риска 
        if 'risk_zone' in name or 'zona_riska' in name:
            ax.add_patch(
                Rectangle(
                    (x - 11, y - 6), 22, 12,
                    facecolor='#e0a824',
                    alpha=0.4,
                    edgecolor='#9a6d12',
                    label='Зона риска'
                )
            )
            ax.text(x, y, 'Риск', ha='center', va='center', fontsize=8)
            continue

        # Динамические препятствия 
        radius = sphere_radius(link)
        if radius is not None:
            ax.add_patch(
                Circle(
                    (x, y), radius,
                    facecolor='#d9534f',
                    edgecolor='#8c2d2a',
                    label='Динам. препятствие'
                )
            )
            continue

        # Статические препятствия 
        size = box_size(link)
        if size is not None and 'obstacle' in name or 'prep' in name:
            ax.add_patch(
                Rectangle(
                    (x - size[0] / 2, y - size[1] / 2),
                    size[0],
                    size[1],
                    facecolor='#666a70',
                    edgecolor='#33363a',
                    label='Стат. препятствие'
                )
            )

    # === Путевые точки ===
    waypoints = [(-45, -45), (45, -42), (42, 42), (-42, 44)]
    for idx, (x, y) in enumerate(waypoints, start=1):
        ax.add_patch(Circle((x, y), 1.8, facecolor='#4c78d8', edgecolor='white'))
        ax.text(x + 2.2, y + 1.5, f'Т{idx}', fontsize=9)

    # === Легенда ===
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(
        unique.values(),
        unique.keys(),
        loc='upper right',
        fontsize=8,
        title='Условные обозначения'
    )

    fig.tight_layout()
    fig.savefig(output.with_suffix('.svg'), bbox_inches='tight')
    fig.savefig(output.with_suffix('.png'), dpi=180, bbox_inches='tight')
    print(f'✓ Визуализация сохранена:')
    print(f'  {output.with_suffix(".svg")}')
    print(f'  {output.with_suffix(".png")}')


if __name__ == '__main__':
    main()

