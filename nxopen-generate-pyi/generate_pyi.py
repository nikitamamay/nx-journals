"""
Журнал для генерации pyi-файлов с типизацией для NXOpen.

Использует `vars()` и работает на принципе рекурсивного обхода модулей, классов,
функций; получает документацию `__doc__` и извлекает из неё сигнатуры функций,
методов, их перегрузки, типы их параметров, типы полей классов.

FIXME...
который анализирует заголовочные `hxx`-файлы в папке `.../UGOPEN/NXOpen` и
извлекает информацию о наследовании классов друг от друга.

Информация о наследовании классов извлекается из С++, потому что в Python
не работает `type(obj).__bases__` при вызове для классов (хоть и работает при
вызове для объектов).

Протестировано для NX 12.

"""

import typing

import sys
import datetime
import os
import traceback
import re
import keyword
import types

from utils import *

logger = create_logger(__name__)



### Константы

BAD_TYPE_NAME = "BAD_TYPE_NAME"
"""Ключевое слово, необходимое при парсинге `__doc__`."""
ENUM_MEMBER_TYPE = "ENUM_MEMBER_TYPE"
"""Ключевое слово, необходимое при парсинге `__doc__`."""

SIMPLE_TYPES = (int, float, str, bool)
"""Простые типы, объекты которых вставляются в текст pyi-файла функцией `repr()`."""



### Регулярные выражения


re_multinewline = re.compile(r"\n\n+")
"""Регулярное выражение, необходимое для удаления многократных `\\n\\n\\n...` в `__doc__`."""

re_doc_rtype = re.compile(r":rtype:\s+([^\n]+)", re.M)
"""
Регулярное выражение для парсинга типа возвращаемого значения функции/метода или типа
поля класса (в getter-методе) в `__doc__`.
"""

re_doc_param = re.compile(r":param\s+(\w+):[\s\S]*?:type[^:]+:\s+([^\n]+)", re.M)
"""Регулярное выражение для парсинга параметров функции/метода в `__doc__`."""

re_field_value_type = re.compile(r"Field Value\s*?Type:([^\n]+)", re.M | re.I)
"""Регулярное выражение для парсинга типа поля класса, не представленного `getter`-методом в `__doc__`."""

re_doc_newline_fix = re.compile(r"(?<!\n):(param|type|returns|rtype)")
"""Регулярное выражение для исправления отстутсвующих переносов строк перед ключевыми словами в `__doc__`."""

re_doc_double_dot_newlines_fix = re.compile(r"(?<!\n)\n\.\. ")
"""
Регулярное выражение для исправления отстутсвующих двойных переносов строк
перед заголовками в `__doc__`, например, для `.. versionadded:: NX4.0.1`.
"""



### Функции для парсинга __doc__ и генерации pyi-файлов


def parse_type(text: str, func_fix_absolute_namespaces: 'typing.Callable[[str], str]') -> str:
    """
    Возвращает корректное представление типа (полученного, как правило, из `__doc__`) на Python.

    Поддерживает следующие формулировки:
    - `A tuple...` -> `tuple` - кортеж;
    - `list of ...` -> `list[...]` - список;
    - `Variant` -> `typing.Any` - произвольный тип;
    - `CallableObject` -> `typing.Callable` - функция;
    - `Id` -> `NXOpen.NXColor` - цвет (почему-то он обозначается как `Id`);
    - `PointerWrapper for...` -> `NXOpen.UF.PointerWrapper` - встречается в `NXOpen.UF`;
    - `:py:class:'...'` или `''...''` -> `...` - убирает оформление для названия класса в __doc__;

    В случае неподдерживаемого оформления возвращает пустую строку и сообщает об ошибке в log-файл.

    Рекурсивно для типа `list of ...`.
    """
    text = text.strip()

    if text.startswith("A tuple"):
        return "tuple"

    if text.startswith("list of "):
        text = parse_type(text[8:], func_fix_absolute_namespaces)
        if text == "":
            return "list"
        return f"'list[{text}]'"

    if text == "Variant":
        text = "typing.Any"

    if text == "CallableObject":
        text = "typing.Callable"

    if text == "Id":
        text = "NXOpen.NXColor"

    if text.startswith("PointerWrapper for"):  # in NXOpen.UF
        text = "NXOpen.UF.PointerWrapper"

    if text.startswith(":py:class:"):
        text = text[10:].strip()  # strip() is for ":py:class: `XYZ`" (with space) in NXOpen.UF

    if text.startswith("``"):  # in NXOpen.UF
        i = text.find("``", 2)
        text = text[2:i]

    if text.startswith("`"):  # for :py:class:`XYZ`
        i = text.find("`", 1)
        text = text[1:i]

    if text.endswith("."):  # return type in NXOpen.UF.Disp.AskCurrentGridContext.__doc__
        text = text[:-1]

    # FIXME
    # сделать сюда поддержку enum
    # if "Enum Member" in text:
    #     text = ENUM_MEMBER_TYPE

    if " " in text:
        logger.warning(f"bad typename {repr(text)}")
        text = ""

    text = func_fix_absolute_namespaces(text)
    return text


