#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Generate mel script for stl and data file

@author: Kevin Middleton

"""

from rotation_matrix import get_euler_angles
from numpy import array
import pandas as pd
import os
import time
import argparse

# Check pandas version (>= 0.17.1)
# There is a problem getting named tuples in 0.17.0 (and possibly lower)
pd_version = float(pd.__version__[2:])
if pd_version <= 17.0:
    raise ImportWarning("pandas version should be >= 0.17.1")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Options')
    parser.add_argument('--stl',
                        help='.stl file',
                        required=True)

    parser.add_argument('--data',
                        help='Path to file with coordinate and force data',
                        required=True)

    parser.add_argument('--sheet',
                        help='Name of excel sheet to read',
                        required=True)

    parser.add_argument('--scale_radius',
                        help='Scale radius to maximum value',
                        action='store_true',
                        default=True,
                        required=False)

    parser.add_argument('--max_radius',
                        help='Maximum force vector radius',
                        type=float,
                        default=8,
                        required=False)

    parser.add_argument('--rev_arrows',
                        help='Reverse arows',
                        default=True,
                        required=False)

    args = parser.parse_args()

    stlfile = args.stl
    datafile = args.data
    sheetname = args.sheet
    scale_radius = args.scale_radius
    cylinder_r_max = args.max_radius
    rev_arrows = args.rev_arrows

    print("scale_radius =", scale_radius)

    file_prefix = stlfile[:-4]

    outfile = file_prefix + ".mel"

    # Read data file
    M = pd.read_excel(datafile, sheetname=sheetname)

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

# defaultAreaLight(1, 1,1,1, 0, 0, 0,0,0, 1, 0);
# setAttr "areaLight1.rotateX" -90;
# setAttr "areaLight1.translateY" 50;
# setAttr "areaLight1.scaleX" 40;
# setAttr "areaLight1.scaleY" 40;
# defaultAreaLight(1, 1,1,1, 0, 0, 0,0,0, 1, 0);
# setAttr "areaLight2.rotateX" 90;
# setAttr "areaLight2.translateY" -50;
# setAttr "areaLight2.scaleX" 40;
# setAttr "areaLight2.scaleY" 40;
# setAttr "areaLightShape1.intensity" 0.2;
# setAttr "areaLightShape2.intensity" 0.2;
#
