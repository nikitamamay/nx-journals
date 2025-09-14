
import typing

import os
import this_logging

import math

import NXOpen
import NXOpen.Assemblies
import NXOpen.GeometricUtilities
import NXOpen.PDM
import NXOpen.Positioning
import NXOpen.UF

import measure

logger = this_logging.getLogger(__name__)



def get_vector_X() -> NXOpen.Vector3d:
    v = NXOpen.Vector3d()
    v.X = 1
    return v


def get_vector_Y() -> NXOpen.Vector3d:
    v = NXOpen.Vector3d()
    v.Y = 1
    return v


def get_vector_Z() -> NXOpen.Vector3d:
    v = NXOpen.Vector3d()
    v.Z = 1
    return v


def get_identity_matrix() -> NXOpen.Matrix3x3:
    """
    Возвращает единичную матрицу.
    ```
    Xx=1     Xy=0     Xz=0
    Yx=0     Yy=1     Yz=0
    Zx=0     Zy=0     Zz=1
    ```
    Такая матрица может служить как:
    - матрица поворота с нулевыми поворотами вокруг осей;
    - матрица из трёх векторов X, Y, Z глобальной системы координат.
    """
    m = NXOpen.Matrix3x3()
    m.Xx = 1
    m.Yy = 1
    m.Zz = 1
    return m


def get_vector_length(v: NXOpen.Vector3d) -> float:
    return math.sqrt(v.X ** 2 + v.Y ** 2 + v.Z ** 2)


def get_scalar_product(v1: NXOpen.Vector3d, v2: NXOpen.Vector3d) -> float:
    return v1.X * v2.X + v1.Y * v2.Y + v1.Z * v2.Z


def get_vector_product(v1: NXOpen.Vector3d, v2: NXOpen.Vector3d) -> NXOpen.Vector3d:
    v3 = NXOpen.Vector3d()
    v3.X = v1.Y * v2.Z - v1.Z * v2.Y
    v3.Y = v1.Z * v2.X - v1.X*v2.Z
    v3.Z = v1.X * v2.Y - v1.Y * v2.X
    return v3


def matrix_to_array(m: NXOpen.Matrix3x3) -> 'list[list[float]]':
    return [
        [m.Xx, m.Xy, m.Xz],
        [m.Yx, m.Yy, m.Yz],
        [m.Zx, m.Zy, m.Zz],
    ]


def array_to_matrix(arr: 'list[list[float]]') -> NXOpen.Matrix3x3:
    m = NXOpen.Matrix3x3()
    m.Xx, m.Xy, m.Xz = arr[0]
    m.Yx, m.Yy, m.Yz = arr[1]
    m.Zx, m.Zy, m.Zz = arr[2]
    return m


def multiply_matrixes(m1: NXOpen.Matrix3x3, m2: NXOpen.Matrix3x3) -> NXOpen.Matrix3x3:
    arr1 = matrix_to_array(m1)
    arr2 = matrix_to_array(m2)
    arr3 = matrix_to_array(NXOpen.Matrix3x3())
    for i in range(3):
        for j in range(3):
            arr3[i][j] = 0
            for k in range(3):
                arr3[i][j] += arr1[i][k] * arr2[k][j]
    return array_to_matrix(arr3)


def copy_point(point: NXOpen.Point3d) -> NXOpen.Point3d:
    p = NXOpen.Point3d()
    p.X = point.X
    p.Y = point.Y
    p.Z = point.Z
    return p

def copy_vector(vector: NXOpen.Vector3d) -> NXOpen.Vector3d:
    v = NXOpen.Vector3d()
    v.X = vector.X
    v.Y = vector.Y
    v.Z = vector.Z
    return v


def get_vector_from_points(start: NXOpen.Point3d, end: NXOpen.Point3d) -> NXOpen.Vector3d:
    v = NXOpen.Vector3d()
    v.X = end.X - start.X
    v.Y = end.Y - start.Y
    v.Z = end.Z - start.Z
    return v


def get_angle_between_vectors(v1: NXOpen.Vector3d, v2: NXOpen.Vector3d) -> float:
    sp = get_scalar_product(v1, v2)
    l1 = get_vector_length(v1)
    l2 = get_vector_length(v2)
    angle = math.acos(sp / l1 / l2)
    return angle


