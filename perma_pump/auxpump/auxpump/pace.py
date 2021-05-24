from .auxpump import NetworkDeckPumps

class OffDeckCulturePumps(NetworkDeckPumps):

    def clean_reservoir(self):
        self._run('clean')

    def prime_reservoir(self):
        self._run('prime')

    def fresh_reservoir(self):
        self._run('fresh')

    def refill_water_rinse(self):
        self._run('refill_rinse')

class PACEDeckPumps(OffDeckCulturePumps):
    pass # Backward compatibility

class LBPumps(NetworkDeckPumps):

    def bleach_clean(self, vol=35):
        self._run('clean', str(vol))

    def prime(self):
        self._run('prime')

    def refill(self, vol=50): # mL
        self._run('fresh', str(vol))

    def empty(self, vol=60):
        self._run('empty', str(vol))

    def fill_water(self, vol=50):
        self._run_direct({'res_water':vol})

    def fill_bleach(self, vol=50):
        self._run_direct({'res_bleach':vol})
