from pace_util_stefan_dev import resource_list_with_prefix
from pace_util_stefan_dev import LayoutManager
from pace_util_stefan_dev import Plate96
from pace_util_stefan_dev import Tip96
from pace_util_stefan_dev import LAYFILE
from pace_util_stefan_dev import layout_item

lay_mgr = LayoutManager(LAYFILE)

lagoons = layout_item(lay_mgr, Plate96, 'lagoons')
holding_wells = layout_item(lay_mgr, Plate96, 'holding_site')
waffle = layout_item(lay_mgr, Plate96, 'waffle')
inducer = layout_item(lay_mgr, Plate96, 'inducer_site')
inducer_wells = layout_item(lay_mgr, Plate96, 'inducer_wells')
reader_tray = layout_item(lay_mgr, Plate96, 'reader_tray')
reader_plates = resource_list_with_prefix(lay_mgr, 'rp_l_', Plate96, 6)

bleach = layout_item(lay_mgr, Plate96, 'bleach_site')
water_0 = layout_item(lay_mgr, Plate96, 'water_site_0')
water_1 = layout_item(lay_mgr, Plate96, 'water_site_1')
water_2 = layout_item(lay_mgr, Plate96, 'water_site_2')
water_sites = [water_0, water_1, water_2]
# Note: this is equivalent to the previous 4 lines: water_sites = resource_list_with_prefix(lay_mgr, 'water_site_', Plate96, 3)

waste = layout_item(lay_mgr, Tip96, 'ht_hw_96washdualchamber2_0001')
water_washer = layout_item(lay_mgr, Tip96, 'ht_hw_96washdualchamber1_0001')

lagoon_tips_0 = layout_item(lay_mgr, Tip96, 'lagoon_tips_0')
lagoon_tips_1 = layout_item(lay_mgr, Tip96, 'lagoon_tips_1')
lagoon_tips_2 = layout_item(lay_mgr, Tip96, 'lagoon_tips_2')
lagoon_tips_3 = layout_item(lay_mgr, Tip96, 'lagoon_tips_3')
lagoon_tips_4 = layout_item(lay_mgr, Tip96, 'lagoon_tips_4')


def lagoon_tips_rotation():
    while True:
        yield lagoon_tips_0
        yield lagoon_tips_1
        yield lagoon_tips_2
        yield lagoon_tips_3
        yield lagoon_tips_4
lagoon_tips_rotation = lagoon_tips_rotation()

def reader_plate_rotation():
    while True:
        for plate in reader_plates:
            yield plate
reader_plate_rotation = reader_plate_rotation()