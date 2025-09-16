"""
Модуль с настройками проекта и вспомогательными функциями.
"""

import typing
import types

import os
import json
import logging

import importlib

### Настройки скриптов

NX_FOLDER = os.getenv("UGII_BASE_DIR", "")
"""Директория установки NX."""

NXOPEN_CPP_FOLDER = os.path.join(NX_FOLDER, "UGOPEN", "NXOpen")  # type: ignore
"""Директория c заголовочными файлами (`*.hxx`) для NXOpen C++."""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
"""Рабочая директория скриптов."""

LOGFILE = os.path.join(BASE_DIR, "nxopen-generate-pyi.log")
"""Путь к log-файлу проекта."""

PYI_NXOPEN_DIR = f"{BASE_DIR}"
"""Путь к родительской директории для папки `NXOpen`, в которой будут создаваться pyi-файлы."""

CLASSES_HIERARCHY_JSON_FILE = os.path.join(BASE_DIR, "classes_hierarchy.json")
"""Путь к JSON-файлу с информацией о наследовании классов NXOpen."""

MODULES_NAMESPACES_JSON_FILE = os.path.join(BASE_DIR, "modules_namespaces.json")
"""Путь к JSON-файлу с информацией о пространсвах имен модулей NXOpen."""


### Константы

MODULES_NAMES = [
    "NXOpen",
    "NXOpen.Annotations",
    "NXOpen.Assemblies",
    "NXOpen.BlockStyler",
    "NXOpen.BodyDes",
    "NXOpen.CAE",
    "NXOpen.CallbackTestNamespace",
    "NXOpen.CAM",
    "NXOpen.Diagramming",
    "NXOpen.DiagrammingLibraryAuthor",
    "NXOpen.Die",
    "NXOpen.Display",
    "NXOpen.DMU",
    "NXOpen.Drafting",
    "NXOpen.Drawings",
    "NXOpen.Facet",
    "NXOpen.Features",
    "NXOpen.Fields",
    "NXOpen.Formboard",
    "NXOpen.Gateway",
    "NXOpen.GeometricAnalysis",
    "NXOpen.GeometricUtilities",
    "NXOpen.Issue",
    "NXOpen.JamTestNamespace",
    "NXOpen.Layer",
    "NXOpen.Layout2d",
    "NXOpen.Markup",
    "NXOpen.MechanicalRouting",
    "NXOpen.Mechatronics",
    "NXOpen.MenuBar",
    "NXOpen.mfgviewmaker",
    "NXOpen.ModlDirect",
    "NXOpen.ModlUtils",
    "NXOpen.Motion",
    "NXOpen.Newapp",
    "NXOpen.OpenXml",
    "NXOpen.Optimization",
    "NXOpen.Options",
    "NXOpen.PartFamily",
    "NXOpen.PDM",
    "NXOpen.PhysMat",
    "NXOpen.PID",
    "NXOpen.Placement",
    "NXOpen.PLAS",
    "NXOpen.Positioning",
    "NXOpen.Preferences",
    "NXOpen.Report",
    "NXOpen.Routing",
    "NXOpen.ShapeSearch",
    "NXOpen.SheetMetal",
    "NXOpen.ShipDesign",
    "NXOpen.SIM",
    "NXOpen.Tooling",
    "NXOpen.UF",
    "NXOpen.UIStyler",
    "NXOpen.UserDefinedObjects",
    "NXOpen.Validate",
    "NXOpen.VisualReporting",
    "NXOpen.Weld",
]
"""Названия модулей, которые подлежат импорту в этом журнале."""



### log-файл

# Следует вызвать для модуля, в котором следует вести log-файл:
#       logger = create_logger(__name__)
#       print = get_log_function(logger)

logging.basicConfig(filename=LOGFILE, level=logging.DEBUG, format="[%(asctime)s] %(levelname)s:%(name)s: %(message)s")

def create_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    return logger

def get_log_function(logger: logging.Logger):
    """
    Возвращает функцию для записи вывода в log-файл.
    Как правило, этой функцией заменяют функцию `print()`.
    """
    def log(*args, end="\n", sep=" "):
        msg = sep.join([str(a) for a in args]) + end
        logger.info(msg)
    return log