def get_doc(obj) -> str:
    """
    Получает документацию (docstring) из `obj.__doc__` и исправляет её:
    - заменяет многократные переносы строк `\\n\\n\\n\\n...` на двойной `\\n\\n`;
    - добавляет отсутствующие переносы строк перед ключевыми словами `:param`, `:type`, `:returns`, `:rtype`
    (для корректной работы функций парсинга параметров и возвращаемого значения);
    - добавляет отстутствующие двойные переносы строк перед заголовками, например, `\\n\\n.. versionadded`.

    Если атрибута `__doc__` нет в `obj`, то возвращается пустая строка.
    """
    if hasattr(obj, "__doc__") and (not obj.__doc__ is None):
        text = obj.__doc__.strip()
        text, _ = re_multinewline.subn("\n\n", text)
        text, _ = re_doc_newline_fix.subn(lambda m: f"\n:{m.group(1)}", text)
        text, _ = re_doc_double_dot_newlines_fix.subn(f"\n\n.. ", text)
        return text
    return ""


def format_docstring(doc: str) -> str:
    """
    Форматирует строку документации для вставки в pyi-файл.

    Если передана пустая строка, то возвращается пустая строка.
    """
    doc = doc.strip()

    if doc == "":
        return ""

    text = doc

    text = text.replace("``-------------------------------------``", "<hr>")

    if text.startswith("<hr>"):  # случается для Field Value
        text = text[4:].strip()

    text = text  # FIXME добавить сюда форматирование csv-table (часто - для enum'ов)

    if "\n" in text:
        text = f'"""\n{text}\n"""'
    else:
        text = f'"""{text}"""'

    if text.endswith('""""'):  # для случаев типа """...foo "bar" """
        text = text[:-3] + ' """'

    text += "\n"
    return text


def parse_return_type(doc: str, func_fix_absolute_namespaces: 'typing.Callable[[str], str]') -> str:
    """
    Извлекает из строки документации `doc` тип возвращаемого значения (после ключевого
    слова `:rtype`).

    Полученный тип корректируется методом `get_doc_type_string()`.
    """
    m = re_doc_rtype.search(doc)
    if not m is None:
        text: str = m.group(1).strip()
        return parse_type(text, func_fix_absolute_namespaces)
    return ""


def parse_field_value_type(doc: str, func_fix_absolute_namespaces: 'typing.Callable[[str], str]') -> str:
    """
    Извлекает из строки документации `doc` тип поля класса (после ключевых слов
    `Field Value \\n Type:`).

    Полученный тип корректируется методом `get_doc_type_string()`.
    """
    m = re_field_value_type.search(doc)
    if not m is None:
        text: str = m.group(1).strip()
        return parse_type(text, func_fix_absolute_namespaces)
    return ""


def parse_parameters(doc: str, func_fix_absolute_namespaces: 'typing.Callable[[str], str]') -> 'list[tuple[str, str]]':
    """
    Извлекает из строки документации `doc` имена и тивы параметров функции (после ключевых слов
    `:param` и `:type`).

    Полученные тип параметров корректируются методом `get_doc_type_string()`.
    """
    params: 'list[tuple[str, str]]' = []
    for m in re_doc_param.finditer(doc):
        param_name = m.group(1)
        param_type = m.group(2)

        if keyword.iskeyword(param_name):
            param_name += "_"

        param_type = parse_type(param_type, func_fix_absolute_namespaces)

        params.append((param_name, param_type))
    return params


