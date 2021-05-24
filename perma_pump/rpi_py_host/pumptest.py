from pacepump import PACEPumpDevice


bit_assigns = {n:1<<i for i, n in enumerate(('res_waste', 'res_bac', 'res_water', 'res_bleach', 'isol_waste', 'isol_water', 'isol_bleach'))}


with PACEPumpDevice() as pd:
    vol = .5
    for n in bit_assigns:
        pd.pump({n:vol})
    #exit()
    pd.vacuum_pulse(1000)
    for i in range(2**len(bit_assigns)):
        print bin(i)
        args = {n:vol*(1 if i%3 == 0 else -1) for n in bit_assigns if bit_assigns[n]&i}
        print args
        pd.pump(args)

