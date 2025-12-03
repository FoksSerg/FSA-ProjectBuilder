#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Разборка файла на модули
Разборка Python файла на модульную структуру
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import os
import json
import shutil
import ast
from typing import Dict, List, Optional, Any, Set
from .parser import CodeParser, parse_file
from .dependency_resolver import DependencyResolver
from config import DEFAULT_MODULES_DIR, DEFAULT_METADATA_DIR


class Rebuilder:
    """Разборка Python файла на модули"""
    
    def __init__(self, source_file: str, target_dir: Optional[str] = None):
        """
        Инициализация разборщика
        
        Args:
            source_file: Путь к исходному Python файлу
            target_dir: Директория для модулей (по умолчанию рядом с файлом)
        """
        self.source_file = os.path.abspath(source_file)
        self.source_dir = os.path.dirname(self.source_file)
        self.source_name = os.path.basename(self.source_file)
        
        if target_dir:
            self.target_dir = os.path.abspath(target_dir)
        else:
            # По умолчанию создаем папку modules рядом с исходным файлом
            self.target_dir = os.path.join(self.source_dir, DEFAULT_MODULES_DIR)
        
        self.metadata_dir = os.path.join(self.target_dir, DEFAULT_METADATA_DIR)
        self.structure = None
        self.module_mapping = {}  # {class_name: module_path}
        # Имя исходного модуля (без расширения) для фильтрации внутренних импортов
        self.source_module_name = os.path.splitext(self.source_name)[0]
        # Флаги создания опциональных файлов
        self.config_created = False
        self.imports_created = False
        # Граф зависимостей для проверки циклических импортов
        self.dependency_graph = {}  # {class_name: [dependencies]}
        self.dependency_resolver = None
        # Динамически определяемые категории проекта
        self.project_categories = set()  # Множество категорий, используемых в проекте
        
    def rebuild(self) -> bool:
        """
        Разборка файла на модули
        
        Returns:
            bool: True если разборка успешна, False если ошибка
        """
        print(f"[REBUILD] Начало разборки файла: {self.source_file}")
        
        # 1. Парсим исходный файл
        print("[REBUILD] Парсинг исходного файла...")
        parser = CodeParser(self.source_file)
        if not parser.parse():
            print("[ERROR] Ошибка парсинга исходного файла")
            return False
        
        self.structure = parser.get_structure()
        print(f"[REBUILD] Найдено: {len(self.structure['classes'])} классов, "
              f"{len(self.structure['functions'])} функций, "
              f"{len(self.structure['imports'])} импортов")
        
        # Инициализируем DependencyResolver для анализа зависимостей
        self.dependency_resolver = DependencyResolver(self.structure)
        self.dependency_graph = self.dependency_resolver.resolve()
        print(f"[REBUILD] Проанализированы зависимости между компонентами")
        
        # 2. Создаем структуру папок
        print("[REBUILD] Создание структуры папок...")
        if not self._create_structure():
            print("[ERROR] Ошибка создания структуры папок")
            return False
        
        # 3. Определяем категории и распределяем по модулям
        print("[REBUILD] Распределение компонентов по модулям...")
        if not self._distribute_components():
            print("[ERROR] Ошибка распределения компонентов")
            return False
        
        # 4. Генерируем __init__.py файлы
        print("[REBUILD] Генерация __init__.py файлов...")
        if not self._generate_init_files():
            print("[ERROR] Ошибка генерации __init__.py файлов")
            return False
        
        # 5. Сохраняем метаданные
        print("[REBUILD] Сохранение метаданных...")
        if not self._save_metadata():
            print("[ERROR] Ошибка сохранения метаданных")
            return False
        
        # 5.5. Обрабатываем config.py - добавляем недостающие импорты (только если был создан)
        if self.config_created:
            print("[REBUILD] Обработка config.py...")
            self._process_config_imports()
        else:
            print("[REBUILD] config.py не создан (нет констант), пропускаем обработку")
        
        # 6. Создаем файл запуска
        print("[REBUILD] Создание файла запуска...")
        if not self._generate_launcher_file():
            print("[WARNING] Не удалось создать файл запуска (не критично)")
        
        print(f"[SUCCESS] Разборка завершена успешно!")
        print(f"[INFO] Модули созданы в: {self.target_dir}")
        return True
    
    def _get_project_categories(self) -> Set[str]:
        """
        Динамическое определение категорий проекта на основе структуры
        
        Returns:
            Set[str]: Множество категорий, используемых в проекте
        """
        categories = set()
        
        if not self.structure:
            return categories
        
        # Определяем категории на основе классов
        for cls in self.structure.get('classes', []):
            category = self._determine_category(cls)
            categories.add(category)
        
        # Определяем категории на основе функций (utils)
        if self.structure.get('functions', []):
            categories.add('utils')
        
        # Определяем категории на основе констант (config)
        if self.structure.get('constants', []):
            categories.add('config')
        
        return categories
    
    def _get_category_order(self, categories: List[str]) -> List[str]:
        """
        Определение порядка категорий на основе зависимостей
        
        Args:
            categories: Список категорий проекта
            
        Returns:
            List[str]: Упорядоченный список категорий
        """
        if not categories:
            return []
        
        # Строим граф зависимостей между категориями
        category_deps = {}  # {category: set(dependent_categories)}
        
        for component_name, deps in self.dependency_graph.items():
            # Определяем категорию компонента
            component_category = None
            if component_name in self.module_mapping:
                component_path = self.module_mapping[component_name]
                rel_path = os.path.relpath(component_path, self.target_dir)
                parts = rel_path.split(os.sep)
                if len(parts) >= 2:
                    component_category = parts[0]
            elif self.structure and 'functions' in self.structure:
                for func in self.structure.get('functions', []):
                    if func['name'] == component_name:
                        component_category = 'utils'
                        break
            
            if component_category and component_category in categories:
                if component_category not in category_deps:
                    category_deps[component_category] = set()
                
                # Определяем категории зависимостей
                for dep in deps:
                    dep_category = None
                    if dep in self.module_mapping:
                        dep_path = self.module_mapping[dep]
                        rel_path = os.path.relpath(dep_path, self.target_dir)
                        parts = rel_path.split(os.sep)
                        if len(parts) >= 2:
                            dep_category = parts[0]
                    elif self.structure and 'functions' in self.structure:
                        for func in self.structure.get('functions', []):
                            if func['name'] == dep:
                                dep_category = 'utils'
                                break
                    
                    if dep_category and dep_category in categories and dep_category != component_category:
                        category_deps[component_category].add(dep_category)
        
        # Топологическая сортировка категорий
        visited = set()
        result = []
        
        def visit(category: str):
            if category in visited:
                return
            visited.add(category)
            # Сначала посещаем зависимости
            for dep_cat in category_deps.get(category, []):
                if dep_cat in categories:
                    visit(dep_cat)
            result.append(category)
        
        # Посещаем все категории
        for category in categories:
            if category not in visited:
                visit(category)
        
        return result
    
    def _create_structure(self) -> bool:
        """Создание структуры папок"""
        try:
            # Создаем основную директорию
            os.makedirs(self.target_dir, exist_ok=True)
            
            # Создаем директорию для метаданных
            os.makedirs(self.metadata_dir, exist_ok=True)
            
            # Определяем категории проекта динамически
            self.project_categories = self._get_project_categories()
            
            # Создаем директории только для категорий, используемых в проекте
            for category in self.project_categories:
                category_dir = os.path.join(self.target_dir, category)
                os.makedirs(category_dir, exist_ok=True)
            
            # Также создаем директорию для utils, если есть функции
            if self.structure and self.structure.get('functions', []):
                utils_dir = os.path.join(self.target_dir, 'utils')
                os.makedirs(utils_dir, exist_ok=True)
            
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка создания структуры: {e}")
            return False
    
    def _distribute_components(self) -> bool:
        """Распределение компонентов по модулям"""
        try:
            # Сохраняем порядок классов из исходного файла
            self.class_order = [cls['name'] for cls in self.structure.get('classes', [])]
            
            # Первый проход: создаем все модули и заполняем mapping
            # Распределяем классы
            for cls in self.structure['classes']:
                category = self._determine_category(cls)
                module_path = self._create_module_file(category, cls['name'], cls['code'], replace_imports=False)
                if module_path:
                    self.module_mapping[cls['name']] = module_path
            
            # Распределяем функции верхнего уровня
            utils_functions = []
            main_function = None
            runner_functions = []
            cleanup_functions = []
            
            for func in self.structure['functions']:
                func_name = func.get('name', '').lower()
                if func_name == 'main':
                    main_function = func
                elif func_name.startswith('run_'):
                    runner_functions.append(func)
                elif func_name.startswith('cleanup_'):
                    cleanup_functions.append(func)
                else:
                    utils_functions.append(func)
            
            # Создаем utils/main.py для функции main() (если есть)
            if main_function:
                main_code = self._generate_main_code(main_function)
                main_path = os.path.join(self.target_dir, 'utils', 'main.py')
                os.makedirs(os.path.dirname(main_path), exist_ok=True)
                with open(main_path, 'w', encoding='utf-8') as f:
                    f.write(main_code)
                print(f"[REBUILD] Создан utils/main.py с функцией main()")
            
            # Создаем utils/runner_functions.py для функций run_* (если есть)
            if runner_functions:
                runner_code = self._generate_runner_functions_code(runner_functions)
                runner_path = os.path.join(self.target_dir, 'utils', 'runner_functions.py')
                os.makedirs(os.path.dirname(runner_path), exist_ok=True)
                with open(runner_path, 'w', encoding='utf-8') as f:
                    f.write(runner_code)
                print(f"[REBUILD] Создан utils/runner_functions.py с {len(runner_functions)} функциями")
            
            # Создаем utils/cleanup.py для функций cleanup_* (если есть)
            if cleanup_functions:
                cleanup_code = self._generate_cleanup_code(cleanup_functions)
                cleanup_path = os.path.join(self.target_dir, 'utils', 'cleanup.py')
                os.makedirs(os.path.dirname(cleanup_path), exist_ok=True)
                with open(cleanup_path, 'w', encoding='utf-8') as f:
                    f.write(cleanup_code)
                print(f"[REBUILD] Создан utils/cleanup.py с {len(cleanup_functions)} функциями")
            
            # Создаем utils/utils.py для остальных функций (если есть)
            if utils_functions:
                utils_code = self._generate_utils_code(utils_functions, replace_imports=False)
                utils_path = os.path.join(self.target_dir, 'utils', 'utils.py')
                os.makedirs(os.path.dirname(utils_path), exist_ok=True)
                with open(utils_path, 'w', encoding='utf-8') as f:
                    f.write(utils_code)
                print(f"[REBUILD] Создан utils/utils.py с {len(utils_functions)} функциями")
            
            # config.py больше не создаем - константы теперь в imports.py
            
            # Создаем imports.py для импортов и констант верхнего уровня
            imports = self.structure.get('imports', [])
            constants = self.structure.get('constants', [])
            if imports or constants:
                imports_code = self._generate_imports_code(imports, constants)
                imports_path = os.path.join(self.target_dir, 'imports.py')
                with open(imports_path, 'w', encoding='utf-8') as f:
                    f.write(imports_code)
                self.imports_created = True
                print(f"[REBUILD] Создан imports.py с {len(imports)} импортами и {len(constants)} константами")
            
            # Создаем init.py для инициализации глобальных переменных (после импорта всех классов)
            if hasattr(self, 'global_init') and self.global_init:
                init_code = self._generate_global_init_code()
                init_path = os.path.join(self.target_dir, 'init.py')
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write(init_code)
                print(f"[REBUILD] Создан init.py для инициализации {len(self.global_init)} глобальных переменных")
            
            # Второй проход: заменяем внутренние импорты во всех модулях
            print("[REBUILD] Замена внутренних импортов...")
            self._replace_imports_in_all_modules()
            
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка распределения компонентов: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _determine_category(self, component: Dict[str, Any]) -> str:
        """
        Определение категории компонента
        
        Args:
            component: Компонент (класс или функция)
            
        Returns:
            str: Категория модуля
        """
        name = component.get('name', '').lower()
        
        # Правила определения категории
        if 'handler' in name:
            return 'handlers'
        elif 'manager' in name or 'monitor' in name:
            return 'managers'
        elif 'gui' in name or 'window' in name or 'dialog' in name:
            return 'gui'
        elif 'util' in name or 'helper' in name:
            return 'utils'
        elif 'model' in name:
            return 'models'
        elif 'analyzer' in name or 'checker' in name:
            return 'analyzers'
        elif 'log' in name or 'logger' in name:
            return 'loggers'  # Изменено с 'logging' на 'loggers' для избежания конфликта со стандартной библиотекой
        else:
            # По умолчанию в core
            return 'core'
    
    def _create_module_file(self, category: str, class_name: str, code: str, replace_imports: bool = True) -> Optional[str]:
        """
        Создание файла модуля для класса
        
        Args:
            category: Категория модуля
            class_name: Имя класса
            code: Код класса
            replace_imports: Заменять ли внутренние импорты (по умолчанию True)
            
        Returns:
            str: Путь к созданному файлу или None
        """
        try:
            # Создаем имя файла точно как имя класса (CamelCase)
            module_path = os.path.join(self.target_dir, category, f"{class_name}.py")
            
            # Нормализуем отступы кода (убираем минимальный отступ)
            normalized_code = self._normalize_indentation(code)
            
            # Применяем отложенные декораторы для модулей с циклическими зависимостями ДО обработки импортов
            # чтобы декораторы были еще в коде
            # Проверяем циклические зависимости через граф зависимостей
            has_cycle = False
            if class_name in self.dependency_graph:
                for dep in self.dependency_graph[class_name]:
                    # Проверяем, есть ли обратная зависимость (циклическая зависимость)
                    if dep in self.dependency_graph and class_name in self.dependency_graph[dep]:
                        has_cycle = True
                        break
                    # Проверяем косвенные циклы через utils
                    if self.structure and 'functions' in self.structure:
                        # Если класс зависит от функции из utils, а utils зависит от класса - цикл
                        for func in self.structure.get('functions', []):
                            if func['name'] == dep:
                                # Функция из utils - проверяем, зависит ли она от этого класса
                                if func['name'] in self.dependency_graph and class_name in self.dependency_graph[func['name']]:
                                    has_cycle = True
                                    break
            
            if has_cycle:
                normalized_code = self._apply_lazy_decorators(normalized_code, class_name)
            
            # Удаляем импорты из кода класса
            code_without_imports = self._remove_imports_from_code(normalized_code)
            
            # Константы не нужно удалять из кода класса - они находятся только на верхнем уровне файла
            # и не попадают в код класса при извлечении парсером
            code_without_constants = code_without_imports
            
            # Заменяем внутренние импорты на правильные относительные импорты (если нужно)
            if replace_imports:
                processed_code = self._replace_internal_imports(code_without_constants, category, class_name)
            else:
                processed_code = code_without_constants
            
            # Добавляем заголовок файла с импортом из imports.py
            header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически сгенерированный модуль из {self.source_name}