def get_base_classes(classname: str, func_fix_absolute_namespaces: 'typing.Callable[[str], str]') -> str:
    """
    Возвращает перечень родительских классов через запятую для класса `classname`.
    Информация берется из глобальной переменной `classes_hierarchy`.

    Если информация о родительских классах в `classes_hierarchy` не представлена,
    подразумевается, что класс ничего не наследует.

    `classname` должен быть в виде полного пути пространств имен класса,
    например: `NXOpen.Routing.Electrical.CableDevice`.
    """
    if not classname in classes_hierarchy:
        return ""
    s = ""
    for base_class_name in classes_hierarchy[classname]:
        if base_class_name.startswith("std."):
            continue
        base_class_name = base_class_name.strip()
        base_class_name = func_fix_absolute_namespaces(base_class_name)
        s += f"{base_class_name}, "
    return s[:-2]


def get_module_name(namespace: str) -> str:
    """
    Возвращает имя модуля для пространства имен `namespace`.

    Если пространство имен не содержит имени модуля или ссылается на неизвестный
    модуль (не представленный в глобальной переменной `modules_namespaces`),
    возвращается пустая строка.
    """
    path_pieces = namespace.split(".")
    for i in range(len(path_pieces), 0, -1):
        module_name = ".".join(path_pieces[:i])
        if module_name in modules_namespaces:
            return module_name
    return ""


def get_fix_absolute_namespaces_function(namespace: str, imports: 'set[str]') -> 'typing.Callable[[str], str]':
    """
    Создает и возращает функцию
    ```
        def func_fix_absolute_namespaces(type_path: str) -> str: ...
    ```

    которая принимает абсолютный путь пространств имен `type_path`
    и, если он принадлежит данному основному пространству имён `namespace`
    (классу или основному модулю), исправляет его на относительный путь для
    этого `namespace`,
    а если путь пространств имен ссылается на другой модуль,
    возвращает абсолютный путь без изменения и добавляет модуль, содержащий
    этот путь, в список импортов основного модуля `imports`.

    Например:
    ```
    # основное пространство имён - это модуль "NXOpen.PDM"
    imports: 'set[str]' = set()
    f = get_fix_absolute_namespaces_function("NXOpen.PDM", imports)

    f("NXOpen.PDM.PartManager.NewPartFromPartBuilder")
    # вернёт относительный путь, "PartManager.NewPartFromPartBuilder"

    f("NXOpen.GeometricUtilities.IComponentBuilder")
    # вернёт абсолютный путь, "NXOpen.GeometricUtilities.IComponentBuilder",
    # и при этом добавит модуль "NXOpen.GeometricUtilities" в imports
    ```
    """
    assert isinstance(imports, set)

    global modules_namespaces
    this_module = get_module_name(namespace)

    def func_fix_absolute_namespaces(type_path: str) -> str:
        global modules_namespaces

        module_name = get_module_name(type_path)

        # when the same module is referenced --- making type_path relative
        if this_module == module_name and type_path.startswith(this_module):
            if not type_path in modules_namespaces[this_module]:
                logger.warning(f"namespace not found: '{type_path}' (func_fix_absolute_namespaces() within module '{this_module}')")
            type_path = type_path[len(this_module) + 1:]

        if module_name != "":
            imports.add(module_name)

        return type_path

    return func_fix_absolute_namespaces


def get_function_pyi(name: str, doc: str, has_self_keyword: bool, func_fix_absolute_namespaces: 'typing.Callable[[str], str]') -> str:
    """
    Возвращает Python-объявление (pyi) для функции или метода с документацией
    (__doc__). При этом имена и типы параметров, тип возвращаемого значения
    извлекается из документации.
    """
    self_keyword = "self" if has_self_keyword else ""

    if doc != "":
        params = ""
        params_list = parse_parameters(doc, func_fix_absolute_namespaces)
        for param_name, param_type in params_list:
            if param_type != "":
                param_type = ": " + param_type
            params += f"{param_name}{param_type}, "
        params = params[:-2]

        rtype = parse_return_type(doc, func_fix_absolute_namespaces)
        if rtype != "":
            rtype = f" -> {rtype}"
        else:
            rtype = f" -> None"
    else:
        params = ""
        rtype = ""

    comma_self_params = ", " if has_self_keyword and params != "" else ""

    s = f"def {name}({self_keyword}{comma_self_params}{params}){rtype}:\n"
    s += indent_lines(format_docstring(doc))
    s += indent_lines("...\n")

    return s



