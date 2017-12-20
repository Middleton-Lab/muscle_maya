from numpy import cross, eye, dot, array, pi
from numpy.linalg import norm
from math import atan2, sqrt

def ssc(v):
    '''
    Calculate the skew-symmetric cross-product matrix of v

    See: See: http://math.stackexchange.com/a/897677/6965
    '''

    return array([[0, -v[2], v[1]],
                  [v[2], 0, -v[0]],
                  [-v[1], v[0], 0]])


def RU(A, B):
    """
    Calculate the rotation matrix required to rotate vector A onto
    vector B. Both vectors will be normalized to a unit vectors prior to
    rotation.

    See: http://math.stackexchange.com/a/897677/6965
    """

    # Normalize A and B
    A_norm = A / norm(A)
    B_norm = B / norm(B)

    # Calculate the rotation matrix. Note that the order is x, y, x.
    U = eye(3) + ssc(cross(A_norm, B_norm)) + \
        (dot(ssc(cross(A_norm, B_norm)), ssc(cross(A_norm, B_norm))) *
            (1 - dot(A_norm, B_norm)) /
            (dot(norm(cross(A_norm, B_norm)), norm(cross(A_norm, B_norm)))))
    return U


def euler(U):
    """
    Decompose rotation matrix U into Euler angles.  Note that the order
    is x, y, x.

    See: http://nghiaho.com/?page_id=846
    """

    xrot = atan2(U[2, 1], U[2, 2]) * 180 / pi
    yrot = atan2(-U[2, 0], sqrt(U[2, 1] ** 2 + U[2, 2] ** 2)) * 180 / pi
    zrot = atan2(U[1, 0], U[0, 0]) * 180 / pi
    return [xrot, yrot, zrot]

def get_euler_angles(A, B):
    """Calculate the Euler angles for rotating A onto B.

    The utility is to set up geometry with a known normal (0, 1, 0),
    and calculate the xyz rotation sequence to match another vector.
    """
    U = RU(A, B)
    euler_angles = euler(U)
    return euler_angles
