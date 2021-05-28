metadata = {"apiLevel": "2.9"}

def run(ctx):
    pcr96 = ctx.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", "1")
    tubes = ctx.load_labware("opentrons_24_tuberack_generic_2ml_screwcap", "2")
    standard384 = ctx.load_labware("corning_384_wellplate_112ul_flat", "3")

    p20s = ctx.load_instrument("p20_single_gen2", "left", tip_racks=[ctx.load_labware("opentrons_96_filtertiprack_20ul","4")])
    p300s = ctx.load_instrument("p300_single_gen2", "right", tip_racks=[ctx.load_labware("opentrons_96_filtertiprack_200ul","5")])

    for pipette in [p20s, p300s]:
        pipette.pick_up_tip()
        for labware in [pcr96, tubes, standard384]:
            pipette.transfer(20, labware.wells_by_name()["A1"].bottom(), labware.wells_by_name()["A1"].bottom(), new_tip='never')
        pipette.return_tip()