Класс: {class_name}
"""

# Импортируем ВСЕ импорты и константы
from imports import *

'''
            
            # Записываем файл
            with open(module_path, 'w', encoding='utf-8') as f:
                f.write(header)
                f.write(processed_code)
            
            print(f"[REBUILD] Создан модуль: {module_path}")
            return module_path
            
        except Exception as e:
            print(f"[ERROR] Ошибка создания модуля {class_name}: {e}")
            return None
    
    def _class_name_to_module_name(self, class_name: str) -> str:
        """Преобразование имени класса в имя модуля (больше не используется, оставлено для совместимости)"""
        # CamelCase -> snake_case
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _remove_imports_from_code(self, code: str) -> str:
        """
        Удаление всех импортов верхнего уровня из кода
        НЕ удаляет локальные импорты внутри функций/методов
        
        Args:
            code: Исходный код
            
        Returns:
            str: Код без импортов верхнего уровня
        """
        if not code:
            return code
        
        lines = code.split('\n')
        result_lines = []
        in_docstring = False
        docstring_char = None
        indent_level = 0  # Уровень отступа (0 = верхний уровень)
        
        for line in lines:
            stripped = line.strip()
            
            # Пропускаем пустые строки
            if not stripped:
                result_lines.append(line)
                continue
            
            # Определяем уровень отступа
            current_indent = len(line) - len(line.lstrip())
            is_top_level = (current_indent == 0)
            
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
            
            # Пропускаем импорты ТОЛЬКО верхнего уровня (не в docstring и не внутри функций/методов)
            if not in_docstring and is_top_level:
                if stripped.startswith('import ') or stripped.startswith('from '):
                    continue
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _remove_constants_from_code(self, code: str, constants: List[Dict[str, Any]], use_line_numbers: bool = False) -> str:
        """
        Удаление констант из кода
        
        Args:
            code: Исходный код
            constants: Список констант для удаления (с информацией о строках)
            use_line_numbers: Если True, использует информацию о строках из парсера (только для исходного файла)
                             Если False, использует только имена констант (для нормализованного кода функций)
            
        Returns:
            str: Код без констант
        """
        if not code or not constants:
            return code
        
        lines = code.split('\n')
        # Создаем множество строк для удаления на основе информации о константах
        lines_to_remove = set()
        
        # Используем информацию о строках только если это исходный файл (не нормализованный код функции)
        if use_line_numbers:
            for const in constants:
                # Используем информацию о строках из парсера (если есть)
                if 'line' in const:
                    start_line = const['line'] - 1  # Парсер использует 1-based, мы используем 0-based
                    # Пытаемся найти конец присваивания
                    # Для многострочных присваиваний нужно найти строку с закрывающей скобкой
                    end_line = start_line
                    open_brackets = 0
                    found_equals = False
                    
                    for i in range(start_line, min(start_line + 100, len(lines))):  # Ограничиваем поиск 100 строками
                        line = lines[i]
                        stripped = line.strip()
                        
                        if '=' in stripped and not found_equals:
                            found_equals = True
                            # Считаем открывающие скобки после =
                            equals_pos = stripped.find('=')
                            after_equals = stripped[equals_pos + 1:]
                            open_brackets += after_equals.count('(') + after_equals.count('[') + after_equals.count('{')
                            open_brackets -= after_equals.count(')') + after_equals.count(']') + after_equals.count('}')
                        else:
                            if found_equals:
                                open_brackets += stripped.count('(') + stripped.count('[') + stripped.count('{')
                                open_brackets -= stripped.count(')') + stripped.count(']') + stripped.count('}')
                        
                        end_line = i
                        
                        # Если все скобки закрыты и есть точка с запятой или пустая строка после
                        if found_equals and open_brackets == 0:
                            # Проверяем, что строка заканчивается правильно
                            if not stripped or stripped.endswith(',') or stripped.endswith(')') or stripped.endswith(']') or stripped.endswith('}'):
                                break
                    
                    # Добавляем все строки константы в множество для удаления
                    for i in range(start_line, end_line + 1):
                        if 0 <= i < len(lines):
                            lines_to_remove.add(i)
        
        # Используем простой метод по именам констант (для нормализованного кода функций)
        if not lines_to_remove:
            constant_names = {const['name'] for const in constants}
            in_docstring = False
            docstring_char = None
            
            for i, line in enumerate(lines):
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
                
                # Пропускаем присваивания констант (только если не в docstring и на верхнем уровне)
                if not in_docstring:
                    # Проверяем, что это присваивание верхнего уровня (не внутри функции/класса)
                    current_indent = len(line) - len(line.lstrip())
                    is_top_level = (current_indent == 0)
                    
                    if is_top_level and '=' in stripped:
                        var_name = stripped.split('=')[0].strip()
                        if ':' in var_name:
                            var_name = var_name.split(':')[0].strip()
                        if var_name in constant_names:
                            lines_to_remove.add(i)
        
        # Собираем результат, пропуская строки для удаления
        result_lines = []
        for i, line in enumerate(lines):
            if i not in lines_to_remove:
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _normalize_indentation(self, code: str) -> str:
        """
        Нормализация отступов кода (убирает минимальный отступ первой строки)
        
        Args:
            code: Исходный код с отступами
            
        Returns:
            str: Код с нормализованными отступами (начинается с нулевого отступа)
        """
        if not code:
            return code
        
        lines = code.split('\n')
        if not lines:
            return code
        
        # Находим первую непустую строку и её отступ
        first_line_indent = 0
        for line in lines:
            if line.strip():
                first_line_indent = len(line) - len(line.lstrip())
                break
        
        # Если первая строка уже без отступа, возвращаем код как есть
        if first_line_indent == 0:
            return code
        
        # Убираем отступ первой строки из всех строк
        normalized_lines = []
        for line in lines:
            if line.strip():  # Непустая строка
                if len(line) > first_line_indent:
                    normalized_lines.append(line[first_line_indent:])
                else:
                    normalized_lines.append(line.lstrip())
            else:  # Пустая строка
                normalized_lines.append('')
        
        return '\n'.join(normalized_lines)
    
    def _generate_main_code(self, main_function: Dict[str, Any]) -> str:
        """Генерация кода для utils/main.py"""
        header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически сгенерированный модуль из {self.source_name}
Функция main()
"""

# Импортируем ВСЕ импорты и константы
from imports import *

'''
        code = header
        
        func_code = main_function.get('code', '')
        # Нормализуем отступы кода функции (убираем минимальный отступ)
        normalized_code = self._normalize_indentation(func_code)
        # Удаляем импорты из кода функции
        code_without_imports = self._remove_imports_from_code(normalized_code)
        # Удаляем константы из кода функции (НЕ используем номера строк, т.к. код уже нормализован)
        constants = self.structure.get('constants', [])
        code_without_constants = self._remove_constants_from_code(code_without_imports, constants, use_line_numbers=False)
        # Заменяем внутренние импорты (это добавит нужные импорты классов)
        processed_code = self._replace_internal_imports(code_without_constants, 'utils', 'main')
        # Удаляем импорты еще раз, так как _replace_internal_imports может добавить их
        # Но теперь они уже правильные (относительные), поэтому оставляем их
        code += processed_code + '\n'
        
        return code
    
    def _generate_runner_functions_code(self, functions: List[Dict[str, Any]]) -> str:
        """Генерация кода для utils/runner_functions.py"""
        header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически сгенерированный модуль из {self.source_name}
Функции run_*
"""

# Импортируем ВСЕ импорты и константы
from imports import *

'''
        code = header
        
        constants = self.structure.get('constants', [])
        
        for func in functions:
            func_code = func.get('code', '')
            # Нормализуем отступы кода функции (убираем минимальный отступ)
            normalized_code = self._normalize_indentation(func_code)
            # Удаляем импорты из кода функции
            code_without_imports = self._remove_imports_from_code(normalized_code)
            # Удаляем константы из кода функции (НЕ используем номера строк, т.к. код уже нормализован)
            code_without_constants = self._remove_constants_from_code(code_without_imports, constants, use_line_numbers=False)
            # Заменяем внутренние импорты
            processed_code = self._replace_internal_imports(code_without_constants, 'utils', func.get('name', ''))
            code += processed_code + '\n\n'
        
        return code
    
    def _generate_cleanup_code(self, functions: List[Dict[str, Any]]) -> str:
        """Генерация кода для utils/cleanup.py"""
        header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически сгенерированный модуль из {self.source_name}
Функции cleanup_*
"""

# Импортируем ВСЕ импорты и константы
from imports import *

'''
        code = header
        
        constants = self.structure.get('constants', [])
        
        for func in functions:
            func_code = func.get('code', '')
            # Нормализуем отступы кода функции (убираем минимальный отступ)
            normalized_code = self._normalize_indentation(func_code)
            # Удаляем импорты из кода функции
            code_without_imports = self._remove_imports_from_code(normalized_code)
            # Удаляем константы из кода функции (НЕ используем номера строк, т.к. код уже нормализован)
            code_without_constants = self._remove_constants_from_code(code_without_imports, constants, use_line_numbers=False)
            # Заменяем внутренние импорты
            processed_code = self._replace_internal_imports(code_without_constants, 'utils', func.get('name', ''))
            code += processed_code + '\n\n'
        
        return code
    
    def _generate_utils_code(self, functions: List[Dict[str, Any]], replace_imports: bool = True) -> str:
        """Генерация кода для utils/utils.py"""
        header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически сгенерированный модуль из {self.source_name}
Функции верхнего уровня
"""

# Импортируем ВСЕ импорты и константы
from imports import *

'''
        code = header
        
        constants = self.structure.get('constants', [])
        
        for func in functions:
            func_code = func.get('code', '')
            # Нормализуем отступы кода функции (убираем минимальный отступ)
            normalized_code = self._normalize_indentation(func_code)
            # Удаляем импорты из кода функции
            code_without_imports = self._remove_imports_from_code(normalized_code)
            # Удаляем константы из кода функции (НЕ используем номера строк, т.к. код уже нормализован)
            code_without_constants = self._remove_constants_from_code(code_without_imports, constants, use_line_numbers=False)
            # Заменяем внутренние импорты (если нужно)
            if replace_imports:
                processed_code = self._replace_internal_imports(code_without_constants, 'utils', func.get('name', ''))
            else:
                processed_code = code_without_constants
            code += processed_code + '\n\n'
        
        return code
    
    def _generate_config_code(self, constants: List[Dict[str, Any]]) -> str:
        """Генерация кода для config.py"""
        header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически сгенерированный модуль из {self.source_name}
Константы и конфигурация
"""

'''
        code = header
        
        for const in constants:
            # Используем исходный код присваивания если есть, иначе значение
            if 'code' in const and const['code']:
                code += const['code'] + '\n'
            else:
                code += f"{const['name']} = {const['value']}\n"
        
        return code
    
    def _generate_imports_code(self, imports: List[Dict[str, Any]], constants: List[Dict[str, Any]]) -> str:
        """Генерация кода для imports.py (импорты и константы)"""
        header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически сгенерированный модуль из {self.source_name}
