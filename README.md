# PRANCE: Phage-and-Robotics Assisted Near-Continuous Evolution

PRANCE is a new method for phage-assisted evolution of biomolecules.

For a Hamilton robot to be PRANCE-compatible, certain equipment must be installed.

## How to enable PRANCE on a Hamilton Microlab STAR

The most general requirements for running PRANCE are a way to load multiple
sources of constant OD bacteria culture onto the robot deck, a way to wash and
sterilize tips for reuse, and a way to automatically obtain real-time spectrophotometric 
measurements from phage-inoculated bacteria culture on the deck.

This repository provides a Python script for running PRANCE, but 
also outlines certain equipment, configurations, and practices that
the authors have found to be the easiest and most widely accessible means
of enabling PRANCE to run on a Hamilton Microlab STAR. The script as provided
only works with the specific equipment indicated in this guide. While 
using different equipment will produce the same experimental outcomes as
long as the protocol is followed correctly, you will have to create and implement 
your own integration schemes if you choose this option. 

https://www.biorxiv.org/content/10.1101/2020.04.01.021022v1


### Pumps
Agrowtek AD6i dosing pump is recommended for the custom pump array.

https://www.agrowtek.com/index.php/products/dosing_systems/dosing-pumps/agrowdose-adi-digital-persitaltic-dosing-pumps-detail

For installation refer to the perma_pump folder.

### Orbital Shaker
The orbital shaker used here is the HT91108 from Big Bear Automation.
It is fitted to the waffle with a baseboard. Refer to the perma_shaker folder for installation.

http://www.bigbearautomation.com/HT91108.htm

### Waffle
The waffle is a 3D printed part designed by the authors which is used as an initial staging point for bacteria culture as it is loaded onto the deck. The 3D printing (.stl) file can be obtained from the Waffle folder.

### Plate Reader
The plate reader is a Clariostar Plate Reader. Follow the instructions in the perma_plate_reader folder for detailed installation instructions.

### Hamilton CO-RE 384 Wash Station
This includes the bleach, water, and waste storage tanks and a pump array connecting these to the wash station itself. These
storage tanks have separate hookups to the waffle to enable washing and sterilization between bacteria loading cycles.

### P&ID for Liquid Flow-paths
![alt text](https://github.com/Golaszewski/PRANCE/blob/main/Extras/pid.png)

### Deck Layout Diagram
![alt text](https://github.com/Golaszewski/PRANCE/blob/main/Extras/decklayout.svg)


### Scripts

Ready-made scripts for running PRANCE and other methods are in PyHamilton_Methods. To run one of these, open a CMD shell, navigate to the folder
containing the desired script, and run with py. For example:
```bat
cd PRANCE\PyHamilton_Methods\210210_PRANCE_w_errorrecovery\reusable-pace
py robot_method.py
```