utils_logger = create_logger(__name__)
"""Logger для модуля `utils`."""


### Глобальные переменные

classes_hierarchy: 'dict[str, list[str]]' = {}
"""
Глобальная переменная-словарь с информацией о наследовании классов.

Формат: `{ "дочерний класс": ["класс-родитель1", "класс-родитель2", ... ] }`

Как `"дочерние классы"`, так и `"классы-родители"` записаны с полным путем
пространств имен, например: `NXNXOpen.CAE.ResponseSimulation.StrainGageType`.

Например:
```
{
    "NXOpen.JtCompare": [
        "NXOpen.TaggedObject",
        "NXOpen.IValidator"
    ],
}
```
"""

modules_namespaces: 'dict[str, set[str]]' = {}
"""
Глобальная переменная-словарь с информацией о наследовании классов.

Формат: `{ "модуль": ["пространство имен 1", "пространство имен 2", ... ] }`

Как `"модули"`, так и `"пространства имен"` записаны с полным путем
пространств имен, например: `NXNXOpen.CAE.ResponseSimulation.StrainGageType`.

Например:
```
{
    "NXOpen.Drafting": [
        "NXOpen.Drafting.CutCopyPasteBuilderTypeOperation",
        "NXOpen.Drafting.CutCopyPasteLeaderBuilder",
        "NXOpen.Drafting.AnnotateViewsBuilderExistingAutomaticAnnotationMemberType",
        ...
    ],
}
```
"""

modules: 'list[types.ModuleType]' = []
"""Список с модулями NXOpen."""


### Вспомогательные функции

def load_classes_hierarchy():
    """Загружает информацию о наследовании классов из JSON-файла в глобальную переменную `classes_hierarchy`."""
    global classes_hierarchy
    with open(CLASSES_HIERARCHY_JSON_FILE, "r", encoding="utf-8") as f:
        classes_hierarchy.update(json.load(f))
        utils_logger.info(f"classes_hierarchy loaded with {len(classes_hierarchy)} objects.")


def save_classes_hierarchy():
    """Сохраняет информацию о наследовании классов из глобальной переменной `classes_hierarchy` в JSON-файл."""
    global classes_hierarchy
    with open(CLASSES_HIERARCHY_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(classes_hierarchy, f, ensure_ascii=False, indent=2)
        utils_logger.info(f"classes_hierarchy saved.")


def load_modules_namespaces():
    """Загружает информацию о пространствах имён модулей из JSON-файла в глобальную переменную `modules_namespaces`."""
    global modules_namespaces
    with open(MODULES_NAMESPACES_JSON_FILE, "r", encoding="utf-8") as f:
        modules_namespaces.update(json.load(f, object_hook=lambda obj: set(obj) if isinstance(obj, list) else obj))
        utils_logger.info(f"modules_namespaces loaded with {len(modules_namespaces)} objects.")


def save_modules_namespaces():
    """Сохраняет информацию о пространствах имён модулей из глобальной переменной `modules_namespaces` в JSON-файл."""
    global modules_namespaces
    with open(MODULES_NAMESPACES_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(modules_namespaces, f, ensure_ascii=False, indent=2, default=lambda obj: list(obj) if isinstance(obj, set) else obj)
        utils_logger.info(f"modules_namespaces saved.")


def indent_lines(text: str, level: int = 1, indent_chars: str = "    ") -> str:
    """
    Вставляет отступы в начале каждой строки текста `text`.

    Если передана пустая строка в `text`, то возвращается пустая строка.
    """
    t = ""
    for line in text.splitlines(True):
        t += indent_chars * level + line
    return t


def import_module(name: str, modules: 'list[types.ModuleType]'):
    """
    Импортирует модуль с названием `name` и добавляет его в список `modules`.

    Пример использования:
    ```
        modules = []
        try:
            import_module("NXOpen.Features", modules)
        except:
            print("Ошибка при импорте модуля 'NXOpen.Features'")
    ```
    """
    m = importlib.import_module(name)
    modules.append(m)



if NX_FOLDER == "":
    logging.error(f"Error: environment variable 'UGII_BASE_DIR' is not defined")
    exit(1)
