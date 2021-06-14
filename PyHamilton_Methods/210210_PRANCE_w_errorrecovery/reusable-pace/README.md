## PRANCE Script

This folder contains functions and utility files to run PRANCE. Once you have installed and configured your equipment and set up your experiment, it is time to run PRANCE. Just open CMD and enter the following commands.

```bat
cd PRANCE\PyHamilton_Methods\210210_PRANCE_w_errorrecovery
py robot_method.py
```

If the program has crashed mid-run and you would like to restart from the most recent checkpoint, run

```bat
py robot_method.py --error_recovery
```

To run a simulation, run

```bat
py robot_method.py --simulate
```

Other scripts are included to calibrate the position of your reader tray (`readertraycalibration.py`), stage pipette tips (`48tipstaging.py`), and other activities associated with PRANCE.


## Process Diagram



![alt_text](https://github.com/Golaszewski/PRANCE/blob/main/Extras/lagoon_prep.svg)

![alt_text](https://github.com/Golaszewski/PRANCE/blob/main/Extras/bleach_tips.svg)

![alt_text](https://github.com/Golaszewski/PRANCE/blob/main/Extras/prep_reader_plate.svg)

![alt_text](https://github.com/Golaszewski/PRANCE/blob/main/Extras/read_plate.svg)

