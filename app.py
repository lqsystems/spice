from fastapi import FastAPI
import math
from pydantic import BaseModel
from typing import List
import asyncio
import opentrons.execute as oe
import opentrons.simulate as os
import opentronsfastapi

# Set our opentrons_env to opentrons.simulate
# On real robots, this would be set to opentrons.execute
opentronsfastapi.opentrons_env = oe 

app = FastAPI()

class DispenseWell(BaseModel):
    address: str

@app.post("/api/demo")
@opentronsfastapi.opentrons_execute()
def demo_procedure(dispenseWell:DispenseWell):

    # Asyncio must be set to allow the robot to run protocols in
    # the background while still responding to API requests
    asyncio.set_event_loop(asyncio.new_event_loop())
    ctx = opentronsfastapi.opentrons_env.get_protocol_api('2.9')

    ctx.home()
    plate = ctx.load_labware("corning_384_wellplate_112ul_flat", 1)
    tip_rack = ctx.load_labware("opentrons_96_tiprack_20ul", 2)
    p20 = ctx.load_instrument("p20_single_gen2", "left", tip_racks=[tip_rack])

    p20.pick_up_tip()

    p20.aspirate(10, plate.wells_by_name()['A1'])
    p20.dispense(10, plate.wells_by_name()[dispenseWell.address])

    p20.drop_tip()
    ctx.home()

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
@opentronsfastapi.opentrons_execute()
def buffer_protocol(buffers:BufferProtocol):

    # Asyncio must be set to allow the robot to run protocols in
    # the background while still responding to API requests
    asyncio.set_event_loop(asyncio.new_event_loop())
    ctx = opentronsfastapi.opentrons_env.get_protocol_api('2.9')
    ctx.home()

    # Setup 96 well labware
    p20_tip_racks = [ctx.load_labware("opentrons_96_tiprack_20ul", x) for x in [3]]
    p300_tip_racks = [ctx.load_labware("opentrons_96_tiprack_300ul", x) for x in [6]]
    p20s = ctx.load_instrument("p20_single_gen2", "left", tip_racks=p20_tip_racks)
    p300s = ctx.load_instrument("p300_single_gen2", "right", tip_racks=p300_tip_racks)
    output_buffers = ctx.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", 1)
    input_buffers = ctx.load_labware("opentrons_24_tuberack_generic_2ml_screwcap", 2)

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
            print(buffer_key)
            buffer_transfer_helper(buffer_key)
    ctx.home()
