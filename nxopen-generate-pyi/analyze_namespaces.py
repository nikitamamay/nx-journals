
import typing
import types

from utils import *

logger = create_logger(__name__)



### Функции для парсинга пространств имен модулей


def _get_module_namespaces(parent_module_name: str, name: str, obj: object, parent_namespace: str = ""):
    """
    Рекурсивный вариант функции `get_module_namespaces()`.
    """
    if not parent_module_name in modules_namespaces:
        modules_namespaces[parent_module_name] = set()

    if parent_namespace != "":
        full_name = f"{parent_namespace}.{name}"
    else:
        full_name = name


    typename = type(obj).__name__
    if typename == "type":
        modules_namespaces[parent_module_name].add(full_name)

    if typename == "module":
        parent_module_name = obj.__name__  # type: ignore
        full_name = parent_module_name

    if typename == "type" or typename == "module":
        for k, v in vars(obj).items():
            if k.startswith("__"):
                continue
            _get_module_namespaces(parent_module_name, k, v, full_name)


def get_module_namespaces(module: types.ModuleType):
    """
    Анализирует и записывает пространства имен модуля `module`
    в глобальную переменную `modules_namespaces`.

    См. `_get_module_namespaces()`.
    """
    _get_module_namespaces(module.__name__, module.__name__, module)


def analyze_namespaces(modules: 'list[types.ModuleType]'):
    """
    Анализирует и записывает пространства имен модулей `modules`
    в глобальную переменную `modules_namespaces`.

    См. `_get_module_namespaces()`.
    """
    global modules_namespaces
    logger.info(f"Analyzing Python NXOpen modules for namespaces...")

    logger.info(f"Clearing modules_namespaces ({len(classes_hierarchy)} objects).")
    modules_namespaces.clear()

    for module in modules:
        logger.info(f"Analyzing module '{module.__name__}' for namespaces")
        try:
            get_module_namespaces(module)
        except:
            logger.error(f"Error while analyzing module '{module.__name__}' for namespaces", exc_info=True)

    save_modules_namespaces()
    logger.info(f"Analyzing Python NXOpen modules for namespaces is done. Now modules_namespaces contains {len(modules_namespaces)} objects.")
