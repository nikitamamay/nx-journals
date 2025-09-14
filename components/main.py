

import this_logging
logger = this_logging.getLogger(__name__)
logger.info("\n\nStarting Journal execution.")




import utils
import gui
import pending_components
import move_component
import fix_constraint
import nxwave

import NXOpen
import NXOpen.Assemblies
import NXOpen.UF

dialog = gui.dialog()


def add_pending_single():
    utils.set_undo_mark("[NM] Add pending components")
    components = dialog.get_selected()

    if len(components) > 0:
        parts = utils.get_parts_of_components(components)
    else:
        parts = [NXOpen.Session.GetSession().Parts.Work]

    for part in parts:
        pending_components.add_pending_components(part, False)

def add_pending_recursive():
    utils.set_undo_mark("[NM] Add pending components recursive")
    components = dialog.get_selected()

    if len(components) > 0:
        parts = utils.get_parts_of_components(components)
    else:
        parts = [NXOpen.Session.GetSession().Parts.Work]

    names = set([p.Name for p in parts])
    for part in parts:
        parts.extend(utils.get_assembly_unique_parts(part, False, names))

    for part in parts:
        pending_components.add_pending_components(part, True)


def set_in_000():
    utils.set_undo_mark("[NM] Set components in (0, 0, 0)")
    components = dialog.get_selected()

    for c in components:
        if c.IsFixed:
            is_yes = gui.ask_question(f"Вы уверены, что хотите переместить зафиксированный компонент '{c.Name}'?")
            if not is_yes:
                continue
        move_component.orient_component(c, move_component.get_identity_matrix())
        pos = c.GetPosition()[0]
        move_component.translate_component(c, move_component.get_vector_from_points(pos, NXOpen.Point3d()))
        logger.info(f"Component '{c.Name}' is oriented and translated to (0, 0, 0)")


def fix_components():
    wp = NXOpen.Session.GetSession().Parts.Work
    try:
        utils.set_undo_mark("[NM] Fix components")
        components = dialog.get_selected()

        if len(components) == 0:
            logger.info("No components selected for fix_component()")
            return

        for c in components:
            fix_constraint.fix_component(c, do_set_workpart=True)
    finally:
        NXOpen.Session.GetSession().Parts.SetWork(wp)



def fix_components_in_parts_recursive():
    wp = NXOpen.Session.GetSession().Parts.Work
    try:
        utils.set_undo_mark("[NM] Fix components recursive")
        components = dialog.get_selected()

        if len(components) > 0:

            fix_components()  # для фиксации тех компонентов, что уже выбраны

            parts = utils.get_parts_of_components(components)
        else:
            wp = NXOpen.Session.GetSession().Parts.Work
            parts = utils.get_assembly_unique_parts(wp, True)

        for part in parts:
            components = fix_constraint.find_fixable_components(part)
            logger.info(f"Found {len(components)} components in part '{part.Name}' to be fixed")
            for c in components:
                fix_constraint.fix_component(c, do_set_workpart=True)
    finally:
        NXOpen.Session.GetSession().Parts.SetWork(wp)







dialog.callbacks["btn_pending_0"] = add_pending_single
dialog.callbacks["btn_pending_recursive"] = add_pending_recursive

dialog.callbacks["btn_000"] = set_in_000

dialog.callbacks["btn_fix"] = fix_components
dialog.callbacks["btn_fix_recursive"] = fix_components_in_parts_recursive

dialog.callbacks["btn_freeze"] = lambda: nxwave._wave_action(dialog.get_selected(), True, False)
dialog.callbacks["btn_freeze_recursive"] = lambda: nxwave._wave_action(dialog.get_selected(), True, True)
dialog.callbacks["btn_unfreeze"] = lambda: nxwave._wave_action(dialog.get_selected(), False, False)
dialog.callbacks["btn_unfreeze_recursive"] = lambda: nxwave._wave_action(dialog.get_selected(), False, True)






dialog.Show()
dialog.Dispose()

logger.info("Journal execution is done.")
