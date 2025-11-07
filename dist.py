#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Создание дистрибутивов
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import sys
import os
import argparse

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_VERSION, DIST_CONFIG, DISTRIBUTOR_TOOLS
from distributors import PyInstallerDistributor, CxFreezeDistributor, NuitkaDistributor


def get_available_distributors(project_dir: str) -> dict:
    """Получение доступных дистрибуторов"""
    distributors = {
        'pyinstaller': PyInstallerDistributor(project_dir),
        'cxfreeze': CxFreezeDistributor(project_dir),
        'nuitka': NuitkaDistributor(project_dir)
    }
    
    available = {}
    for name, dist in distributors.items():
        if dist.is_available():
            available[name] = dist
    
    return available


def main():
    """Главная функция создания дистрибутива"""
    parser = argparse.ArgumentParser(
        description='FSA-ProjectBuilder - Создание дистрибутивов'
    )
    parser.add_argument(
        '--project',
        type=str,
        required=True,
        help='Путь к проекту'
    )
    parser.add_argument(
        '--main',
        type=str,
        default='main.py',
        help='Главный файл проекта (по умолчанию: main.py)'
    )
    parser.add_argument(
        '--tool',
        type=str,
        choices=['pyinstaller', 'cxfreeze', 'nuitka', 'auto'],
        default='auto',
        help='Инструмент для сборки (по умолчанию: auto - автоматический выбор)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Выходная директория (по умолчанию: project/dist)'
    )
    parser.add_argument(
        '--onefile',
        action='store_true',
        help='Создать один исполняемый файл'
    )
    parser.add_argument(
        '--windowed',
        action='store_true',
        help='Скрыть консольное окно (Windows)'
    )
    parser.add_argument(
        '--icon',
        type=str,
        help='Путь к иконке'
    )
    parser.add_argument(
        '--name',
        type=str,
        help='Имя выходного файла'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'FSA-ProjectBuilder {APP_VERSION}'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"FSA-ProjectBuilder - Создание дистрибутива")
    print(f"Версия: {APP_VERSION}")
    print("=" * 60)
    print()
    
    project_dir = os.path.abspath(args.project)
    if not os.path.exists(project_dir):
        print(f"[ERROR] Директория проекта не найдена: {project_dir}")
        sys.exit(1)
    
    main_file = args.main
    main_file_path = os.path.join(project_dir, main_file)
    if not os.path.exists(main_file_path):
        print(f"[ERROR] Главный файл не найден: {main_file_path}")
        sys.exit(1)
    
    # Получаем доступные дистрибуторы
    available = get_available_distributors(project_dir)
    
    if not available:
        print("[ERROR] Не найдено доступных инструментов для создания дистрибутивов")
        print("[INFO] Установите один из следующих инструментов:")
        print("  - PyInstaller: pip install pyinstaller")
        print("  - cx_Freeze: pip install cx_Freeze")
        print("  - Nuitka: pip install nuitka")
        sys.exit(1)
    
    print(f"[INFO] Доступные инструменты: {', '.join(available.keys())}")
    
    # Выбираем дистрибутор
    if args.tool == 'auto':
        # Приоритет: PyInstaller > cx_Freeze > Nuitka
        if 'pyinstaller' in available:
            tool_name = 'pyinstaller'
        elif 'cxfreeze' in available:
            tool_name = 'cxfreeze'
        elif 'nuitka' in available:
            tool_name = 'nuitka'
        else:
            tool_name = list(available.keys())[0]
    else:
        if args.tool not in available:
            print(f"[ERROR] Инструмент '{args.tool}' недоступен")
            print(f"[INFO] Доступные инструменты: {', '.join(available.keys())}")
            sys.exit(1)
        tool_name = args.tool
    
    distributor = available[tool_name]
    
    print(f"[INFO] Используется инструмент: {tool_name}")
    print(f"[INFO] Проект: {project_dir}")
    print(f"[INFO] Главный файл: {main_file}")
    if args.output:
        print(f"[INFO] Выходная директория: {args.output}")
    print()
    
    # Подготавливаем конфигурацию
    config = DIST_CONFIG.get(tool_name, {}).copy()
    
    if args.onefile:
        config['onefile'] = True
    
    if args.windowed:
        config['windowed'] = True
    
    if args.icon:
        config['icon'] = os.path.abspath(args.icon)
    
    if args.name:
        config['name'] = args.name
    
    if args.output:
        distributor.output_dir = os.path.abspath(args.output)
    
    # Создаем дистрибутив
    success = distributor.create_distribution(main_file, config)
    
    if success:
        print()
        print("=" * 60)
        print("[SUCCESS] Дистрибутив создан успешно!")
        print(f"[INFO] Выходная директория: {distributor.output_dir}")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("[ERROR] Создание дистрибутива завершено с ошибками")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
