from fastapi import FastAPI
import math
from pydantic import BaseModel
from typing import List
import asyncio
import opentronsfastapi as otf

app = FastAPI()
app.include_router(otf.default_routes)

### Buffer optimization ###

class BufferSetup(BaseModel):
    address: str
    name: str

class BufferVol(BaseModel):
    name: str
    volume: float

class BufferTube(BaseModel):
    address: str
    buffer_volumes: List[BufferVol]

class BufferProtocol(BaseModel):
    setup: List[BufferSetup]
    buffers: List[BufferTube]

@app.post("/api/buffer")
@otf.opentrons_execute(apiLevel='2.0')
def buffer_protocol(buffers:BufferProtocol,
                    version = otf.ot_flags.protocol_version_flag,
                    protocol = otf.ot_flags.protocol_context
                    ):

    # Setup 96 well labware
    p20_tip_racks = [protocol.load_labware("opentrons_96_tiprack_20ul", x) for x in [3]]
    p300_tip_racks = [protocol.load_labware("opentrons_96_tiprack_300ul", x) for x in [6]]
    p20s = protocol.load_instrument("p20_single_gen2", "left", tip_racks=p20_tip_racks)
    p300s = protocol.load_instrument("p300_single_gen2", "right", tip_racks=p300_tip_racks)
    output_buffers = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    input_buffers = protocol.load_labware("opentrons_24_tuberack_generic_2ml_screwcap", 2)

    # First, set all buffer tubes to a dictionary
    buffer_dict = {}
    buffer_loc = {}
    for bs in buffers.setup:
        buffer_dict[bs.name] = []
        buffer_loc[bs.name] = input_buffers.wells_by_name()[bs.address]

    # Next, append each buffer volume to the buffer dict
    for bt in buffers.buffers:
        for bv in bt.buffer_volumes:
            buffer_dict[bv.name].append({"volume":bv.volume, "to":output_buffers.wells_by_name()[bt.address]})

    # The volume with the largest average volume goes first, then everything else
    largest_average_buffer = ""
    largest_average_buffer_vol = 0
    for buffer_key, buffer_values in buffer_dict.items():
        num_transfers = len(buffer_values)
        total_transfer = 0
        for bv in buffer_values:
            total_transfer+=bv["volume"]
        av = total_transfer/num_transfers
        if av > largest_average_buffer_vol:
            largest_average_buffer = buffer_key
            largest_average_buffer_vol = av

    
    def buffer_transfer_helper(buffer_name):
        target_vols = buffer_dict[buffer_name]
        input_well = buffer_loc[buffer_name]
        p20s_tip = False
        p300s_tip = False
        p20s_transfers = []
        p300s_transfers = []
        
        transfer = {"aspirate": 0, "dispenses": []}
        for tv in target_vols:
            if tv["volume"] > 20:
                if p300s_tip == False:
                    p300s_transfer = {"aspirate": 0, "dispenses": []}
                    p300s_tip = True
                if p300s_transfer["aspirate"] + tv["volume"] > 270:
                    p300s_transfers.append(p300s_transfer)
                    p300s_transfer = {"aspirate": 0, "dispenses": []}
                p300s_transfer["dispenses"].append(tv)
                p300s_transfer["aspirate"] += tv["volume"]
            if tv["volume"] <= 20:
                if p20s_tip == False:
                    p20s_transfer = {"aspirate": 0, "dispenses": []}
                    p20s_tip = True
                if p20s_transfer["aspirate"] + tv["volume"] > 18:
                    p20s_transfers.append(p20s_transfer)
                    p20s_transfer = {"aspirate": 0, "dispenses": []}
                p20s_transfer["dispenses"].append(tv)
                p20s_transfer["aspirate"] += tv["volume"]

        if p300s_tip == True:
            p300s_transfers.append(p300s_transfer)
        if p20s_tip == True:
            p20s_transfers.append(p20s_transfer)

        if p300s_tip == True:
            p300s.pick_up_tip()
            for transfer in p300s_transfers:
                p300s.aspirate(transfer["aspirate"], input_well)
                for dispense in transfer["dispenses"]:
                    p300s.dispense(dispense["volume"], dispense["to"])
            p300s.drop_tip()
        if p20s_tip == True:
            p20s.pick_up_tip()
            for transfer in p20s_transfers:
                p20s.aspirate(transfer["aspirate"], input_well)
                for dispense in transfer["dispenses"]:
                    p20s.dispense(dispense["volume"], dispense["to"])
            p20s.drop_tip()

    buffer_transfer_helper(largest_average_buffer)
    for buffer_key, _ in buffer_dict.items():
        if buffer_key != largest_average_buffer:
            buffer_transfer_helper(buffer_key)
