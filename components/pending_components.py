
import typing

import os

import this_logging

import NXOpen
import NXOpen.Assemblies
import NXOpen.PDM
import NXOpen.Positioning
import NXOpen.UF



logger = this_logging.getLogger(__name__)


TEMPLATES = {
    "Разработка": "@DB/model-assy-mm-nx12/A",  # контрольная структура
    "Деталь": "@DB/NX_template_DET/00",  # деталь
    "Сборочная единица": "@DB/NX_template_ASSY/00",  # сборочная единица
}

TYPES = {
    "Design": "Разработка",
    "SPB5_Det": "Деталь",
    "SPB5_Assy": "Сборочная единица",
}


def get_db_name(id_: str, rev: str) -> str:
    return f"@DB/{id_}/{rev}"


def list_pending_components(part: NXOpen.Part) -> 'list[str]':
    """
    Возвращает обозначения и ревизии деталей в списке ожидания.
    Функция предназначена для отображения списка деталей в TreeView в dialog.

    Не доделано:
    FIXME извлечь из этого наименования обозначение и ревизию
    """
    parts_names: list[str] = []

    session = NXOpen.Session.GetSession()
    pdm_session: NXOpen.PDM.PdmSession = session.PdmSession

    pm: NXOpen.PDM.PartManager = session.Parts.PDMPartManager
    pcm: NXOpen.PDM.PendingComponentsManager = pm.NewPendingComponentsManager(part)
    handles: 'list[str]' = pcm.GetComponents()
    for handle in handles:
        filename = pcm.GetComponentPartFileName(handle)
        parts_names.append(filename)  # FIXME извлечь из этого наименования обозначение и ревизию
    return parts_names


def add_pending_components(part: NXOpen.Part, go_recursive_on_added: bool = True):
    session = NXOpen.Session.GetSession()
    pdm_session: NXOpen.PDM.PdmSession = session.PdmSession

    pm: NXOpen.PDM.PartManager = session.Parts.PDMPartManager
    pcm: NXOpen.PDM.PendingComponentsManager = pm.NewPendingComponentsManager(part)
    handles: 'list[str]' = pcm.GetComponents()

    logger.info(f"Pending components count in '{part.Name}' is {len(handles)}.")

    added_components: 'list[NXOpen.Assemblies.Component]' = []

    for handle in handles:
        try:
            filename = pcm.GetComponentPartFileName(handle)
            logger.debug(f"'{handle}' '{filename}'")

            open_part_and_fix_template(filename)

            # по-умолчанию создается по шаблону "Empty". см. open_part_and_fix_template()
            component, load_status = pcm.AddComponent(handle)
            added_components.append(component)
        except:
            logger.error(f"Cannot add pending component with handle='{handle}'", exc_info=True)

    if go_recursive_on_added:
        for component in added_components:
            component_part: NXOpen.Part = component.Prototype
            add_pending_components(component_part, go_recursive_on_added)


def open_part_and_fix_template(filename: str) -> None:
    session: NXOpen.Session = NXOpen.Session.GetSession()
    try:
        part = session.Parts.FindObject(filename)
    except:
        part, _ = session.Parts.Open(filename)

    part_name = part.Name
    part_type = part.GetStringAttribute("DB_PART_TYPE")
    template_name = part.GetStringAttribute("DB_SEED_PART_USED")  # NULL

    logger.info(f"'{part.Name}': DB_PART_TYPE='{part_type}', DB_SEED_PART_USED='{template_name}'")

    if template_name in ("NULL", "Metric"):
        try:
            new_template_name = TEMPLATES[TYPES[part_type]]
        except:
            logger.error(f"Cannot find template for part_type='{part_type}' in part '{part_name}'")
            return

        logger.info(f"Closing '{part.Name}'")
        part.Close(
            NXOpen.BasePart.CloseWholeTree.FalseValue,
            NXOpen.BasePart.CloseModified.CloseModified,
            session.Parts.NewPartCloseResponses(),
        )


        logger.info(f"Setting '{part_name}' template as '{new_template_name}'")
        session.Parts.SetSeedPartTemplateData(filename, new_template_name, False)
        part, _ = session.Parts.Open(filename)
        logger.info(f"Opened '{part_name}' in background")


def main():
    session: NXOpen.Session = NXOpen.Session.GetSession()
    markID = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "[NM] Run Journal")  # type: ignore

    wp = session.Parts.Work
    if wp is None:
        raise Exception("no work part")

    add_pending_components(wp, True)



if __name__ == "__main__":
    main()
