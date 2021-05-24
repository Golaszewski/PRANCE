from pace_util import AgrowPumps

pumps=AgrowPumps(port="COM10")

pumps.ensure_empty()