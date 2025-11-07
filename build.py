#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Сборка модулей в один файл
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import sys
import os
import argparse

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_VERSION, BUILD_CONFIG
from core.builder import Builder, build_modules


def main():
    """Главная функция сборки"""
    parser = argparse.ArgumentParser(
        description='FSA-ProjectBuilder - Сборка модулей в один файл'
    )
    parser.add_argument(
        '--project',
        type=str,
        help='Путь к проекту (директория с модулями)'
    )
    parser.add_argument(
        '--modules-dir',
        type=str,
        help='Директория с модулями (по умолчанию: modules/)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Выходной файл (по умолчанию: modules_dir + "_built.py")'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Применить очистку кода (удаление пустых строк)'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'FSA-ProjectBuilder {APP_VERSION}'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"FSA-ProjectBuilder - Сборка модулей")
    print(f"Версия: {APP_VERSION}")
    print("=" * 60)
    print()
    
    # Определяем директорию с модулями
    if args.modules_dir:
        modules_dir = os.path.abspath(args.modules_dir)
    elif args.project:
        modules_dir = os.path.join(args.project, 'modules')
    else:
        print("[ERROR] Укажите --project или --modules-dir")
        sys.exit(1)
    
    if not os.path.exists(modules_dir):
        print(f"[ERROR] Директория с модулями не найдена: {modules_dir}")
        sys.exit(1)
    
    # Определяем выходной файл
    output_file = args.output
    
    # Настройка конфигурации
    config = BUILD_CONFIG.copy()
    if args.cleanup:
        config['cleanup']['remove_empty_lines'] = True
    
    # Выполняем сборку
    print(f"[INFO] Директория модулей: {modules_dir}")
    if output_file:
        print(f"[INFO] Выходной файл: {output_file}")
    print()
    
    success = build_modules(modules_dir, output_file, config)
    
    if success:
        print()
        print("=" * 60)
        print("[SUCCESS] Сборка завершена успешно!")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("[ERROR] Сборка завершена с ошибками")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