Все импорты и константы из исходного файла
Используется всеми классами и функциями
"""

'''
        code = header
        
        # Разделяем константы на простые и инициализацию глобальных переменных
        simple_constants = []  # Простые константы (APP_VERSION, COMPONENTS_CONFIG)
        global_init = []  # Инициализация глобальных переменных (создание экземпляров)
        
        # Получаем имена всех классов для проверки
        class_names = {cls['name'] for cls in self.structure.get('classes', [])}
        
        for const in constants:
            const_code = const.get('code', '')
            const_name = const.get('name', '')
            
            # Проверяем, создает ли константа экземпляр класса
            is_class_instance = False
            for class_name in class_names:
                if f"{class_name}()" in const_code:
                    is_class_instance = True
                    break
            
            if is_class_instance:
                # Это инициализация глобальной переменной с созданием экземпляра класса
                # Заменяем на инициализацию как None (создание будет в init.py)
                # Извлекаем имя переменной
                if '=' in const_code:
                    var_name = const_code.split('=')[0].strip()
                    # Убираем возможные аннотации типов
                    if ':' in var_name:
                        var_name = var_name.split(':')[0].strip()
                    global_init.append({
                        'name': var_name,
                        'original_code': const_code,
                        'init_code': f"{var_name} = None  # Будет инициализирован в init.py"
                    })
            else:
                # Простая константа
                simple_constants.append(const)
        
        # Сохраняем информацию о глобальной инициализации для использования в init.py
        if not hasattr(self, 'global_init'):
            self.global_init = []
        self.global_init.extend(global_init)
        
        # ============================================================================
        # ИМПОРТЫ
        # ============================================================================
        if imports:
            # Сначала извлекаем импорты из __future__ (они должны быть первыми)
            future_imports = []
            import_statements = []
            from_imports = {}
            
            for imp in imports:
                # Пропускаем импорты из исходного файла (внутренние импорты)
                if imp['type'] == 'from_import' and imp.get('module') == self.source_module_name:
                    continue  # Исключаем внутренние импорты
                
                # Импорты из __future__ должны быть первыми
                if imp['type'] == 'from_import' and imp.get('module') == '__future__':
                    name = imp['name']
                    alias = f" as {imp['alias']}" if imp.get('alias') else ""
                    future_imports.append(f"{name}{alias}")
                elif imp['type'] == 'import':
                    # Пропускаем импорты исходного файла
                    if imp['module'] == self.source_module_name:
                        continue
                    alias = f" as {imp['alias']}" if imp.get('alias') else ""
                    import_statements.append(f"import {imp['module']}{alias}")
                elif imp['type'] == 'from_import':
                    module = imp['module']
                    if module not in from_imports:
                        from_imports[module] = []
                    name = imp['name']
                    alias = f" as {imp['alias']}" if imp.get('alias') else ""
                    from_imports[module].append(f"{name}{alias}")
        
        # Добавляем импорты из __future__ первыми
        if future_imports:
            names = ', '.join(sorted(set(future_imports)))
            code += f"from __future__ import {names}\n\n"
        
        # Добавляем import
        for stmt in sorted(set(import_statements)):
            code += stmt + '\n'
        
        # Добавляем from ... import (кроме __future__, он уже добавлен)
        for module in sorted(from_imports.keys()):
            if module != '__future__':
                names = ', '.join(from_imports[module])
                code += f"from {module} import {names}\n"
            
            code += '\n'
        
        # ============================================================================
        # КОНСТАНТЫ
        # ============================================================================
        if simple_constants:
            code += '# ============================================================================\n'
            code += '# КОНСТАНТЫ\n'
            code += '# ============================================================================\n\n'
            
            for const in simple_constants:
                # Используем исходный код присваивания
                if 'code' in const and const['code']:
                    code += const['code'] + '\n'
                else:
                    # Fallback: если нет кода, создаем простое присваивание
                    code += f"{const['name']} = {const.get('value', 'None')}\n"
            
            code += '\n'
        
        # ============================================================================
        # ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (инициализация как None)
        # ============================================================================
        if global_init:
            code += '# ============================================================================\n'
            code += '# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (инициализация)\n'
            code += '# ============================================================================\n'
            code += '# ВАЖНО: Создание экземпляров классов будет выполнено в init.py\n'
            code += '# после импорта всех классов\n'
            code += '# ============================================================================\n\n'
            
            for init_var in global_init:
                code += init_var['init_code'] + '\n'
            
            code += '\n'
        
        return code
    
    def _generate_global_init_code(self) -> str:
        """
        Генерация кода для init.py (инициализация глобальных переменных)
        Этот файл создает экземпляры классов ПОСЛЕ импорта всех классов
        """
        header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически сгенерированный модуль из {self.source_name}
Инициализация глобальных переменных
Создание экземпляров классов ПОСЛЕ импорта всех классов
"""

# Импортируем все импорты и константы
from imports import *

'''
        code = header
        
        # Добавляем создание экземпляров классов
        if hasattr(self, 'global_init') and self.global_init:
            # Сначала импортируем нужные классы
            code += '# ============================================================================\n'
            code += '# ИМПОРТ КЛАССОВ ДЛЯ ИНИЦИАЛИЗАЦИИ\n'
            code += '# ============================================================================\n'
            code += '# ВАЖНО: Классы должны быть импортированы ДО создания экземпляров\n'
            code += '# ============================================================================\n\n'
            
            # Определяем, какие классы нужны для инициализации
            needed_classes = set()
            for init_var in self.global_init:
                original_code = init_var['original_code']
                # Ищем вызовы классов в коде (например, ActivityTracker())
                import re
                class_calls = re.findall(r'(\w+)\(\)', original_code)
                for class_name in class_calls:
                    # Проверяем, что это действительно класс (есть в структуре)
                    if class_name in self.module_mapping:
                        needed_classes.add(class_name)
            
            # Импортируем нужные классы
            for class_name in sorted(needed_classes):
                # Определяем категорию класса
                if class_name in self.module_mapping:
                    module_path = self.module_mapping[class_name]
                    rel_path = os.path.relpath(module_path, self.target_dir)
                    parts = rel_path.split(os.sep)
                    if len(parts) >= 2:
                        category = parts[0]
                        code += f"from {category}.{class_name} import {class_name}\n"
            
            code += '\n'
            
            # Теперь создаем экземпляры
            code += '# ============================================================================\n'
            code += '# ИНИЦИАЛИЗАЦИЯ ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ\n'
            code += '# ============================================================================\n'
            code += '# ВАЖНО: Этот код выполняется ПОСЛЕ импорта всех классов\n'
            code += '# ============================================================================\n\n'
            
            for init_var in self.global_init:
                # Используем оригинальный код создания экземпляра
                code += init_var['original_code'] + '\n'
            
            code += '\n'
        
        return code
    
    def _generate_init_files(self) -> bool:
        """Генерация __init__.py файлов"""
        try:
            # Генерируем __init__.py для каждой категории проекта
            for category in self.project_categories:
                category_dir = os.path.join(self.target_dir, category)
                if os.path.exists(category_dir):
                    # Находим все модули в категории
                    modules = []
                    for file in os.listdir(category_dir):
                        if file.endswith('.py') and file != '__init__.py':
                            module_name = file[:-3]  # Убираем .py
                            modules.append(module_name)
                    
                    if modules:
                        # Генерируем __init__.py
                        init_code = self._generate_init_code(category, modules)
                        init_path = os.path.join(category_dir, '__init__.py')
                        with open(init_path, 'w', encoding='utf-8') as f:
                            f.write(init_code)
            
            # Генерируем главный __init__.py
            main_init_code = self._generate_main_init_code()
            main_init_path = os.path.join(self.target_dir, '__init__.py')
            with open(main_init_path, 'w', encoding='utf-8') as f:
                f.write(main_init_code)
            
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка генерации __init__.py: {e}")
            return False
    
    def _generate_init_code(self, category: str, modules: List[str]) -> str:
        """Генерация кода для __init__.py категории"""
        code = f'''"""
{category.capitalize()} модули
"""

'''
        # Определяем порядок импорта на основе зависимостей
        # Используем DependencyResolver для определения порядка
        if self.structure and 'classes' in self.structure:
            # Создаем словарь зависимостей для модулей этой категории
            module_dependencies = {}
            for module in modules:
                # Ищем класс с таким именем (snake_case -> CamelCase)
                class_name = self._module_name_to_class_name(module)
                # Ищем класс в структуре
                for cls in self.structure.get('classes', []):
                    if cls['name'] == class_name:
                        # Получаем зависимости класса
                        deps = set()
                        # Зависимости от базовых классов
                        for base in cls.get('bases', []):
                            # Проверяем, есть ли этот класс в модулях этой категории
                            base_module = self._class_name_to_module_name(base)
                            if base_module in modules:
                                deps.add(base_module)
                        # Зависимости из анализа использований
                        usages = self.structure.get('usages', {})
                        if class_name in usages:
                            for used in usages[class_name]:
                                used_module = self._class_name_to_module_name(used)
                                if used_module in modules:
                                    deps.add(used_module)
                        module_dependencies[module] = deps
                        break
            
            # Топологическая сортировка модулей
            sorted_modules = self._topological_sort_modules(modules, module_dependencies)
        else:
            # Если нет структуры, просто сортируем по алфавиту
            sorted_modules = sorted(modules)
        
        # Определяем модули с циклическими зависимостями
        # Проверяем циклические зависимости как внутри категории, так и между категориями
        # Также проверяем косвенные циклические зависимости через цепочку модулей
        modules_with_cycles = set()
        
        # Собираем все модули, которые импортируют utils (они могут создавать циклические зависимости)
        utils_dependent_modules = set()
        # Определяем функции из utils
        utils_functions = set()
        if self.structure and 'functions' in self.structure:
            for func in self.structure.get('functions', []):
                utils_functions.add(func['name'])
        
        for module in sorted_modules:
            class_name = self._module_name_to_class_name(module)
            # Проверяем, импортирует ли модуль функции из utils
            if class_name in self.dependency_graph:
                for dep in self.dependency_graph[class_name]:
                    # Проверяем, является ли зависимость функцией из utils
                    if dep in utils_functions:
                        utils_dependent_modules.add(module)
        
        # Проверяем, импортирует ли utils модули из этой категории
        utils_imports_category = False
        if self.structure and 'functions' in self.structure:
            for func in self.structure.get('functions', []):
                func_name = func.get('name', '')
                if func_name in utils_functions:
                    # Проверяем зависимости функции через граф зависимостей
                    if func_name in self.dependency_graph:
                        for dep in self.dependency_graph[func_name]:
                            # Проверяем, является ли зависимость классом из этой категории
                            if dep in self.module_mapping:
                                dep_path = self.module_mapping[dep]
                                rel_path = os.path.relpath(dep_path, self.target_dir)
                                parts = rel_path.split(os.sep)
                                if len(parts) >= 2:
                                    dep_category = parts[0]
                                    if dep_category == category:
                                        utils_imports_category = True
                                        break
        
        # Если utils импортирует модули из этой категории, а модули импортируют utils - циклическая зависимость
        if utils_imports_category:
            modules_with_cycles.update(utils_dependent_modules)
        
        # Проверяем прямые циклические зависимости
        for module in sorted_modules:
            class_name = self._module_name_to_class_name(module)
            # Проверяем, есть ли циклические зависимости у этого класса
            if class_name in self.dependency_graph:
                for dep in self.dependency_graph[class_name]:
                    # Проверяем, есть ли обратная зависимость (циклическая зависимость)
                    if dep in self.dependency_graph and class_name in self.dependency_graph[dep]:
                        # Есть циклическая зависимость - помечаем оба модуля
                        dep_module = self._class_name_to_module_name(dep)
                        modules_with_cycles.add(module)
                        modules_with_cycles.add(dep_module)
        
        # Генерируем импорты в правильном порядке
        # Для модулей с циклическими зависимостями НЕ импортируем в __init__.py
        # Они будут импортированы напрямую из модулей там, где нужны
        for module in sorted_modules:
            if module in modules_with_cycles:
                # Не импортируем модули с циклическими зависимостями в __init__.py
                # Они будут импортированы напрямую из модулей там, где нужны
                code += f"# Модуль {module} имеет циклические зависимости - не импортируем в __init__.py\n"
                code += f"# Импортируйте классы напрямую: from {category}.{module} import ClassName\n\n"
            else:
                code += f"from .{module} import *\n"
        
        return code
    
    def _module_name_to_class_name(self, module_name: str) -> str:
        """Преобразование имени модуля в имя класса (snake_case -> CamelCase)"""
        import re
        parts = module_name.split('_')
        return ''.join(word.capitalize() for word in parts)
    
    def _topological_sort_modules(self, modules: List[str], dependencies: Dict[str, Set[str]]) -> List[str]:
        """Топологическая сортировка модулей на основе зависимостей"""
        # Инициализируем зависимости для всех модулей
        deps = {m: dependencies.get(m, set()) for m in modules}
        
        # Топологическая сортировка
        visited = set()
        result = []
        
        def visit(module: str):
            if module in visited:
                return
            visited.add(module)
            # Сначала посещаем зависимости
            for dep in deps.get(module, set()):
                if dep in modules:
                    visit(dep)
            result.append(module)
        
        for module in modules:
            if module not in visited:
                visit(module)
        
        return result
    
    def _generate_main_init_code(self) -> str:
        """Генерация главного __init__.py"""
        code = f'''"""
Автоматически сгенерированные модули из {self.source_name}
"""

