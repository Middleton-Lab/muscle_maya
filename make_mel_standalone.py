#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Generate mel script for stl and data file

@author: Kevin Middleton

"""

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

from numpy import array
import pandas as pd
import os
import time

# Check pandas version (>= 0.17.1)
# There is a problem getting named tuples in 0.17.0 (and possibly lower)
pd_version = float(pd.__version__[2:])
if pd_version <= 17.0:
    raise ImportWarning("pandas version should be >= 0.17.1")

def make_mel(base_path, stlfile, datafile, sheet_name, scale_radius, cylinder_r_max, rev_arrows, rescale_factor):
    file_prefix = stlfile[:-4]

    outfile = os.path.join(base_path, file_prefix + ".mel")

    # Read data file
    M = pd.read_excel(os.path.join(base_path, datafile), sheet_name=sheet_name)

    M = M[M.ID == file_prefix]

    # Set up radii for cylinder and cone
    if scale_radius:
        # Normalize to maximum force value
        M['cylinder_r'] = M.force / max(M.force)
        M.cylinder_r *= cylinder_r_max
    else:
        M['cylinder_r'] = cylinder_r_max / 2

    M['cone_r'] = M.cylinder_r * 2
    M['cone_hr'] = 2  # cone_r / 2

    # Open mel script outfile for writing
    print('Writing ' + outfile)
    f = open(outfile, 'w')

    # Write header info
    f.write('// File: ' + outfile + '\n')
    f.write('// Generated: ' + time.strftime("%Y/%m/%d %H:%M:%S") + '\n')
    f.write('// Note: the ratio of max to min forces is ')
    f.write(str(round(max(M.force) / min(M.force), 3)))
    f.write('.\n\n')

    # Import shader information
    f.write('// Import color shader presets\n')
    f.write('file -import -type "mayaBinary"  -ignoreVersion -ra true ')
    f.write('-mergeNamespacesOnClash false -namespace "Color_Presets" ')
    f.write('-options "v=0;"  -pr "Color_Presets.mb";\n\n')

    # Import model. Note need full path to stl.
    f.write('// Import Alligator model\n')
    f.write('file -import -type "STL_ATF"  -ignoreVersion -ra true ')
    f.write('-mergeNamespacesOnClash false -namespace "' + file_prefix + '" ')
    f.write('-pr "' + os.path.abspath(stlfile) + '";\n')
    f.write('rename polySurface1 stl_model;\n')
    f.write('select -r stl_model;\n')
    f.write('hyperShade -assign Color_Presets:Bone;\n')
    f.write('hide stl_model;\n\n')

    # Loop through muscles in coordinates file
    for data in M.itertuples():
        muscle = data.muscle[0] + data.muscle[2:]
        f.write('// Muscle ' + muscle + ';\n')

        if rev_arrows:
            insertion_x = data.x_insertion
            insertion_y = data.y_insertion
            insertion_z = data.z_insertion
            origin_x = data.x_origin
            origin_y = data.y_origin
            origin_z = data.z_origin
        else:
            # Note reversing origin and insertion from coords file to put the arrows
            # on the correct end.
            insertion_x = data.x_origin
            insertion_y = data.y_origin
            insertion_z = data.z_origin
            origin_x = data.x_insertion
            origin_y = data.y_insertion
            origin_z = data.z_insertion

        origin_coords = str(origin_x) + ' ' + str(origin_y) + ' ' + \
            str(origin_z)
        insertion_coords = str(insertion_x) + ' ' + str(insertion_y) + ' ' + \
            str(insertion_z)

        # Euler angles
        origin = array([origin_x, origin_y, origin_z])
        insertion = array([insertion_x, insertion_y, insertion_z])
        B = insertion - origin
        A = array([0., 1., 0.])
        R = get_euler_angles(A, B)
        rotations = str(R[0]) + ' ' + str(R[1]) + ' ' + str(R[2])


        # Create a curve from origin to insertion
        f.write('curve -n curve1 -d 1 -p ' + origin_coords + ' -p ' +
            insertion_coords + ' -k 0 -k 1;\n')

        # Create a circle at the origin with a (0, 1, 0) normal
        f.write('circle -n circ -ch on -o on -c ' + origin_coords + ' -nrx 0 ')
        f.write('-nry 1 -nrz 0 -radius ' + str(data.cylinder_r) + ';\n')

        # Apply Euler rotations
        f.write('rotate -r -pivot ' + origin_coords + ' -xyz ' + rotations +
            ' circ;\n')

        # Extrude cylinder
        f.write('extrude -n ' + muscle + 'cyl -et 1 -po 0 circ curve1;\n')

        # Make, rotate, and move cone
        f.write('cone -n ' + muscle + 'Cone -po 0 -axis 0 1 0 -r ' +
            str(data.cone_r) + ' -hr ' + str(data.cone_hr) + ';\n')
        f.write('rotate -r -xyz ' + rotations + ' ' + muscle + 'Cone;\n')
        f.write('move ' + insertion_coords + ' ' + muscle + 'Cone;\n')

        # Clean up
        f.write('select -r curve1;\n')
        f.write('doDelete;\n')
        f.write('select -r circ;\n')
        f.write('doDelete;\n')

        # Apply shader
        shader = 'Color_Presets:' + muscle[1:] + "SG"
        f.write('select -r ' + muscle + 'Cone' + ' ' + muscle + 'cyl;\n')
        f.write('hyperShade -assign ' + shader + ';\n')

        # Reverse surface normals
        f.write('reverseSurface -ch on -rpo on -d 3 ' + muscle + 'cyl;\n\n')

    # Unhide stl_model
    f.write('// Unhide stl_model;\n')
    f.write('showHidden stl_model;\n')

    # Group all objects together
    f.write('// Group objects for animation;\n')
    f.write('')

    f.close()

    print('\n')
 
# Light above
# defaultAreaLight(1, 1,1,1, 0, 0, 0,0,0, 1, 0);
# setAttr "areaLight1.rotateX" -90;
# setAttr "areaLight1.translateY" 50;
# setAttr "areaLight1.scaleX" 40;
# setAttr "areaLight1.scaleY" 40;
# defaultAreaLight(1, 1,1,1, 0, 0, 0,0,0, 1, 0);
# Light below
# setAttr "areaLight2.rotateX" 90;
# setAttr "areaLight2.translateY" -50;
# setAttr "areaLight2.scaleX" 40;
# setAttr "areaLight2.scaleY" 40;
# setAttr "areaLightShape1.intensity" 0.2;
# setAttr "areaLightShape2.intensity" 0.2;
#

control_file = '/Users/kmm/Google Drive/Work/Research/Alligator Maya/specimens/Control_File.xlsx'
ctrl = pd.read_excel(control_file)

for data in ctrl.itertuples():
    print("Processing " + data.base_path)
    make_mel(data.base_path,
             data.stlfile,
             data.datafile,
             data.sheet_name,
             data.scale_radius,
             data.cylinder_r_max,
             data.rev_arrows,
             data.rescale_factor)


# base_path = '/Users/kmm/Google Drive/Work/Research/Alligator Maya/specimens/alligator/AL_008'
# stlfile = 'AL_008.stl'
# datafile = 'AL_008_joints.xlsx'
# sheet_name = 'Sheet1'
# scale_radius = True
# cylinder_r_max = 8
# rev_arrows = True
# rescale_factor = 1
