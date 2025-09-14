
import typing

import os
import this_logging

import NXOpen
import NXOpen.Assemblies
import NXOpen.PDM
import NXOpen.Positioning
import NXOpen.UF


logger = this_logging.getLogger(__name__)



PRECISION = 10**(-7)


def do_floats_equal(x: float, y: float) -> bool:
    return abs(x - y) < PRECISION




def find_fixable_components(part: NXOpen.Part) -> 'list[NXOpen.Assemblies.Component]':
    components: 'dict[str, NXOpen.Assemblies.Component]' = {}

    asm = part.ComponentAssembly
    if asm is None or asm.RootComponent is None:
        return []

    for child in asm.RootComponent.GetChildren():

        logger.debug(f"checking '{child.Name}' for being unconstained")

        if child.IsFixed:
            logger.debug(f"skipping '{child.Name}' since it is already fixed")
            continue

        if child.IsSuppressed:
            logger.debug(f"skipping '{child.Name}' since it is suppressed")
            continue

        if child.Name in components:
            logger.debug(f"skipping '{child.Name}' since component are constained previously")
            continue

        constraints = child.GetConstraints()

        if len(constraints) > 0:
            logger.debug(f"skipping '{child.Name}' since it is constrained")
            continue

        point: NXOpen.Point3d = child.GetPosition()[0]

        if not do_floats_equal(point.X, 0.0) or not do_floats_equal(point.Y, 0.0) or not do_floats_equal(point.Z, 0.0):
            logger.debug(f"skipping '{child.Name}' since it is not in (0,0,0)")
            continue

        logger.debug(f"listing '{child.Name}' to be constrained")
        components[child.Name] = child

    return list(components.values())


def fix_component(component: NXOpen.Assemblies.Component, do_set_workpart: bool = True) -> None:
    parent_component = component.Parent
    if parent_component is None:
        logger.error(f"{component.Name} doesn't have parent component. Is it top level assembly?")
        return

    parent_part: NXOpen.Part = parent_component.Prototype  # type: ignore
    if do_set_workpart:
        NXOpen.Session.GetSession().Parts.SetWork(parent_part)

    asm = parent_part.ComponentAssembly
    positioner = asm.Positioner

    if component.IsFixed:
        logger.info(f"Skipping '{component.Name}' in '{parent_part.Name}', since it is already fixed")
        return

    constraint: NXOpen.Positioning.ComponentConstraint = positioner.CreateConstraint(True)  # type: ignore
    constraint.ArrangementSpecific = False
    constraint.ConstraintType = NXOpen.Positioning.Constraint.Type.Fix  # type: ignore
    constraint.CreateConstraintReference(component, component, False, False)

    logger.info(f"Created fix constraint for component '{component.Name}'")




def main():
    session: NXOpen.Session = NXOpen.Session.GetSession()
    markID = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "[NM] Run Journal")  # type: ignore

    wp = session.Parts.Work
    logger.info(f"workpart is {wp}")

    # pdmpart: NXOpen.PDM.PdmPart = wp.PDMPart
    # pdm_session: NXOpen.PDM.PdmSession = session.PdmSession
    # pm: NXOpen.PDM.PartManager = session.Parts.PDMPartManager

    for c in find_fixable_components(wp):
        fix_component(c)



if __name__ == "__main__":
    main()