'''
        # Определяем категории с циклическими зависимостями
        # Проверяем циклические зависимости между категориями через граф зависимостей
        categories_with_cycles = set()
        category_dependencies = {}  # {category: set(dependent_categories)}
        
        # Собираем зависимости между категориями
        # Проверяем как классы, так и функции
        for component_name, deps in self.dependency_graph.items():
            # Определяем категорию компонента (класс или функция)
            component_category = None
            if component_name in self.module_mapping:
                component_path = self.module_mapping[component_name]
                rel_path = os.path.relpath(component_path, self.target_dir)
                parts = rel_path.split(os.sep)
                if len(parts) >= 2:
                    component_category = parts[0]
            else:
                # Проверяем, является ли компонент функцией из utils
                if self.structure and 'functions' in self.structure:
                    for func in self.structure.get('functions', []):
                        if func['name'] == component_name:
                            component_category = 'utils'
                            break
            
            if component_category:
                if component_category not in category_dependencies:
                    category_dependencies[component_category] = set()
                
                for dep in deps:
                    # Определяем категорию зависимости
                    dep_category = None
                    if dep in self.module_mapping:
                        dep_path = self.module_mapping[dep]
                        rel_path = os.path.relpath(dep_path, self.target_dir)
                        parts = rel_path.split(os.sep)
                        if len(parts) >= 2:
                            dep_category = parts[0]
                    else:
                        # Проверяем, является ли зависимость функцией из utils
                        if self.structure and 'functions' in self.structure:
                            for func in self.structure.get('functions', []):
                                if func['name'] == dep:
                                    dep_category = 'utils'
                                    break
                    
                    if dep_category and dep_category != component_category:
                        category_dependencies[component_category].add(dep_category)
        
        # Проверяем циклические зависимости между категориями
        for category, deps in category_dependencies.items():
            for dep_category in deps:
                # Проверяем, есть ли обратная зависимость
                if dep_category in category_dependencies and category in category_dependencies[dep_category]:
                    # Есть циклическая зависимость между категориями
                    categories_with_cycles.add(category)
                    categories_with_cycles.add(dep_category)
        
        # Также проверяем косвенные циклические зависимости
        # Если категория A зависит от категории B, а категория B зависит от категории C, и категория C зависит от категории A
        # То все три категории имеют циклические зависимости
        for category in category_dependencies.keys():
            visited = set()
            def has_cycle_to(start_cat, target_cat, path):
                if start_cat == target_cat and len(path) > 1:
                    # Найден цикл
                    for cat in path:
                        categories_with_cycles.add(cat)
                    return True
                if start_cat in visited:
                    return False
                visited.add(start_cat)
                for dep_cat in category_dependencies.get(start_cat, []):
                    if has_cycle_to(dep_cat, target_cat, path + [start_cat]):
                        return True
                visited.remove(start_cat)
                return False
            
            # Проверяем циклы для каждой категории
            for target_cat in category_dependencies.keys():
                if target_cat != category:
                    has_cycle_to(category, target_cat, [])
        
        # Импортируем из всех категорий проекта
        # Для категорий с циклическими зависимостями НЕ импортируем в __init__.py
        # Они будут импортированы напрямую из модулей там, где нужны
        for category in self.project_categories:
            category_dir = os.path.join(self.target_dir, category)
            if os.path.exists(category_dir):
                if category in categories_with_cycles:
                    # Не импортируем категории с циклическими зависимостями в __init__.py
                    # Они будут импортированы напрямую из модулей там, где нужны
                    code += f"# Категория {category} имеет циклические зависимости - не импортируем в __init__.py\n"
                    code += f"# Импортируйте классы напрямую: from {category}.module_name import ClassName\n\n"
                else:
                    code += f"from .{category} import *\n"
        
        return code
    
    def _save_metadata(self) -> bool:
        """Сохранение метаданных"""
        try:
            metadata = {
                'source_file': self.source_file,
                'source_name': self.source_name,
                'target_dir': self.target_dir,
                'structure': self.structure,
                'module_mapping': self.module_mapping,
                'total_classes': len(self.structure.get('classes', [])),
                'total_functions': len(self.structure.get('functions', [])),
                'total_imports': len(self.structure.get('imports', []))
            }
            
            metadata_path = os.path.join(self.metadata_dir, 'metadata.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка сохранения метаданных: {e}")
            return False
    
    def _generate_launcher_file(self) -> bool:
        """Генерация файла запуска разобранного проекта"""
        try:
            # Имя файла запуска такое же, как у исходного файла
            launcher_name = self.source_name
            
            # Создаем файл в директории модулей (независимо от исходного проекта)
            launcher_path = os.path.join(self.target_dir, launcher_name)
            
            # Генерируем код файла запуска
            launcher_code = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Файл запуска разобранного проекта
Автоматически сгенерирован FSA-ProjectBuilder
Исходный файл: {self.source_name}

Порядок импорта классов сохранен как в исходном файле
"""

from __future__ import print_function
import sys
import os

# Добавляем путь к модулям в sys.path (текущая директория)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# КРИТИЧЕСКИ ВАЖНО: Сначала импортируем imports.py
# Это переопределяет print (если есть) и делает доступными все импорты и константы
    from imports import *

'''
            
            # Импортируем все классы В ТОЧНОМ ПОРЯДКЕ, как в исходном файле
            class_order = getattr(self, 'class_order', [])
            if not class_order:
                # Fallback: используем порядок из структуры
                class_order = [cls['name'] for cls in self.structure.get('classes', [])]
            
            for class_name in class_order:
                # Находим категорию класса
                category = None
                for cls in self.structure.get('classes', []):
                    if cls['name'] == class_name:
                        category = self._determine_category(cls)
                        break
                
                if category:
                    # Импортируем класс: from category.ClassName import ClassName
                    launcher_code += f"from {category}.{class_name} import {class_name}\n"
            
            launcher_code += '\n'
            
            # Импортируем init.py для инициализации глобальных переменных (после импорта всех классов)
            if hasattr(self, 'global_init') and self.global_init:
                launcher_code += '''# Инициализация глобальных переменных (создание экземпляров классов)
# ВАЖНО: Это выполняется ПОСЛЕ импорта всех классов
from init import *

'''
            
            # Импортируем main из utils.main
            launcher_code += '''# Импортируем main из utils.main
        try:
    from utils.main import main
except ImportError:
    print("[ERROR] Не удалось импортировать main из utils.main")
        sys.exit(1)

if __name__ == '__main__':
    main()
'''
            
            # Записываем файл запуска
            with open(launcher_path, 'w', encoding='utf-8') as f:
                f.write(launcher_code)
            
            print(f"[REBUILD] Создан файл запуска: {launcher_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка генерации файла запуска: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _replace_internal_imports(self, code: str, current_category: str, component_name: str) -> str:
        """
        Замена внутренних импортов (из исходного файла) на правильные относительные импорты
        
        Args:
            code: Исходный код
            current_category: Текущая категория модуля
            component_name: Имя компонента (класс или функция)
            
        Returns:
            str: Код с замененными импортами
        """
        import re
        
        # Получаем имя исходного модуля
        source_module = self.source_module_name
        
        # Создаем обратное отображение: имя класса -> (категория, имя_модуля)
        class_to_module = {}
        for cls_name, module_path in self.module_mapping.items():
            # Извлекаем категорию и имя модуля из пути
            rel_path = os.path.relpath(module_path, self.target_dir)
            parts = rel_path.split(os.sep)
            if len(parts) >= 2:
                category = parts[0]
                module_file = parts[1]
                module_name = os.path.splitext(module_file)[0]
                class_to_module[cls_name] = (category, module_name)
        
        # Заменяем импорты из исходного файла
        # Также обрабатываем уже замененные импорты для проверки циклических зависимостей
        lines = code.split('\n')
        result_lines = []
        
        for line in lines:
            # Проверяем уже замененные импорты (from category.module import ClassName)
            # Это нужно для обработки циклических зависимостей
            pattern_existing = re.compile(r'from\s+(\w+)\.(\w+)\s+import\s+(\w+)')
            match_existing = pattern_existing.search(line)
            
            if match_existing and not line.strip().startswith('#'):
                existing_category = match_existing.group(1)
                existing_module = match_existing.group(2)
                existing_class = match_existing.group(3)
                
                # Проверяем, есть ли этот класс в наших модулях
                if existing_class in class_to_module:
                    dep_category, dep_module = class_to_module[existing_class]
                    # Проверяем циклические зависимости
                    should_use_lazy = False
                    if component_name == 'utils':
                        # Проверяем циклические зависимости для utils
                        if self.structure and 'functions' in self.structure:
                            for func in self.structure.get('functions', []):
                                func_name = func.get('name', '')
                                if func_name in self.dependency_graph and existing_class in self.dependency_graph[func_name]:
                                    # Функция из utils использует класс - проверяем обратную зависимость
                                    if existing_class in self.dependency_graph:
                                        for dep in self.dependency_graph[existing_class]:
                                            # Проверяем, является ли зависимость функцией из utils
                                            if self.structure and 'functions' in self.structure:
                                                for f in self.structure.get('functions', []):
                                                    if f['name'] == dep:
                                                        # Есть циклическая зависимость
                                                        should_use_lazy = True
                                                        break
                    elif component_name and self._would_create_cycle(component_name, existing_class):
                        should_use_lazy = True
                    
                    if should_use_lazy:
                        # Циклическая зависимость - используем отложенный импорт
                        print(f"[REBUILD] Обнаружена циклическая зависимость между {component_name} и {existing_class} в уже замененном импорте, используем отложенный импорт")
                        # Заменяем импорт на отложенный импорт
                        code = self._replace_with_lazy_import(code, existing_class, dep_category, dep_module)
                        # Пропускаем эту строку импорта
                        continue
            # Пропускаем строки с заголовками и комментариями
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                result_lines.append(line)
                continue
            
            # Ищем импорты из исходного файла
            # Паттерн: from source_module import ...
            pattern_from = re.compile(rf'from\s+{re.escape(source_module)}\s+import\s+(\w+)')
            match_from = pattern_from.search(line)
            
            if match_from:
                imported_name = match_from.group(1)
                # Проверяем, есть ли этот класс в наших модулях
                if imported_name in class_to_module:
                    category, module_name = class_to_module[imported_name]
                    # Проверяем, не пытаемся ли мы импортировать класс из самого себя (циклический импорт)
                    if category == current_category and module_name == component_name.lower().replace('_', ''):
                        # Циклический импорт - удаляем строку
                        continue
                    # Проверяем циклические зависимости через граф зависимостей
                    # Для utils.py проверяем циклические зависимости через функции из графа
                    should_use_lazy = False
                    if component_name == 'utils':
                        # Проверяем, есть ли циклическая зависимость между функциями из utils и классом
                        # Ищем функции из utils, которые используют этот класс
                        if self.structure and 'functions' in self.structure:
                            for func in self.structure.get('functions', []):
                                func_name = func.get('name', '')
                                if func_name in self.dependency_graph and imported_name in self.dependency_graph[func_name]:
                                    # Функция из utils использует класс - проверяем обратную зависимость
                                    if imported_name in self.dependency_graph:
                                        for dep in self.dependency_graph[imported_name]:
                                            # Проверяем, является ли зависимость функцией из utils
                                            if self.structure and 'functions' in self.structure:
                                                for f in self.structure.get('functions', []):
                                                    if f['name'] == dep:
                                                        # Есть циклическая зависимость
                                                        should_use_lazy = True
                                                        break
                    elif component_name and self._would_create_cycle(component_name, imported_name):
                        should_use_lazy = True
                    
                    if should_use_lazy:
                        # Циклическая зависимость - используем отложенный импорт
                        print(f"[REBUILD] Обнаружена циклическая зависимость между {component_name} и {imported_name} в _replace_internal_imports, используем отложенный импорт")
                        # Заменяем импорт на отложенный импорт
                        code = self._replace_with_lazy_import(code, imported_name, category, module_name)
                        # Пропускаем эту строку импорта
                        continue
                    # Используем абсолютные импорты, так как модули находятся в одной директории
                    new_import = f"from {category}.{module_name} import {imported_name}"
                    # Заменяем строку
                    line = pattern_from.sub(new_import, line)
                    result_lines.append(line)
                else:
                    # Класс не найден в модулях - возможно это функция или константа
                    # Пытаемся найти в utils или config
                    if imported_name in [f['name'] for f in self.structure.get('functions', [])]:
                        # Функция - импортируем из utils
                        new_import = f"from utils.utils import {imported_name}"
                        line = pattern_from.sub(new_import, line)
                        result_lines.append(line)
                    elif imported_name in [c['name'] for c in self.structure.get('constants', [])]:
                        # Константа - импортируем из imports (config.py больше не создается)
                        new_import = f"from imports import {imported_name}"
                        line = pattern_from.sub(new_import, line)
                        result_lines.append(line)
                    else:
                        # Неизвестный импорт - удаляем строку, чтобы не было ошибок
                        # Пропускаем эту строку
                        pass
                continue
            
            # Также обрабатываем import source_module
            pattern_import = re.compile(rf'import\s+{re.escape(source_module)}\b')
            if pattern_import.search(line):
                # Удаляем импорт исходного модуля
                # Пропускаем эту строку
                continue
            
            # Проверяем циклические импорты: from category.module import Class, где Class == component_name
            # Паттерн: from category.module import Class
            pattern_category_import = re.compile(rf'from\s+(\w+)\.(\w+)\s+import\s+(\w+)')
            match_category = pattern_category_import.search(line)
            if match_category:
                import_category, import_module, import_class = match_category.groups()
                # Преобразуем имя компонента в snake_case для сравнения
                component_snake = component_name[0].lower() + ''.join(c.lower() if c.islower() else '_' + c.lower() for c in component_name[1:]) if component_name else ''
                # Проверяем, не пытаемся ли мы импортировать класс из самого себя
                # Случай 1: from category.module import Class, где category == current_category, module == component_snake, Class == component_name
                if import_category == current_category and import_module == component_snake and import_class == component_name:
                    # Циклический импорт - удаляем строку
                    continue
                # Случай 2: from category.module import Class, где Class == component_name и module соответствует имени компонента
                if import_class == component_name and import_category == current_category:
                    if import_module == component_snake:
                        # Циклический импорт - удаляем строку
                        continue
                # Случай 3: from category.module import Class, где category == current_category и module == component_snake
                # Это означает, что мы пытаемся импортировать из того же модуля
                if import_category == current_category and import_module == component_snake:
                    # Циклический импорт - удаляем строку
                    continue
                # Случай 4: from category.module import Class, где category == current_category и module == import_module
                # Это означает, что мы пытаемся импортировать из модуля с таким же именем в той же категории
                if import_category == current_category and import_module == component_snake:
                    # Циклический импорт - удаляем строку
                    continue
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _replace_imports_in_all_modules(self) -> None:
        """Замена внутренних импортов во всех созданных модулях"""
        import re
        
        # Обрабатываем все модули классов
        for class_name, module_path in self.module_mapping.items():
            try:
                # Читаем файл
                with open(module_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Извлекаем категорию и имя модуля из пути
                rel_path = os.path.relpath(module_path, self.target_dir)
                parts = rel_path.split(os.sep)
                if len(parts) >= 2:
                    category = parts[0]
                    
                    # Заменяем импорты
                    processed_content = self._replace_internal_imports(content, category, class_name)
                    
                    # Сначала проверяем и удаляем циклические импорты функций из utils.utils
                    processed_content = self._remove_circular_function_imports(processed_content, category, class_name)
                    
                    # Анализируем код через AST для поиска использований
                    # ВАЖНО: _add_missing_imports может изменить content через _replace_with_lazy_import
                    # Поэтому нужно использовать processed_content, а не content
                    processed_content = self._add_missing_imports(processed_content, category, class_name)
                    
                    # Заменяем импорты из config на imports (config.py больше не создается)
                    processed_content = self._replace_config_imports(processed_content)
                    
                    # Удаляем циклические импорты функций из runner_functions.py (если они были добавлены)
                    if category == 'core' or category == 'handlers' or category == 'managers' or category == 'analyzers' or category == 'gui' or category == 'loggers':
                        # Удаляем импорты функций из runner_functions.py из классов (они не должны быть там)
                        import re
                        pattern = re.compile(r'from\s+utils\.runner_functions\s+import\s+\w+')
                        processed_content = pattern.sub('', processed_content)
                    
                    # Сохраняем обратно
                    with open(module_path, 'w', encoding='utf-8') as f:
                        f.write(processed_content)
            except Exception as e:
                print(f"[WARNING] Не удалось обработать импорты в {module_path}: {e}")
        
        # Обрабатываем utils.py
        utils_path = os.path.join(self.target_dir, 'utils', 'utils.py')
        if os.path.exists(utils_path):
            try:
                with open(utils_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Для utils.py используем имя файла как component_name для проверки циклических зависимостей
                processed_content = self._replace_internal_imports(content, 'utils', 'utils')
                
                # Удаляем прямые импорты классов из utils.utils (они создают циклические зависимости)
                # utils.utils НЕ должен импортировать классы напрямую - используем отложенный импорт
                import re
                # Удаляем импорты классов (например, from core.UniversalProcessRunner import UniversalProcessRunner)
                class_import_pattern = re.compile(r'^from\s+(\w+)\.(\w+)\s+import\s+(\w+)\s*$', re.MULTILINE)
                lines = processed_content.split('\n')
                filtered_lines = []
                for line in lines:
                    match = class_import_pattern.match(line)
                    if match:
                        import_category, import_module, import_class = match.groups()
                        # Проверяем, является ли это классом (не функцией)
                        if import_class in self.module_mapping:
                            # Это класс - удаляем импорт, будет использован отложенный импорт
                            print(f"[REBUILD] Удален прямой импорт класса {import_class} из utils.utils (будет использован отложенный импорт)")
                            continue
                    filtered_lines.append(line)
                processed_content = '\n'.join(filtered_lines)
                
                processed_content = self._add_missing_imports(processed_content, 'utils', 'utils')
                
                # Удаляем прямые импорты классов из utils.utils ЕЩЕ РАЗ (на случай если _add_missing_imports их добавил)
                # utils.utils НЕ должен импортировать классы напрямую - используем отложенный импорт
                import re
                # Удаляем импорты классов (например, from core.UniversalProcessRunner import UniversalProcessRunner)
                class_import_pattern = re.compile(r'^from\s+(\w+)\.(\w+)\s+import\s+(\w+)\s*$', re.MULTILINE)
                lines = processed_content.split('\n')
                filtered_lines = []
                for line in lines:
                    match = class_import_pattern.match(line)
                    if match:
                        import_category, import_module, import_class = match.groups()
                        # Проверяем, является ли это классом (не функцией)
                        if import_class in self.module_mapping:
                            # Это класс - удаляем импорт, будет использован отложенный импорт
                            print(f"[REBUILD] Удален прямой импорт класса {import_class} из utils.utils (будет использован отложенный импорт)")
                            continue
                    filtered_lines.append(line)
                processed_content = '\n'.join(filtered_lines)
                
                # Заменяем импорты из config на imports
                processed_content = self._replace_config_imports(processed_content)
                
                with open(utils_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content)
            except Exception as e:
                print(f"[WARNING] Не удалось обработать импорты в {utils_path}: {e}")
        
        # Обрабатываем utils/main.py
        main_path = os.path.join(self.target_dir, 'utils', 'main.py')
        if os.path.exists(main_path):
            try:
                with open(main_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Разделяем на части: до from imports import * и после
                parts = content.split('from imports import *')
                if len(parts) == 2:
                    # Есть from imports import *
                    before_imports = parts[0]
                    after_imports = parts[1]
                    
                    # Обрабатываем только часть после from imports import *
                    processed_after = self._replace_internal_imports(after_imports, 'utils', 'main')
                    processed_after = self._add_missing_imports(processed_after, 'utils', 'main')
                    # Заменяем импорты из config на imports
                    processed_after = self._replace_config_imports(processed_after)
                    
                    # Собираем обратно: до from imports import *, сам импорт, и обработанная часть
                    processed_content = before_imports + 'from imports import *' + processed_after
                else:
                    # Нет from imports import *, обрабатываем весь файл
                    processed_content = self._replace_internal_imports(content, 'utils', 'main')
                    processed_content = self._add_missing_imports(processed_content, 'utils', 'main')
                    # Заменяем импорты из config на imports
                    processed_content = self._replace_config_imports(processed_content)
                
                with open(main_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content)
            except Exception as e:
                print(f"[WARNING] Не удалось обработать импорты в {main_path}: {e}")
        
        # Обрабатываем utils/runner_functions.py
        runner_path = os.path.join(self.target_dir, 'utils', 'runner_functions.py')
        if os.path.exists(runner_path):
            try:
                with open(runner_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                processed_content = self._replace_internal_imports(content, 'utils', 'runner_functions')
                # Добавляем недостающие импорты для runner_functions.py (но не добавляем импорты функций из него самого)
                # Создаем временную версию _add_missing_imports, которая не добавляет импорты функций из runner_functions.py
                processed_content = self._add_missing_imports(processed_content, 'utils', 'runner_functions')
                # Заменяем импорты из config на imports
                processed_content = self._replace_config_imports(processed_content)
                
                with open(runner_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content)
            except Exception as e:
                print(f"[WARNING] Не удалось обработать импорты в {runner_path}: {e}")
        
        # Обрабатываем utils/cleanup.py
        cleanup_path = os.path.join(self.target_dir, 'utils', 'cleanup.py')
        if os.path.exists(cleanup_path):
            try:
                with open(cleanup_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                processed_content = self._replace_internal_imports(content, 'utils', 'cleanup')
                processed_content = self._add_missing_imports(processed_content, 'utils', 'cleanup')
                # Заменяем импорты из config на imports
                processed_content = self._replace_config_imports(processed_content)
                
                with open(cleanup_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content)
            except Exception as e:
                print(f"[WARNING] Не удалось обработать импорты в {cleanup_path}: {e}")
    
    def _add_missing_imports(self, content: str, category: str, component_name: str) -> str:
        """Добавление недостающих импортов на основе анализа кода через AST"""
        import ast
        import re
        
        try:
            # Парсим код в AST
            tree = ast.parse(content)
            
            # Собираем все используемые имена
            used_names = set()
            base_classes = set()
            decorators = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Load):
                        used_names.add(node.id)
                elif isinstance(node, ast.ClassDef):
                    # Собираем базовые классы
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_classes.add(base.id)
                        elif isinstance(base, ast.Attribute):
                            attr_name = self._get_attr_name(base)
                            base_classes.add(attr_name.split('.')[0])
                    # Собираем декораторы класса
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name):
                            decorators.add(decorator.id)
                        elif isinstance(decorator, ast.Attribute):
                            attr_name = self._get_attr_name(decorator)
                            decorators.add(attr_name.split('.')[0])
                        elif isinstance(decorator, ast.Call):
                            # Обрабатываем декораторы с вызовом (например, @track_class_activity('WinePackageHandler'))
                            if isinstance(decorator.func, ast.Name):
                                decorators.add(decorator.func.id)
                            elif isinstance(decorator.func, ast.Attribute):
                                attr_name = self._get_attr_name(decorator.func)
                                decorators.add(attr_name.split('.')[0])
                elif isinstance(node, ast.FunctionDef):
                    # Собираем декораторы функций/методов
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name):
                            decorators.add(decorator.id)
                        elif isinstance(decorator, ast.Attribute):
                            attr_name = self._get_attr_name(decorator)
                            decorators.add(attr_name.split('.')[0])
                        elif isinstance(decorator, ast.Call):
                            # Обрабатываем декораторы с вызовом
                            if isinstance(decorator.func, ast.Name):
                                decorators.add(decorator.func.id)
                            elif isinstance(decorator.func, ast.Attribute):
                                attr_name = self._get_attr_name(decorator.func)
                                decorators.add(attr_name.split('.')[0])
            
            # Определяем, какие импорты нужно добавить
            imports_to_add = []
            
            # Проверяем ABC
            if 'ABC' in base_classes or 'ABC' in used_names:
                has_abc_import = any('ABC' in line and ('import' in line or 'from' in line) and 'abc' in line
                                    for line in content.split('\n'))
                if not has_abc_import:
                    imports_to_add.append('from abc import ABC, abstractmethod')
            
            # Проверяем декораторы и функции из utils
            # Ищем все декораторы, которые могут быть функциями
            if self.structure and 'functions' in self.structure:
                function_names = [f['name'] for f in self.structure.get('functions', [])]
            else:
                function_names = []
            
            for decorator in decorators:
                # Проверяем, есть ли этот декоратор в функциях проекта
                if decorator in function_names:
                    # Проверяем циклические зависимости для функций из utils
                    # Если component_name импортирует функцию из utils, а utils импортирует component_name - цикл
                    if component_name and decorator in function_names:
                        # Проверяем, импортирует ли utils этот компонент через граф зависимостей
                        utils_imports_component = False
                        if decorator in self.dependency_graph:
                            if component_name in self.dependency_graph[decorator]:
                                utils_imports_component = True
                        
                        # Также проверяем обратную зависимость
                        if component_name in self.dependency_graph:
                            if decorator in self.dependency_graph[component_name]:
                                # Есть циклическая зависимость - используем отложенный импорт
                                print(f"[REBUILD] Обнаружена циклическая зависимость между {component_name} и {decorator}, используем отложенный импорт")
                                # Удаляем прямой импорт
                                import re
                                import_pattern = re.compile(rf'from\s+utils\.utils\s+import\s+{re.escape(decorator)}\b')
                                content = import_pattern.sub(f'# Отложенный импорт для избежания циклических зависимостей\n# from utils.utils import {decorator}', content)
                                # Удаляем декораторы на уровне модуля - они будут применены при первом вызове метода
                                # Заменяем @decorator('ClassName') на пустую строку
                                pattern = re.compile(rf'^\s*@{re.escape(decorator)}\([^)]+\)\s*$', re.MULTILINE)
                                content = pattern.sub('', content)
                                # Удаляем пустые строки после удаления декораторов
                                lines = content.split('\n')
                                cleaned_lines = []
                                prev_empty = False
                                for line in lines:
                                    if line.strip() == '':
                                        if not prev_empty:
                                            cleaned_lines.append(line)
                                        prev_empty = True
                                    else:
                                        cleaned_lines.append(line)
                                        prev_empty = False
                                content = '\n'.join(cleaned_lines)
                                continue
                    
                    has_import = any(decorator in line and ('import' in line or 'from' in line)
                                    for line in content.split('\n'))
                    if not has_import:
                        # Проверяем циклические зависимости для функций из utils
                        # Если component_name импортирует функцию из utils, а utils импортирует component_name - цикл
                        if component_name and decorator in function_names:
                            # Проверяем, импортирует ли utils этот компонент через граф зависимостей
                            if component_name in self.dependency_graph:
                                if decorator in self.dependency_graph[component_name]:
                                    # Есть циклическая зависимость - используем отложенный импорт
                                    print(f"[REBUILD] Обнаружена циклическая зависимость между {component_name} и {decorator}, используем отложенный импорт")
                                    # Удаляем прямой импорт, если он есть
                                    import re
                                    import_pattern = re.compile(rf'from\s+utils\.utils\s+import\s+{re.escape(decorator)}\b')
                                    content = import_pattern.sub(f'# Отложенный импорт для избежания циклических зависимостей\n# from utils.utils import {decorator}', content)
                                    continue
                        # Определяем, где находится функция (обычно в utils)
                        # Проверяем, есть ли функция в utils
                        # Используем абсолютные импорты, так как модули находятся в одной директории
                        imports_to_add.append(f'from utils.utils import {decorator}')
                        print(f"[REBUILD] Добавлен импорт {decorator} в {os.path.basename(component_name) if component_name else 'utils.py'}")
                else:
                    # Отладочный вывод для проверки
                    # Проверяем, является ли декоратор функцией из utils (универсальная проверка)
                    if decorator in function_names:
                        print(f"[DEBUG] Decorator {decorator} not in function_names. Total functions: {len(function_names)}, First 5: {function_names[:5] if function_names else 'empty'}")
                        print(f"[DEBUG] self.structure exists: {self.structure is not None}, has functions: {'functions' in self.structure if self.structure else False}")
            
            # Проверяем базовые классы из других модулей
            for base_class in base_classes:
                # Проверяем, есть ли этот класс в наших модулях
                if base_class in self.module_mapping:
                    # Определяем категорию и модуль
                    module_path = self.module_mapping[base_class]
                    rel_path = os.path.relpath(module_path, self.target_dir)
                    parts = rel_path.split(os.sep)
                    if len(parts) >= 2:
                        base_category = parts[0]
                        base_module_file = parts[1]
                        base_module_name = os.path.splitext(base_module_file)[0]
                        
                        # Проверяем, не пытаемся ли мы импортировать класс из самого себя (циклический импорт)
                        component_module_name = self._class_name_to_module_name(component_name) if component_name else ''
                        if base_category == category and base_module_name == component_module_name:
                            # Циклический импорт - пропускаем
                            continue
                        
                        # Проверяем циклические зависимости через граф зависимостей
                        if component_name and self._would_create_cycle(component_name, base_class):
                            # Циклическая зависимость - используем отложенный импорт
                            print(f"[REBUILD] Обнаружена циклическая зависимость между {component_name} и {base_class}, используем отложенный импорт")
                            continue
                        
                        has_import = any(base_class in line and ('import' in line or 'from' in line)
                                        for line in content.split('\n'))
                        if not has_import:
                            # Используем абсолютные импорты, так как модули находятся в одной директории
                            imports_to_add.append(f'from {base_category}.{base_module_name} import {base_class}')
            
            # Проверяем использование классов в коде (например, UniversalProcessRunner())
            # Проверяем все имена, которые могут быть классами из наших модулей
            for used_name in used_names:
                # Пропускаем стандартные типы и встроенные функции
                if used_name in ['str', 'int', 'float', 'bool', 'list', 'dict', 'tuple', 'set', 'None', 'True', 'False', 'print', 'len', 'range', 'enumerate', 'zip', 'isinstance', 'hasattr', 'getattr', 'setattr', 'type', 'super', 'object', 'Exception', 'BaseException', 'ValueError', 'KeyError', 'AttributeError', 'TypeError', 'ImportError', 'NameError', 'OSError', 'IOError', 'FileNotFoundError', 'PermissionError', 'NotImplementedError', 'StopIteration', 'GeneratorExit', 'SystemExit', 'KeyboardInterrupt']:
                    continue
                
                # Проверяем, есть ли этот класс в наших модулях
                if used_name in self.module_mapping:
                    # Определяем категорию и модуль
                    module_path = self.module_mapping[used_name]
                    rel_path = os.path.relpath(module_path, self.target_dir)
                    parts = rel_path.split(os.sep)
                    if len(parts) >= 2:
                        used_category = parts[0]
                        used_module_file = parts[1]
                        used_module_name = os.path.splitext(used_module_file)[0]
                        
                        # Проверяем, не пытаемся ли мы импортировать класс из самого себя (циклический импорт)
                        component_module_name = self._class_name_to_module_name(component_name) if component_name else ''
                        if used_category == category and used_module_name == component_module_name:
                            # Циклический импорт - пропускаем
                            continue
                        
                        # Проверяем циклические зависимости через граф зависимостей
                        if component_name and self._would_create_cycle(component_name, used_name):
                            # Циклическая зависимость - используем отложенный импорт внутри функций/методов
                            # Заменяем использование на отложенный импорт
                            print(f"[REBUILD] Обнаружена циклическая зависимость между {component_name} и {used_name}, используем отложенный импорт")
                            # Не добавляем импорт на уровне модуля - он будет импортирован внутри функций/методов при необходимости
                            # Заменяем использование на вызов функции с отложенным импортом
                            content = self._replace_with_lazy_import(content, used_name, used_category, used_module_name)
                            # Также удаляем импорт на уровне модуля, если он есть
                            import re
                            import_pattern = re.compile(rf'from\s+{re.escape(used_category)}\.{re.escape(used_module_name)}\s+import\s+{re.escape(used_name)}\b')
                            content = import_pattern.sub('', content)
                            # НЕ добавляем импорт в imports_to_add
                            continue
                        
                        # Проверка циклических зависимостей между utils и другими категориями (универсальная проверка)
                        # Если utils импортирует класс, а класс импортирует функцию из utils - цикл
                        # НО: для runner_functions.py это НЕ циклическая зависимость, т.к. runner_functions.py не импортируется в классы
                        if component_name == 'runner_functions':
                            # Для runner_functions.py всегда добавляем импорты классов (нет циклических зависимостей)
                            pass
                        elif component_name == used_name:
                            # Проверяем, импортирует ли utils этот класс через граф зависимостей
                            # Ищем функции из utils, которые используют этот класс
                            utils_imports_class = False
                            if self.structure and 'functions' in self.structure:
                                for func in self.structure.get('functions', []):
                                    func_name = func['name']
                                    if func_name in self.dependency_graph:
                                        if component_name in self.dependency_graph[func_name]:
                                            utils_imports_class = True
                                            break
                            
                            if utils_imports_class:
                                # Циклическая зависимость - используем отложенный импорт
                                print(f"[REBUILD] Обнаружена циклическая зависимость между utils.utils и {used_name}, используем отложенный импорт")
                                content = self._replace_with_lazy_import(content, used_name, used_category, used_module_name)
                                import re
                                import_pattern = re.compile(rf'from\s+{re.escape(used_category)}\.{re.escape(used_module_name)}\s+import\s+{re.escape(used_name)}\b')
                                content = import_pattern.sub('', content)
                                continue
                        
                        # Проверяем, импортирует ли utils этот класс (для всех классов)
                        # Если utils импортирует класс, а класс импортирует что-то из utils - цикл
                        # НО: для runner_functions.py это НЕ циклическая зависимость, т.к. runner_functions.py не импортируется в классы
                        # НО: для utils.utils это ОСОБЫЙ случай - utils.utils НЕ должен импортировать классы напрямую
                        # Классы импортируются только в других классах или в main.py, но не в utils.utils
                        # Если utils.utils импортирует класс, а класс импортирует что-то из utils.utils - это циклический импорт
                        if category == 'utils' and component_name == 'utils' and used_name in self.module_mapping:
                            # utils.utils НЕ должен импортировать классы напрямую - это создает циклические зависимости
                            # Классы используют функции из utils.utils, но utils.utils не должен импортировать классы
                            # Поэтому для utils.utils ВСЕГДА используем отложенный импорт для классов
                            print(f"[REBUILD] Обнаружена попытка импорта класса {used_name} в utils.utils - используем отложенный импорт для избежания циклических зависимостей")
                            content = self._replace_with_lazy_import(content, used_name, used_category, used_module_name)
                            import re
                            import_pattern = re.compile(rf'from\s+{re.escape(used_category)}\.{re.escape(used_module_name)}\s+import\s+{re.escape(used_name)}\b')
                            content = import_pattern.sub('', content)
                            continue
                        
                        has_import = any(used_name in line and ('import' in line or 'from' in line)
                                        for line in content.split('\n'))
                        if not has_import:
                            # Используем абсолютные импорты, так как модули находятся в одной директории
                            imports_to_add.append(f'from {used_category}.{used_module_name} import {used_name}')
            
            # Проверяем стандартные модули (builtins, queue и т.д.)
            standard_modules = {
                'builtins': ['builtins.', 'builtins.print', 'builtins.open'],
                'queue': ['queue.', 'Queue(', 'Empty'],
                'os': ['os.', 'os.path', 'os.getenv', 'os.environ'],
                'sys': ['sys.', 'sys.argv', 'sys.exit', 'sys.path'],
                'json': ['json.', 'json.load', 'json.dump'],
                're': ['re.', 're.match', 're.search', 're.compile'],
                'typing': ['typing.', 'List[', 'Dict[', 'Optional['],
                'abc': ['abc.', 'ABC', 'abstractmethod'],
                'collections': ['collections.', 'collections.deque'],
                'datetime': ['datetime.', 'datetime.datetime', 'datetime.now'],
                'threading': ['threading.', 'threading.Thread', 'threading.Lock', 'threading.current_thread', 'threading.Lock()', 'threading.Thread(', '= threading.', 'threading.Lock()', 'threading.Thread('],
                'tempfile': ['tempfile.', 'tempfile.mkdtemp'],
                'shutil': ['shutil.', 'shutil.copy', 'shutil.rmtree'],
                'subprocess': ['subprocess.', 'subprocess.run', 'subprocess.Popen'],
                'hashlib': ['hashlib.', 'hashlib.md5', 'hashlib.sha256'],
                'time': ['time.', 'time.sleep', 'time.time'],
                'traceback': ['traceback.', 'traceback.print_exc']
            }
            
            # Проверяем использование стандартных модулей через AST
            for module_name, patterns in standard_modules.items():
                # Проверяем использование через AST
                module_used = False
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name):
                        if node.id == module_name and isinstance(node.ctx, ast.Load):
                            module_used = True
                            break
                    elif isinstance(node, ast.Attribute):
                        # Проверяем использование через атрибуты (например, threading.Lock())
                        if isinstance(node.value, ast.Name) and node.value.id == module_name:
                            module_used = True
                            break
                        # Также проверяем полное имя атрибута
                        attr_name = self._get_attr_name(node)
                        if attr_name.startswith(f'{module_name}.'):
                            module_used = True
                            break
                
                # Также проверяем через паттерны в тексте (более надежный способ)
                # Для threading проверяем более тщательно - сначала проверяем текст, потом AST
                # Для threading всегда проверяем текст ПЕРВЫМ делом - это самый надежный способ
                if module_name == 'threading':
                    # Для threading всегда проверяем текст - это самый надежный способ
                    if 'threading.' in content or 'threading.Lock()' in content or 'threading.Thread(' in content:
                        module_used = True
                        print(f"[REBUILD] Найдено использование threading в {component_name}")
                elif not module_used:
                    for pattern in patterns:
                        if pattern in content:
                            module_used = True
                            break
                
                if module_used:
                    has_import = any(f'import {module_name}' in line or f'from {module_name}' in line
                                    for line in content.split('\n'))
                    if not has_import:
                        imports_to_add.append(f'import {module_name}')
                        if module_name == 'threading':
                            print(f"[REBUILD] Добавлен импорт threading в {component_name} (найдено использование threading. в коде)")
            
            # Проверяем использование функций из utils.utils (например, check_system_requirements, get_global_universal_runner)
            if self.structure and 'functions' in self.structure:
                function_names = [f['name'] for f in self.structure.get('functions', [])]
                # Определяем, какие функции находятся в utils/utils.py
                utils_functions = []
                runner_functions = []
                for func in self.structure.get('functions', []):
                    func_name = func.get('name', '')
                    # Функции, которые не являются run_* или cleanup_*, обычно находятся в utils.py
                    if not func_name.startswith('run_') and not func_name.startswith('cleanup_') and func_name != 'main':
                        utils_functions.append(func_name)
                    # Функции run_* находятся в runner_functions.py
                    elif func_name.startswith('run_'):
                        runner_functions.append(func_name)
                
                # Проверяем использование функций из utils.utils
                for func_name in utils_functions:
                    # Проверяем использование через AST и через текст
                    # Для main.py проверяем более тщательно - ищем вызовы функций
                    func_used = func_name in used_names or func_name in content or f'{func_name}(' in content
                    if func_used:
                        has_import = any(f'{func_name}' in line and ('import' in line or 'from' in line) and 'utils' in line
                                        for line in content.split('\n'))
                        if not has_import:
                            # Проверяем циклические зависимости для функций из utils
                            # Циклическая зависимость: если component_name импортирует функцию из utils.utils, 
                            # а utils.utils импортирует component_name - цикл
                            # НО: для main.py и классов это НЕ циклическая зависимость, так как они не импортируются в utils.utils
                            is_circular = False
                            # main.py НИКОГДА не создает циклических зависимостей с utils.utils
                            # Классы ТОЖЕ не создают циклических зависимостей с utils.utils (классы могут импортировать функции из utils.utils)
                            # Циклическая зависимость возможна только если utils.utils импортирует component_name
                            # НО: если component_name - это класс, то utils.utils НЕ импортирует класс напрямую
                            # Классы импортируются только в других классах или в main.py, но не в utils.utils
                            # Поэтому для классов ВСЕГДА можно импортировать функции из utils.utils
                            if component_name and component_name != 'main' and component_name != 'utils':
                                # Проверяем, является ли component_name классом (не функцией)
                                is_class = component_name in self.module_mapping
                                if is_class:
                                    # Для классов ВСЕГДА можно импортировать функции из utils.utils (нет циклических зависимостей)
                                    is_circular = False
                                else:
                                    # Для функций проверяем циклические зависимости
                                    # Если utils.utils импортирует component_name, а component_name импортирует функцию из utils.utils - цикл
                                    if 'utils' in self.dependency_graph:
                                        if component_name in self.dependency_graph.get('utils', []):
                                            # Есть циклическая зависимость - используем отложенный импорт
                                            print(f"[REBUILD] Обнаружена циклическая зависимость между {component_name} и {func_name} (через utils.utils), используем отложенный импорт")
                                            is_circular = True
                            
                            # Для main.py и классов ВСЕГДА добавляем импорты функций из utils.utils (они не создают циклических зависимостей)
                            if component_name == 'main':
                                # В main.py всегда можно импортировать из utils.utils
                                imports_to_add.append(f'from utils.utils import {func_name}')
                                print(f"[REBUILD] Добавлен импорт {func_name} в main.py")
                            elif not is_circular and component_name != 'utils':
                                # В классах и других файлах можно импортировать из utils.utils (если нет циклических зависимостей)
                                imports_to_add.append(f'from utils.utils import {func_name}')
                                print(f"[REBUILD] Добавлен импорт {func_name} в {component_name}")
                
                # Проверяем использование функций из utils/runner_functions.py (например, run_gui_monitor)
                for func_name in runner_functions:
                    # Проверяем использование через AST и через текст
                    func_used = func_name in used_names or func_name in content or f'{func_name}(' in content
                    if func_used:
                        has_import = any(f'{func_name}' in line and ('import' in line or 'from' in line) and 'runner_functions' in line
                                        for line in content.split('\n'))
                        if not has_import:
                            # НЕ добавляем импорты функций из runner_functions.py в сам файл runner_functions.py
                            if component_name == 'runner_functions':
                                # Это сам файл runner_functions.py - не добавляем импорты функций из него
                                continue
                            
                            # Для main.py всегда добавляем импорты функций из runner_functions.py
                            if component_name == 'main':
                                imports_to_add.append(f'from utils.runner_functions import {func_name}')
                                print(f"[REBUILD] Добавлен импорт {func_name} в main.py")
                            elif component_name != 'utils':
                                # В других файлах можно импортировать из runner_functions.py
                                imports_to_add.append(f'from utils.runner_functions import {func_name}')
            
            # Специальная проверка для COMPONENTS_CONFIG в utils/utils.py
            if 'COMPONENTS_CONFIG' in used_names or 'COMPONENTS_CONFIG' in content:
                has_import = any('COMPONENTS_CONFIG' in line and ('import' in line or 'from' in line)
                                for line in content.split('\n'))
                if not has_import:
                    imports_to_add.append('from imports import COMPONENTS_CONFIG')
            
            # Специальная проверка для APP_VERSION
            if 'APP_VERSION' in used_names or 'APP_VERSION' in content:
                has_import = any('APP_VERSION' in line and ('import' in line or 'from' in line)
                                for line in content.split('\n'))
                if not has_import:
                    imports_to_add.append('from imports import APP_VERSION')
            
            # Удаляем gui_log=True из print() вызовов
            import re
            # Удаляем gui_log=True в любом месте аргументов print()
            content = re.sub(r',\s*gui_log=True', '', content)
            content = re.sub(r'gui_log=True\s*,', '', content)
            content = re.sub(r'\s+gui_log=True', '', content)
            content = re.sub(r'gui_log=True\s+', '', content)
            
            # Добавляем импорты, если нужно
            if imports_to_add:
                lines = content.split('\n')
                insert_pos = 0
                
                # Ищем конец docstring модуля
                in_docstring = False
                found_coding = False
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith('# -*- coding:'):
                        found_coding = True
                        continue
                    if found_coding and stripped.startswith('"""') and not in_docstring:
                        in_docstring = True
                        if stripped.endswith('"""') and len(stripped) > 3:
                            in_docstring = False
                            if i + 1 < len(lines):
                                if not lines[i + 1].strip():
                                    insert_pos = i + 2
                                else:
                                    insert_pos = i + 1
                            else:
                                insert_pos = i + 1
                            break
                    elif in_docstring and stripped == '"""':
                        in_docstring = False
                        if i + 1 < len(lines):
                            if not lines[i + 1].strip():
                                insert_pos = i + 2
                            else:
                                insert_pos = i + 1
                        else:
                            insert_pos = i + 1
                        break
                
                if insert_pos == 0:
                    # Ищем строку с классом или функцией
                    for i, line in enumerate(lines):
                        if line.strip().startswith('class ') or line.strip().startswith('def '):
                            insert_pos = i
                            break
                    if insert_pos == 0:
                        insert_pos = 8
                
                if insert_pos > 0:
                    for imp in imports_to_add:
                        lines.insert(insert_pos, imp)
                        insert_pos += 1
                    lines.insert(insert_pos, '')  # Пустая строка после импортов
                    content = '\n'.join(lines)
                    print(f"[REBUILD] Добавлены импорты в {os.path.basename(component_name) if component_name else 'utils.py'}: {', '.join(imports_to_add)}")
        
        except Exception as e:
            # Если не удалось распарсить, возвращаем исходный код
            pass
        
        return content
    
    def _get_attr_name(self, node: ast.Attribute) -> str:
        """Получение полного имени атрибута"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attr_name(node.value)}.{node.attr}"
        return node.attr
    
    def _process_config_imports(self) -> None:
        """Обработка config.py - добавление недостающих импортов на основе анализа кода"""
        config_path = os.path.join(self.target_dir, 'config.py')
        if not os.path.exists(config_path):
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Анализируем код через AST для поиска использований
            imports_to_add = []
            
            try:
                import ast
                tree = ast.parse(content)
                
                # Собираем все используемые имена
                used_names = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name):
                        if isinstance(node.ctx, ast.Load):
                            used_names.add(node.id)
                    elif isinstance(node, ast.Attribute):
                        # Обрабатываем атрибуты (например, builtins.open)
                        attr_name = self._get_attr_name(node)
                        if '.' in attr_name:
                            base_name = attr_name.split('.')[0]
                            used_names.add(base_name)
                
                # Проверяем, какие классы используются из наших модулей
                for class_name in used_names:
                    # Проверяем, есть ли этот класс в наших модулях
                    if class_name in self.module_mapping:
                        # Определяем категорию и модуль
                        module_path = self.module_mapping[class_name]
                        rel_path = os.path.relpath(module_path, self.target_dir)
                        parts = rel_path.split(os.sep)
                        if len(parts) >= 2:
                            category = parts[0]
                            module_file = parts[1]
                            module_name = os.path.splitext(module_file)[0]
                            
                            # Проверяем, есть ли уже импорт
                            has_import = any(class_name in line and ('import' in line or 'from' in line)
                                            for line in content.split('\n'))
                            if not has_import:
                                # config.py находится в корне модулей, поэтому используем абсолютные импорты
                                imports_to_add.append(f'from {category}.{module_name} import {class_name}')
                
                # Проверяем стандартные модули (builtins, queue и т.д.)
                standard_modules = ['builtins', 'queue', 'os', 'sys', 'json', 're', 'typing', 'abc', 'collections', 'datetime', 'threading', 'tempfile', 'shutil', 'subprocess', 'hashlib', 'time', 'traceback']
                for module_name in standard_modules:
                    # Проверяем использование через точку (например, builtins.open, queue.Queue)
                    if f'{module_name}.' in content:
                        has_import = any(f'import {module_name}' in line or f'from {module_name}' in line
                                        for line in content.split('\n'))
                        if not has_import:
                            imports_to_add.append(f'import {module_name}')
                    # Также проверяем использование без точки (например, Queue() из queue)
                    elif module_name in ['queue']:
                        # Для queue проверяем использование Queue, Empty и т.д.
                        if 'Queue(' in content or 'queue.' in content or 'Empty' in content:
                            has_import = any(f'import {module_name}' in line or f'from {module_name}' in line
                                            for line in content.split('\n'))
                            if not has_import:
                                imports_to_add.append(f'import {module_name}')
            
            except Exception as e:
                # Если не удалось распарсить, используем простую проверку
                print(f"[WARNING] Не удалось распарсить config.py через AST: {e}")
            
            # Добавляем импорты, если нужно
            if imports_to_add:
                lines = content.split('\n')
                insert_pos = 0
                
                # Ищем конец docstring модуля
                in_docstring = False
                found_coding = False
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith('# -*- coding:'):
                        found_coding = True
                        continue
                    if found_coding and stripped.startswith('"""') and not in_docstring:
                        in_docstring = True
                        if stripped.endswith('"""') and len(stripped) > 3:
                            in_docstring = False
                            if i + 1 < len(lines):
                                if not lines[i + 1].strip():
                                    insert_pos = i + 2
                                else:
                                    insert_pos = i + 1
                            else:
                                insert_pos = i + 1
                            break
                    elif in_docstring and stripped == '"""':
                        in_docstring = False
                        if i + 1 < len(lines):
                            if not lines[i + 1].strip():
                                insert_pos = i + 2
                            else:
                                insert_pos = i + 1
                        else:
                            insert_pos = i + 1
                        break
                
                if insert_pos == 0:
                    insert_pos = 8
                
                if insert_pos > 0:
                    for imp in imports_to_add:
                        lines.insert(insert_pos, imp)
                        insert_pos += 1
                    lines.insert(insert_pos, '')  # Пустая строка после импортов
                    content = '\n'.join(lines)
                    with open(config_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"[REBUILD] Добавлены импорты в config.py: {', '.join(imports_to_add)}")
        except Exception as e:
            print(f"[WARNING] Не удалось обработать config.py: {e}")
    
    def _apply_lazy_decorators(self, content: str, class_name: str) -> str:
        """
        Применяет отложенные декораторы для handlers файлов
        
        Args:
            content: Исходный код модуля
            class_name: Имя класса
            
        Returns:
            str: Код с отложенными декораторами
        """
        import ast
        import re
        
        try:
            # Определяем функции из utils для проверки декораторов
            utils_functions = set()
            if self.structure and 'functions' in self.structure:
                for func in self.structure.get('functions', []):
                    utils_functions.add(func['name'])
            
            # Парсим код в AST
            tree = ast.parse(content)
            
            # Собираем методы с декораторами из utils (которые могут создавать циклические зависимости)
            methods_with_decorator = {}  # {method_name: decorator_name}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            # Проверяем декораторы метода
                            for decorator in item.decorator_list:
                                decorator_name = None
                                if isinstance(decorator, ast.Call):
                                    if isinstance(decorator.func, ast.Name):
                                        decorator_name = decorator.func.id
                                    elif isinstance(decorator.func, ast.Attribute):
                                        decorator_name = self._get_attr_name(decorator.func).split('.')[-1]
                                elif isinstance(decorator, ast.Name):
                                    decorator_name = decorator.id
                                elif isinstance(decorator, ast.Attribute):
                                    decorator_name = self._get_attr_name(decorator).split('.')[-1]
                                
                                # Проверяем, является ли декоратор функцией из utils
                                if decorator_name in utils_functions:
                                    # Проверяем, есть ли циклическая зависимость
                                    if decorator_name in self.dependency_graph:
                                        if class_name in self.dependency_graph[decorator_name]:
                                            # Есть циклическая зависимость - применяем отложенный декоратор
                                            methods_with_decorator[item.name] = decorator_name
                                    break
            
            # Если нет методов с декораторами, возвращаем код как есть
            if not methods_with_decorator:
                return content
            
            # Генерируем функции отложенного импорта для каждого декоратора
            lazy_import_funcs = []
            decorator_names = set(methods_with_decorator.values())
            for decorator_name in decorator_names:
                lazy_import_funcs.append(f'''
# Отложенный импорт для избежания циклических зависимостей
# from utils.utils import {decorator_name}

def _get_{decorator_name}():
    """Отложенный импорт для избежания циклических зависимостей"""
    from utils.utils import {decorator_name}
    return {decorator_name}
''')
            
            lazy_import_func = '\n'.join(lazy_import_funcs)
            
            # Находим место для вставки (после импортов, перед классом)
            lines = content.split('\n')
            insert_pos = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('class '):
                    insert_pos = i
                    break
            
            # Вставляем функции отложенного импорта
            if insert_pos > 0:
                # Вставляем функции перед классом
                lines.insert(insert_pos, lazy_import_func)
                content = '\n'.join(lines)
            else:
                # Если класс не найден, добавляем в начало файла
                lines.insert(0, lazy_import_func)
                content = '\n'.join(lines)
            
            # Удаляем декораторы из методов (для всех декораторов из utils)
            for decorator_name in decorator_names:
                pattern = re.compile(rf'^\s*@{re.escape(decorator_name)}\([^)]+\)\s*$', re.MULTILINE)
            content = pattern.sub('', content)
            
            # Удаляем пустые строки после удаления декораторов
            lines = content.split('\n')
            cleaned_lines = []
            prev_empty = False
            for line in lines:
                if line.strip() == '':
                    if not prev_empty:
                        cleaned_lines.append(line)
                    prev_empty = True
                else:
                    cleaned_lines.append(line)
                    prev_empty = False
            content = '\n'.join(cleaned_lines)
            
            # НЕ вызываем декораторы на уровне модуля, чтобы избежать циклических зависимостей
            # Вместо этого применяем декораторы при первом вызове метода через декоратор-обертку
            # Добавляем комментарий о том, что декораторы будут применены при первом вызове
            apply_comment = f'\n# Декораторы {", ".join(decorator_names)} будут применены автоматически при первом вызове методов\n'
            apply_comment += '# через механизм отложенного применения декораторов\n'
            
            # Создаем обертки для методов, которые применяют декоратор при первом вызове
            wrapper_code = '\n# Применяем декораторы при первом вызове методов\n'
            wrapper_code += f'_decorated_methods_{class_name} = {{}}\n'
            wrapper_code += f'def _apply_decorator_on_call(cls, method_name, class_name, decorator_name):\n'
            wrapper_code += f'    """Применяет декоратор при первом вызове метода"""\n'
            wrapper_code += f'    cache_key = (cls, method_name, decorator_name)\n'
            wrapper_code += f'    if cache_key not in _decorated_methods_{class_name}:\n'
            wrapper_code += f'        method = getattr(cls, method_name)\n'
            wrapper_code += f'        decorator_func = globals().get(f"_get_{{decorator_name}}")()\n'
            wrapper_code += f'        decorated = decorator_func(class_name)(method)\n'
            wrapper_code += f'        _decorated_methods_{class_name}[cache_key] = decorated\n'
            wrapper_code += f'        setattr(cls, method_name, decorated)\n'
            wrapper_code += f'    return _decorated_methods_{class_name}[cache_key]\n'
            
            # Обертываем методы класса
            for method_name, decorator_name in methods_with_decorator.items():
                wrapper_code += f'\n# Обертка для метода {method_name} с декоратором {decorator_name}\n'
                wrapper_code += f'_original_{method_name} = {class_name}.{method_name}\n'
                wrapper_code += f'def _{method_name}_wrapper(self, *args, **kwargs):\n'
                wrapper_code += f'    _apply_decorator_on_call({class_name}, \'{method_name}\', \'{class_name}\', \'{decorator_name}\')\n'
                wrapper_code += f'    return getattr(self, \'{method_name}\')(*args, **kwargs)\n'
                wrapper_code += f'{class_name}.{method_name} = _{method_name}_wrapper\n'
            
            content += apply_comment + wrapper_code
            
            return content
            
        except Exception as e:
            print(f"[WARNING] Ошибка применения отложенных декораторов для {class_name}: {e}")
            return content
    
    def _remove_circular_function_imports(self, content: str, category: str, component_name: str) -> str:
        """Удаление циклических импортов функций из utils.utils"""
        import re
        
        if not self.structure or 'functions' not in self.structure:
            return content
        
        function_names = [f['name'] for f in self.structure.get('functions', [])]
        
        # Проверяем все импорты из utils.utils
        for func_name in function_names:
            # Проверяем циклические зависимости
            if component_name and component_name in self.dependency_graph:
                if func_name in self.dependency_graph[component_name]:
                    # Есть циклическая зависимость - удаляем прямой импорт
                    # Удаляем импорт из строки вида "from utils.utils import track_class_activity"
                    import_pattern = re.compile(rf'from\s+utils\.utils\s+import\s+{re.escape(func_name)}\b')
                    content = import_pattern.sub(f'# Отложенный импорт для избежания циклических зависимостей\n# from utils.utils import {func_name}', content)
                    # Удаляем из списка импортов, если это часть многострочного импорта
                    import_pattern2 = re.compile(rf',\s*{re.escape(func_name)}\b')
                    content = import_pattern2.sub('', content)
                    import_pattern3 = re.compile(rf'\b{re.escape(func_name)}\s*,')
                    content = import_pattern3.sub('', content)
                    # Удаляем декораторы на уровне модуля - они будут применены при первом вызове метода
                    # Заменяем @track_class_activity('ClassName') на пустую строку
                    if func_name == 'track_class_activity':
                        pattern = re.compile(rf'^\s*@{re.escape(func_name)}\([^)]+\)\s*$', re.MULTILINE)
                        content = pattern.sub('', content)
                        # Удаляем пустые строки после удаления декораторов
                        lines = content.split('\n')
                        cleaned_lines = []
                        prev_empty = False
                        for line in lines:
                            if line.strip() == '':
                                if not prev_empty:
                                    cleaned_lines.append(line)
                                prev_empty = True
                            else:
                                cleaned_lines.append(line)
                                prev_empty = False
                        content = '\n'.join(cleaned_lines)
                    print(f"[REBUILD] Удален циклический импорт {func_name} из {component_name}")
        
            return content
    
    def _replace_with_lazy_import(self, content: str, class_name: str, category: str, module_name: str) -> str:
        """
        Замена использования класса на отложенный импорт внутри функций/методов
        
        Args:
            content: Исходный код
            class_name: Имя класса для отложенного импорта
            category: Категория модуля
            module_name: Имя модуля
            
        Returns:
            str: Код с замененными использованиями на отложенные импорты
        """
        import re
        
        # Создаем функцию для отложенного импорта
        lazy_import_func = f'''
def _get_{class_name.lower()}():
    """Отложенный импорт для избежания циклических зависимостей"""
    from {category}.{module_name} import {class_name}
    return {class_name}
'''
        
        # Проверяем, есть ли уже функция-геттер
        getter_name = f'_get_{class_name.lower()}'
        if getter_name in content:
            # Функция-геттер уже есть, не добавляем
            pass
        else:
            # Добавляем функцию отложенного импорта в начало модуля (после импортов)
            lines = content.split('\n')
            insert_pos = 0
            # Ищем конец импортов
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Пропускаем комментарии и пустые строки
                if stripped.startswith('#') or not stripped:
                    continue
                # Ищем начало класса или функции
                if stripped.startswith('class ') or (stripped.startswith('def ') and not stripped.startswith('def _get_')):
                    insert_pos = i
                    break
            
            if insert_pos > 0:
                lines.insert(insert_pos, lazy_import_func)
                content = '\n'.join(lines)
        
        # Заменяем импорт на уровне модуля на комментарий
        import_pattern = re.compile(rf'from\s+{re.escape(category)}\.{re.escape(module_name)}\s+import\s+{re.escape(class_name)}\b')
        content = import_pattern.sub(f'# Отложенный импорт для избежания циклических зависимостей\n# from {category}.{module_name} import {class_name}', content)
        
        # Заменяем использование класса на вызов функции отложенного импорта
        # Ищем паттерны: ClassName( или ClassName.
        pattern1 = re.compile(rf'\b{class_name}\(')
        pattern2 = re.compile(rf'\b{class_name}\.')
        pattern3 = re.compile(rf'@\s*{re.escape(class_name)}\b')  # Для декораторов
        
        # Заменяем все использования класса
        lines = content.split('\n')
        result_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Пропускаем строки с комментариями и docstrings
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                result_lines.append(line)
                continue
            
            # Заменяем использование класса на отложенный импорт
            if class_name in line:
                # Заменяем ClassName( на _get_classname()(
                line = pattern1.sub(f'{getter_name}()(', line)
                # Заменяем ClassName. на _get_classname().
                line = pattern2.sub(f'{getter_name}().', line)
                # Заменяем @ClassName на @_get_classname()() для декораторов
                line = pattern3.sub(f'@{getter_name}()()', line)
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _would_create_cycle(self, from_class: str, to_class: str) -> bool:
        """
        Проверка, создаст ли добавление импорта циклическую зависимость
        
        Args:
            from_class: Класс, который хочет импортировать
            to_class: Класс, который импортируется
            
        Returns:
            bool: True если создаст циклическую зависимость
        """
        if not from_class or not to_class:
            return False
        
        # Проверяем, есть ли путь от to_class к from_class (цикл)
        visited = set()
        
        def has_path_to(start: str, target: str) -> bool:
            """Проверка наличия пути от start к target"""
            if start == target:
                return True
            if start in visited:
                return False
            visited.add(start)
            
            # Проверяем зависимости start
            for dep in self.dependency_graph.get(start, []):
                if has_path_to(dep, target):
                    return True
            return False
        
        # Если есть путь от to_class к from_class, то добавление импорта создаст цикл
        return has_path_to(to_class, from_class)
    
    def _replace_config_imports(self, content: str) -> str:
        """
        Замена импортов из config на imports (config.py больше не создается)
        
        Args:
            content: Исходный код
            
        Returns:
            str: Код с замененными импортами
        """
        import re
        
        # Заменяем from config import ... на from imports import ...
        pattern = re.compile(r'from\s+config\s+import\s+(\w+)')
        content = pattern.sub(r'from imports import \1', content)
        
        # Заменяем import config на from imports import * (если нужно)
        # Но обычно это не используется, поэтому просто удаляем
        pattern_import = re.compile(r'^import\s+config\b', re.MULTILINE)
        content = pattern_import.sub('', content)
        
        return content


def rebuild_file(source_file: str, target_dir: Optional[str] = None) -> bool:
    """
    Удобная функция для разборки файла на модули
    
    Args:
        source_file: Путь к исходному Python файлу
        target_dir: Директория для модулей (опционально)
        
    Returns:
        bool: True если разборка успешна, False если ошибка
    """
    rebuilder = Rebuilder(source_file, target_dir)
    return rebuilder.rebuild()

