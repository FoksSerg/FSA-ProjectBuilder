#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Разборка файла на модули
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import sys
import os
import argparse

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import APP_VERSION
from core.rebuilder import Rebuilder, rebuild_file


def main():
    """Главная функция разборки"""
    parser = argparse.ArgumentParser(
        description='FSA-ProjectBuilder - Разборка файла на модули'
    )
    parser.add_argument(
        '--project',
        type=str,
        help='Путь к проекту (директория с файлом)'
    )
    parser.add_argument(
        '--file',
        type=str,
        required=True,
        help='Имя файла для разборки'
    )
    parser.add_argument(
        '--target',
        type=str,
        help='Целевая директория для модулей (по умолчанию: modules/)'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'FSA-ProjectBuilder {APP_VERSION}'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"FSA-ProjectBuilder - Разборка на модули")
    print(f"Версия: {APP_VERSION}")
    print("=" * 60)
    print()
    
    # Определяем путь к исходному файлу
    if args.project:
        source_file = os.path.join(args.project, args.file)
    else:
        source_file = args.file
    
    source_file = os.path.abspath(source_file)
    
    if not os.path.exists(source_file):
        print(f"[ERROR] Файл не найден: {source_file}")
        sys.exit(1)
    
    # Определяем целевую директорию
    target_dir = args.target
    if args.project and not target_dir:
        target_dir = os.path.join(args.project, 'modules')
    
    # Выполняем разборку
    print(f"[INFO] Исходный файл: {source_file}")
    if target_dir:
        print(f"[INFO] Целевая директория: {target_dir}")
    print()
    
    success = rebuild_file(source_file, target_dir)
    
    if success:
        print()
        print("=" * 60)
        print("[SUCCESS] Разборка завершена успешно!")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("[ERROR] Разборка завершена с ошибками")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
