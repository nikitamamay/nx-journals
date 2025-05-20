import typing

import sys
import datetime
import os

import math

import NXOpen
import NXOpen.Features
import NXOpen.GeometricUtilities
import NXOpen.Layer


if "debug" in sys.argv:
    LOG_PATH = r"D:\Projects\github-nx-macros\nx-macros\log.txt"
    sys.stdout = open(LOG_PATH, "a", encoding="utf-8")
    print("---------")


PRECISION_POWER = 6
FLOATS_PRECISION = 10**(-PRECISION_POWER)

THICKNESS_LAYER_NAME_PREFIX = "S_"

# int_thickness: layer_number
_layers_for_thicknesses: 'dict[int, int]' = {}
_layers_initialized = False


COLORS: 'list[int]' = [
    184, 161, 120, 84, 66, 102, 140, 135, 194, 191, # neutral strong - темные средненасыщенные
    109, 110, 40, 3, 34, 32, 122, 163, # светлые слабонасыщенные
    181, 186, 78, 6, 11, 36, 108, 31, 103, 211, 164, 125, # светлые самые насыщенные
    # 146, 182, 77, 46, 30, 169, 25, 169, # темные сильнонасыщенные
    # 117, 155, 120, 47, 66, 93, 133, 205, 165, # vibrant strong - светлые средненасыщенные
]




def do_floats_equal(a, b):
    return abs(a - b) <= FLOATS_PRECISION

def round_tail_s(x: float) -> str:
    s = str(round(x * (10 ** PRECISION_POWER)) / (10 ** PRECISION_POWER))
    if s.endswith(".0"):
        s = s[:-2]
    return s


def get_color_for_i(i: int) -> int:
    colors_count = len(COLORS)
    if i >= colors_count:
        i %= colors_count
        print(f"Warning: not enough colors: {i} are requested, but there are only {colors_count}")
    return COLORS[i]


def get_color_for_layer(layer: int) -> int:
    global _layers_for_thicknesses
    for i, l in enumerate(sorted(set(_layers_for_thicknesses.values()))):
        if l == layer:
            return get_color_for_i(i)
    raise Exception(f"Not found color for layer={layer}")



def get_layer_name(thickness: float) -> str:
    return f'{THICKNESS_LAYER_NAME_PREFIX}{round_tail_s(thickness)}'


def get_selected_objects(type_ = object):
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
        ) -> NXOpen.Body:
    bodies: 'list[NXOpen.Body]' = []
    for body in workPart.Bodies:
        if feature in body.GetFeatures():
            bodies.append(body)
    return bodies


def get_bodies_and_thicknesses(
        workPart: NXOpen.Part,
        offset_surfaces: 'list[NXOpen.Features.OffsetSurface]'
        ) -> 'dict[float, list[NXOpen.Body]]':
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
    global layer_start_from

    used_layers: 'set[int]' = set()
    lc: NXOpen.Layer.CategoryCollection = workPart.LayerCategories
    for category in lc:
        category: NXOpen.Layer.Category
        if not category.Name == "ALL":
            for l in category.GetMemberLayers():
                used_layers.add(l)

    print(used_layers)

    layer_number = 2
    while layer_number < 250:
        if not layer_number in used_layers:
            return layer_number
        layer_number += 1
    raise Exception("No category-free layers found")


def get_int_thickness(x: float) -> int:
    return round(x * 10 ** 6)

def get_thickness_from_int(x: int) -> float:
    return float(x) / (10 ** 6)


def initialize_layers(workPart: NXOpen.Part):
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
            int_thickness = get_int_thickness(thickness)
            _layers_for_thicknesses[int_thickness] = layer_number


def get_layer_for_thickness(
        workPart: NXOpen.Part,
        thickness: float,
        ):
    global _layers_for_thicknesses, _layers_initialized
    if not _layers_initialized:
        initialize_layers(workPart)

    int_thickness: int = get_int_thickness(thickness)

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


    for thickness, bodies in get_bodies_and_thicknesses(wp, offset_surfaces).items():
        layer_number: int = get_layer_for_thickness(wp, thickness)
        color_number = get_color_for_layer(layer_number)

        print(color_number, layer_number, bodies)
        change_object_display(bodies, color_number, layer_number)