def get_angle_with_axis(v1: NXOpen.Vector3d, v2: NXOpen.Vector3d) -> 'tuple[NXOpen.Vector3d, float]':
    v3 = get_vector_product(v1, v2)
    sp = get_scalar_product(v1, v2)
    l1 = get_vector_length(v1)
    l2 = get_vector_length(v2)
    l3 = get_vector_length(v3)
    if l3 == 0.0:
        return (get_vector_X(), 0.0)
    angle_sin = l3 / l1 / l2
    angle_cos = sp / l1 / l2
    angle = math.atan2(angle_sin, angle_cos)
    v3 = normalize_vector(v3)
    logger.info(f"angle={math.degrees(angle)}deg, sin={angle_sin}, cos={angle_cos}, v3={v3}")
    return v3, angle


def multiply_vector(v: NXOpen.Vector3d, x: float) -> NXOpen.Vector3d:
    v.X *= x
    v.Y *= x
    v.Z *= x
    return v


def normalize_vector(v: NXOpen.Vector3d) -> NXOpen.Vector3d:
    l = get_vector_length(v)
    return multiply_vector(v, 1/l)


def transform_point(point: NXOpen.Point3d, transform_matrix: NXOpen.Matrix3x3) -> NXOpen.Point3d:
    p = NXOpen.Point3d()
    p.X = point.X * transform_matrix.Xx + point.Y * transform_matrix.Yx + point.Z * transform_matrix.Zx
    p.Y = point.X * transform_matrix.Xy + point.Y * transform_matrix.Yy + point.Z * transform_matrix.Zy
    p.Z = point.X * transform_matrix.Xz + point.Y * transform_matrix.Yz + point.Z * transform_matrix.Zz
    return p


def transform_vector(vector: NXOpen.Vector3d, transform_matrix: NXOpen.Matrix3x3) -> NXOpen.Vector3d:
    v = NXOpen.Vector3d()
    v.X = vector.X * transform_matrix.Xx + vector.Y * transform_matrix.Yx + vector.Z * transform_matrix.Zx
    v.Y = vector.X * transform_matrix.Xy + vector.Y * transform_matrix.Yy + vector.Z * transform_matrix.Zy
    v.Z = vector.X * transform_matrix.Xz + vector.Y * transform_matrix.Yz + vector.Z * transform_matrix.Zz
    return v


def project_vector_to_plane(vector: NXOpen.Vector3d, plane_normal: NXOpen.Vector3d) -> NXOpen.Vector3d:
    return get_vector_product(get_vector_product(plane_normal, vector), plane_normal)


def get_vectors_from_matrix(csys_orientation: NXOpen.Matrix3x3) -> 'tuple[NXOpen.Vector3d, NXOpen.Vector3d, NXOpen.Vector3d]':
    """
    Orientation - это матрица, где `(Xx, Xy, Xz)` - координаты вектора оси Х компонента в системе координат сборки; то же и для `(Yx, Yy, Yz)` и `(Zx, Zy, Zz)`.
    """
    vectorX = NXOpen.Vector3d()
    vectorX.X = csys_orientation.Xx
    vectorX.Y = csys_orientation.Xy
    vectorX.Z = csys_orientation.Xz

    vectorY = NXOpen.Vector3d()
    vectorY.X = csys_orientation.Yx
    vectorY.Y = csys_orientation.Yy
    vectorY.Z = csys_orientation.Yz

    vectorZ = NXOpen.Vector3d()
    vectorZ.X = csys_orientation.Zx
    vectorZ.Y = csys_orientation.Zy
    vectorZ.Z = csys_orientation.Zz
    return (vectorX, vectorY, vectorZ)


