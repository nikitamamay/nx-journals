import typing

import sys
import os

import re

import str_utils2


from utils import *

logger = create_logger(__name__)


re_class_decl = re.compile(r"^\s*class\s+([^:;{\n]+):([^{\n]+)\s*?{", re.M)

re_nxexport = re.compile(r"\w*EXPORT")
re_nxdeprecated = re.compile(r"NX_DEPRECATED\(['\"][^'\"]+['\"]\)")



class CPP_NamespaceManager():
    def __init__(self):
        self.is_triggered = False
        self.name = ""
        self._current_namespace: 'str|None' = None

        self.namespaces: 'list[tuple[str, int]]' = []
        """list of tuple[ (str) namespace_name, (int) parenthesis_level ]"""

    def opened(self, level: int):
        if self.is_triggered:
            n = self.name.strip()
            self.namespaces.append((n, level))
            self.untrigger()
            self._current_namespace = None

    def closed(self, level: int):
        if len(self.namespaces) > 0 and self.namespaces[-1][1] == level:
            self.namespaces.pop()
            self._current_namespace = None

    def trigger(self):
        self.is_triggered = True

    def check(self, letter):
        if self.is_triggered:
            if letter == ";":
                self.untrigger()
                return
            self.name += letter

    def get_current_namespace(self) -> str:
        if self._current_namespace is None:
            self._current_namespace = "::".join([ns for ns, _ in self.namespaces])
        return self._current_namespace

    def untrigger(self):
        self.is_triggered = False
        self.name = ""


# class CPP_ClassManager():
#     def __init__(self):
#         self.is_triggered = False
#         self.name = ""

#     def opened(self, level: int):
#         if self.is_triggered:
#             n = self.name.strip()
#             self.namespaces.append([n, level])
#             self.untrigger()
#             self._current_namespace = None

#     def closed(self, level: int):
#         if len(self.namespaces) > 0 and self.namespaces[-1][1] == level:
#             self.namespaces.pop()
#             self._current_namespace = None

#     def trigger(self):
#         self.is_triggered = True

#     def check(self, letter):
#         if self.is_triggered:
#             if letter == ";":
#                 self.untrigger()
#                 return
#             self.name += letter

#     def get_current_namespace(self) -> str:
#         if self._current_namespace is None:
#             self._current_namespace = "::".join([ns for ns, _ in self.namespaces])
#         return self._current_namespace

#     def untrigger(self):
#         self.is_triggered = False
#         self.name = ""


