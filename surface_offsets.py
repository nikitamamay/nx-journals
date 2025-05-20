"""
Скрипт предназначен для работы с оболочечными моделями при их подготовке перед
экспортом в Ansys.

Пользователю необходимо выделить операции типа "Смещение поверхности"
("Offset Surface") и вызвать скрипт. Для листовых тел, связанных с этими
операциями, скрипт распознает толщину как удвоенное расстояние смещения
(по модулю) в операциях "Смещение поверхности", и в соответствии с этими
толщинами выполняет перенос тел по слоям и раскрашивание по цветам.

Применение слоёв позволяет посчитать количество листовых тел в разрезе толщин,
а еще можно скрыть слои (и его объекты) с какими-то определенными толщинами.
Цветовая индикация позволяет определить толщину тела по известной толщине
другого тела такого же цвета --- без необходимости выделять объект и как-то
искать значение заданной толщины.

Само собой, при применении этого скрипта необходимо у операций "Смещение
поверхности", которые необходимо обработать скриптом, задавать численное
значение смещения равным по модулю половине толщины листовой детали.
В случае, если необходимо выполнить дополнительное смещение поверхности,
следует воспользоваться отдельной операцией, например, "Заменить грань" или
"Переместить грань". В противном случае выполнение скрипта приведет
к некорректным результатам.

Для удобного выделения всех операций "Смещение поверхности" ("Offset Surface")
можно настроить и применить фильтр к навигатору модели (к дереву построения),
кликнув ПКМ по пустому полю или по заголовку таблицы-навигатора и выбрав
соответствующую опцию меню.

"""

import typing

import sys
import datetime
import os

import NXOpen
import NXOpen.Features
import NXOpen.GeometricUtilities
import NXOpen.Layer


if "debug" in " ".join(sys.argv[1:]):
    temp_folder = os.getenv("TEMP")
    current_basename = os.path.basename(__file__) + ".log"
    LOG_PATH = os.path.join(temp_folder, current_basename)
    sys.stdout = open(LOG_PATH, "a", encoding="utf-8")
    print(f"\n--------- {datetime.datetime.now().isoformat()} ---------")
    print(f"sys.argv: {sys.argv}")


PRECISION_POWER = 6

THICKNESS_LAYER_NAME_PREFIX = "S_"

# { int_thickness: layer_number }
_layers_for_thicknesses: 'dict[int, int]' = {}
_layers_initialized = False


COLORS: 'list[int]' = [
    181, 186, 114, 6, 60, 106, 31, 103, 211, 164, 125,  # principal с изменениями
    146, 182, 77, 46, 30, 169, 25, 169, # темные сильнонасыщенные
    109, 110, 40, 3, 34, 32, 122, 163, # светлые слабонасыщенные
    # 184, 161, 120, 84, 66, 102, 140, 135, 194, 191, # neutral strong - темные средненасыщенные
    # 181, 186, 78, 6, 11, 36, 108, 31, 103, 211, 164, 125, # principal без изменений
    # 145, 112, 41, 6, 10, 36, 108, 19, 139, 200, 83, # meduim vibrant с изменениями
    # 117, 155, 120, 47, 66, 93, 133, 205, 165, # vibrant strong - светлые средненасыщенные
]



def round_tail_s(x: float) -> str:
    """
    Округляет float до `PRECISION_POWER` знаков после запятой (убирая погрешности
    вычислений) и возвращает строковое представление числа без `.0`.
    """
    s = str(round(x * (10 ** PRECISION_POWER)) / (10 ** PRECISION_POWER))
    if s.endswith(".0"):
        s = s[:-2]
    return s


def get_color_for_i(i: int) -> int:
    """
    Возвращает номер цвета по порядковому номеру `i`.
    """
    colors_count = len(COLORS)
    if i >= colors_count:
        i %= colors_count
        print(f"Warning: not enough colors: {i} are requested, but there are only {colors_count}")
    return COLORS[i]


def get_color_for_layer(layer: int) -> int:
    """
    Возвращает номер цвета по номеру слоя, на котором располагаются листовые тела.
    """
    global _layers_for_thicknesses
    for i, l in enumerate(
        map(
            lambda x: _layers_for_thicknesses[x],
            sorted(
                _layers_for_thicknesses.keys(),
                reverse=True,
            ),
        )
    ):
        if l == layer:
            return get_color_for_i(i)
    raise Exception(f"Not found color for layer={layer}")



def get_layer_name(thickness: float) -> str:
    """
    Возвращает название [категории] слоя для листовых тел толщиной `thickness`.
    """
    return f'{THICKNESS_LAYER_NAME_PREFIX}{round_tail_s(thickness)}'


def get_selected_objects(type_ = object) -> 'list[object]':
    """
    Возвращает список выбранных в NX объектов типа `type_`.
    """
    sel: NXOpen.Selection = NXOpen.UI.GetUI().SelectionManager

    objs = []

    for i in range(sel.GetNumSelectedObjects()):
        obj = sel.GetSelectedTaggedObject(i)
        if isinstance(obj, type_):
            objs.append(obj)
    return objs


def get_thickness(
        workPart: NXOpen.Part,
        offset_surface: NXOpen.Features.OffsetSurface,
        ) -> float:
    """
    Возвращает толщину листового тела как удвоенное смещение (по модулю)
    для данной операции `offset_surface`.
    """
    fc: NXOpen.Features.FeatureCollection = workPart.Features
    osb: NXOpen.Features.OffsetSurfaceBuilder = fc.CreateOffsetSurfaceBuilder(offset_surface)
    fsos: NXOpen.GeometricUtilities.FaceSetOffsetList = osb.FaceSets
    fso: NXOpen.GeometricUtilities.FaceSetOffset = fsos.FindItem(0)
    o: NXOpen.Expression = fso.Offset

    # толщина срединной поверхности = удвоенное смещение
    thickness: float = abs(o.Value) * 2
    return thickness


