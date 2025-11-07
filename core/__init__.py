"""
FSA-ProjectBuilder - Ядро системы
Модули для парсинга, сборки и разборки проектов
"""

__version__ = "0.1.0"

# Экспорт основных классов
from .parser import CodeParser, parse_file
from .dependency_resolver import DependencyResolver
from .rebuilder import Rebuilder, rebuild_file
from .builder import Builder, build_modules

__all__ = [
    'CodeParser',
    'parse_file',
    'DependencyResolver',
    'Rebuilder',
    'rebuild_file',
    'Builder',
    'build_modules'
]
