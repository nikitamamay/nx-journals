import NXOpen
import NXOpen.Assemblies

import this_logging
logger = this_logging.getLogger(__name__)


def measure_part(
        part_with_bodies: NXOpen.Part,
        csys_part: 'NXOpen.Part' = None, # type: ignore
        component: 'NXOpen.Assemblies.Component' = None  # type:ignore
        ) -> 'tuple[NXOpen.Point3d, float, float]':
    bodies = []
    for b in part_with_bodies.Bodies:  # type: ignore
        b: NXOpen.Body
        if b.IsSolidBody:
            if not component is None:
                b = component.FindOccurrence(b)  # type:ignore
            bodies.append(b)

    if len(bodies) == 0:
        raise Exception(f"No solid bodies found in part '{part_with_bodies.Name}'")

    if csys_part is None:
        csys_part = part_with_bodies

    units = [
        csys_part.UnitCollection.GetBase("Area"),
        csys_part.UnitCollection.GetBase("Volume"),
        csys_part.UnitCollection.GetBase("Mass"),
        csys_part.UnitCollection.GetBase("Length"),
        csys_part.UnitCollection.GetBase("Force"),  # for Weight
    ]

    mp = csys_part.MeasureManager.NewMassProperties(units, 0.95, bodies)
    logger.info(f"for part '{part_with_bodies.Name}' with {len(bodies)} bodies: mass={mp.Mass}, volume={mp.Volume}, area={mp.Area}, centroid={mp.Centroid}")

    return mp.Centroid, mp.Volume, mp.Area


def measure_body(body: NXOpen.Body, csys_part: 'NXOpen.Part' = None):  # type:ignore
    if csys_part is None:
        csys_part = body.OwningPart

    units = [
        csys_part.UnitCollection.GetBase("Area"),
        csys_part.UnitCollection.GetBase("Volume"),
        csys_part.UnitCollection.GetBase("Mass"),
        csys_part.UnitCollection.GetBase("Length"),
        csys_part.UnitCollection.GetBase("Force"),  # for Weight
    ]

    mp = csys_part.MeasureManager.NewMassProperties(units, 0.95, [body])

    logger.info(f"for body '{body.Name}' in '{body.OwningPart.Name}': mass={mp.Mass}, volume={mp.Volume}, area={mp.Area}, centroid={mp.Centroid}")

    return mp.Centroid, mp.Volume, mp.Area
