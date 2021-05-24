import sys
import time
import ast

from i2cpump import PumpDevice

# Prime all lines function: Run all lines enough to push out all air.
# Clear line function: function that continuously fills and flushes culture until
#   all the culture that was sitting in the line has been exchanged. Reservoir is left empty.
# Clean function: Calls: flush, [fill with bleach, flush]x2, [fill with water, flush]x2
# Fresh function: fills the reservoir with bacterial culture.

#use_isolator = False
#num_wells = 16

res_capacity = 35
res_bac_level = res_capacity

line_vols = {
        'res_waste':6.0, #'res_waste':20.0, # added when switching to weaker pump after original waste pump failed 190411
        'res_bac':10.0,
        'res_water':6.0,
        'res_bleach':6.0,
        'isol_waste':6.0,
        'isol_water':6.0,
        'isol_bleach':6.0
        }

#isol_vol_per_well = 1000.0/1000 # uL
#isol_wells_vol = num_wells*isol_vol_per_well
#isol_chamber_vol = 5.0

margin = 1.15

#def empty_isol_wells(p_dev): # empty chamber first
#    p_dev.vacuum_pulse(3000)
#    time.sleep(1.5)
#    p_dev.pump({'isol_waste':isol_wells_vol})

def complete_empty(p_dev, res_capacity=res_capacity):
    p_dev.pump({'res_waste':(res_capacity + line_vols['res_waste'])*margin})

def empty_reservoir(p_dev, vol=res_capacity):
    vol = float(vol) # handle string args
    p_dev.pump({'res_waste':(vol + line_vols['res_waste'])*margin})

def prime_all_lines(p_dev):
    complete_empty(p_dev)
    waste_assignments = [('res_bac', 'res_waste'),
                       ('res_water', 'res_waste'),
                      ('res_bleach', 'res_waste')]
    for liq, waste in waste_assignments:
        p_dev.pump({liq:line_vols[liq]})
        p_dev.pump({waste:line_vols[liq]*margin})
    #refill_rinse(p_dev)

def clear_line(p_dev):
    empty_reservoir(p_dev)
    p_dev.pump({'res_bac':line_vols['res_bac'], 'res_waste':line_vols['res_bac']*3})

def clean(p_dev, vol=res_capacity):
    # To clean:  Fill reservoir with bleach, then empty it. Fill it with water and empty it 4x.
    vol = float(vol) # handle string args
    complete_empty(p_dev, vol)
    p_dev.pump({'res_bleach':vol})
    time.sleep(5)
    complete_empty(p_dev, vol)
    rinse_num = 4
    for rinse_round in range(rinse_num):
        p_dev.pump({'res_water':vol*margin})
        complete_empty(p_dev, vol)

def fresh(p_dev, bac_mls=res_bac_level):
    bac_mls = float(bac_mls) # handle string args
    empty_reservoir(p_dev)
    p_dev.pump({'res_bac':line_vols['res_bac'], # flush out the long bac tube
                'res_waste':line_vols['res_bac']*margin})
    p_dev.pump({'res_bac':bac_mls})

#def refill_rinse(p_dev):
#    p_dev.pump({'isol_waste':7.0}) # Temp syringe water bath waste
#    p_dev.pump({'isol_water':5.5}) # Temp syringe water bath supply

def direct_command(p_dev, map_str):
    # use map_str, an eval-able dict of pump ids (ints or default names)
    # to volumes. execute all given pump commands simultaneously.
    test_l = list(map_str.strip())
    if (not (test_l.pop(0) == '{' and test_l.pop() == '}')
        or any(s in test_l for s in '[]{}')):
        raise ValueError('malformed map from pump ids to volumes ' + map_str)
    cmd_dict = ast.literal_eval(map_str)
    if not all((isinstance(k, int) or isinstance(k, str))
           and (isinstance(v, int) or isinstance(v, float))
           for k, v in cmd_dict.iteritems()):
        raise ValueError('malformed map from pump ids to volumes ' + map_str)
    p_dev.pump(cmd_dict)

cmd_def = {'prime': prime_all_lines,
           'clear_line':clear_line,
           'clean':clean,
           'fresh':fresh,
           'empty':empty_reservoir,
           #'refill_rinse':refill_rinse,
           'direct_cmd':direct_command}

if __name__ == '__main__':
    with PumpDevice() as p_dev:
        cmd = sys.argv[1]
        args = sys.argv[2:]
        cmd_def[cmd](p_dev, *args)
