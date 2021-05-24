import sys, time
from pacepump import PACEPumpDevice

# Prime all lines function: Run all lines enough to push out all air.
# Clear line function: function that continuously fills and flushes culture until
#   all the culture that was sitting in the line has been exchanged. Reservoir is left empty.
# Clean function: Calls: flush, [fill with bleach, flush]x2, [fill with water, flush]x2
# Fresh function: fills the reservoir with bacterial culture.

# To clean: vacuum-pulse the isolator. Empty both reservoir and isolator. Fill reservoir with bleach, then empty it. Fill it with water and empty it 4x. Fill isolator with bleach all the way to the top, empty its bottom portion, then pulse the vacuum and empty the rest. Do the same with the water 4x. 

use_isolator = False # TODO: IS THIS WHAT YOU WANT
num_wells = 16

res_capacity = 10.0 if use_isolator else 8.0 # TODO: IS THIS ALSO WHAT YOU WANT
res_drain_dead_vol = 7.0
res_vol_per_tip = 500/1000.0 # uL
if use_isolator:
    res_bac_level = res_drain_dead_vol + num_wells*res_vol_per_tip
else:
    res_bac_level = res_capacity

line_vols = {
        'res_waste':2.0,
        'res_bac':30.0,
        'res_water':6.0,
        'res_bleach':6.0,
        'isol_waste':6.0,
        'isol_water':6.0,
        'isol_bleach':6.0
        }

isol_vol_per_well = 1000.0/1000 # uL
isol_wells_vol = num_wells*isol_vol_per_well
isol_chamber_vol = 5.0 # TODO: IS THIS ALSO ALSO WHAT YOU WANT 93 - isol_wells_vol # 110 total to fill isolator to brim

margin = 1.15

def empty_isol_wells(p_dev): # empty chamber first
    p_dev.vacuum_pulse(3000)
    time.sleep(1.5)
    p_dev.pump({'isol_waste':isol_wells_vol})

if use_isolator:
    # IS THIS OVERRIDDEN BELOW?? Check!
    def complete_empty(p_dev):
        isol_amnt = (isol_chamber_vol + line_vols['isol_waste'])*margin
        p_dev.pump({'res_waste':(res_capacity + line_vols['res_waste'])*margin,
                    'isol_waste':isol_amnt})
        empty_isol_wells(p_dev)
        p_dev.pump({waste:line_vols[waste]*margin for waste in ('res_waste', 'isol_waste')})
else:
    # override default to include no isolator things
    def complete_empty(p_dev):
        p_dev.pump({'res_waste':(res_capacity + line_vols['res_waste'])*margin})

def empty_reservoir(p_dev, vol=res_capacity):
    vol = float(vol) # handle string args
    p_dev.pump({'res_waste':(vol + line_vols['res_waste'])*margin})

def prime_all_lines(p_dev):
    complete_empty(p_dev)
    waste_assignments = [('res_bac', 'res_waste'),
                       ('res_water', 'res_waste'),
                      ('res_bleach', 'res_waste')]
    if use_isolator:
        waste_assignments += [('isol_water', 'isol_waste'),
                             ('isol_bleach', 'isol_waste')]
    for liq, waste in waste_assignments:
        p_dev.pump({liq:line_vols[liq]})
        p_dev.pump({waste:line_vols[liq]*margin})
    refill_rinse(p_dev)

def clear_line(p_dev):
    empty_reservoir(p_dev)
    p_dev.pump({'res_bac':line_vols['res_bac'], 'res_waste':line_vols['res_bac']*3})

def clean(p_dev):
# To clean:  Fill reservoir with bleach, then empty it. Fill it with water and empty it 4x. Fill isolator with bleach all the way to the top, empty its bottom portion, then pulse the vacuum and empty the rest. Do the same with the water 4x. 
    complete_empty(p_dev)
    if use_isolator:
        p_dev.pump({'res_bleach':res_capacity,
                    'isol_bleach':isol_chamber_vol + isol_wells_vol})
    else:
        p_dev.pump({'res_bleach':res_capacity})
    time.sleep(5)
    complete_empty(p_dev)
    rinse_num = 3
    margin_inc = .01
    for rinse_round in range(1, rinse_num + 1):
        rinse_margin = 1.0 + margin_inc*rinse_round # go over the previous level a bit each time
        if use_isolator:
            p_dev.pump({'res_water':res_capacity*rinse_margin,
                'isol_water':(isol_chamber_vol + isol_wells_vol)*rinse_margin})
        else:
            p_dev.pump({'res_water':res_capacity*rinse_margin})
        complete_empty(p_dev)

def fresh(p_dev, bac_mls=res_bac_level):
    bac_mls = float(bac_mls) # handle string args
    empty_reservoir(p_dev)
    #p_dev.pump({'res_bac':line_vols['res_bac'], # flush out the long bac tube
    #            'res_waste':line_vols['res_bac']*margin})
    p_dev.pump({'res_bac':bac_mls})

def refill_rinse(p_dev):
    p_dev.pump({'isol_waste':7.0}) # Temp syringe water bath waste
    p_dev.pump({'isol_water':5.5}) # Temp syringe water bath supply

cmd_def = {'prime': prime_all_lines,
           'clear_line':clear_line,
           'clean':clean,
           'fresh':fresh,
           'empty':empty_reservoir,
           'refill_rinse':refill_rinse}

if __name__ == '__main__':
    with PACEPumpDevice() as p_dev:
        cmd = sys.argv[1]
        args = sys.argv[2:]
        cmd_def[cmd](p_dev, *args)
