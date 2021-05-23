from pace_util import (HamiltonInterface, normal_logging, initialize, tip_pick_up, tip_eject,
                       LayoutManager, Tip96, resource_list_with_prefix)

lay_mgr = LayoutManager("assets\\48staging.lay")

start_tips = resource_list_with_prefix(lay_mgr, "start_tips_", Tip96, 5)
dest_tips = resource_list_with_prefix(lay_mgr, "dest_tips_", Tip96, 5)

if __name__ == '__main__':
    with HamiltonInterface() as ham_int: # initializing Hamilton interface
        normal_logging(ham_int)
        initialize(ham_int)
        for start_tiprack, dest_tiprack in zip(start_tips, dest_tips):
            for col_start in range(0, 96, 16): # start indexes of even columns (0, 16, 32...)
                tip_pick_up(ham_int, [(start_tiprack, col_start + 8 + i) for i in range(8)]) # odd column
                tip_eject(ham_int, [(dest_tiprack, col_start + i) for i in range(8)]) # even column
