"""

Журнал для генерации pyi-файлов для NXOpen.

Предназначен для автоматического создания pyi-файлов с объявлениями модулей,
функций, классов, методов с их текстовой документацией и корректными, насколько
это возможно, аннотациями типов.

Для получения информации о наследовании классов друг от друга используется
анализ заголовочных файлов C++ в папке `%UGII_BASE_DIR%/UGOPEN/NXOpen`.
Анализ кода C++ здесь применён по то причине, что `type(obj).__bases__`
не работает при вызове для классов (хоть и работает при вызове для объектов).

При генерации pyi-файлов использует `vars()` и работает на принципе рекурсивного
обхода модулей, классов, функций; получает документацию `__doc__` и извлекает
из неё сигнатуры функций, методов, их перегрузки, типы их параметров,
типы полей классов.

Протестировано для NX 12.

(c) Nikita Mamay, 04.06.2025.
"""

import typing
import types

import getopt

import sys

from utils import *

import analyze_cpp
import analyze_namespaces
import generate_pyi
import nx_gui


logger = create_logger(__name__)


VERSION_MSG = f"nxopen-generate-pyi v2025.06.04"

USAGE_MSG = f"""\
Использование:
    nxopen-generate-pyi/main.py [OPTIONS]

    Внимание! Запускать необходимо в NX (Menu -> Tools -> Journal -> Play...),
    указав путь к файлу "nxopen-generate-pyi/main.py" и введя аргументы (опции)
    программы в поле "Enter Journal Arguments".

Опции [OPTIONS]:
    -h, --help
        Вывести информацию об использовании программы и выйти.

    -v, --version
        Вывести версию программы и выйти.

    -i, --import_check
        Попытаться импортировать модули NXOpen и выйти.

    -a, --all
        Выполнить весь возможный функционал.
        Эквивалентно опциям "--cpp --namespaces --modules".

    -c, --cpp
        Извлечь и сохранить информацию о наследовании классов друг от друга
        из заголовочных файлов C++ для NXOpen.

    -n, --namespaces
        Проанализровать Python-модули NXOpen и сохранить информацию
        о пространствах имён в этих модулях.

    -g, --generate_pyi
        Сгенерировать pyi-файлы для модулей NXOpen.
"""

HELP_MSG = f"""\
{VERSION_MSG} - журнал для генерации pyi-файлов для NXOpen.

Предназначен для автоматического создания pyi-файлов с объявлениями модулей,
функций, классов, методов с их текстовой документацией и корректными, насколько
это возможно, аннотациями типов.

{USAGE_MSG}\

Файлы:
    По-умолчанию в папке с программой создаётся файл 'nxopen-generate-pyi.log',
    который содержит информационные сообщения и сообщения об ошибках.

(c) Nikita Mamay."""


class CMD_Options:
    do_import_check: bool = False
    do_debug: bool = False
    do_cpp: bool = False
    do_namespaces: bool = False
    do_generate_pyi: bool = False


def show_help():
    try:
        nx_gui.show_NX_message("nxopen-generate-pyi - Help", HELP_MSG)
    except:
        pass
    finally:
        logger.info(f"\n{HELP_MSG}")


def show_usage():
    try:
        nx_gui.show_NX_message("nxopen-generate-pyi - Help", HELP_MSG)
    except:
        pass
    finally:
        logger.info(f"\n{USAGE_MSG}")


def show_version():
    try:
        nx_gui.show_NX_message("nxopen-generate-pyi - Version", VERSION_MSG)
    except:
        pass
    finally:
        logger.info(f"\n{VERSION_MSG}")


def main() -> int:
    global modules

    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "hvaidcng",
            ["help", "version", "all", "import_check", "debug", "cpp", "namespaces", "generate_pyi"],
        )

        if len(opts) == 0:
            show_usage()
            return 2

        for o, a in opts:
            if o in ("-h", "--help"):
                show_help()
                return 0

            elif o in ("-v", "--version"):
                show_version()
                return 0

            elif o in ("-a", "--all"):
                CMD_Options.do_cpp = True
                CMD_Options.do_namespaces = True
                CMD_Options.do_generate_pyi = True

            elif o in ("-i", "--import_check"):
                CMD_Options.do_import_check = True

            elif o in ("-d", "--debug"):
                CMD_Options.do_debug = True

            elif o in ("-c", "--cpp"):
                CMD_Options.do_cpp = True

            elif o in ("-n", "--namespaces"):
                CMD_Options.do_namespaces = True

            elif o in ("-g", "--generate_pyi"):
                CMD_Options.do_generate_pyi = True

            else:
                raise Exception(f"Unknown option '{o}'")

        logger.info(f"Starting '{__file__}' with opts={opts} args={args}")
    except:
        logger.error("Error while parsing command line arguments", exc_info=True)
        show_usage()
        return 2

    try:
        if CMD_Options.do_debug:
            # import random
            # files = random.sample(files, 1)

            # files = [
            #     "D:/Programs/Siemens NX 12/UGOPEN/NXOpen/Callback.hxx"
            # ]
            return 0


        for name in MODULES_NAMES:
            try:
                import_module(name, modules)
            except:
                logger.error(f"Error while importing module '{name}'", exc_info=False)
                # logger.debug(f"Error while importing module '{name}'", exc_info=True)

        logger.info(f"Imported modules count is {len(modules)} of {len(MODULES_NAMES)} requested.")

        if CMD_Options.do_import_check:
            l = len(modules)
            for i, module in enumerate(modules):
                logger.info(f"{i+1}/{l}: '{module.__name__}' {module}")
            return 0


        if len(modules) == 0:
            logger.error(f"No modules imported!")
            return 1



        if CMD_Options.do_cpp:
            analyze_cpp.parse_cpp_files()

        if CMD_Options.do_namespaces:
            analyze_namespaces.analyze_namespaces(modules)

        if CMD_Options.do_generate_pyi:
            generate_pyi.generate_modules_pyi(modules)

    except:
        logger.error("error while executing main():", exc_info=True)
    return 0


if __name__ == "__main__":
    rc = main()
    if rc != 0:
        exit(rc)
