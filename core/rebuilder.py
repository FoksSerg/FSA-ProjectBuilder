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
from typing import Dict, List, Optional, Any
from .parser import CodeParser, parse_file
from .dependency_resolver import DependencyResolver
from config import MODULE_CATEGORIES, DEFAULT_MODULES_DIR, DEFAULT_METADATA_DIR


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
        
        print(f"[SUCCESS] Разборка завершена успешно!")
        print(f"[INFO] Модули созданы в: {self.target_dir}")
        return True
    
    def _create_structure(self) -> bool:
        """Создание структуры папок"""
        try:
            # Создаем основную директорию
            os.makedirs(self.target_dir, exist_ok=True)
            
            # Создаем директорию для метаданных
            os.makedirs(self.metadata_dir, exist_ok=True)
            
            # Создаем директории для категорий модулей
            for category in MODULE_CATEGORIES.keys():
                category_dir = os.path.join(self.target_dir, category)
                os.makedirs(category_dir, exist_ok=True)
            
            return True
        except Exception as e:
            print(f"[ERROR] Ошибка создания структуры: {e}")
            return False
    
    def _distribute_components(self) -> bool:
        """Распределение компонентов по модулям"""
        try:
            # Распределяем классы
            for cls in self.structure['classes']:
                category = self._determine_category(cls)
                module_path = self._create_module_file(category, cls['name'], cls['code'])
                if module_path:
                    self.module_mapping[cls['name']] = module_path
            
            # Распределяем функции верхнего уровня
            utils_functions = []
            for func in self.structure['functions']:
                utils_functions.append(func)
            
            if utils_functions:
                # Создаем utils.py для функций верхнего уровня
                utils_code = self._generate_utils_code(utils_functions)
                utils_path = os.path.join(self.target_dir, 'utils', 'utils.py')
                os.makedirs(os.path.dirname(utils_path), exist_ok=True)
                with open(utils_path, 'w', encoding='utf-8') as f:
                    f.write(utils_code)
            
            # Создаем config.py для констант
            constants = self.structure.get('constants', [])
            if constants:
                config_code = self._generate_config_code(constants)
                config_path = os.path.join(self.target_dir, 'config.py')
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(config_code)
            
            # Создаем imports.py для импортов верхнего уровня
            imports = self.structure.get('imports', [])
            if imports:
                imports_code = self._generate_imports_code(imports)
                imports_path = os.path.join(self.target_dir, 'imports.py')
                with open(imports_path, 'w', encoding='utf-8') as f:
                    f.write(imports_code)
            
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
            return 'logging'
        else:
            # По умолчанию в core
            return 'core'
    
    def _create_module_file(self, category: str, class_name: str, code: str) -> Optional[str]:
        """
        Создание файла модуля для класса
        
        Args:
            category: Категория модуля
            class_name: Имя класса
            code: Код класса
            
        Returns:
            str: Путь к созданному файлу или None
        """
        try:
            # Создаем имя файла из имени класса
            module_name = self._class_name_to_module_name(class_name)
            module_path = os.path.join(self.target_dir, category, f"{module_name}.py")
            
            # Добавляем заголовок файла
            header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически сгенерированный модуль из {self.source_name}
Класс: {class_name}
"""

'''
            
            # Записываем файл
            with open(module_path, 'w', encoding='utf-8') as f:
                f.write(header)
                f.write(code)
            
            print(f"[REBUILD] Создан модуль: {module_path}")
            return module_path
            
        except Exception as e:
            print(f"[ERROR] Ошибка создания модуля {class_name}: {e}")
            return None
    
    def _class_name_to_module_name(self, class_name: str) -> str:
        """Преобразование имени класса в имя модуля"""
        # CamelCase -> snake_case
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _generate_utils_code(self, functions: List[Dict[str, Any]]) -> str:
        """Генерация кода для utils.py"""
        header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически сгенерированный модуль из {self.source_name}
Функции верхнего уровня
"""

'''
        code = header
        
        for func in functions:
            code += func.get('code', '') + '\n\n'
        
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
    
    def _generate_imports_code(self, imports: List[Dict[str, Any]]) -> str:
        """Генерация кода для imports.py"""
        header = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматически сгенерированный модуль из {self.source_name}
Импорты верхнего уровня
"""

'''
        code = header
        
        # Группируем импорты
        import_statements = []
        from_imports = {}
        
        for imp in imports:
            if imp['type'] == 'import':
                alias = f" as {imp['alias']}" if imp.get('alias') else ""
                import_statements.append(f"import {imp['module']}{alias}")
            elif imp['type'] == 'from_import':
                module = imp['module']
                if module not in from_imports:
                    from_imports[module] = []
                name = imp['name']
                alias = f" as {imp['alias']}" if imp.get('alias') else ""
                from_imports[module].append(f"{name}{alias}")
        
        # Добавляем import
        for stmt in sorted(set(import_statements)):
            code += stmt + '\n'
        
        # Добавляем from ... import
        for module in sorted(from_imports.keys()):
            names = ', '.join(from_imports[module])
            code += f"from {module} import {names}\n"
        
        return code
    
    def _generate_init_files(self) -> bool:
        """Генерация __init__.py файлов"""
        try:
            # Генерируем __init__.py для каждой категории
            for category in MODULE_CATEGORIES.keys():
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
        for module in sorted(modules):
            code += f"from .{module} import *\n"
        
        return code
    
    def _generate_main_init_code(self) -> str:
        """Генерация главного __init__.py"""
        code = f'''"""
Автоматически сгенерированные модули из {self.source_name}
"""

'''
        # Импортируем из всех категорий
        for category in MODULE_CATEGORIES.keys():
            category_dir = os.path.join(self.target_dir, category)
            if os.path.exists(category_dir):
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

