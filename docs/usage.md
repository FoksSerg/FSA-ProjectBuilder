# Использование FSA-ProjectBuilder

## Быстрый старт

### GUI режим

```bash
python main.py
```

### Консольный режим

#### Разборка проекта

```bash
python rebuild.py --project /path/to/project --file main.py
```

#### Сборка проекта

```bash
python build.py --project /path/to/project
```

#### Создание дистрибутива

```bash
python dist.py --project /path/to/project --format exe
```

## Примеры

### Пример 1: Разборка проекта

```bash
# Разобрать astra_automation.py на модули
python rebuild.py --project /Volumes/FSA-PRJ/Project/FSA-AstraInstall --file astra_automation.py
```

### Пример 2: Сборка проекта

```bash
# Собрать модули обратно в один файл
python build.py --project /Volumes/FSA-PRJ/Project/FSA-AstraInstall
```

### Пример 3: Создание дистрибутива

```bash
# Создать Windows .exe файл
python dist.py --project /Volumes/FSA-PRJ/Project/FSA-AstraInstall --format exe --tool pyinstaller
```

## Настройки

Настройки проекта хранятся в `.projectbuilder/config.json`