def get_matrix_from_vectors(vectorX: NXOpen.Vector3d, vectorY: NXOpen.Vector3d, vectorZ: NXOpen.Vector3d) -> NXOpen.Matrix3x3:
    """
    Orientation - это матрица, где `(Xx, Xy, Xz)` - координаты вектора оси Х компонента в системе координат сборки; то же и для `(Yx, Yy, Yz)` и `(Zx, Zy, Zz)`.
    """
    csys_orientation = NXOpen.Matrix3x3()
    csys_orientation.Xx = vectorX.X
    csys_orientation.Xy = vectorX.Y
    csys_orientation.Xz = vectorX.Z
    csys_orientation.Yx = vectorY.X
    csys_orientation.Yy = vectorY.Y
    csys_orientation.Yz = vectorY.Z
    csys_orientation.Zx = vectorZ.X
    csys_orientation.Zy = vectorZ.Y
    csys_orientation.Zz = vectorZ.Z
    return csys_orientation


def get_rotation_matrix(angle_X: float, angle_Y: float, angle_Z: float) -> NXOpen.Matrix3x3:
    """
    Matrix3x3 - это:
    Xx  Xy  Xz
    Yx  Yy  Yz
    Zx  Zy  Zz
    """
    sinA, cosA = math.sin(angle_X), math.cos(angle_X)
    sinB, cosB = math.sin(angle_Y), math.cos(angle_Y)
    sinG, cosG = math.sin(angle_Z), math.cos(angle_Z)

    m = NXOpen.Matrix3x3()
    m.Xx = cosB * cosG
    m.Xy = -sinG * cosB
    m.Xz = sinB
    m.Yx = sinA * sinB * cosG + sinG * cosA
    m.Yy = -sinA * sinB * sinG + cosA * cosG
    m.Yz = -sinA * cosB
    m.Zx = sinA * sinG - sinB * cosA * cosG
    m.Zy = sinA * cosG + sinB * sinG * cosA
    m.Zz = cosA * cosB

    return m



def get_rotation_matrix_around_axis(axis_vector: NXOpen.Vector3d, angle: float) -> NXOpen.Matrix3x3:
    """
    Matrix3x3 - это:
    Xx  Xy  Xz
    Yx  Yy  Yz
    Zx  Zy  Zz
    """
    x = axis_vector.X
    y = axis_vector.Y
    z = axis_vector.Z
    cos = math.cos(angle)
    sin = math.sin(angle)
    m = NXOpen.Matrix3x3()
    m.Xx = cos + (1 - cos)*x*x
    m.Xy = (1 - cos) * x * y - sin*z
    m.Xz = (1 - cos) * x * z + sin * y
    m.Yx = (1 - cos) * y * x + sin * z
    m.Yy = cos + (1 - cos) * y * y
    m.Yz = (1 - cos) * y * z - sin * x
    m.Zx = (1 - cos) * z * x - sin * y
    m.Zy = (1 - cos) * z * y + sin * x
    m.Zz = cos + (1 - cos) * z * z
    return m