def get_pyi(name: str, obj: object, parent_namespace: str, module_imports: 'set[str]', parent = None) -> str:
    """
    Возвращает Python-объявление (pyi) для объектов любого типа, среди которых:
    - `module` - модуль. Для него вызывается `write_module_pyi()`;
    - `type` - подразумевается как класс, и для него вызывается рекурсивно;
    - `classmethod_descriptor` - подразумевается как статический метод класса (`@staticmethod`);
    - `method_descriptor`, `wrapper_descriptor`, `builtin_function_or_method`
        подразумеваются как методы класса (если `parent` - это класс) или обычные функции модуля.
        Поддерживается перегрузка функций (если `__doc__` начинается с "Overloaded") с применением
        декоратора `@typing.overload`;
    - `getset_descriptor`, которые в действительности `@property`, `@property.setter`, но здесь
        создаются просто как поля класса;
    - `member_descriptor` - поле класса, которое импользуется только в `NXOpen.NXExpression`.
    - `enum MemberType` -.

    Если тип неизвестный, то вовращается pyi-объявление как для глобальной переменной модуля или
    как для поля класса; при этом, вероятно, в pyi-файле окажется проблема типа "Type is not defined".

    Использует `vars(obj)` для рекурсивного обхода.
    """
    assert isinstance(module_imports, set)

    if name == "__doc__":
        """Элемент `__doc__` обрабатывается функцией `get_doc()`, поэтому здесь пропускается."""
        return ""

    if name == "__init__":
        """
        Конструкторы пропускаются.

        Предполагалось, что будет создаваться объявление конструктора `__init__()` с его документацией
        (и технически это возможно), но так как в пользовательских скриптах NXOpen объекты создаются
        не конструкторами, а возвращаются статическими и обычными методами, объявления конструторов и
        их неинформативная документация оказались бесполезны.

        Документация к конструкторам предлагает вызвать `help(type(self))`, но этот вызов возвращает
        пустую строку.
        """
        return ""

    if name == "__new__":
        """
        Элемент __new__ пропускается, так как в пользовательских скриптах метод не вызывается,
        а его документация неинформативна.
        """
        return ""

    s = ""  # Строка с pyi-объявлением для объекта `obj`
    typename = type(obj).__name__  # текстовое название типа объекта `obj`
    full_name = f"{parent_namespace}.{name}"  # полный путь пространств имен для объекта `obj`

    func_fix_absolute_namespaces = get_fix_absolute_namespaces_function(parent_namespace, module_imports)

    # module, e.g. NXOpen.Routing.Electrical
    if typename == "module":
        global modules
        if not obj in modules:
            logger.info(f"adding not imported module: '{obj.__name__}' (found in '{parent_namespace}')")  # type: ignore
            write_module_pyi(obj)

    # class
    elif typename == "type":
        logger.info(f"generating pyi for class '{full_name}'")
        base_classes = get_base_classes(full_name, func_fix_absolute_namespaces)
        s = f"\nclass {name}({base_classes}):\n"
        s += indent_lines(format_docstring(get_doc(obj)))

        for k, v in vars(obj).items():
            s += indent_lines(get_pyi(k, v, full_name, module_imports, obj))

        s += "\n"

    # static method
    elif typename == "classmethod_descriptor":
        doc = get_doc(obj)
        if doc == "":
            logger.warning(f"empty __doc__ for static method '{full_name}'")

            if full_name == "NXOpen.Session.GetSession":
                s = "\n"
                s += "# docstring and return type are hard-coded since this method has no __doc__\n"
                s += "@staticmethod\n"
                s += "def GetSession() -> NXOpen.Session:\n"
                s += indent_lines('"""Gets the singleton for :py:class:`NXOpen.Session`."""\n')
                s += indent_lines('...\n')
                s += "\n"
                return s

        s = "\n"
        s += "@staticmethod\n"
        s += get_function_pyi(name, doc, False, func_fix_absolute_namespaces)
        s += "\n"


    # module function or class method
    elif typename in ("method_descriptor", "wrapper_descriptor", "builtin_function_or_method"):
        doc = get_doc(obj)
        has_self_keyword = type(parent).__name__ == "type"

        s = "\n"

        # есть случаи в NXOpen.BlockStyler.SelectObject.AddFilter(), где overloaded не прописан, но факту есть
        if doc.startswith("Overloaded") or doc.count("Signature") > 1:
            doc_pieces = list(filter(
                lambda dp: dp != "" and not dp.startswith("Overloaded"),
                [p.strip() for p in doc.split("``-------------------------------------``")]
            ))

            if len(doc_pieces) == 1:  # e.g. NXOpen.Annotations.SelectTableSectionList.SetArray
                logger.warning(f"the __doc__ of the function '{full_name}' says that its overloaded, but only single signature is found.")
                s += get_function_pyi(name, doc, has_self_keyword, func_fix_absolute_namespaces)
                s += "\n"
                return s

            for doc_piece in doc_pieces:
                s += "@typing.overload\n"
                s += get_function_pyi(name, doc_piece, has_self_keyword, func_fix_absolute_namespaces)
                s += "\n"
        else:
            s += get_function_pyi(name, doc, has_self_keyword, func_fix_absolute_namespaces)
            s += "\n"


    # property with getter-setter
    elif typename == "getset_descriptor":
        doc = get_doc(obj)
        s_type = parse_return_type(doc, func_fix_absolute_namespaces)

        # if s_type == BAD_TYPE_NAME:
        #     s_type = ""

        if s_type == "":
            s_type = parse_field_value_type(doc, func_fix_absolute_namespaces)

        if s_type != "":
            s_type = ": " + s_type

        s = f"{name}{s_type} = ...\n"
        s += format_docstring(doc)  # no indent

    # something special used only in NXOpen.NXExpression class
    elif typename == "member_descriptor":
        logger.info(f"member_descriptor: {name} of type {type(obj)} in '{parent_namespace}', object is '{obj}'")
        s = f"{name} = ...  # member_descriptor\n"

    # other
    else:
        # enum value
        if typename.endswith("MemberType"):
            s = f"{name} = {str(obj)}  # {typename}\n"
            return s

        # enum value for NXOpen.UF module
        if isinstance(obj, SIMPLE_TYPES):
            s = f"{name} = {repr(obj)}  # {typename}\n"
            return s

        # unknown
        # print(f"unknown typename for: {name} of type {type(obj)} (typename={typename}) in '{parent_namespace}', object is {obj}")
        msg = ""

        s_type = parse_type(typename, func_fix_absolute_namespaces)
        if s_type == "InterfaceIdentifier":
            s_type = ""
            msg = "InterfaceIdentifier"

        if s_type != "":
            s_type = ": " + s_type
        if msg != "":
            msg = ": " + msg

        s = f"{name}{s_type} = ...  # unknown typename{msg}\n"

    return s


