#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FSA-ProjectBuilder - Конфигурация проекта
Версия: 0.1.0
Компания: ООО "НПА Вира-Реалтайм"
"""

# Версия приложения
APP_VERSION = "0.1.0"
APP_NAME = "FSA-ProjectBuilder"
APP_DESCRIPTION = "Универсальный инструмент для модуляризации, сборки и создания дистрибутивов Python проектов"

# Настройки по умолчанию
DEFAULT_MODULES_DIR = "modules"
DEFAULT_BUILT_SUFFIX = "_built"
DEFAULT_METADATA_DIR = ".metadata"

# Настройки разборки
REBUILD_CONFIG = {
    "preserve_comments": True,
    "preserve_docstrings": True,
    "preserve_formatting": True,
    "auto_generate_init": True,
    "create_metadata": True
}

# Настройки сборки
BUILD_CONFIG = {
    "cleanup": {
        "remove_empty_lines": False,
        "max_empty_lines": 2,
        "remove_trailing_whitespace": False,
        "normalize_indentation": False
    },
    "imports": {
        "remove_unused": False,
        "group_imports": False,
        "sort_imports": False,
        "import_order": ["standard", "third_party", "local"]
    },
    "reorganization": {
        "sort_classes": False,
        "sort_method": "category",  # "alphabetical", "category", "dependency", "size"
        "group_related": False,
        "add_separators": False
    },
    "optimization": {
        "find_duplicates": False,
        "extract_constants": False,
        "improve_docstrings": False
    }
}

# Настройки дистрибутивов
DIST_CONFIG = {
    "default_tool": "pyinstaller",  # "pyinstaller", "cx_freeze", "nuitka"
    "include_icons": True,
    "include_resources": True,
    "optimize_size": True,
    "sign_code": False
}

# Поддерживаемые инструменты для дистрибутивов
DISTRIBUTOR_TOOLS = {
    "pyinstaller": {
        "name": "PyInstaller",
        "install": "pip install pyinstaller",
        "supported_platforms": ["windows", "linux", "macos"]
    },
    "cx_freeze": {
        "name": "cx_Freeze",
        "install": "pip install cx_Freeze",
        "supported_platforms": ["windows", "linux", "macos"]
    },
    "nuitka": {
        "name": "Nuitka",
        "install": "pip install nuitka",
        "supported_platforms": ["windows", "linux", "macos"]
    }
}

# Категории модулей
MODULE_CATEGORIES = {
    "config": "Конфигурация",
    "handlers": "Обработчики",
    "managers": "Менеджеры",
    "gui": "Графический интерфейс",
    "utils": "Утилиты",
    "models": "Модели данных",
    "analyzers": "Анализаторы",
    "logging": "Логирование",
    "core": "Ядро системы"
}

