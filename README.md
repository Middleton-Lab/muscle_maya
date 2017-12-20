# muscle_maya

## Input files

1. Coordinates file with at least the following columns
    - ID: matches the stem of the stl file. This is used to subset the rows matching ID, allowing you to store multiple sets of taxa or specimens in one file.
    - x_origin, y_origin, z_origin: (x, y, z) coordinates of the "origin"
    - x_insertion, y_insertion, z_insertion: (x, y, z) coordinates of the "insertion"
    - force: used to scale the diameter of the vector and arrow
    - muscle: Used to color vectors using standard Holliday lab palette
2. .stl file with model (binary format OK).

## Generate .mel script

The general pattern is:

```
python make_mel.py --stl "./full/path/to/stl" --data "forces_file.xlsx" --sheet "sheet_name"
```

Note that you need to include the full path to the stl file. The full path is not needed for the forces files, because it is not written to the maya file.

By default, the force vector diameteres are scaled to the to maximum force. The maximum radius can be set with '--max_radius'.

## In Maya

- Windows --> General Editors --> Script Editor
- Drop the .mel file into the MEL tab.
