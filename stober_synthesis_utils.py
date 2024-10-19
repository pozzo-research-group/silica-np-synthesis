import requests
import pandas as pd
from science_jubilee import Machine as science_jubilee
from science_jubilee.tools import HTTPSyringe as syringe
from science_jubilee.tools import Pipette
import time
import numpy as np
import logging

logger = logging.getLogger(__name__)

def _update_current_stock(stocks, stock_volumes, transfer_volume):
    """
    Find the next appropriate stock vial with enough stock for the transfer
    """
    names = {stock.name:stock for stock in stocks}

    for name in names:
        if stock_volumes[name] > transfer_volume:
            return names[name]
    
    raise AssertionError(f'Ran out of ethanol stocks - no vial contains enough for {transfer_volume} uL transfer. Current volumes: {stock_volumes}')

def count_stock_vials(sample_table, volume_per_vial):

    teos_count = int(np.ceil(sample_table['teos_volume'].sum()/volume_per_vial))
    ammonia_count = int(np.ceil(sample_table['ammonia_volume'].sum()/volume_per_vial))
    water_count = int(np.ceil(sample_table['water_volume'].sum()/volume_per_vial))
    ethanol_count = int(np.ceil(sample_table['ethanol_volume'].sum()/volume_per_vial))

    return {'teos_count':teos_count, 'ammonia_count':ammonia_count, 'water_count':water_count, 'ethanol_count':ethanol_count}


# this is for etoh
def add_etoh(jubilee, P300, sample_table, location_lookup, ethanol_stocks, max_pipette_volume = 290, stocks_usable_volume = 17000):
    jubilee.pickup_tool(P300)
    P300.pickup_tip()
    # The maximum volume that a P300 pipette can handle is 300 μL\

    stock_volumes = {stock.name:stocks_usable_volume for stock in ethanol_stocks}

    for i, row in sample_table.iterrows():
        uuid = row['uuid']
        etoh_vol = row['ethanol_volume']

        dispense_loc = location_lookup[uuid]

        ### Transfer split calculation
        n_full_transfers = int(np.floor(etoh_vol / max_pipette_volume))
        final_etoh_vol = etoh_vol - n_full_transfers*max_pipette_volume
        #########

        # etoh transfer execution
        for k in range(n_full_transfers):
            current_stock = _update_current_stock(ethanol_stocks, stock_volumes, max_pipette_volume)
            P300.aspirate(max_pipette_volume, current_stock.bottom(+5))
            P300.dispense(max_pipette_volume, dispense_loc.bottom(+22), s = 1000)
            time.sleep(3)
            stock_volumes[current_stock.name] -= max_pipette_volume
            logger.info(f'Dispensed {max_pipette_volume} uL ethanol into {dispense_loc}')
        # final transfer to hit vol
        current_stock = _update_current_stock(ethanol_stocks, stock_volumes, final_etoh_vol)
        P300.aspirate(final_etoh_vol, current_stock)
        P300.dispense(final_etoh_vol, dispense_loc.bottom(+22))
        logger.info(f'Dispensed {final_etoh_vol} uL ethanol into {dispense_loc}')
        time.sleep(3)
        stock_volumes[current_stock.name] -= final_etoh_vol

        logger.info(f'Ethanol dispense complete: {etoh_vol} uL Ethanol dispensed into {dispense_loc}')


    P300.drop_tip()
    jubilee.park_tool()

def _refill_syringe(syringe, stocks, stock_volumes):
    #1. get current stock to use
    aspirate_vol = syringe.capacity - syringe.remaining_volume - 1 
    current_stock = _update_current_stock(stocks, stock_volumes, aspirate_vol)
    #2. aspirate from stock

    logger.info(f'Refilling {syringe.name} with {aspirate_vol} uL from {current_stock}')
    syringe.aspirate(aspirate_vol, current_stock.bottom(+5), s = 10)
    #3. update remaining volumes
    stock_volumes[current_stock.name] -= aspirate_vol

    return stock_volumes

# for ammonia, water and TEOS
def add_reactants_batch(jubilee, reactant_syringe, mix_syringe, sample_table, location_lookup, reactant_name, stocks, stocks_usable_volume = 17000, mix_after = None, dwell_time = 3 ):
    
    if mix_after is not None:
        assert isinstance(mix_after, tuple), 'mix after must be a tuple containing mix_volume, n_mix, wash stocks'
        assert len(mix_after) == 3, 'mix after must be a tuple containing mix_volume, n_mix, wash stocks'

        mix_vol = mix_after[0]
        n_mix = mix_after[1]
        wash_stocks = mix_after[2]
    
    jubilee.pickup_tool(reactant_syringe)

    stock_volumes = {stock.name:stocks_usable_volume for stock in stocks}


    for i, row in sample_table.iterrows():

        uuid = row['uuid']
        dispense_volume = row[reactant_name]

        dispense_location = location_lookup[uuid]

        # make sure syringe has enough volume
        if dispense_volume > reactant_syringe.remaining_volume:
            stock_volumes = _refill_syringe(reactant_syringe, stocks, stock_volumes)

        reactant_syringe.dispense(dispense_volume, dispense_location.bottom(+5), s = 20)
        time.sleep(dwell_time)
        logger.info(f'Dispensed {dispense_volume} uL of {reactant_name} into {dispense_location}')

        if mix_after is not None:
            jubilee.park_tool()
            jubilee.pickup_tool(mix_syringe)
            
            mix_syringe.mix(mix_vol, n_mix, dispense_location.bottom(+5), s_aspirate = 2000, s_dispense = 500)
            logger.info(f'Mixed well {dispense_location} {n_mix} times, {mix_vol} uL per cycle')

            for stock in wash_stocks:
                mix_syringe.mix(mix_vol, 5, stock.bottom(+10), t_hold = 3, s_aspirate = 2000, s_dispense = 500)

            logger.info(f'Washed mix syringe in wash solutions {wash_stocks}')

            jubilee.park_tool()
            jubilee.pickup_tool(reactant_syringe)


    jubilee.park_tool()


def first_mix(jubilee, mix_syringe, mix_vol, location_lookup, wash_stocks, n_mix):
    jubilee.pickup_tool(mix_syringe)
    
    for name, well in location_lookup.items():
        mix_syringe.mix(mix_vol, n_mix, well.bottom(+5), s_aspirate = 2000, s_dispense = 500)
        logger.info(f'Mixed well {well} {n_mix} times, {mix_vol} uL per cycle')

        for stock in wash_stocks:
            mix_syringe.mix(mix_vol, 5, stock.bottom(+10), t_hold = 3, s_aspirate = 2000, s_dispense = 500)

        logger.info(f'Washed mix syringe in wash solutions {wash_stocks}')

    jubilee.park_tool()



