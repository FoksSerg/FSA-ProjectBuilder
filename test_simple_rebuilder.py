#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для SimpleRebuilder
"""

from __future__ import print_function
import sys
import os

# Добавляем путь к core
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.parser import CodeParser
from core.simple_rebuilder import SimpleRebuilder

def main():
    # Пути к файлам
    source_file = '/Volumes/FSA-PRJ/Project/FSA-ProjectBuilder/TEST/OneFile/astra_automation.py'
    target_dir = '/Volumes/FSA-PRJ/Project/FSA-ProjectBuilder/TEST/OneFile/Modules'
    
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ SIMPLE REBUILDER")
    print("=" * 80)
    print(f"Исходный файл: {source_file}")
    print(f"Целевая директория: {target_dir}")
    print()
    
    # 1. Парсим исходный файл
    print("[1/2] Парсинг исходного файла...")
    parser = CodeParser(source_file)
    if not parser.parse():
        print("[ERROR] Ошибка парсинга исходного файла")
        return False
    
    structure = parser.get_structure()
    print(f"[OK] Найдено: {len(structure['classes'])} классов, "
          f"{len(structure['functions'])} функций, "
          f"{len(structure['imports'])} импортов")
    print()
    
    # 2. Запускаем разборщик
    print("[2/2] Запуск SimpleRebuilder...")
    rebuilder = SimpleRebuilder(
        source_file=source_file,
        target_dir=target_dir,
        structure=structure
    )
    
    if rebuilder.rebuild():
        print()
        print("=" * 80)
        print("РАЗБОРКА ЗАВЕРШЕНА УСПЕШНО!")
        print("=" * 80)
        return True
    else:
        print()
        print("=" * 80)
        print("РАЗБОРКА ЗАВЕРШИЛАСЬ С ОШИБКАМИ!")
        print("=" * 80)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

