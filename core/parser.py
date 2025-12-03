#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Парсер Python кода
Парсинг Python файлов с помощью AST для извлечения структуры
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
import ast
import os
from typing import Dict, List, Optional, Tuple, Any


class CodeParser:
    """Парсер Python кода для извлечения структуры"""
    
    def __init__(self, file_path: str):
        """
        Инициализация парсера
        
        Args:
            file_path: Путь к Python файлу для парсинга
        """
        self.file_path = file_path
        self.ast_tree = None
        self.source_code = None
        self.lines = []
        
    def parse(self) -> bool:
        """
        Парсинг файла в AST
        
        Returns:
            bool: True если парсинг успешен, False если ошибка
        """
        try:
            # Читаем файл
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.source_code = f.read()
                self.lines = self.source_code.split('\n')
            
            # Парсим в AST
            self.ast_tree = ast.parse(self.source_code, filename=self.file_path)
            return True
            
        except SyntaxError as e:
            print(f"[ERROR] Синтаксическая ошибка в файле {self.file_path}: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Ошибка парсинга файла {self.file_path}: {e}")
            return False
    
    def get_imports(self) -> List[Dict[str, Any]]:
        """
        Извлечение всех импортов из файла
        
        Returns:
            List[Dict]: Список импортов с информацией
        """
        imports = []
        
        if not self.ast_tree:
            return imports
        
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append({
                        'type': 'from_import',
                        'module': module,
                        'name': alias.name,
                        'alias': alias.asname,
                        'line': node.lineno
                    })
        
        return imports
    
    def get_classes(self) -> List[Dict[str, Any]]:
        """
        Извлечение классов верхнего уровня
        ВАЖНО: Используем tree.body, а не ast.walk()!
        AST гарантирует точные границы через lineno и end_lineno
        """
        classes = []
        
        if not self.ast_tree:
            return classes
        
        # Ищем классы ТОЛЬКО верхнего уровня в tree.body
        # AST гарантирует, что tree.body содержит только верхний уровень
        for node in self.ast_tree.body:
            if isinstance(node, ast.ClassDef):
                # AST знает точные границы!
                start_line = node.lineno
                end_line = getattr(node, 'end_lineno', start_line)
                
                # Получаем базовые классы
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(self._get_attr_name(base))
                
                # Получаем docstring
                docstring = ast.get_docstring(node)
                
                # Получаем методы класса
                methods = self._get_class_methods(node)
                
                # Извлекаем код ТОЧНО по границам AST
                # end_line уже 1-based, start_line тоже 1-based
                # Для среза нужен 0-based, поэтому start_line - 1
                code = '\n'.join(self.lines[start_line - 1:end_line]) if self.lines else ''
                
                classes.append({
                    'name': node.name,
                    'bases': bases,
                    'docstring': docstring,
                    'methods': methods,
                    'start_line': start_line,
                    'end_line': end_line,
                    'code': code,
                    'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
                })
        
        return classes
    
    def get_functions(self) -> List[Dict[str, Any]]:
        """
        Извлечение всех функций из файла (не методов классов)
        
        Returns:
            List[Dict]: Список функций с информацией
        """
        functions = []
        
        if not self.ast_tree:
            return functions
        
        # Собираем все методы классов для исключения
        class_methods = set()
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        class_methods.add(item.name)
        
        # Ищем функции верхнего уровня (только в корне модуля, не внутри классов)
        for node in self.ast_tree.body:
            if isinstance(node, ast.FunctionDef) and node.name not in class_methods:
                docstring = ast.get_docstring(node)
                
                # Получаем аргументы
                args = [arg.arg for arg in node.args.args]
                
                start_line = node.lineno
                # Используем end_lineno если доступен, иначе вычисляем по AST
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    end_line = node.end_lineno
                else:
                    # Если end_lineno недоступен, используем последнюю строку тела функции
                    end_line = start_line
                    if node.body:
                        last_node = node.body[-1]
                        if hasattr(last_node, 'end_lineno') and last_node.end_lineno:
                            end_line = last_node.end_lineno
                        elif hasattr(last_node, 'lineno'):
                            end_line = last_node.lineno
                
                # Извлекаем код функции (end_line уже 1-based, поэтому используем end_line без +1)
                code = '\n'.join(self.lines[start_line - 1:end_line]) if self.lines else ''
                
                functions.append({
                    'name': node.name,
                    'args': args,
                    'docstring': docstring,
                    'start_line': start_line,
                    'end_line': end_line,
                    'code': code,
                    'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
                })
        
        return functions
    
    def get_constants(self) -> List[Dict[str, Any]]:
        """
        Извлечение констант (переменных верхнего уровня)
        ВАЖНО: Используем AST напрямую - он знает точные границы!
        AST гарантирует, что tree.body содержит только верхний уровень
        
        Returns:
            List[Dict]: Список констант с информацией
        """
        constants = []
        
        if not self.ast_tree:
            return constants
        
        # Ищем переменные верхнего уровня ТОЛЬКО в tree.body
        # AST гарантирует, что tree.body содержит только верхний уровень
        for node in self.ast_tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # AST знает точные границы!
                        start_line = node.lineno
                        end_line = getattr(node, 'end_lineno', start_line)
                        
                        # Извлекаем код ТОЧНО по границам AST
                        if self.lines and start_line <= len(self.lines):
                            # end_line уже 1-based, start_line тоже 1-based
                            # Для среза нужен 0-based, поэтому start_line - 1
                            # end_line уже 1-based, но для среза нужно включить, поэтому просто end_line
                            assignment_code = '\n'.join(self.lines[start_line - 1:end_line])
                            
                            # ВАЖНО: Проверяем, что константа верхнего уровня
                            # Если константа верхнего уровня, она НЕ должна иметь отступов
                            # Проверяем первую строку кода (не пустую и не комментарий)
                            code_lines = assignment_code.split('\n')
                            first_code_line = None
                            for line in code_lines:
                                stripped = line.strip()
                                if stripped and not stripped.startswith('#'):
                                    first_code_line = line
                                    break
                            
                            # Если первая строка кода имеет отступ - это не верхний уровень
                            if first_code_line and first_code_line[0] in [' ', '\t']:
                                # Это не верхний уровень - пропускаем
                                continue
                        else:
                            # Если не удалось получить код, пропускаем
                            continue
                        
                        constants.append({
                            'name': target.id,
                            'line': start_line,
                            'end_line': end_line,  # Сохраняем end_line для проверки покрытия!
                            'code': assignment_code
                        })
        
        return constants
    
    def get_usages(self, component_name: str, code: str) -> List[str]:
        """
        Анализ использований компонента (класса/функции/константы) в коде
        
        Args:
            component_name: Имя компонента для поиска
            code: Код для анализа
            
        Returns:
            List[str]: Список использованных компонентов
        """
        if not code:
            return []
        
        try:
            # Парсим код в AST
            tree = ast.parse(code)
            usages = []
            
            # Собираем все имена в коде
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    # Проверяем, что это не присваивание (ctx=Store)
                    if isinstance(node.ctx, ast.Load):
                        usages.append(node.id)
                elif isinstance(node, ast.Attribute):
                    # Обрабатываем атрибуты (например, Class.method)
                    attr_name = self._get_attr_name(node)
                    # Извлекаем базовое имя (до первой точки)
                    if '.' in attr_name:
                        base_name = attr_name.split('.')[0]
                        usages.append(base_name)
            
            # Фильтруем только уникальные использования
            return list(set(usages))
        except Exception as e:
            # Если не удалось распарсить, возвращаем пустой список
            return []
    
    def get_all_usages(self) -> Dict[str, List[str]]:
        """
        Анализ всех использований классов, функций и констант в коде
        
        Returns:
            Dict[str, List[str]]: Словарь {component_name: [used_components]}
        """
        if not self.ast_tree:
            return {}
        
        # Собираем все имена компонентов
        all_components = {}
        for cls in self.get_classes():
            all_components[cls['name']] = cls['code']
        for func in self.get_functions():
            all_components[func['name']] = func['code']
        for const in self.get_constants():
            all_components[const['name']] = const.get('code', '')
        
        # Анализируем использования для каждого компонента
        usages = {}
        for component_name, component_code in all_components.items():
            component_usages = self.get_usages(component_name, component_code)
            # Фильтруем только те использования, которые есть в списке компонентов
            filtered_usages = [u for u in component_usages if u in all_components and u != component_name]
            if filtered_usages:
                usages[component_name] = filtered_usages
        
        return usages
    
    def get_structure(self) -> Dict[str, Any]:
        """
        Получение полной структуры файла
        
        Returns:
            Dict: Полная структура файла
        """
        return {
            'file_path': self.file_path,
            'file_name': os.path.basename(self.file_path),
            'imports': self.get_imports(),
            'classes': self.get_classes(),
            'functions': self.get_functions(),
            'constants': self.get_constants(),
            'usages': self.get_all_usages(),  # Добавляем анализ использований
            'total_lines': len(self.lines) if self.lines else 0
        }
    
    def _get_class_methods(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Получение методов класса"""
        methods = []
        
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                docstring = ast.get_docstring(item)
                args = [arg.arg for arg in item.args.args]
                
                methods.append({
                    'name': item.name,
                    'args': args,
                    'docstring': docstring,
                    'line': item.lineno,
                    'decorators': [self._get_decorator_name(d) for d in item.decorator_list]
                })
        
        return methods
    
    def _get_parent(self, node: ast.AST) -> Optional[ast.AST]:
        """Получение родительского узла (упрощенная версия)"""
        # Для полной реализации нужно использовать ast.NodeVisitor
        # Здесь упрощенная версия
        return None
    
    def _get_attr_name(self, node: ast.Attribute) -> str:
        """Получение полного имени атрибута"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attr_name(node.value)}.{node.attr}"
        return node.attr
    
    def _get_decorator_name(self, node: ast.AST) -> str:
        """Получение имени декоратора"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_attr_name(node)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return self._get_attr_name(node.func)
        return str(node)
    
    def _get_value_repr(self, node: ast.AST) -> str:
        """Получение строкового представления значения"""
        if isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Num):
            return str(node.n)
        return str(node)


def parse_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Удобная функция для парсинга файла
    
    Args:
        file_path: Путь к Python файлу
        
    Returns:
        Dict: Структура файла или None при ошибке
    """
    parser = CodeParser(file_path)
    if parser.parse():
        return parser.get_structure()
    return None

