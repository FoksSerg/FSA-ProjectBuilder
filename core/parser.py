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
        Извлечение всех классов из файла
        
        Returns:
            List[Dict]: Список классов с информацией
        """
        classes = []
        
        if not self.ast_tree:
            return classes
        
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.ClassDef):
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
                
                # Получаем строки кода класса
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                
                classes.append({
                    'name': node.name,
                    'bases': bases,
                    'docstring': docstring,
                    'methods': methods,
                    'start_line': start_line,
                    'end_line': end_line,
                    'code': '\n'.join(self.lines[start_line - 1:end_line]) if self.lines else '',
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
        
        # Ищем функции верхнего уровня
        for node in ast.walk(self.ast_tree):
            if isinstance(node, ast.FunctionDef) and node.name not in class_methods:
                # Проверяем, что функция не внутри класса
                parent = self._get_parent(node)
                if not isinstance(parent, ast.ClassDef):
                    docstring = ast.get_docstring(node)
                    
                    # Получаем аргументы
                    args = [arg.arg for arg in node.args.args]
                    
                    start_line = node.lineno
                    end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                    
                    functions.append({
                        'name': node.name,
                        'args': args,
                        'docstring': docstring,
                        'start_line': start_line,
                        'end_line': end_line,
                        'code': '\n'.join(self.lines[start_line - 1:end_line]) if self.lines else '',
                        'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
                    })
        
        return functions
    
    def get_constants(self) -> List[Dict[str, Any]]:
        """
        Извлечение констант (переменных верхнего уровня)
        
        Returns:
            List[Dict]: Список констант с информацией
        """
        constants = []
        
        if not self.ast_tree:
            return constants
        
        # Ищем переменные верхнего уровня
        for node in self.ast_tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Получаем исходный код присваивания полностью
                        start_line = node.lineno - 1  # AST использует 1-based индексацию
                        
                        # Определяем конец присваивания
                        if hasattr(node, 'end_lineno') and node.end_lineno:
                            end_line = node.end_lineno  # end_lineno уже 1-based
                        else:
                            # Для однострочных присваиваний
                            end_line = node.lineno
                        
                        # Извлекаем код из исходного файла (lines использует 0-based индексацию)
                        if self.lines and start_line < len(self.lines):
                            # end_line уже 1-based (например, 10 означает строку 10)
                            # start_line уже 0-based (node.lineno - 1, например, 9 для строки 10)
                            # Для среза [start:end] end не включается, поэтому нужно end_line+1 (1-based -> 0-based)
                            # end_line (1-based) = end_line (0-based для среза), но нужно включить, поэтому +1
                            assignment_code = '\n'.join(self.lines[start_line:end_line+1])
                            
                            # Убираем лишние пробелы в начале, но сохраняем структуру
                            code_lines = assignment_code.split('\n')
                            if code_lines:
                                # Находим минимальный отступ
                                non_empty_lines = [l for l in code_lines if l.strip()]
                                if non_empty_lines:
                                    min_indent = min(len(l) - len(l.lstrip()) for l in non_empty_lines)
                                    # Убираем минимальный отступ
                                    assignment_code = '\n'.join(l[min_indent:] if len(l) > min_indent else l for l in code_lines)
                        else:
                            # Если не удалось получить код, пытаемся извлечь значение
                            value_part = self._get_value_repr(node.value)
                            assignment_code = f"{target.id} = {value_part}"
                        
                        constants.append({
                            'name': target.id,
                            'value': assignment_code,  # Сохраняем полный код присваивания
                            'line': node.lineno,
                            'code': assignment_code  # Сохраняем код
                        })
        
        return constants
    
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

