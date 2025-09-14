import typing

import NXOpen
import NXOpen.Assemblies
import NXOpen.UF


def get_parts_of_components(components: 'list[NXOpen.Assemblies.Component]') -> 'list[NXOpen.Part]':
    parts = []
    for c in components:
        part = c.Prototype
        if not part in parts:
            parts.append(part)
    return parts


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


def iterate_children_components() -> 'typing.Generator[NXOpen.Assemblies.Component, None, None]':
    asm = NXOpen.Session.GetSession().Parts.Work.ComponentAssembly
    if asm is None or asm.RootComponent is None:
        return None
    for child in asm.RootComponent.GetChildren():
        yield child



def ___get_part(component: NXOpen.Assemblies.Component) -> NXOpen.Part:
    """
    Вариант получения детали от компонента через `NXOpen.UF.UFSession.Assem.AskComponentData()`.

    Используй `NXOpen.Assemblies.Component.Prototype`, который на самом деле возвращает `NXOpen.Part`.
    """
    owning = component.OwningPart
    if owning is None:
        owning = NXOpen.Session.GetSession().Parts.Work

    ufsession: NXOpen.UF.UFSession = NXOpen.UF.UFSession.GetUFSession()
    name: str = ufsession.Assem.AskComponentData(component.Tag)[0]  # type: ignore
    part: NXOpen.Part = NXOpen.Session.GetSession().Parts.FindObject(name)  # type: ignore
    return part


def get_assembly_unique_parts(part: NXOpen.Part, do_include_top_part: bool = False, added_parts_names: 'set[str]' = set()) -> 'list[NXOpen.Part]':
    parts: list[NXOpen.Part] = []
    if do_include_top_part:
        if not part.Name in added_parts_names:
            parts.append(part)
            added_parts_names.add(part.Name)

    asm = part.ComponentAssembly
    if asm is None or asm.RootComponent is None:
        return parts

    for child_component in asm.RootComponent.GetChildren():
        p: NXOpen.Part = child_component.Prototype  # type: ignore
        if not p.Name in added_parts_names:
            parts.append(p)
            added_parts_names.add(p.Name)
            parts.extend(get_assembly_unique_parts(p, False, added_parts_names))

    return parts


def set_undo_mark(name: str) -> int:
    return NXOpen.Session.GetSession().SetUndoMark(NXOpen.Session.MarkVisibility.Visible, name)  # type: ignore

