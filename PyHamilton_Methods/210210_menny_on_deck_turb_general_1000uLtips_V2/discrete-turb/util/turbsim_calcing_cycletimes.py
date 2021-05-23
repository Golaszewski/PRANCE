import os
import sys
turb_ctrl_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if turb_ctrl_path not in sys.path:
    sys.path.append(turb_ctrl_path)

from turb_control import ParamEstTurbCtrlr
import numpy as np
import matplotlib.pyplot as plt
import random
import time
import threading
import csv

class SimTurbidostat:
    def __init__(self, controller, cycle_time, setpoint=0.0, init_od=None, growth_k=2.08): # commonly cited double every 20 minutes
        self.cycle_time = cycle_time # in seconds
        self.growth_k = growth_k # ground truth k (hrs^-1), different from controller k estimate
        if init_od is None:
            init_od = controller.last_known_od()
        else:
            self = init_od # ground truth od, different from controller od
        self.od = init_od/(1 + controller.last_known_output())
        controller.output_limits = 0.0, .68
        controller.setpoint = setpoint
        self.controller = controller
        self.wait_thread = None

    def update(self, realtime=False):
        if self.wait_thread: # use threading for delays to allow multiple simultaneous real-time simulations
            self.wait_thread.join()
        # grow culture
        self.od = min(self.od*np.exp(self.cycle_time/3600*self.growth_k), 1.0)
        delta_time = None if realtime else self.cycle_time
        meas_noise = rand_between(-.005, .005) + .1/(1+random.random()*10000) # Occasional very large spikes, as when clumps occlude sensor
        meas_od = max(0.0001, self.od + meas_noise)
        if delta_time:
            transfer_vol_frac = self.controller.step(delta_time, meas_od)
        else:
            transfer_vol_frac = self.controller(meas_od) # exercise callable functionality
        # add mechanical/operational noise
        actual_transfer_vol_frac = transfer_vol_frac + rand_between(-.01, .01)
        # dilute according to command
        self.od = self.od/(1+actual_transfer_vol_frac)
        if realtime:
            self.wait_thread = threading.Thread(target=lambda: time.sleep(cycle_time))
            self.wait_thread.start() 

    def set_k(self, k):
        self.growth_k = k

    def set_od(self, od):
        self.od = od

def rand_between(a, b):
    return min(a,b) + random.random()*abs(b-a)

def n_turb_cycle_time(n):
    # using logs from 200121_menny_on_deck_turb_landscape
    reader_time = 241 # 4 minutes and 1 second. from logs.
    replace_time = 75 # 1 minute and 15 seconds. from logs.
    return max(n//8 * replace_time, n//96 * reader_time)


if __name__ == '__main__':
    with open('all_time_courses_all_possible_numbers_of_wells_up_to_480.csv', 'w+') as out_f:
        output_fields = ['num_turbs', 'cycle_time', 'turb_num', 'actual_k', 'hours', 'od_measurement', 'k_estimate', 'transfer_vol']
        writer = csv.DictWriter(out_f, fieldnames=output_fields)
        writer.writeheader()

        times = []
        def write_new_data():
            for i, sim_turb in enumerate(sim_turbs):
                od_course = sim_turb.controller.scrape_history('od')
                trans_vol_course = sim_turb.controller.scrape_history('output')
                k_est_course = sim_turb.controller.scrape_history('k_estimate')
                for time, od, trans_vol, k_est in zip(times, od_course, trans_vol_course, k_est_course):
                    writer.writerow({
                            'num_turbs': num_turbs,
                            'cycle_time': round(cycle_time/60, 3),
                            'turb_num': i,
                            'actual_k': round(sim_turb.growth_k, 3),
                            'hours': round(time, 3),
                            'od_measurement': round(od, 5),
                            'k_estimate': round(k_est, 3),
                            'transfer_vol': round(trans_vol, 4)
                            })
        def plotem():
            od_courses, output_courses, k_courses = ([st.controller.scrape_history(key) for st in sim_turbs] for key in ('od', 'output', 'k_estimate'))
            #print(k_courses)
            plt.plot(times, list(zip(*od_courses)))
            plt.figure()
            plt.plot(times, list(zip(*output_courses)))
            plt.figure()
            plt.plot(times, list(zip(*k_courses)))
            plt.figure()
            plt.plot([ks[-1] for ks in k_courses], [ods[-1] for ods in od_courses])
            plt.show()

        for num_turbs in range(8, 481):
            cycle_time = n_turb_cycle_time(num_turbs)
            controllers = [ParamEstTurbCtrlr(init_k=.45) for _ in range(num_turbs)]
            sim_turbs = [SimTurbidostat(ctrlr, cycle_time) for ctrlr in controllers]

            for w, sim_turb in enumerate(sim_turbs):
                sim_turb.controller.setpoint = .4
                sim_turb.set_od(rand_between(.0002, .7))
                # linear range between 2 bounds
                sim_turb.set_k((num_turbs-w)/num_turbs*.0001 + w/num_turbs*1.0)

            for i in range(100):
                print('cycle:', i)
                try:
                    #tooth_size = 40
                    #if i % tooth_size == 0:
                    #    tooth_height = .02 + rand_between(0,.06)
                    #    for w, sim_turb in enumerate(sim_turbs):
                    #        sim_turb.controller.setpoint = (i%(tooth_size*2)/tooth_size)*tooth_height+.4
                            #print((i%(tooth_size*2)/tooth_size)*tooth_height+.4)
                    for sim_turb in sim_turbs:
                        sim_turb.update()
                    #time.sleep(cycle_time/sim_time_dilation)
                except KeyboardInterrupt:
                    exit()#import pdb; pdb.set_trace()

            times = [i*cycle_time/3600 for i in range(len(sim_turbs[0].controller.history()))]
            write_new_data()

    plotem()
        #finally:
        #    for sim_turb in sim_turbs:
        #        sim_turb.controller.save(save_dir='sim_controller_history')