def get_feature_bodies(
        workPart: NXOpen.Part,
        feature: NXOpen.Features.Feature,
        ) -> 'list[NXOpen.Body]':
    """
    Возвращает список тел, которые образованы данной операцией `feature`.
    """
    bodies: 'list[NXOpen.Body]' = []
    for body in workPart.Bodies:
        if feature in body.GetFeatures():
            bodies.append(body)
    return bodies


def get_bodies_and_thicknesses(
        workPart: NXOpen.Part,
        offset_surfaces: 'list[NXOpen.Features.OffsetSurface]'
        ) -> 'dict[float, list[NXOpen.Body]]':
    """
    Возвращает распределение тел по толщинам
    в виде словаря `{ толщина : список тел }` для тех тел, которые образованы
    операциями из списка `offset_surfaces`.
    """
    d: 'dict[float, list[NXOpen.Body]]' = {}

    for os in offset_surfaces:
        bodies = get_feature_bodies(workPart, os)
        thickness = get_thickness(workPart, os)

        if not thickness in d:
            d[thickness] = []

        if not bodies in d[thickness]:
            d[thickness].extend(bodies)
    return d


def get_next_free_layer(
        workPart: NXOpen.Part,
        ) -> int:
    """
    Возвращает самый маленький (близкий к 0) номер слоя, для которого не назначена
    ни одна категория.
    """
    global layer_start_from

    used_layers: 'set[int]' = set()
    lc: NXOpen.Layer.CategoryCollection = workPart.LayerCategories
    for category in lc:
        category: NXOpen.Layer.Category
        if not category.Name == "ALL":
            for l in category.GetMemberLayers():
                used_layers.add(l)

    layer_number = 2
    while layer_number < 250:
        if not layer_number in used_layers:
            return layer_number
        layer_number += 1

    # FIXME добавить проверку, чтобы слой был ещё и пустым (не_содержал объектов)

    raise Exception("No category-free layers found")


def _get_int_thickness(x: float) -> int:
    return round(x * 10 ** 6)


def initialize_layers(workPart: NXOpen.Part) -> None:
    """
    Считывает в модели номера слоёв с категориями, названия которых отражают
    толщины листовых тел.

    То есть, если в модели уже есть слои с характерно названными категориями,
    то будут использоваться именно эти слои, а не "новые".
    """
    global _layers_for_thicknesses, _layers_initialized
    _layers_initialized = True

    lc: NXOpen.Layer.CategoryCollection = workPart.LayerCategories
    for category in lc:
        category: NXOpen.Layer.Category
        category_name: str = category.Name
        if category_name.startswith(THICKNESS_LAYER_NAME_PREFIX):
            thickness = float(category_name[len(THICKNESS_LAYER_NAME_PREFIX):])
            layers: 'list[int]' = category.GetMemberLayers()
            if len(layers) == 0: continue
            layer_number: int = layers[0]
            int_thickness = _get_int_thickness(thickness)
            _layers_for_thicknesses[int_thickness] = layer_number


def get_layer_for_thickness(
        workPart: NXOpen.Part,
        thickness: float,
        ) -> int:
    """
    Возвращет номер слоя для листовых тел с толщиной `thickness`.

    При необходимости создает новую категорию слоёв с характерным названием типа
    `S_20` (где 20 - толщина в мм) и присваивает её свободному слою.
    """
    global _layers_for_thicknesses, _layers_initialized
    if not _layers_initialized:
        initialize_layers(workPart)

    int_thickness: int = _get_int_thickness(thickness)

    if not int_thickness in _layers_for_thicknesses:
        lm: NXOpen.Layer.LayerManager = workPart.Layers
        lc: NXOpen.Layer.CategoryCollection = workPart.LayerCategories

        category_name = get_layer_name(thickness)

        layer_number = get_next_free_layer(workPart)
        try:
            # если нет категории слоев - создаем
            category = lc.CreateCategory(category_name, "", [layer_number])
        except:
            # на случай, если категория с таким именем уже существует, но не содержит слоёв (см. continue в initialize_layers())
            category = lc.FindObject(category_name)
            category.SetMemberLayers([layer_number])

        _layers_for_thicknesses[int_thickness] = layer_number

    return _layers_for_thicknesses[int_thickness]


def change_object_display(obj_list: 'list[NXOpen.DisplayableObject]', color = None, layer = None):
    """
    Изменяет цвет и/или слой объектов в модели.
    """
    displayModification1 = NXOpen.Session.GetSession().DisplayManager.NewDisplayModification()
    displayModification1.ApplyToAllFaces = True
    if not color is None:
        displayModification1.NewColor = int(color)
    if not layer is None:
        displayModification1.NewLayer = int(layer)
    displayModification1.Apply(obj_list)



if __name__ == "__main__":
    theSession  = NXOpen.Session.GetSession()
    wp: NXOpen.Part = theSession.Parts.Work
    # displayPart = theSession.Parts.Display

    initialize_layers(wp)


    offset_surfaces: 'list[NXOpen.Features.OffsetSurface]' = get_selected_objects(NXOpen.Features.OffsetSurface)

    print(f"selected OffsetSurfaces count: {len(offset_surfaces)}")

    bt = get_bodies_and_thicknesses(wp, offset_surfaces)

    for thickness in sorted(bt.keys(), reverse=True):
        bodies = bt[thickness]
        layer_number: int = get_layer_for_thickness(wp, thickness)
        color_number = get_color_for_layer(layer_number)

        print(f"thickness={thickness}, color={color_number}, layer={layer_number}, bodies count={len(bodies)}")
        change_object_display(bodies, color_number, layer_number)