class CPP_Parser:
    def __init__(self):
        # статусы для текущей ситуации при побуквенном парсинге:
        self.is_string: bool = False
        self.is_html_tag: bool = False

        self.is_line_comment: bool = False
        self.is_block_comment: bool = False

        self.is_current_backslash: bool = False
        self.is_prev_backslash: bool = False

        self.current_string_char: str = ""
        self.current_string: str = ""

        self.par1_count: int = 0
        """Parenthesis counter: `( )`"""
        self.par2_count: int = 0
        """Parenthesis counter: `{ }`"""
        self.par3_count: int = 0
        """Parenthesis counter: `[ ]`"""

        self.keywords_status = {}

        self.ns_mgr = CPP_NamespaceManager()
        # self.cls_mgr = CPP_ClassManager()

    def check_keyword(self, keyword: str, letter: str) -> int:
        try:
            self.keywords_status[keyword]
        except KeyError:
            self.keywords_status[keyword] = 0

        j = self.keywords_status[keyword]
        if letter == keyword[j]:
            self.keywords_status[keyword] += 1
            if self.keywords_status[keyword] == len(keyword):
                self.keywords_status[keyword] = 0
                return j + 1
        else:
            self.keywords_status[keyword] = 0
        return self.keywords_status[keyword]

    def backslash(self, text: typing.Iterable[str], letter: str, i: int):
        self.is_prev_backslash = self.is_current_backslash
        self.is_current_backslash = letter == "\\"

    def comment(self, text: typing.Iterable[str], letter: str, i: int):
        if not self.is_string:
            if self.is_line_comment and letter == "\n":
                self.is_line_comment = False

            if self.is_block_comment and self.check_keyword("*/", letter) == 2:
                self.is_block_comment = False

            if self.check_keyword("//", letter) == 2:
                self.is_line_comment = True

            if self.check_keyword("/*", letter) == 2:
                self.is_block_comment = True

    def string(self, text: typing.Iterable[str], letter: str, i: int):
        if self.is_block_comment or self.is_line_comment:
            return

        if letter in str_utils2.QUOTES:
            if not self.is_string:
                self.is_string = True
                self.current_string_char = letter

            else:
                if not self.is_prev_backslash:
                    self.current_string += letter
                    self.is_string = False

        if self.is_string:
            self.current_string += letter

    def parenthesis_counter(self, text: typing.Iterable[str], letter: str, i: int):
        if self.is_string or self.is_block_comment or self.is_line_comment:
            return

        if letter == "(":
            self.par1_count += 1
        if letter == ")":
            self.par1_count -= 1

        if letter == "{":
            self.par2_count += 1
            self.ns_mgr.opened(self.par2_count)

        if letter == "}":
            self.ns_mgr.closed(self.par2_count)
            self.par2_count -= 1

        if letter == "[":
            self.par3_count += 1
        if letter == "]":
            self.par3_count -= 1

    def cpp(self, text: typing.Iterable[str], letter: str, i: int):
        if self.is_string or self.is_block_comment or self.is_line_comment:
            return

        self.ns_mgr.check(letter)
        # self.cls_mgr.check(letter)

        if self.check_keyword("namespace", letter) == 9:
            self.ns_mgr.trigger()

        # if self.check_keyword("class", letter) == 5:
        #     self.cls_mgr.trigger()






def get_classname(text: str) -> str:
    text, _ = re_nxexport.subn("", text)
    text = text.strip()
    return text

def get_base_classes(text: str) -> 'list[str]':
    elements = [el.strip() for el in text.split(",")]
    for i in range(len(elements)):
        elements[i] = elements[i] \
            .replace("public", "") \
            .replace("virtual", "") \

        elements[i] = elements[i].replace("::", ".")
        elements[i] = elements[i].strip()
    return elements




def get_namespace(text: str, target_i: int) -> str:
    p = CPP_Parser()
    str_utils2.parse_with_callbacks(text, [
        p.backslash,
        p.comment,
        p.string,

        p.parenthesis_counter,

        p.cpp,
    ], 0, target_i)

    ns = p.ns_mgr.get_current_namespace()
    ns = ns.replace("::", ".")

    return ns



def parse_file(filepath: str) -> None:
    global classes_hierarchy

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    text, _ = re_nxdeprecated.subn("", text)  # removing DEPRECATION warnings

    for m in re_class_decl.finditer(text):
        classname = get_classname(m.group(1))

        if classname == "iterator":
            continue

        i_target = m.start()
        ns = get_namespace(text, i_target)
        if len(ns) > 0:
            ns += "."

        classname = ns + classname
        baseclasses = get_base_classes(m.group(2))

        classes_hierarchy[classname] = baseclasses

        s = f"class {classname}({', '.join(baseclasses)})"

        # print(f"\t{repr(m.group(0))}\n\t'{s}'")



def parse_cpp_files():
    global classes_hierarchy
    logger.info(f"Parsing C++ files...")

    logger.info(f"Clearing classes_hierarchy ({len(classes_hierarchy)} objects).")
    classes_hierarchy.clear()

    files = os.listdir(NXOPEN_CPP_FOLDER)
    logger.info(f"Listing directory '{NXOPEN_CPP_FOLDER}'. Files found: {len(files)}")

    for file in files:
        filepath = os.path.join(NXOPEN_CPP_FOLDER, file)
        logger.info(f"Parsing file '{filepath}'")
        try:
            parse_file(filepath)
        except:
            logger.error(f"Error while parsing C++ file '{filepath}'", exc_info=True)

    save_classes_hierarchy()
    logger.info(f"Parsing of C++ files is done. Now classes_hierarchy contains {len(classes_hierarchy)} objects.")




if __name__ == "__main__":
    parse_cpp_files()
