
import typing

import os

import NXOpen
import NXOpen.Assemblies
import NXOpen.UF

import this_logging

import utils


logger = this_logging.getLogger(__name__)



def is_frozen(part: NXOpen.Part) -> bool:
    ufsession: NXOpen.UF.UFSession = NXOpen.UF.UFSession.GetUFSession()
    status = ufsession.Wave.AskDelayStatus(part.Tag)  # type: ignore
    return \
        status == NXOpen.UF.Wave.DelayStatus.PERSISTENT_FROZEN \
        or status == NXOpen.UF.Wave.DelayStatus.SESSION_FROZEN

def freeze_parts(parts: 'typing.Iterable[NXOpen.Part]'):
    tags = [part.Tag for part in parts]
    ufsession: NXOpen.UF.UFSession = NXOpen.UF.UFSession.GetUFSession()
    # ufsession.Wave.FreezePersistently(len(tags), tags)  # type: ignore
    for part in parts:
        try:
            ufsession.Wave.FreezePersistently(1, [part.Tag])  # type: ignore
        except:
            logger.error(f"Error with part '{part.Name}'", exc_info=True)


def unfreeze_parts(parts: 'typing.Iterable[NXOpen.Part]'):
    tags = [part.Tag for part in parts]
    ufsession: NXOpen.UF.UFSession = NXOpen.UF.UFSession.GetUFSession()
    # ufsession.Wave.Unfreeze(len(tags), tags)  # type: ignore
    for part in parts:
        try:
            ufsession.Wave.Unfreeze(1, [part.Tag])  # type: ignore
        except:
            logger.error(f"Error with part '{part.Name}'", exc_info=True)





def _wave_action(components: 'list[NXOpen.Assemblies.Component]', action_to_freeze: bool, is_recursive: bool) -> None:
    s_freeze = "Freeze" if action_to_freeze else "Unfreeze"
    s_frozen = "Frozen" if action_to_freeze else "Unfrozen"
    s_recursive = " recursive" if is_recursive else ""
    utils.set_undo_mark(f"[NM] {s_freeze} components{s_recursive}")

    action = freeze_parts if action_to_freeze else unfreeze_parts

    if len(components) > 0:
        parts = utils.get_parts_of_components(components)
    else:
        parts = [NXOpen.Session.GetSession().Parts.Work]

    if is_recursive:
        names = set([p.Name for p in parts])
        for part in parts:
            parts.extend(utils.get_assembly_unique_parts(part, True, names))

    # action(parts)
    for p in parts:
        action([p])
    logger.info(f"{s_frozen} parts count is {len(parts)}.")



def main():

    ### parsing arguments

    import sys
    argv = " ".join(sys.argv[1:])
    logger.info(f"Args: '{argv}'")

    do_freeze = "freeze" in argv
    do_unfreeze = "unfrz" in argv  # Попался! "freeze" - это подстрока "unfreeze" !
    is_recursive = "recursive" in argv

    if do_freeze == do_unfreeze:
        raise Exception("Bad action specified")

    ### doing journal

    components: 'list[NXOpen.Assemblies.Component]' = utils.get_selected_objects(NXOpen.Assemblies.Component)  # type: ignore

    _wave_action(components, do_freeze, is_recursive)

    return


def debug():
    session: NXOpen.Session = NXOpen.Session.GetSession()
    ufsession: NXOpen.UF.UFSession = NXOpen.UF.UFSession.GetUFSession()

    markID = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "[NM] Run Journal")  # type: ignore

    wp = session.Parts.Work
    if wp is None:
        raise Exception("no work part")

    logger.info(f"work part is '{wp.Name}'")

    all_parts = utils.get_assembly_unique_parts(wp, True)

    logger.info(f"all_parts {[p.Name for p in all_parts]}")

    wave_parts = list(filter(is_frozen, all_parts))

    markID = NXOpen.Session.GetSession().SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "[NM] Unfreeze parts")  # type: ignore
    unfreeze_parts(wave_parts)

    markID = NXOpen.Session.GetSession().SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "[NM] Freeze parts")  # type: ignore
    freeze_parts(wave_parts)







if __name__ == "__main__":
    main()
