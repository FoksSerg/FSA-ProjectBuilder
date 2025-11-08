# Использование FSA-ProjectBuilder

## Быстрый старт

### GUI режим (рекомендуется)

```bash
python main.py
```

GUI интерфейс предоставляет:
- Выбор проекта и главного файла
- Визуализацию структуры проекта
- Предпросмотр разборки и сборки
- Выполнение операций с логированием
- Просмотр структуры проекта в дереве

### Консольный режим

#### Разборка проекта

```bash
# Разборка файла на модули
python rebuild.py --project /path/to/project --file main.py

# С указанием целевой директории
python rebuild.py --project /path/to/project --file main.py --target /path/to/modules
```

#### Сборка проекта

```bash
# Сборка модулей в один файл
python build.py --project /path/to/project

# С указанием директории модулей
python build.py --modules-dir /path/to/modules

# С указанием выходного файла
python build.py --modules-dir /path/to/modules --output /path/to/output.py

# С применением очистки кода
python build.py --modules-dir /path/to/modules --cleanup
```

#### Создание дистрибутива

```bash
# Создание дистрибутива (автоматический выбор инструмента)
python dist.py --project /path/to/project --main main.py

# С указанием инструмента
python dist.py --project /path/to/project --main main.py --tool pyinstaller

# Создание одного исполняемого файла
python dist.py --project /path/to/project --main main.py --onefile

# С иконкой
python dist.py --project /path/to/project --main main.py --icon icon.ico
```

## Примеры

### Пример 1: Разборка проекта

```bash
# Разобрать main.py на модули
python rebuild.py --project /path/to/project --file main.py

# Результат: создается директория modules/ с разобранными модулями
# Структура:
# modules/
#   ├── config.py          # Константы
#   ├── imports.py         # Импорты
#   ├── core/              # Основные классы
#   ├── handlers/          # Обработчики
#   ├── utils/             # Утилиты
#   └── .metadata/         # Метаданные
```

### Пример 2: Сборка проекта

```bash
# Собрать модули обратно в один файл
python build.py --project /path/to/project

# Или с указанием директории модулей
python build.py --modules-dir /path/to/project/modules --output main_built.py

# Результат: создается файл main_built.py с объединенным кодом
```

### Пример 3: Самосборка проекта

```bash
# Разобрать сам проект FSA-ProjectBuilder
python rebuild.py --project . --file main.py

# Собрать модули обратно
python build.py --project .
```

### Пример 4: Создание дистрибутива

```bash
# Создать Windows .exe файл с PyInstaller
python dist.py --project /path/to/project --main main.py --tool pyinstaller --onefile

# Создать macOS .app с cx_Freeze
python dist.py --project /path/to/project --main main.py --tool cxfreeze --windowed

# Создать Linux исполняемый файл с Nuitka
python dist.py --project /path/to/project --main main.py --tool nuitka --onefile
```

## Настройки

Настройки проекта хранятся в `config.py`:

- **REBUILD_CONFIG** - настройки разборки (сохранение комментариев, docstrings и т.д.)
- **BUILD_CONFIG** - настройки сборки (очистка, оптимизация импортов, реорганизация)
- **DIST_CONFIG** - настройки дистрибутивов (инструмент по умолчанию, опции)
- **MODULE_CATEGORIES** - категории модулей для автоматической категоризации

## Категории модулей

При разборке файла компоненты автоматически распределяются по категориям:

- **config** - Конфигурация и константы
- **handlers** - Обработчики событий
- **managers** - Менеджеры и мониторы
- **gui** - Графический интерфейс
- **utils** - Утилиты и вспомогательные функции
- **models** - Модели данных
- **analyzers** - Анализаторы кода
- **logging** - Логирование
- **core** - Ядро системы (по умолчанию)

## Логирование

Все операции логируются в файлы в директории `Logs/`:
- Формат имени: `fsa_projectbuilder_YYYYMMDD_HHMMSS.log`
- Содержит подробную информацию о всех операциях
- Уровни логирования: DEBUG, INFO, WARNING, ERROR

