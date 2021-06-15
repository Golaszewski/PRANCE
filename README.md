# PRANCE: Phage-and-Robotics Assisted Near-Continuous Evolution

![alt text](https://github.com/Golaszewski/PRANCE/blob/main/Extras/Life-cycle-of-filamentous-phages-Filamentous-phage-binds-to-the-F-pilus-of-a-host-E%20(1).png)

*Huang, Johnny & Bishop-Hurley, Sharon & Cooper, Matthew. (2012). Development of Anti-Infectives Using Phage Display: Biological Agents against Bacteria, Viruses, and Parasites. Antimicrobial agents and chemotherapy. 56. 4569-82. 10.1128/AAC.00567-12.*

PRANCE is a new method for phage-assisted evolution of biomolecules. The ability of an M13 bacteriophage protein to perform some objective function is tied to the phage's ability to reproduce, thereby selecting for phage variants which successfully perform the objective function in an evolutionary sense.

To accomplish this, bacteria are constantly cycled onto the deck into wells containing evolving populations of the M13 phage. The flowrate of bacteria culture is fast enough that they do not have time to divide before being cycled off the deck into waste. Meanwhile, samples of the phage-inoculated wells (or lagoons) are dispensed to reader plates which are transported to a ClarioStar plate reader to assess the average phage activity in each well. This data is used to automatically update the stringency of the selection on a well-to-well basis, providing a form of automatic feedback control for the slection. 

https://www.biorxiv.org/content/10.1101/2020.04.01.021022v1


For a Hamilton robot to be PRANCE-compatible, certain equipment must be installed.

## How to enable PRANCE on a Hamilton Microlab STAR

The most general requirements for running PRANCE are a way to load multiple
sources of bacteria culture at a fixed optical density onto the robot deck, a way to wash and
sterilize tips for reuse, and a way to automatically obtain real-time spectrophotometric 
measurements from phage-inoculated bacteria culture.

This repository provides a Python script for running PRANCE, but 
also outlines certain equipment, configurations, and practices that
the authors have found to be the easiest and most widely accessible means
of enabling PRANCE to run on a Hamilton Microlab STAR. The code provided
only works with the specific equipment indicated in this guide. Different equipment will produce the 
same experimental outcome  as long as the protocol is followed, but you will have to create and implement 
your own integration schemes if you choose this option. 


Equipment | Description
------------- | -------------
Pumps  | Agrowtek AD6i dosing pump is recommended for the custom pump array.
Orbital Shaker | The orbital shaker used here is the HT91108 from Big Bear Automation. It is fitted to the waffle with a baseboard. Refer to the perma_shaker folder for installation.
Waffle | The waffle is a 3D printed part designed by the authors which is used as an initial staging point for bacteria culture as it is loaded onto the deck. The 3D printing (.stl) file can be obtained from the Waffle folder.
Plate Reader |  The plate reader is a Clariostar Plate Reader. Follow the instructions in the perma_plate_reader folder for detailed installation instructions.
Hamilton CO-RE 384 Wash Station | This includes the bleach, water, and waste storage tanks and a pump array connecting these to the wash station itself. These storage tanks have separate hookups to the waffle to enable washing and sterilization between bacteria loading cycles.



## Flowpaths for PRANCE

The washer pump module loads bleach and water from storage tanks into the CO-RE washer module on the robot deck. The washer pump module also pumps water, bleach solution, and waste from the washer module into the waste storage tank. A separate pump constantly pumps waste from the waste storage tank to the sink for automatic disposal. Note that bleach inactivation of biohazards may take up to 20 minutes. Check with your EHS team to make sure your PRANCE setup is compliant with health and safety standards.

An array of six pumps is used to load bacteria culture onto the waffle, and to wash and sterilize the waffle. Three pumps are used with three separate surgical tubing lines to
load bacteria from flasks, held in a 4 deg. C refrigerator to keep bacteria at constant optical density. Two pumps are used to load bleach and water, respectively, into the waffle and one pump is used to flush liquid from the waffle into the waste storage tank. 

### Flow Diagram for PRANCE
![alt text](https://github.com/Golaszewski/PRANCE/blob/main/Extras/pid.png)

## Deck Layout for PRANCE

The deck layout for PRANCE consists of the waffle+shaker, the CO-RE washer module, 1000uL pipette tip racks, several sets of wells to hold bacteria culture at various stages, and reader plates for measuring samples from phage-inoculated bacteria culture.

Refer to the \assets\deck.lay file in the relevant method folder for the exact configuration of deck components.

![alt text](https://github.com/Golaszewski/PRANCE/blob/main/Extras/decklayout.svg)


## Running PRANCE Scripts

Ready-made scripts for running PRANCE and other methods are in PyHamilton_Methods. To run one of these, open a CMD shell, navigate to the folder
containing the desired script, and run with py. For example:
```bat
cd PRANCE\PyHamilton_Methods\210210_PRANCE_w_errorrecovery\reusable-pace
py robot_method.py
```
