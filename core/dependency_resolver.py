#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Разрешение зависимостей
Определение зависимостей между классами и модулями
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

from __future__ import print_function
from typing import Dict, List, Set, Optional, Tuple, Any


class DependencyResolver:
    """Разрешение зависимостей между компонентами"""
    
    def __init__(self, structure: Dict[str, Any]):
        """
        Инициализация разрешителя зависимостей
        
        Args:
            structure: Структура файла от парсера
        """
        self.structure = structure
        self.dependencies = {}  # {component_name: [dependencies]}
        self.dependents = {}    # {component_name: [dependents]}
        
    def resolve(self) -> Dict[str, List[str]]:
        """
        Разрешение всех зависимостей
        
        Returns:
            Dict: Словарь зависимостей {component: [dependencies]}
        """
        self._analyze_classes()
        self._analyze_functions()
        self._build_dependency_graph()
        
        return self.dependencies
    
    def get_load_order(self) -> List[str]:
        """
        Получение порядка загрузки компонентов (топологическая сортировка)
        
        Returns:
            List: Порядок загрузки компонентов
        """
        # Собираем все компоненты
        all_components = set()
        for deps in self.dependencies.values():
            all_components.update(deps)
        all_components.update(self.dependencies.keys())
        
        # Топологическая сортировка
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(component: str):
            if component in temp_visited:
                # Циклическая зависимость
                return
            if component in visited:
                return
            
            temp_visited.add(component)
            
            # Посещаем зависимости
            for dep in self.dependencies.get(component, []):
                if dep in all_components:
                    visit(dep)
            
            temp_visited.remove(component)
            visited.add(component)
            result.append(component)
        
        for component in all_components:
            if component not in visited:
                visit(component)
        
        return result
    
    def _analyze_classes(self):
        """Анализ зависимостей классов"""
        for cls in self.structure.get('classes', []):
            cls_name = cls['name']
            dependencies = set()
            
            # Зависимости от базовых классов
            for base in cls.get('bases', []):
                dependencies.add(base)
            
            # Зависимости от импортов (упрощенно)
            # В будущем можно анализировать использование в методах
            
            self.dependencies[cls_name] = list(dependencies)
    
    def _analyze_functions(self):
        """Анализ зависимостей функций"""
        for func in self.structure.get('functions', []):
            func_name = func['name']
            dependencies = set()
            
            # Анализ аргументов и использования (упрощенно)
            # В будущем можно анализировать тело функции
            
            self.dependencies[func_name] = list(dependencies)
    
    def _build_dependency_graph(self):
        """Построение графа зависимостей"""
        # Строим обратный граф (dependents)
        for component, deps in self.dependencies.items():
            for dep in deps:
                if dep not in self.dependents:
                    self.dependents[dep] = []
                self.dependents[dep].append(component)
    
    def detect_cycles(self) -> List[List[str]]:
        """
        Обнаружение циклических зависимостей
        
        Returns:
            List: Список циклов (каждый цикл - список компонентов)
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(component: str):
            if component in rec_stack:
                # Найден цикл
                cycle_start = path.index(component)
                cycle = path[cycle_start:] + [component]
                cycles.append(cycle)
                return
            
            if component in visited:
                return
            
            visited.add(component)
            rec_stack.add(component)
            path.append(component)
            
            for dep in self.dependencies.get(component, []):
                dfs(dep)
            
            rec_stack.remove(component)
            path.pop()
        
        for component in self.dependencies.keys():
            if component not in visited:
                dfs(component)
        
        return cycles

