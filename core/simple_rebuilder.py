#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Упрощенный разборщик проектов
Автоматически разбирает монолитный Python файл на модульную структуру
Версия: 1.0.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import os
import ast
import json
import re
import shutil
from typing import Dict, List, Tuple, Optional, Set, Any
from .parser import CodeParser


class SimpleRebuilder:
    """Упрощенный разборщик проектов
    
    Правила:
    1. Все импорты и константы в imports.py
    2. Классы и функции содержат только from imports import * и свой код
    3. Порядок инициализации как в исходном файле
    4. Нет анализа графов зависимостей - порядок из исходника
    5. Нет добавления импортов обратно - только удаление
    6. Дедупликация импортов перед добавлением в imports.py
    """
    
    def __init__(self, source_file: str, target_dir: str, structure: Dict):
        """
        Инициализация разборщика
        
        Args:
            source_file: Путь к исходному Python файлу
            target_dir: Директория для модулей
            structure: Структура файла от CodeParser
        """
        self.source_file = os.path.abspath(source_file)
        self.source_dir = os.path.dirname(self.source_file)
        self.source_name = os.path.basename(self.source_file)
        self.source_name_no_ext = os.path.splitext(self.source_name)[0]
        self.target_dir = os.path.abspath(target_dir)
        self.metadata_dir = os.path.join(self.target_dir, '.metadata')
        self.structure = structure
        
        # Читаем исходный код
        with open(self.source_file, 'r', encoding='utf-8') as f:
            self.source_code = f.read()
            self.source_lines = self.source_code.split('\n')
        
        # Парсим AST
        self.ast_tree = ast.parse(self.source_code, filename=self.source_file)
        
        # Собранные импорты (все уровни)
        self.all_imports = []  # List[Dict]
        self.conditional_imports = []  # List[Tuple[start_line, end_line, code]]
        self.overrides = []  # List[Dict]
        
        # Глобальные переменные
        self.global_init = []  # List[Dict] - для init.py
        self.simple_constants = []  # List[Dict] - для imports.py
        
        # Порядок классов из исходного файла
        self.class_order = []
        
        # Массив всех компонентов (классы и функции) с полным кодом
        self.components = []  # List[Dict] - все компоненты с полным кодом
        
    def rebuild(self) -> bool:
        """
        Главный метод разборки
        
        Returns:
            bool: True если разборка успешна, False если ошибка
        """
        print(f"[SIMPLE_REBUILD] Начало разборки файла: {self.source_file}")
        print(f"[SIMPLE_REBUILD] Всего строк в исходном файле: {len(self.source_lines)}")
        
        # 1. Извлекаем все компоненты (классы и функции) в массив
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 1: Извлечение всех компонентов")
        print("[SIMPLE_REBUILD] ========================================")
        if not self._extract_all_components():
            print("[ERROR] Ошибка извлечения компонентов")
            return False
        
        # 2. Проверяем целостность извлечения
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 2: Валидация извлечения")
        print("[SIMPLE_REBUILD] ========================================")
        if not self._validate_extraction():
            print("[ERROR] Ошибка валидации извлечения")
            return False
        
        # 3. Создаем структуру папок
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 3: Создание структуры папок")
        print("[SIMPLE_REBUILD] ========================================")
        if not self._create_structure():
            print("[ERROR] Ошибка создания структуры папок")
            return False
        
        # 4. Собираем все импорты (верхний уровень, классы, функции)
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 4: Сбор всех импортов")
        print("[SIMPLE_REBUILD] ========================================")
        self._collect_all_imports()
        
        # 5. Ищем переопределения встроенных функций/модулей
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 5: Поиск переопределений")
        print("[SIMPLE_REBUILD] ========================================")
        self._find_builtin_overrides()
        
        # 6. Разделяем константы и глобальные переменные
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 6: Анализ констант и глобальных переменных")
        print("[SIMPLE_REBUILD] ========================================")
        self._analyze_constants_and_globals()
        
        # 7. Генерируем imports.py
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 7: Генерация imports.py")
        print("[SIMPLE_REBUILD] ========================================")
        if not self._generate_imports_code():
            print("[ERROR] Ошибка генерации imports.py")
            return False
        
        # 8. Генерируем модули классов
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 8: Генерация модулей классов")
        print("[SIMPLE_REBUILD] ========================================")
        if not self._distribute_classes():
            print("[ERROR] Ошибка генерации модулей классов")
            return False
        
        # 9. Генерируем модули функций
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 9: Генерация модулей функций")
        print("[SIMPLE_REBUILD] ========================================")
        if not self._distribute_functions():
            print("[ERROR] Ошибка генерации модулей функций")
            return False
        
        # 10. Генерируем init.py
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 10: Генерация init.py")
        print("[SIMPLE_REBUILD] ========================================")
        if not self._generate_init_code():
            print("[ERROR] Ошибка генерации init.py")
            return False
        
        # 11. Генерируем лаунчер
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 11: Генерация лаунчера")
        print("[SIMPLE_REBUILD] ========================================")
        if not self._generate_launcher_file():
            print("[ERROR] Ошибка генерации лаунчера")
            return False
        
        # 12. Генерируем __init__.py файлы
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 12: Генерация __init__.py файлов")
        print("[SIMPLE_REBUILD] ========================================")
        if not self._generate_init_files():
            print("[ERROR] Ошибка генерации __init__.py файлов")
            return False
        
        # 13. Сохраняем метаданные
        print("[SIMPLE_REBUILD] ========================================")
        print("[SIMPLE_REBUILD] ЭТАП 13: Сохранение метаданных")
        print("[SIMPLE_REBUILD] ========================================")
        self._save_metadata()
        
        print("[SIMPLE_REBUILD] Разборка завершена успешно!")
        return True
    
    def _extract_all_components(self) -> bool:
        """
        Извлечение всех компонентов (классов и функций) в массив
        
        Returns:
            bool: True если извлечение успешно, False если ошибка
        """
        print("[SIMPLE_REBUILD]   Начало извлечения компонентов...")
        
        # Извлекаем классы
        classes = self.structure.get('classes', [])
        print(f"[SIMPLE_REBUILD]   Найдено классов: {len(classes)}")
        
        for i, cls in enumerate(classes, 1):
            class_name = cls.get('name', '')
            start_line = cls.get('start_line', 0)
            end_line = cls.get('end_line', 0)
            code = cls.get('code', '')
            
            # Определяем категорию
            category = self._determine_category(class_name)
            
            # Подсчитываем строки кода
            code_lines = len(code.split('\n')) if code else 0
            
            print(f"[SIMPLE_REBUILD]   [{i}/{len(classes)}] Класс: {class_name}")
            print(f"[SIMPLE_REBUILD]      - Строки: {start_line}-{end_line} ({end_line - start_line + 1} строк)")
            print(f"[SIMPLE_REBUILD]      - Код: {code_lines} строк")
            print(f"[SIMPLE_REBUILD]      - Категория: {category}")
            
            # Сохраняем в массив компонентов
            self.components.append({
                'type': 'class',
                'name': class_name,
                'code': code,
                'start_line': start_line,
                'end_line': end_line,
                'category': category,
                'original': cls  # Сохраняем оригинальную структуру
            })
            
            # Сохраняем порядок классов
            self.class_order.append(class_name)
        
        # Извлекаем функции
        functions = self.structure.get('functions', [])
        print(f"[SIMPLE_REBUILD]   Найдено функций: {len(functions)}")
        
        for i, func in enumerate(functions, 1):
            func_name = func.get('name', '')
            start_line = func.get('start_line', 0)
            end_line = func.get('end_line', 0)
            code = func.get('code', '')
            
            # Определяем модуль для функции
            if func_name == 'main':
                module = 'main'
            elif func_name.startswith('run_'):
                module = 'runner_functions'
            elif func_name.startswith('cleanup_'):
                module = 'cleanup'
            else:
                module = 'utils'
            
            # Подсчитываем строки кода
            code_lines = len(code.split('\n')) if code else 0
            
            print(f"[SIMPLE_REBUILD]   [{i}/{len(functions)}] Функция: {func_name}")
            print(f"[SIMPLE_REBUILD]      - Строки: {start_line}-{end_line} ({end_line - start_line + 1} строк)")
            print(f"[SIMPLE_REBUILD]      - Код: {code_lines} строк")
            print(f"[SIMPLE_REBUILD]      - Модуль: {module}")
            
            # Сохраняем в массив компонентов
            self.components.append({
                'type': 'function',
                'name': func_name,
                'code': code,
                'start_line': start_line,
                'end_line': end_line,
                'module': module,
                'original': func  # Сохраняем оригинальную структуру
            })
        
        print(f"[SIMPLE_REBUILD]   Итого компонентов извлечено: {len(self.components)}")
        print(f"[SIMPLE_REBUILD]   - Классов: {len(classes)}")
        print(f"[SIMPLE_REBUILD]   - Функций: {len(functions)}")
        
        return True
    
    def _validate_extraction(self) -> bool:
        """
        Валидация извлечения компонентов
        
        Проверяет:
        1. Все ли компоненты извлечены
        2. Нет ли пропусков в коде
        3. Правильность границ компонентов
        
        Returns:
            bool: True если валидация успешна, False если ошибка
        """
        print("[SIMPLE_REBUILD]   Начало валидации извлечения...")
        
        # 1. Проверяем, что все компоненты извлечены
        classes_count = len([c for c in self.components if c['type'] == 'class'])
        functions_count = len([c for c in self.components if c['type'] == 'function'])
        
        expected_classes = len(self.structure.get('classes', []))
        expected_functions = len(self.structure.get('functions', []))
        
        print(f"[SIMPLE_REBUILD]   Проверка количества компонентов:")
        print(f"[SIMPLE_REBUILD]      - Классов: извлечено {classes_count}, ожидалось {expected_classes}")
        print(f"[SIMPLE_REBUILD]      - Функций: извлечено {functions_count}, ожидалось {expected_functions}")
        
        if classes_count != expected_classes:
            print(f"[ERROR] Несоответствие количества классов: {classes_count} != {expected_classes}")
            return False
        
        if functions_count != expected_functions:
            print(f"[ERROR] Несоответствие количества функций: {functions_count} != {expected_functions}")
            return False
        
        # 2. Проверяем покрытие кода
        covered_lines = set()
        total_code_lines = 0
        
        for comp in self.components:
            start = comp.get('start_line', 0)
            end = comp.get('end_line', 0)
            code = comp.get('code', '')
            
            if start and end:
                # Добавляем строки в покрытие
                comp_lines = set(range(start, end + 1))
                covered_lines.update(comp_lines)
                
                # Подсчитываем строки кода
                code_lines = len(code.split('\n')) if code else 0
                total_code_lines += code_lines
        
        print(f"[SIMPLE_REBUILD]   Проверка покрытия кода:")
        print(f"[SIMPLE_REBUILD]      - Покрыто строк: {len(covered_lines)}")
        print(f"[SIMPLE_REBUILD]      - Всего строк кода в компонентах: {total_code_lines}")
        print(f"[SIMPLE_REBUILD]      - Всего строк в исходном файле: {len(self.source_lines)}")
        
        # 3. Проверяем, что код компонентов не пустой
        empty_components = []
        for comp in self.components:
            code = comp.get('code', '').strip()
            if not code:
                empty_components.append(comp['name'])
        
        if empty_components:
            print(f"[WARNING] Найдены компоненты с пустым кодом: {', '.join(empty_components)}")
        
        # 4. Проверяем границы компонентов
        overlapping = []
        components_sorted = sorted(self.components, key=lambda x: x.get('start_line', 0))
        
        for i in range(len(components_sorted) - 1):
            curr = components_sorted[i]
            next_comp = components_sorted[i + 1]
            
            curr_end = curr.get('end_line', 0)
            next_start = next_comp.get('start_line', 0)
            
            if curr_end >= next_start:
                overlapping.append({
                    'first': curr['name'],
                    'second': next_comp['name'],
                    'overlap': curr_end - next_start + 1
                })
        
        if overlapping:
            print(f"[WARNING] Найдены перекрывающиеся компоненты:")
            for overlap in overlapping:
                print(f"[WARNING]   - {overlap['first']} и {overlap['second']} перекрываются на {overlap['overlap']} строк")
        else:
            print(f"[SIMPLE_REBUILD]   Перекрытий компонентов не найдено")
        
        # 5. Проверяем, что все компоненты имеют правильную структуру
        invalid_components = []
        for comp in self.components:
            if not comp.get('name'):
                invalid_components.append('компонент без имени')
            if not comp.get('code'):
                invalid_components.append(f"{comp.get('name', 'unknown')} без кода")
            if not comp.get('start_line') or not comp.get('end_line'):
                invalid_components.append(f"{comp.get('name', 'unknown')} без границ")
        
        if invalid_components:
            print(f"[ERROR] Найдены некорректные компоненты: {', '.join(invalid_components)}")
            return False
        
        print(f"[SIMPLE_REBUILD]   Валидация завершена успешно!")
        print(f"[SIMPLE_REBUILD]   Все компоненты извлечены и проверены")
        
        return True
    
    def _create_structure(self) -> bool:
        """Создание структуры папок"""
        try:
            # Создаем целевую директорию
            os.makedirs(self.target_dir, exist_ok=True)
            
            # Создаем папки категорий (определим при распределении классов)
            # Пока создаем только utils и metadata
            os.makedirs(os.path.join(self.target_dir, 'utils'), exist_ok=True)
            os.makedirs(self.metadata_dir, exist_ok=True)
            
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка создания структуры: {e}")
            return False
    
    def _determine_category(self, class_name: str) -> str:
        """Определение категории класса по имени"""
        name_lower = class_name.lower()
        
        if 'handler' in name_lower:
            return 'handlers'
        elif 'manager' in name_lower or 'monitor' in name_lower:
            return 'managers'
        elif 'gui' in name_lower or 'window' in name_lower or 'dialog' in name_lower:
            return 'gui'
        elif 'analyzer' in name_lower or 'checker' in name_lower:
            return 'analyzers'
        elif 'log' in name_lower or 'logger' in name_lower:
            return 'loggers'
        else:
            return 'core'
    
    def _collect_all_imports(self):
        """Сбор всех импортов из верхнего уровня, классов и функций"""
        print("[SIMPLE_REBUILD]   - Импорты верхнего уровня...")
        # 1. Импорты верхнего уровня (из structure)
        top_level_imports = self.structure.get('imports', [])
        self.all_imports.extend(top_level_imports)
        print(f"[SIMPLE_REBUILD]   - Найдено {len(top_level_imports)} импортов верхнего уровня")
        
        # 2. Импорты из классов (только верхний уровень класса, не методы)
        print("[SIMPLE_REBUILD]   - Импорты из классов...")
        classes = self.structure.get('classes', [])
        for i, class_info in enumerate(classes, 1):
            class_code = class_info.get('code', '')
            if class_code:
                # Упрощенный подход: извлекаем импорты только из начала класса (до первого метода)
                imports = self._extract_imports_from_class_start(class_code)
                self.all_imports.extend(imports)
            if i % 10 == 0:
                print(f"[SIMPLE_REBUILD]   - Обработано {i}/{len(classes)} классов...")
        
        # 3. Импорты из функций (только верхний уровень функции)
        print("[SIMPLE_REBUILD]   - Импорты из функций...")
        functions = self.structure.get('functions', [])
        for func_info in functions:
            func_code = func_info.get('code', '')
            if func_code:
                # Упрощенный подход: извлекаем импорты только из начала функции
                imports = self._extract_imports_from_function_start(func_code)
                self.all_imports.extend(imports)
        
        # 4. Ищем условные импорты (try-except, if)
        print("[SIMPLE_REBUILD]   - Поиск условных импортов...")
        self._find_conditional_imports()
        
        # 5. Дедуплицируем импорты
        print("[SIMPLE_REBUILD]   - Дедупликация импортов...")
        self.all_imports = self._deduplicate_imports(self.all_imports)
        print(f"[SIMPLE_REBUILD]   - Итого уникальных импортов: {len(self.all_imports)}")
    
    def _extract_imports_from_class_start(self, code: str) -> List[Dict]:
        """Извлечение импортов из начала класса (до первого метода)"""
        imports = []
        lines = code.split('\n')
        
        # Находим минимальный отступ класса
        class_indent = None
        for line in lines:
            if line.strip() and not line.strip().startswith('#'):
                class_indent = len(line) - len(line.lstrip())
                break
        
        if class_indent is None:
            return imports
        
        # Извлекаем импорты только из начала класса (до первого метода/вложенного класса)
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Пропускаем пустые строки и комментарии
            if not stripped or stripped.startswith('#'):
                continue
            
            # Проверяем отступ - должен быть на уровне класса
            indent = len(line) - len(line.lstrip())
            if indent != class_indent:
                continue
            
            # Если встретили определение метода или вложенного класса - останавливаемся
            if stripped.startswith('def ') or stripped.startswith('class '):
                break
            
            # Проверяем, является ли строка импортом
            if stripped.startswith('import ') or stripped.startswith('from '):
                # Парсим импорт через regex
                import_info = self._parse_import_line(stripped)
                if import_info:
                    imports.extend(import_info)
        
        return imports
    
    def _extract_imports_from_function_start(self, code: str) -> List[Dict]:
        """Извлечение импортов из начала функции"""
        imports = []
        lines = code.split('\n')
        
        # Находим отступ функции (первая строка после def)
        func_indent = None
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                # Следующая строка после def - это тело функции
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.strip():
                        func_indent = len(next_line) - len(next_line.lstrip())
                break
        
        if func_indent is None:
            return imports
        
        # Извлекаем импорты только из начала функции (до первого оператора)
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Пропускаем пустые строки и комментарии
            if not stripped or stripped.startswith('#'):
                continue
            
            # Проверяем отступ - должен быть на уровне тела функции
            indent = len(line) - len(line.lstrip())
            if indent != func_indent:
                continue
            
            # Если встретили оператор (не импорт) - останавливаемся
            if not (stripped.startswith('import ') or stripped.startswith('from ')):
                break
            
            # Парсим импорт
            if stripped.startswith('import ') or stripped.startswith('from '):
                import_info = self._parse_import_line(stripped)
                if import_info:
                    imports.extend(import_info)
        
        return imports
    
    def _parse_import_line(self, line: str) -> List[Dict]:
        """Парсинг строки импорта"""
        imports = []
        
        # Простой импорт: import module
        match = re.match(r'^import\s+(\w+(?:\s*,\s*\w+)*)', line)
        if match:
            modules = [m.strip() for m in match.group(1).split(',')]
            for module in modules:
                imports.append({
                    'type': 'import',
                    'module': module,
                    'alias': None,
                    'line': 0
                })
            return imports
        
        # Импорт from: from module import name
        match = re.match(r'^from\s+(\S+)\s+import\s+(.+)', line)
        if match:
            module = match.group(1)
            names = match.group(2)
            for name in names.split(','):
                name = name.strip()
                alias = None
                if ' as ' in name:
                    name, alias = name.split(' as ', 1)
                    name = name.strip()
                    alias = alias.strip()
                imports.append({
                    'type': 'from_import',
                    'module': module,
                    'name': name,
                    'alias': alias,
                    'line': 0
                })
        
        return imports
    
    def _get_parent_node(self, tree: ast.AST, target: ast.AST) -> Optional[ast.AST]:
        """Получение родительского узла (упрощенная версия)"""
        class ParentFinder(ast.NodeVisitor):
            def __init__(self, target):
                self.target = target
                self.parent = None
                self._found = False
            
            def generic_visit(self, node):
                if self._found:
                    return
                
                for child in ast.iter_child_nodes(node):
                    if child == self.target:
                        self.parent = node
                        self._found = True
                        return
                    self.generic_visit(child)
        
        finder = ParentFinder(target)
        finder.generic_visit(tree)
        return finder.parent
    
    def _extract_imports_regex(self, code: str, top_level_only: bool) -> List[Dict]:
        """Извлечение импортов через regex (fallback)"""
        imports = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Простой импорт
            match = re.match(r'^import\s+(\w+(?:\s*,\s*\w+)*)', stripped)
            if match:
                modules = [m.strip() for m in match.group(1).split(',')]
                for module in modules:
                    imports.append({
                        'type': 'import',
                        'module': module,
                        'alias': None,
                        'line': i
                    })
            
            # Импорт from
            match = re.match(r'^from\s+(\S+)\s+import\s+(.+)', stripped)
            if match:
                module = match.group(1)
                names = match.group(2)
                for name in names.split(','):
                    name = name.strip()
                    if ' as ' in name:
                        name, alias = name.split(' as ', 1)
                        name = name.strip()
                        alias = alias.strip()
                    else:
                        alias = None
                    imports.append({
                        'type': 'from_import',
                        'module': module,
                        'name': name,
                        'alias': alias,
                        'line': i
                    })
        
        return imports
    
    def _find_conditional_imports(self):
        """Поиск условных импортов (try-except, if)
        ВАЖНО: Используем массив компонентов для проверки покрытия!
        Не включаем код из классов/функций в условные импорты!
        """
        # Строим карту покрытия компонентов
        covered_lines = set()
        for comp in self.components:
            start = comp.get('start_line', 0)
            end = comp.get('end_line', 0)
            if start and end:
                covered_lines.update(range(start, end + 1))
        
        lines = self.source_lines
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Пропускаем код из классов/функций
            if (i + 1) in covered_lines:
                i += 1
                continue
            
            # Ищем try-except блоки с импортами
            if line.startswith('try:'):
                start_line = i + 1
                # Ищем соответствующий except
                indent = len(lines[i]) - len(lines[i].lstrip())
                j = i + 1
                found_except = False
                
                while j < len(lines):
                    curr_line = lines[j].strip()
                    if not curr_line or curr_line.startswith('#'):
                        j += 1
                        continue
                    
                    curr_indent = len(lines[j]) - len(lines[j].lstrip())
                    if curr_indent <= indent and curr_line.startswith('except'):
                        found_except = True
                        # Ищем конец блока except
                        while j < len(lines):
                            if lines[j].strip() and not lines[j].strip().startswith('#'):
                                if len(lines[j]) - len(lines[j].lstrip()) <= indent:
                                    if not lines[j].strip().startswith('except'):
                                        break
                            j += 1
                        end_line = j
                        break
                    j += 1
                
                if found_except:
                    # Проверяем, есть ли импорты в этом блоке
                    block_code = '\n'.join(lines[start_line - 1:end_line])
                    if 'import ' in block_code or 'from ' in block_code:
                        self.conditional_imports.append((start_line, end_line, block_code))
                    i = end_line
                    continue
            
            # Ищем if блоки с импортами (платформенные импорты)
            # ВАЖНО: Проверяем, что это верхний уровень (без отступов)
            if line.startswith('if ') and not lines[i].startswith((' ', '\t')):
                # Проверяем, что в следующих строках есть импорт
                has_import = False
                for j in range(i + 1, min(i + 10, len(lines))):
                    if (j + 1) in covered_lines:
                        break  # Попали в компонент - пропускаем
                    curr_line = lines[j].strip()
                    if curr_line.startswith('import ') or curr_line.startswith('from '):
                        has_import = True
                        break
                
                if has_import:
                    # Упрощенная проверка - если в следующих строках есть импорт
                    start_line = i + 1
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    j = i + 1
                    
                    while j < len(lines) and j < i + 10:  # Ограничиваем поиск
                        if (j + 1) in covered_lines:
                            break  # Попали в компонент - пропускаем
                        curr_line = lines[j].strip()
                        if curr_line.startswith('import ') or curr_line.startswith('from '):
                            # Ищем конец блока
                            while j < len(lines):
                                if (j + 1) in covered_lines:
                                    break  # Попали в компонент
                                if lines[j].strip() and not lines[j].strip().startswith('#'):
                                    curr_indent = len(lines[j]) - len(lines[j].lstrip())
                                    if curr_indent <= indent:
                                        break
                                j += 1
                            end_line = j
                            block_code = '\n'.join(lines[start_line - 1:end_line])
                            self.conditional_imports.append((start_line, end_line, block_code))
                            i = end_line
                            break
                        j += 1
            
            i += 1
    
    def _deduplicate_imports(self, imports: List[Dict]) -> List[Dict]:
        """Дедупликация импортов с сохранением порядка"""
        seen = set()
        result = []
        
        # Сначала добавляем __future__ импорты (они должны быть первыми)
        future_imports = []
        other_imports = []
        
        for imp in imports:
            if imp['type'] == 'from_import' and imp['module'] == '__future__':
                future_imports.append(imp)
            else:
                other_imports.append(imp)
        
        # Дедуплицируем __future__ импорты
        for imp in future_imports:
            key = (imp['type'], imp['module'], imp['name'], imp.get('alias'))
            if key not in seen:
                seen.add(key)
                result.append(imp)
        
        # Дедуплицируем остальные импорты
        for imp in other_imports:
            # Создаем ключ для дедупликации
            if imp['type'] == 'import':
                key = (imp['type'], imp['module'], imp.get('alias'))
            else:  # from_import
                # Пропускаем импорты из исходного файла (astra_automation)
                if imp['module'] == self.source_name_no_ext or imp['module'] == 'astra_automation':
                    continue
                key = (imp['type'], imp['module'], imp['name'], imp.get('alias'))
            
            if key not in seen:
                seen.add(key)
                result.append(imp)
        
        return result
    
    def _find_builtin_overrides(self):
        """Универсальный поиск переопределений встроенных функций/модулей"""
        patterns = [
            # builtins.*
            ('builtins', ['print', 'input', 'open', '__import__', 'exit', 'quit']),
            # sys.*
            ('sys', ['stdout', 'stderr', 'stdin', 'excepthook', 'displayhook', 'exit']),
            # sys._* (глобальные переменные)
            ('sys', ['_gui_instance', '_original_print', '_original_input']),
        ]
        
        for module_name, attributes in patterns:
            for attr_name in attributes:
                # Ищем присваивание module.attr = ...
                for node in ast.walk(self.ast_tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Attribute):
                                if (isinstance(target.value, ast.Name) and 
                                    target.value.id == module_name and
                                    target.attr == attr_name):
                                    # Нашли переопределение
                                    override_info = self._extract_related_code(node)
                                    if override_info:
                                        self.overrides.append(override_info)
    
    def _extract_related_code(self, assign_node: ast.Assign) -> Optional[Dict]:
        """Извлечение связанного кода переопределения"""
        # Находим функцию, которая присваивается
        if isinstance(assign_node.value, ast.Name):
            func_name = assign_node.value.id
            
            # Ищем определение функции
            func_def = None
            related_vars = []
            
            for node in ast.walk(self.ast_tree):
                # Ищем определение функции
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    func_def = node
                
                # Ищем связанные переменные (_original_print и т.д.)
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            # Ищем переменные, связанные с builtins.print
                            if (isinstance(node.value, ast.Attribute) and
                                isinstance(node.value.value, ast.Name) and
                                node.value.value.id == 'builtins' and
                                node.value.attr == 'print'):
                                related_vars.append(node)
            
            if func_def:
                # Определяем границы блока
                start_line = min(
                    func_def.lineno,
                    assign_node.lineno,
                    *[v.lineno for v in related_vars] if related_vars else [assign_node.lineno]
                )
                end_line = max(
                    func_def.end_lineno if hasattr(func_def, 'end_lineno') else func_def.lineno,
                    assign_node.lineno,
                    *[v.lineno for v in related_vars] if related_vars else [assign_node.lineno]
                )
                
                # Извлекаем код блока
                code = '\n'.join(self.source_lines[start_line - 1:end_line])
                
                return {
                    'target': f'{assign_node.targets[0].value.id}.{assign_node.targets[0].attr}',
                    'start_line': start_line,
                    'end_line': end_line,
                    'code': code
                }
        
        return None
    
    def _analyze_constants_and_globals(self):
        """Анализ констант и глобальных переменных
        
        ВАЖНО: Используем массив компонентов для проверки покрытия.
        Только потом анализируем константы верхнего уровня.
        """
        print("[SIMPLE_REBUILD]   Начало анализа констант и глобальных переменных...")
        
        # 1. Строим карту покрытия кода из массива компонентов
        covered_lines = set()
        
        for comp in self.components:
            start = comp.get('start_line', 0)
            end = comp.get('end_line', 0)
            if start and end:
                covered_lines.update(range(start, end + 1))
        
        # Сохраняем covered_lines для использования в _generate_imports_code
        self.covered_lines = covered_lines
        
        print(f"[SIMPLE_REBUILD]   - Покрыто строками компонентов: {len(covered_lines)}")
        
        # 2. Теперь анализируем константы - только те, что НЕ внутри классов/функций
        constants = self.structure.get('constants', [])
        print(f"[SIMPLE_REBUILD]   - Найдено констант парсером: {len(constants)}")
        
        skipped_by_coverage = 0
        skipped_by_indent = 0
        skipped_by_keywords = 0
        added_constants = 0
        
        for const in constants:
            name = const.get('name', '')
            code = const.get('code', '')
            line = const.get('line', 0)
            end_line = const.get('end_line', line)  # Используем end_line из AST!
            
            # Пропускаем константы внутри классов или функций
            # Проверяем покрытие по ВСЕМ строкам константы
            const_lines = set(range(line, end_line + 1))
            if const_lines.intersection(covered_lines):
                skipped_by_coverage += 1
                continue
            
            # Проверяем оригинальный код (до strip) на наличие отступов
            original_code = const.get('code', '')
            if original_code and original_code[0] in [' ', '\t']:
                skipped_by_indent += 1
                continue
            
            code = code.strip()
            
            # Пропускаем код, который явно не является константой
            # (содержит self, if, def, class, return, методы классов, и т.д.)
            forbidden_keywords = ['self.', 'if ', 'def ', 'class ', 'return ', 'import ', 'from ', 
                                'try:', 'except', 'for ', 'while ', 'with ', 'check_status', 
                                'update_status', 'update_progress', 'print(']
            if any(keyword in code for keyword in forbidden_keywords):
                continue
            
            # Проверяем, является ли это инициализацией экземпляра класса
            if '(' in code and '=' in code:
                # Пытаемся найти вызов конструктора класса
                match = re.search(r'=\s*(\w+)\s*\(', code)
                if match:
                    class_name = match.group(1)
                    # Это глобальная переменная с экземпляром класса
                    self.global_init.append({
                        'name': name,
                        'class_name': class_name,
                        'code': code,
                        'line': line
                    })
                    continue
            
            # Простая константа (только если это действительно присваивание верхнего уровня)
            if '=' in code and not code.strip().startswith('#'):
                # Проверяем, что это простое присваивание
                # Исключаем код с ключевыми словами, методами, операторами управления потоком
                forbidden_keywords = ['if ', 'def ', 'class ', 'self.', 'return ', 'try:', 'except',
                                     'for ', 'while ', 'with ', 'import ', 'from ', 'print(', 'os.',
                                     'sys.', 'check_status', 'update_status', 'update_progress']
                if any(keyword in code for keyword in forbidden_keywords):
                    continue
                # Для многострочных - только словари/списки/кортежи (константы)
                if '\n' in code:
                    if not (code.strip().startswith(('{', '[', '(')) or name in ['COMPONENTS_CONFIG', 'APP_VERSION']):
                        continue
                # Проверяем, что имя константы соответствует коду
                if name and not code.strip().startswith(name):
                    continue
                self.simple_constants.append(const)
                added_constants += 1
            else:
                skipped_by_keywords += 1
        
        print(f"[SIMPLE_REBUILD]   Статистика фильтрации констант:")
        print(f"[SIMPLE_REBUILD]      - Пропущено по покрытию (внутри классов/функций): {skipped_by_coverage}")
        print(f"[SIMPLE_REBUILD]      - Пропущено по отступам (код из классов): {skipped_by_indent}")
        print(f"[SIMPLE_REBUILD]      - Пропущено по ключевым словам (не константы): {skipped_by_keywords}")
        print(f"[SIMPLE_REBUILD]      - Добавлено простых констант: {added_constants}")
        print(f"[SIMPLE_REBUILD]   - Итого простых констант: {len(self.simple_constants)}")
        print(f"[SIMPLE_REBUILD]   - Итого глобальных переменных для init.py: {len(self.global_init)}")
    
    def _generate_imports_code(self) -> bool:
        """Генерация imports.py"""
        try:
            lines = []
            
            # Заголовок
            lines.append('#!/usr/bin/env python')
            lines.append('# -*- coding: utf-8 -*-')
            lines.append('"""')
            lines.append(f'Автоматически сгенерированный модуль из {self.source_name}')
            lines.append('Все импорты и константы из исходного файла')
            lines.append('Используется всеми классами и функциями')
            lines.append('"""')
            lines.append('')
            
            # 1. __future__ импорты (добавляем один раз, если есть)
            # Проверяем, есть ли __future__ импорты в списке
            has_future_print = False
            for imp in self.all_imports:
                if imp['type'] == 'from_import' and imp['module'] == '__future__' and imp['name'] == 'print_function':
                    has_future_print = True
                    break
            
            if has_future_print:
                lines.append('from __future__ import print_function')
                lines.append('')
            
            # 2. Простые импорты (в порядке из исходника)
            lines.append('# ============================================================================')
            lines.append('# ИМПОРТЫ')
            lines.append('# ============================================================================')
            
            # Группируем импорты
            simple_imports = [imp for imp in self.all_imports if imp['type'] == 'import']
            from_imports = [imp for imp in self.all_imports if imp['type'] == 'from_import']
            
            # Простые импорты
            for imp in simple_imports:
                if imp.get('alias'):
                    lines.append(f"import {imp['module']} as {imp['alias']}")
                else:
                    lines.append(f"import {imp['module']}")
            
            # Импорты from (исключаем __future__ - они уже добавлены)
            from_groups = {}
            for imp in from_imports:
                # Пропускаем __future__ импорты (они уже добавлены)
                if imp['module'] == '__future__':
                    continue
                # Пропускаем импорты из исходного файла (это циклические импорты)
                if imp['module'] == self.source_name_no_ext or imp['module'] == 'astra_automation':
                    # Но сохраняем информацию о функции get_component_field - она должна быть в utils.utils
                    if imp['name'] == 'get_component_field':
                        # Эта функция будет импортирована из utils.utils
                        continue
                    continue
                module = imp['module']
                if module not in from_groups:
                    from_groups[module] = []
                from_groups[module].append(imp)
            
            for module, imports in from_groups.items():
                names = []
                for imp in imports:
                    if imp.get('alias'):
                        names.append(f"{imp['name']} as {imp['alias']}")
                    else:
                        names.append(imp['name'])
                lines.append(f"from {module} import {', '.join(names)}")
            
            lines.append('')
            
            # 3. Условные импорты (try-except, if)
            if self.conditional_imports:
                lines.append('# ============================================================================')
                lines.append('# УСЛОВНЫЕ ИМПОРТЫ')
                lines.append('# ============================================================================')
                for start, end, code in self.conditional_imports:
                    lines.append(code)
                    lines.append('')
            
            # 4. Переопределения (после всех импортов)
            if self.overrides:
                lines.append('# ============================================================================')
                lines.append('# ПЕРЕОПРЕДЕЛЕНИЯ ВСТРОЕННЫХ ФУНКЦИЙ/МОДУЛЕЙ')
                lines.append('# ============================================================================')
                for override in self.overrides:
                    lines.append(override['code'])
                    lines.append('')
            
            # 5. Константы (только простые присваивания верхнего уровня)
            if self.simple_constants:
                lines.append('# ============================================================================')
                lines.append('# КОНСТАНТЫ')
                lines.append('# ============================================================================')
                final_constants = []
                skipped_count = 0
                
                for const in self.simple_constants:
                    code = const.get('code', '')
                    name = const.get('name', '')
                    line = const.get('line', 0)
                    
                    # Проверяем оригинальный код (до strip) на наличие отступов
                    original_code = code
                    if original_code and original_code[0] in [' ', '\t']:
                        skipped_count += 1
                        continue
                    
                    code = code.strip()
                    
                    # ВАЖНО: Специальные константы (COMPONENTS_CONFIG, APP_VERSION) пропускаем проверку
                    # Они должны попасть в imports.py независимо от фильтров
                    is_special_constant = name in ['COMPONENTS_CONFIG', 'APP_VERSION']
                    
                    # Проверяем, что это действительно простая константа
                    # Исключаем код с ключевыми словами, методами, операторами управления потоком
                    forbidden_keywords = ['if ', 'def ', 'class ', 'self.', 'return ', 'try:', 'except', 
                                         'for ', 'while ', 'with ', 'import ', 'from ', 'print(', 'os.', 
                                         'sys.', 'check_status', 'update_status', 'update_progress',
                                         'wineprefix_path', 'processes_list', 'return_code', 'real_user',
                                         'actual_status', 'component_id', 'config', 'stage_name', 'stage_progress']
                    
                    # Пропускаем код с запрещенными ключевыми словами (кроме специальных констант)
                    if not is_special_constant and any(keyword in code for keyword in forbidden_keywords):
                        skipped_count += 1
                        continue
                    
                    # Пропускаем код, который не является присваиванием
                    if '=' not in code:
                        skipped_count += 1
                        continue
                    
                    # Проверяем, что это простое присваивание (одна строка или простое многострочное)
                    if '\n' in code:
                        # Для многострочных - проверяем, что это словарь/список, а не код
                        if not (code.strip().startswith(('{', '[', '(')) or name in ['COMPONENTS_CONFIG', 'APP_VERSION']):
                            skipped_count += 1
                            continue
                        
                        # Для многострочных констант проверяем, что все строки не содержат запрещенных ключевых слов
                        # ВАЖНО: Специальные константы пропускаем эту проверку
                        if not is_special_constant:
                            code_lines = code.split('\n')
                            has_forbidden = False
                            for line_text in code_lines:
                                line_stripped = line_text.strip()
                                # Пропускаем пустые строки и комментарии
                                if not line_stripped or line_stripped.startswith('#'):
                                    continue
                                # Проверяем на запрещенные ключевые слова
                                if any(keyword in line_stripped for keyword in forbidden_keywords):
                                    has_forbidden = True
                                    break
                                # Проверяем, что строка не начинается с отступа (код из классов)
                                # ВАЖНО: Для словарей/списков отступы допустимы (это структура данных)
                                # Проверяем только, что это не код (if, def, class и т.д.)
                                if line_text and line_text[0] in [' ', '\t']:
                                    # Проверяем, не является ли это кодом (if, def, class и т.д.)
                                    if any(line_stripped.startswith(kw) for kw in ['if ', 'def ', 'class ', 'return ', 'for ', 'while ', 'with ', 'try:', 'except']):
                                        has_forbidden = True
                                        break
                            
                            if has_forbidden:
                                skipped_count += 1
                                continue
                    
                    # Проверяем, что имя константы соответствует коду
                    if name and not code.strip().startswith(name):
                        skipped_count += 1
                        continue
                    
                    # Проверяем, что код не попадает в покрытие компонентов
                    if hasattr(self, 'covered_lines') and line in self.covered_lines:
                        skipped_count += 1
                        continue
                    
                    # Дополнительная проверка: для многострочных констант проверяем все строки
                    if '\n' in code and hasattr(self, 'covered_lines'):
                        code_lines = code.split('\n')
                        for i, line_text in enumerate(code_lines):
                            # Вычисляем номер строки для каждой строки кода
                            line_num = line + i
                            if line_num in self.covered_lines:
                                skipped_count += 1
                                break
                        else:
                            # Если не нашли строки в покрытии, добавляем константу
                            final_constants.append(code)
                        continue
                    
                    final_constants.append(code)
                
                print(f"[SIMPLE_REBUILD]   - Добавлено констант в imports.py: {len(final_constants)}")
                print(f"[SIMPLE_REBUILD]   - Пропущено констант при генерации: {skipped_count}")
                
                for code in final_constants:
                    lines.append(code)
                    lines.append('')
            
            # 6. Глобальные переменные (как None)
            if self.global_init:
                lines.append('# ============================================================================')
                lines.append('# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (инициализация)')
                lines.append('# ============================================================================')
                lines.append('# ВАЖНО: Создание экземпляров классов будет выполнено в init.py')
                lines.append('# после импорта всех классов')
                lines.append('# ============================================================================')
                lines.append('')
                for global_var in self.global_init:
                    var_name = global_var['name']
                    lines.append(f"{var_name} = None  # Будет инициализирован в init.py")
                lines.append('')
            
            # Записываем файл
            imports_path = os.path.join(self.target_dir, 'imports.py')
            with open(imports_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            file_size = os.path.getsize(imports_path)
            print(f"[SIMPLE_REBUILD]   - Создан файл: {imports_path} ({file_size} байт)")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка генерации imports.py: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _distribute_classes(self) -> bool:
        """Распределение классов по модулям"""
        try:
            print("[SIMPLE_REBUILD]   Начало распределения классов...")
            
            # Получаем классы из массива компонентов
            classes = [c for c in self.components if c['type'] == 'class']
            print(f"[SIMPLE_REBUILD]   Найдено классов в массиве компонентов: {len(classes)}")
            
            # Группируем классы по категориям
            categories = {}
            for cls in classes:
                category = cls.get('category', 'core')
                if category not in categories:
                    categories[category] = []
                categories[category].append(cls)
            
            print(f"[SIMPLE_REBUILD]   Категории классов: {list(categories.keys())}")
            
            # Создаем папки категорий
            for category in categories.keys():
                category_dir = os.path.join(self.target_dir, category)
                os.makedirs(category_dir, exist_ok=True)
                print(f"[SIMPLE_REBUILD]   Создана папка категории: {category}")
            
            # Генерируем модули классов
            for i, cls in enumerate(classes, 1):
                category = cls.get('category', 'core')
                print(f"[SIMPLE_REBUILD]   [{i}/{len(classes)}] Создание модуля: {category}/{cls['name']}.py")
                if not self._create_class_module(cls, category):
                    print(f"[ERROR] Ошибка создания модуля класса {cls['name']}")
                    return False
            
            print(f"[SIMPLE_REBUILD]   Все классы успешно распределены по модулям")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка распределения классов: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_class_module(self, class_info: Dict, category: str) -> bool:
        """Создание модуля класса"""
        try:
            class_name = class_info['name']
            class_code = class_info.get('code', '')
            
            # Нормализуем отступы
            class_code = self._normalize_indentation(class_code)
            
            # Удаляем импорты
            class_code = self._remove_imports_from_code(class_code)
            
            # Удаляем константы
            class_code = self._remove_constants_from_code(class_code)
            
            # Удаляем переопределения
            class_code = self._remove_overrides_from_code(class_code)
            
            # Генерируем модуль
            lines = []
            lines.append('#!/usr/bin/env python')
            lines.append('# -*- coding: utf-8 -*-')
            lines.append('"""')
            lines.append(f'Автоматически сгенерированный модуль из {self.source_name}')
            lines.append(f'Класс: {class_name}')
            lines.append('"""')
            lines.append('')
            lines.append('# Импортируем ВСЕ импорты и константы')
            lines.append('from imports import *')
            lines.append('')
            lines.append(class_code)
            
            # Сохраняем файл
            file_name = f"{class_name}.py"
            file_path = os.path.join(self.target_dir, category, file_name)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            file_size = os.path.getsize(file_path)
            print(f"[SIMPLE_REBUILD]      - Создан файл: {file_path} ({file_size} байт)")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка создания модуля класса {class_info['name']}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _distribute_functions(self) -> bool:
        """Распределение функций по модулям"""
        try:
            print("[SIMPLE_REBUILD]   Начало распределения функций...")
            
            # Получаем функции из массива компонентов
            functions = [c for c in self.components if c['type'] == 'function']
            print(f"[SIMPLE_REBUILD]   Найдено функций в массиве компонентов: {len(functions)}")
            
            # Разделяем функции по модулям
            main_func = None
            run_functions = []
            cleanup_functions = []
            other_functions = []
            
            for func in functions:
                module = func.get('module', 'utils')
                if module == 'main':
                    main_func = func
                elif module == 'runner_functions':
                    run_functions.append(func)
                elif module == 'cleanup':
                    cleanup_functions.append(func)
                else:
                    other_functions.append(func)
            
            print(f"[SIMPLE_REBUILD]   Распределение функций по модулям:")
            print(f"[SIMPLE_REBUILD]      - main: {1 if main_func else 0}")
            print(f"[SIMPLE_REBUILD]      - runner_functions: {len(run_functions)}")
            print(f"[SIMPLE_REBUILD]      - cleanup: {len(cleanup_functions)}")
            print(f"[SIMPLE_REBUILD]      - utils: {len(other_functions)}")
            
            # Генерируем модули
            if main_func:
                print(f"[SIMPLE_REBUILD]   Создание модуля: utils/main.py")
                if not self._generate_function_module('main', [main_func], 'utils/main.py'):
                    return False
            
            if run_functions:
                print(f"[SIMPLE_REBUILD]   Создание модуля: utils/runner_functions.py ({len(run_functions)} функций)")
                if not self._generate_functions_module('runner_functions', run_functions, 'utils/runner_functions.py'):
                    return False
            
            if cleanup_functions:
                print(f"[SIMPLE_REBUILD]   Создание модуля: utils/cleanup.py ({len(cleanup_functions)} функций)")
                if not self._generate_functions_module('cleanup', cleanup_functions, 'utils/cleanup.py'):
                    return False
            
            if other_functions:
                print(f"[SIMPLE_REBUILD]   Создание модуля: utils/utils.py ({len(other_functions)} функций)")
                if not self._generate_functions_module('utils', other_functions, 'utils/utils.py'):
                    return False
            
            print(f"[SIMPLE_REBUILD]   Все функции успешно распределены по модулям")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка распределения функций: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_function_module(self, module_name: str, functions: List[Dict], file_path: str) -> bool:
        """Генерация модуля с одной функцией (main.py)"""
        return self._generate_functions_module(module_name, functions, file_path)
    
    def _generate_functions_module(self, module_name: str, functions: List[Dict], file_path: str) -> bool:
        """Генерация модуля с несколькими функциями"""
        try:
            lines = []
            lines.append('#!/usr/bin/env python')
            lines.append('# -*- coding: utf-8 -*-')
            lines.append('"""')
            lines.append(f'Автоматически сгенерированный модуль из {self.source_name}')
            func_names = [f['name'] for f in functions]
            lines.append(f'Функции: {", ".join(func_names)}')
            lines.append('"""')
            lines.append('')
            lines.append('# Импортируем ВСЕ импорты и константы')
            lines.append('from imports import *')
            lines.append('')
            
            # Добавляем код функций
            for func in functions:
                func_code = func.get('code', '')
                
                # Нормализуем отступы
                func_code = self._normalize_indentation(func_code)
                
                # Удаляем импорты
                func_code = self._remove_imports_from_code(func_code)
                
                # Удаляем константы
                func_code = self._remove_constants_from_code(func_code)
                
                # Удаляем переопределения
                func_code = self._remove_overrides_from_code(func_code)
                
                lines.append(func_code)
                lines.append('')
            
            # Сохраняем файл
            full_path = os.path.join(self.target_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            file_size = os.path.getsize(full_path)
            print(f"[SIMPLE_REBUILD]      - Создан файл: {full_path} ({file_size} байт, {len(functions)} функций)")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка генерации модуля функций {module_name}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_init_code(self) -> bool:
        """Генерация init.py"""
        try:
            if not self.global_init:
                # Если нет глобальных переменных для инициализации, создаем пустой файл
                init_path = os.path.join(self.target_dir, 'init.py')
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('#!/usr/bin/env python\n# -*- coding: utf-8 -*-\n"""\nАвтоматически сгенерированный модуль\nИнициализация глобальных переменных\n"""\n\nfrom imports import *\n')
                return True
            
            lines = []
            lines.append('#!/usr/bin/env python')
            lines.append('# -*- coding: utf-8 -*-')
            lines.append('"""')
            lines.append(f'Автоматически сгенерированный модуль из {self.source_name}')
            lines.append('Инициализация глобальных переменных')
            lines.append('Создание экземпляров классов ПОСЛЕ импорта всех классов')
            lines.append('"""')
            lines.append('')
            lines.append('# Импортируем все импорты и константы')
            lines.append('from imports import *')
            lines.append('')
            
            # Определяем классы, нужные для инициализации
            needed_classes = set()
            for global_var in self.global_init:
                class_name = global_var.get('class_name')
                if class_name:
                    needed_classes.add(class_name)
            
            # Импортируем классы в порядке из исходного файла
            if needed_classes:
                lines.append('# ============================================================================')
                lines.append('# ИМПОРТ КЛАССОВ ДЛЯ ИНИЦИАЛИЗАЦИИ')
                lines.append('# ============================================================================')
                
                # Импортируем классы в порядке из исходного файла
                for class_name in self.class_order:
                    if class_name in needed_classes:
                        # Определяем категорию класса
                        category = self._determine_category(class_name)
                        lines.append(f"from {category}.{class_name} import {class_name}")
                
                lines.append('')
            
            # Инициализация глобальных переменных
            lines.append('# ============================================================================')
            lines.append('# ИНИЦИАЛИЗАЦИЯ ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ')
            lines.append('# ============================================================================')
            
            for global_var in self.global_init:
                # Извлекаем код инициализации из исходного файла
                code = global_var.get('code', '')
                # Убираем комментарии и лишние пробелы
                code = code.strip()
                if code:
                    lines.append(code)
            
            # Записываем файл
            init_path = os.path.join(self.target_dir, 'init.py')
            with open(init_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            file_size = os.path.getsize(init_path)
            print(f"[SIMPLE_REBUILD]   - Создан файл: {init_path} ({file_size} байт)")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка генерации init.py: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_launcher_file(self) -> bool:
        """Генерация лаунчера astra_automation.py"""
        try:
            lines = []
            lines.append('#!/usr/bin/env python')
            lines.append('# -*- coding: utf-8 -*-')
            lines.append('"""')
            lines.append('Файл запуска разобранного проекта')
            lines.append('Автоматически сгенерирован FSA-ProjectBuilder')
            lines.append(f'Исходный файл: {self.source_name}')
            lines.append('')
            lines.append('Порядок импорта классов сохранен как в исходном файле')
            lines.append('"""')
            lines.append('')
            lines.append('from __future__ import print_function')
            lines.append('import sys')
            lines.append('import os')
            lines.append('')
            lines.append('# Добавляем путь к модулям в sys.path')
            lines.append('sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))')
            lines.append('')
            lines.append('# КРИТИЧЕСКИ ВАЖНО: Сначала импортируем imports.py')
            lines.append('# Это переопределяет встроенные функции (если есть) и делает доступными')
            lines.append('# все импорты и константы')
            lines.append('from imports import *')
            lines.append('')
            
            # Импортируем все классы в порядке из исходного файла
            lines.append('# Импортируем все классы В ТОЧНОМ ПОРЯДКЕ из исходного файла')
            for class_name in self.class_order:
                category = self._determine_category(class_name)
                lines.append(f"from {category}.{class_name} import {class_name}")
            
            lines.append('')
            lines.append('# Инициализация глобальных переменных (после импорта всех классов)')
            lines.append('from init import *')
            lines.append('')
            lines.append('# Импортируем main из utils.main')
            lines.append('from utils.main import main')
            lines.append('')
            lines.append("if __name__ == '__main__':")
            lines.append('    main()')
            
            # Записываем файл
            launcher_path = os.path.join(self.target_dir, self.source_name)
            with open(launcher_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            file_size = os.path.getsize(launcher_path)
            print(f"[SIMPLE_REBUILD]   - Создан файл: {launcher_path} ({file_size} байт)")
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка генерации лаунчера: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_init_files(self) -> bool:
        """Генерация __init__.py файлов для категорий"""
        try:
            print("[SIMPLE_REBUILD]   Начало генерации __init__.py файлов...")
            
            # Группируем классы по категориям из массива компонентов
            categories = {}
            classes = [c for c in self.components if c['type'] == 'class']
            for cls in classes:
                category = cls.get('category', 'core')
                if category not in categories:
                    categories[category] = []
                categories[category].append(cls['name'])
            
            print(f"[SIMPLE_REBUILD]   Найдено категорий: {list(categories.keys())}")
            
            # Генерируем __init__.py для каждой категории
            # ВАЖНО: Импортируем классы в том же порядке, что и в исходном файле!
            for category, class_names in categories.items():
                print(f"[SIMPLE_REBUILD]   Создание __init__.py для категории: {category} ({len(class_names)} классов)")
                lines = []
                lines.append('"""')
                lines.append(f'Автоматически сгенерированный модуль из {self.source_name}')
                lines.append(f'Категория: {category}')
                lines.append('"""')
                lines.append('')
                
                # Сортируем классы по порядку из исходного файла (self.class_order)
                # Это гарантирует, что базовые классы импортируются перед наследниками
                sorted_class_names = []
                for class_name in self.class_order:
                    if class_name in class_names:
                        sorted_class_names.append(class_name)
                
                # Если какие-то классы не попали в self.class_order, добавляем их в конец
                for class_name in class_names:
                    if class_name not in sorted_class_names:
                        sorted_class_names.append(class_name)
                
                for class_name in sorted_class_names:
                    lines.append(f"from {category}.{class_name} import {class_name}")
                
                init_path = os.path.join(self.target_dir, category, '__init__.py')
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                print(f"[SIMPLE_REBUILD]      - Создан файл: {init_path}")
            
            # Генерируем __init__.py для utils
            functions = [c for c in self.components if c['type'] == 'function']
            if functions:
                lines = []
                lines.append('"""')
                lines.append(f'Автоматически сгенерированный модуль из {self.source_name}')
                lines.append('Категория: utils')
                lines.append('"""')
                lines.append('')
                
                # Импортируем функции из модулей
                main_func = [f for f in functions if f['name'] == 'main']
                if main_func:
                    lines.append('from utils.main import main')
                
                run_functions = [f for f in functions if f['name'].startswith('run_')]
                if run_functions:
                    for func in run_functions:
                        lines.append(f"from utils.runner_functions import {func['name']}")
                
                cleanup_functions = [f for f in functions if f['name'].startswith('cleanup_')]
                if cleanup_functions:
                    for func in cleanup_functions:
                        lines.append(f"from utils.cleanup import {func['name']}")
                
                other_functions = [f for f in functions if not f['name'] == 'main' and 
                                  not f['name'].startswith('run_') and 
                                  not f['name'].startswith('cleanup_')]
                if other_functions:
                    for func in other_functions:
                        lines.append(f"from utils.utils import {func['name']}")
                
                init_path = os.path.join(self.target_dir, 'utils', '__init__.py')
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Ошибка генерации __init__.py файлов: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _normalize_indentation(self, code: str) -> str:
        """Нормализация отступов в коде"""
        lines = code.split('\n')
        if not lines:
            return code
        
        # Находим минимальный отступ (игнорируем пустые строки)
        min_indent = None
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if min_indent is None or indent < min_indent:
                    min_indent = indent
        
        if min_indent is None or min_indent == 0:
            return code
        
        # Убираем минимальный отступ
        normalized = []
        for line in lines:
            if line.strip():
                normalized.append(line[min_indent:])
            else:
                normalized.append('')
        
        return '\n'.join(normalized)
    
    def _remove_imports_from_code(self, code: str) -> str:
        """Удаление импортов из кода (только верхний уровень)"""
        lines = code.split('\n')
        result = []
        in_docstring = False
        docstring_char = None
        
        for line in lines:
            stripped = line.strip()
            
            # Обработка docstrings
            if '"""' in line or "'''" in line:
                if not in_docstring:
                    in_docstring = True
                    if '"""' in line:
                        docstring_char = '"""'
                    else:
                        docstring_char = "'''"
                else:
                    if docstring_char in line:
                        in_docstring = False
                        docstring_char = None
            
            # Пропускаем импорты верхнего уровня (не в docstring)
            if not in_docstring:
                if stripped.startswith('import ') or stripped.startswith('from '):
                    continue
            
            result.append(line)
        
        return '\n'.join(result)
    
    def _remove_constants_from_code(self, code: str) -> str:
        """Удаление констант из кода (только верхний уровень)"""
        # Удаляем константы, которые уже в simple_constants
        lines = code.split('\n')
        result = []
        
        for line in lines:
            stripped = line.strip()
            
            # Пропускаем пустые строки и комментарии
            if not stripped or stripped.startswith('#'):
                result.append(line)
                continue
            
            # Проверяем, является ли это константой
            is_constant = False
            for const in self.simple_constants:
                const_name = const.get('name', '')
                if const_name and stripped.startswith(const_name + ' ='):
                    is_constant = True
                    break
            
            if is_constant:
                continue
            
            result.append(line)
        
        return '\n'.join(result)
    
    def _remove_overrides_from_code(self, code: str) -> str:
        """Удаление переопределений из кода"""
        if not self.overrides:
            return code
        
        lines = code.split('\n')
        result = []
        
        for i, line in enumerate(lines, 1):
            # Проверяем, попадает ли строка в какой-либо блок переопределения
            in_override = False
            for override in self.overrides:
                if override['start_line'] <= i <= override['end_line']:
                    in_override = True
                    break
            
            if not in_override:
                result.append(line)
        
        return '\n'.join(result)
    
    def _save_metadata(self):
        """Сохранение метаданных"""
        try:
            metadata = {
                'source_file': self.source_file,
                'source_name': self.source_name,
                'target_dir': self.target_dir,
                'class_order': self.class_order,
                'global_init': self.global_init,
                'overrides': [o['target'] for o in self.overrides],
                'categories': list(set([self._determine_category(c) for c in self.class_order]))
            }
            
            metadata_path = os.path.join(self.metadata_dir, 'metadata.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"[OK] Сохранены метаданные: {metadata_path}")
            
        except Exception as e:
            print(f"[WARNING] Ошибка сохранения метаданных: {e}")