def write_module_pyi(module):
    """
    Создает pyi-объявления для объектов модуля `module` и записывает в файл
    `__init__.pyi` в соответствующей ему директории.

    Директории создаются автоматически, образуя структуру:
    ```
    PYI_NXOPEN_DIR/
        NXOpen/
            __init__.pyi
            Annotations/
                __init__.pyi
            Assemblies/
                __init__.pyi
                ProductInterface/
                    __init__.pyi
            ...
    ```
    """
    try:
        logger.info(f"generating pyi for module '{module.__name__}'")

        filepath = PYI_NXOPEN_DIR + "/" + module.__name__.replace(".", "/") + "/__init__.pyi"
        dir_path = os.path.dirname(filepath)
        os.makedirs(dir_path, exist_ok=True)

        s = ""
        s += f"# module '{module.__name__}'\n"
        s += f"#\n"
        s += f"# Automatically generated {datetime.datetime.now().isoformat()}\n"
        s += f"#\n"
        s += format_docstring(get_doc(module))
        s += "\n"
        s += "import typing\n"
        s += "\n"

        imports: 'set[str]' = set()
        contents = ""

        for k, v in vars(module).items():
            if k.startswith("__"):
                continue
            contents += get_pyi(k, v, module.__name__, imports, None)

        for i in sorted(set(imports)):
            if i == module.__name__:
                continue
            s += f"import {i}\n"

        s += "\n\n"
        s += contents
        s += "\n"

        if module.__name__ == "NXOpen":
            s += "# elements below are hard-coded, because they are not present\n"
            s += "# in any `vars()` dictionaries of any modules.\n\n"
            s += "class TaggedObjectCollection:\n"
            s += indent_lines("def __iter__(self): ...\n")
            s += "\n"
            s += "Tag = int\n"
            s += "\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(s)

        logger.info(f"done generating pyi for module '{module.__name__}', written in '{filepath}'")

    except Exception as e:
        logger.error(f"error with module '{module.__name__}'", exc_info=True)


def generate_modules_pyi(modules: 'list[types.ModuleType]'):
    load_classes_hierarchy()
    load_modules_namespaces()

    for module in modules:
        write_module_pyi(module)




if __name__ == "__main__":
    # import NXOpen
    # modules = [NXOpen]


    # load_classes_hierarchy()
    # load_modules_namespaces()

    # import NXOpen.Annotations

    # o = NXOpen.Annotations.SelectTableSectionList.SetArray
    # logger.debug(f"{repr(o.__doc__)}")

    pass
