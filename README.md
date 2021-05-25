# PRANCE: Phage-and-Robotics Assisted Near-Continuous Evolution

PRANCE is a new method for PHAGE-assisted evolution of biomolecules.

For a Hamilton robot to be PRANCE-compatible, certain equipment must be installed.

### P&ID for Liquid Flow-paths
![alt text](https://github.com/Golaszewski/PRANCE/blob/main/Extras/pid.png)

### Pumps
Agrowtek AD6i dosing pump is recommended for the custom pump array.

https://www.agrowtek.com/index.php/products/dosing_systems/dosing-pumps/agrowdose-adi-digital-persitaltic-dosing-pumps-detail

For installation refer to the perma_pump folder.

### Orbital Shaker

The orbital shaker is fitted to the waffle. Refer to the perma_shaker folder for installation.

http://www.bigbearautomation.com/HT91108.htm

### Waffle

The waffle is a 3D printed part designed by the authors which is used as a staging point for bacteria culture loaded onto the deck. The 3D printing (.stl) file can be obtained from the Waffle folder.

### Scripts

Ready-made scripts for running PRANCE and other methods are in PyHamilton_Methods. To run one of these, open a CMD shell, navigate to the folder
containing the desired script, and run with py. For example:
```bat
cd PRANCE\PyHamilton_Methods\210210_PRANCE_w_errorrecovery\reusable-pace
py robot_method.py
```