def orient_component(
        component: NXOpen.Assemblies.Component,
        target_orientation: NXOpen.Matrix3x3 = get_identity_matrix(),
        rotation_center_point: NXOpen.Point3d = NXOpen.Point3d(),
        ) -> None:
    parent_component = component.Parent
    if parent_component is None:
        logger.error(f"{component.Name} doesn't have parent component. Is it top level assembly?")
        return

    parent_part: NXOpen.Part = parent_component.Prototype  # type: ignore
    asm = parent_part.ComponentAssembly

    point_start, orientation = component.GetPosition()
    center_point_end = copy_point(rotation_center_point)

    logger.debug(f"original '{component.Name}' pos={point_start}, orient={orientation}")

    x_global, y_global, z_global = get_vectors_from_matrix(target_orientation)

    ### 1) вращение в плоскости X

    y_c = get_vectors_from_matrix(orientation)[1]
    y_c = project_vector_to_plane(y_c, x_global)

    axis, angleX_to_rotate = get_angle_with_axis(y_global, y_c)
    angleX_to_rotate *= -1  # минус, потому что функция возвращает фактическое значение угла, а надо вращать на этот угол в противоположную сторону

    mX = get_rotation_matrix_around_axis(axis, -angleX_to_rotate) # минус, потому что в NX повороты происходят по часовой стрелке

    orientation = multiply_matrixes(orientation, mX)
    center_point_end = transform_point(center_point_end, mX)

    logger.debug(f"after around X '{component.Name}' orient={orientation}")

    ### 2*) вращение в плоскости Z

    y_c = get_vectors_from_matrix(orientation)[1]
    y_c = project_vector_to_plane(y_c, z_global)

    axis, angleZ_to_rotate = get_angle_with_axis(y_global, y_c)
    angleZ_to_rotate *= -1  # минус, потому что функция возвращает фактическое значение угла, а надо вращать на этот угол в противоположную сторону

    mZ = get_rotation_matrix_around_axis(axis, -angleZ_to_rotate) # минус, потому что в NX повороты происходят по часовой стрелке

    orientation = multiply_matrixes(orientation, mZ)
    center_point_end = transform_point(center_point_end, mZ)
    logger.debug(f"after around Z '{component.Name}' orient={orientation}")

    ### 3*) вращение в плоскости Y

    z_c = get_vectors_from_matrix(orientation)[2]
    z_c = project_vector_to_plane(z_c, y_global)

    axis, angleY_to_rotate = get_angle_with_axis(z_global, z_c)
    angleY_to_rotate *= -1  # минус, потому что функция возвращает фактическое значение угла, а надо вращать на этот угол в противоположную сторону

    mY = get_rotation_matrix_around_axis(axis, -angleY_to_rotate) # минус, потому что в NX повороты происходят по часовой стрелке

    orientation = multiply_matrixes(orientation, mY)
    center_point_end = transform_point(center_point_end, mY)
    logger.debug(f"after around Y '{component.Name}' orient={orientation}")

    ### 4) линейное перемещение к центру

    vector_delta_translation = get_vector_from_points(center_point_end, rotation_center_point)

    ### 5) финиш

    m_total = multiply_matrixes(multiply_matrixes(mX, mZ), mY)

    asm.MoveComponent(component, vector_delta_translation, m_total)  # FIXME перемещения происходят в СК родительского компонента, а требуемые значения задаются в СК головной сборки
    logger.debug(f"end '{component.Name}' pos={point_start}, orient={orientation}")
    logger.info(f"Component '{component.Name}' is rotated")





def translate_component(component: NXOpen.Assemblies.Component, vector: NXOpen.Vector3d):
    parent_component = component.Parent
    if parent_component is None:
        logger.error(f"{component.Name} doesn't have parent component. Is it top level assembly?")
        return

    parent_part: NXOpen.Part = parent_component.Prototype  # type: ignore
    asm = parent_part.ComponentAssembly

    """При отсутсвии поворотов матрица должна быть диагональной!"""
    asm.MoveComponent(component, vector, get_identity_matrix())  # FIXME перемещения происходят в СК родительского компонента, а требуемые значения задаются в СК головной сборки
    logger.info(f"Component '{component.Name}' is translated")





def main():
    session: NXOpen.Session = NXOpen.Session.GetSession()
    ufsession: NXOpen.UF.UFSession = NXOpen.UF.UFSession.GetUFSession()

    markID = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "[NM] Run Journal")  # type: ignore

    wp = session.Parts.Work
    if wp is None:
        raise Exception("no work part")
    logger.info(f"work part is '{wp.Name}'")




    components: list[NXOpen.Assemblies.Component] = get_selected_objects(NXOpen.Assemblies.Component)  # type: ignore

    logger.info(f"selected components: {components}")


    csys = get_matrix_from_vectors(
        get_vector_X(),
        get_vector_Y(),
        get_vector_Z(),
    )


    for c in components:
        logger.info(f"component '{c.Name}'")
        # set_component_in_center_csys(c)

        parent_part: NXOpen.Part = c.Parent.Prototype  # type: ignore
        asm = parent_part.ComponentAssembly

        p: NXOpen.Part = c.Prototype  # type: ignore

        start_point = measure.measure_part(p, wp, c)[0]

        csys = get_identity_matrix()
        csys = c.Parent.Parent.GetPosition()[1]

        orient_component(c, csys, rotation_center_point=start_point)


    ### (!)

    # p: NXOpen.Part = c.Prototype  # type: ignore
    # bodies = list(p.Bodies)
    # b = c.FindOccurrence(bodies[0])



if __name__ == "__main__":
    main()
