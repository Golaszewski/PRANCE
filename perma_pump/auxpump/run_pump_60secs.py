from auxpump.pace import PACEDeckPumps
print('Pump for 1 minute. CTRL+C to stop.')
vol = 20
with PACEDeckPumps() as pumps:
    for pump_id in 1, 4, 5:
        pumps._run_direct({pump_id:vol, 0:vol+5})
