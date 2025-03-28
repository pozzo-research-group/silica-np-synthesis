import requests
import pandas as pd
from science_jubilee import Machine as science_jubilee
from science_jubilee.tools import HTTPSyringe as syringe
from science_jubilee.tools import Pipette
import time
import numpy as np
import logging
import json
from sample_utilities import samples

logger = logging.getLogger(__name__)


class Stocks():

    def __init__(self, stock_list, usable_volume = 17000):
        """
        Keeps track of available stock volumes in each stock vial
        """

        self.current_volumes = {stock.name:usable_volume for stock in stock_list}
        self.stock_list_lookup = {stock.name:stock for stock in stock_list}

    def get_available_stock(self, transfer_volume, update = True):
        """
        Find the next appropriate stock vial with enough stock for the transfer
        """
        for name, volume in self.current_volumes.items():
            if volume > transfer_volume:
                stock = self.stock_list_lookup[name]
                if update:
                    self.update_available_volume(stock.name, transfer_volume)
                return stock
        
        raise AssertionError(f'Ran out of ethanol stocks - no vial contains enough for {transfer_volume} uL transfer. Current volumes: {self.current_volumes}')

    def update_available_volume(self, stock, volume_used):
        """
        Update the available volume for a stock
        """
        self.current_volumes[stock.name] -= volume_used

    def get_current_volumes(self):
        return self.current_volumes

class SampleWells():

    def __init__(self, stock_plates):
        """
        Class to keep track of sample locations and get the next clean well

        Params:
        -------
        stock_plates: dictionary of {plate_name: labware}
        """
        self.labware = stock_plates

        self.wells = {}
        for name, labware in self.labware.items():
            for well_name in labware.wells.items():
                well_name = f'{name}_{well_name}'
                status = 'clean'
                sample = None
                self.wells[well_name] = {'status': status, 'sample': sample}

    def get_next_clean_well(self):
        for well_name, well in self.wells.items():
            if well['status'] == 'clean':
                return well_name
        raise AssertionError('No clean wells available')

    def get_well_for_sample(self, sample_uuid):
        clean_well_name = self.get_next_clean_well()

        self.wells[clean_well_name]['status'] = 'used'
        self.wells[clean_well_name]['sample'] = sample_uuid

        clean_well = self.wells[clean_well_name]
        return clean_well


    def get_sample_wells(self):
        return self.sample_table


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

def _refill_syringe(syringe, stocks, refill_dwell):
    #1. get current stock to use
    aspirate_vol = syringe.capacity - syringe.remaining_volume - 1 
    current_stock = stocks.get_available_stock(aspirate_vol, update = False)
    #2. aspirate from stock

    logger.info(f'Refilling {syringe.name} with {aspirate_vol} uL from {current_stock}')
    syringe.aspirate(aspirate_vol, current_stock.bottom(+5), s = 10, dwell_before = refill_dwell)
    #3. update remaining volumes
    #backlash correction
    syringe.dispense(50, current_stock.bottom(+5), s = 10)
    stocks.update_available_volume(current_stock, aspirate_vol + 50)

    return

# for ammonia, water and TEOS
def add_reactants_batch(jubilee, reactant_syringe, mix_syringe, sample_table, location_lookup, reactant_name, stocks, mix_after = None, dwell_time = 3, wait = False, refill_dwell = 0, n_rinse = 5, return_time = False):
    
    if mix_after is not None:
        assert isinstance(mix_after, tuple), 'mix after must be a tuple containing mix_volume, n_mix, wash stocks'
        assert len(mix_after) == 3, 'mix after must be a tuple containing mix_volume, n_mix, wash stocks'

        mix_vol = mix_after[0]
        n_mix = mix_after[1]
        wash_stocks = mix_after[2]
    
    jubilee.pickup_tool(reactant_syringe)


    for i, row in sample_table.iterrows():

        uuid = row['uuid']
        dispense_volume = row[reactant_name]

        dispense_location = location_lookup[uuid]

        # need to account for dispenses > syringe volume
        n_dispenses = int(np.ceil(dispense_volume / (reactant_syringe.capacity)))
        step_volume = dispense_volume/n_dispenses
        print(f'breaking dispense into {n_dispenses} of volume {step_volume}')

        for i in range(n_dispenses):
            # make sure syringe has enough volume
            if dispense_volume > reactant_syringe.remaining_volume:
                _refill_syringe(reactant_syringe, stocks, refill_dwell)
                print('remaining vol: ', reactant_syringe.remaining_volume)

            reactant_syringe.dispense(step_volume, dispense_location.bottom(+5), s = 20)
            time.sleep(dwell_time)
            logger.info(f'Dispensed {dispense_volume} uL of {reactant_name} into {dispense_location}')
        dispense_time = time.time()

        if mix_after is not None:
            jubilee.park_tool()
            jubilee.pickup_tool(mix_syringe)
            
            mix_syringe.mix(mix_vol, n_mix, dispense_location.bottom(+5), s_aspirate = 2000, s_dispense = 500)
            logger.info(f'Mixed well {dispense_location} {n_mix} times, {mix_vol} uL per cycle')

            for stock in wash_stocks:
                mix_syringe.mix(mix_vol, n_rinse, stock.bottom(+10), t_hold = 3, s_aspirate = 2000, s_dispense = 500)

            logger.info(f'Washed mix syringe in wash solutions {wash_stocks}')

            jubilee.park_tool()
            jubilee.pickup_tool(reactant_syringe)
        if wait:
            jubilee.move_to(z = 200)
            inp = input('Hit any key when ready to continue')


    jubilee.park_tool()
    if return_time:
        return dispense_time


def first_mix(jubilee, mix_syringe, mix_vol, location_lookup, wash_stocks, n_mix, n_rinse = 5):
    jubilee.pickup_tool(mix_syringe)
    
    for name, well in location_lookup.items():
        mix_syringe.mix(mix_vol, n_mix, well.bottom(+5), s_aspirate = 2000, s_dispense = 500)
        logger.info(f'Mixed well {well} {n_mix} times, {mix_vol} uL per cycle')

        for stock in wash_stocks:
            mix_syringe.mix(mix_vol, n_rinse, stock.bottom(+10), t_hold = 3, s_aspirate = 2000, s_dispense = 500)

        logger.info(f'Washed mix syringe in wash solutions {wash_stocks}')

    jubilee.park_tool()


def reactant_transfer(jubilee, syringe, stocks, destination, volume, volume_buffer, rinse_stocks = None, rinse_vol = 500, n_rinse = 1, dwell_time = 3):
    """ Reactant transfer using non-dedicated syringe in a one at a time manner. 


    Params:
    -------
    jubilee: Jubilee object
    syringe: syringe object
    source: well object
    destination: well object
    volume: float, volume to transfer
    volume_buffer: float, buffer volume aspirate in syringe
    rinse_stocks: list of well objects, stocks to rinse syringe in
    rinse_vol: float, volume to rinse syringe in
    n_rinse: int, number of times to rinse syringe
    dwell_time: float, time to dwell after dispensing



    """
    syringe.set_pulsewidth(syringe.empty_position - 1)
    syringe.load_syringe(0, syringe.empty_position-1)

    jubilee.pickup_tool(syringe)

    
    # need to account for dispenses > syringe volume
    n_dispenses = int(np.ceil(volume / (syringe.capacity - volume_buffer)))
    step_volume = volume/n_dispenses
    print(f'breaking dispense into {n_dispenses} of volume {step_volume}')
    
    for i in range(n_dispenses):
        # make sure syringe has enough volume
        if i == 0:
            source = stocks.get_available_stock(step_volume + volume_buffer, update = False)
            syringe.aspirate(step_volume + volume_buffer, source.bottom(+5), s = 10, dwell_before = 5)
            stocks.update_available_volume(source, step_volume + volume_buffer)
        else:
            source = stocks.get_available_stock(step_volume, update = False)
            syringe.aspirate(step_volume, source.bottom(+5), s = 10, dwell_before = 5)
            stocks.update_available_volume(source, step_volume)

        
        

        syringe.dispense(step_volume, destination.bottom(+5), s = 200)
        time.sleep(dwell_time)
        logger.info(f'Dispensed {volume} uL from {source} into {destination}')

    syringe.dispense(volume_buffer, source.bottom(+5), s = 20)

    if rinse_stocks is not None:
        print(f'Rinsing {syringe.name}') 
        for stock in rinse_stocks:
            syringe.mix(rinse_vol, n_rinse, stock.bottom(+10), t_hold = 3, s_aspirate = 2000, s_dispense = 1000)

        logger.info(f'Washed mix syringe in wash solutions {rinse_stocks}')

    jubilee.park_tool()
    syringe.set_pulsewidth(syringe.empty_position - 1)
    syringe.load_syringe(0, syringe.empty_position-1)



def get_next_sample(constants_fp, config_fp, synthesized_samples_fp):
    """
    Get the next sample to make from the sample server 
    """
    # load config
    with open(config_fp, 'r') as f:
        config = json.load(f)

    with open(constants_fp, 'r') as f:
        constants = json.load(f)

    with open(synthesized_samples_fp, 'r') as f:
        synthesized_samples = [line.rstrip() for line in f]

    url = f'http://{config["sample_server"]["ip_address"]}:{config["sample_server"]["port"]}/get_proposed_candidates'

    response = requests.get(url)
    proposed_samples = response.json()

    proposed_samples = {sample['id']:sample for sample in proposed_samples}
    proposed_samples_uuids = list(proposed_samples.keys())



    # remove synthesized samples from proposed samples
    proposed_samples_uuids = [sample for sample in proposed_samples_uuids if sample not in synthesized_samples]

    if len(proposed_samples) > 1:
        print(f'Multiple samples proposed: {proposed_samples}')
        # need to get oldest sample

        sample_orders = [proposed_samples[uuid]['sample_order'] for uuid in proposed_samples_uuids]
        selected_sample_uuid = proposed_samples_uuids[np.argmin(sample_orders)]
        selected_sample = proposed_samples[selected_sample_uuid]

    else:
        selected_sample_uuid = proposed_samples_uuids[0]
        selected_sample = proposed_samples[selected_sample_uuid]

    teos_vol_frac = selected_sample['teos_vf']
    ethanol_vol_frac = selected_sample['ethanol_vf']
    ammonia_vol_frac = selected_sample['ammonia_vf']
    water_vol_frac = selected_sample['water_vf']
    ctab_mass_conc = selected_sample['ctab_mass']
    f127_mass_conc = selected_sample['f127_mass']

    target_volume = config['experiment_constants']['target_volume']

    # convert candidate volume fracctions to volumes - neeed to account for dilutions here
    sample = samples.MesoporousSample(target_volume, constants_fp, teos_vol_frac=teos_vol_frac, ammonia_vol_frac=ammonia_vol_frac, water_vol_frac=water_vol_frac, ethanol_vol_frac=ethanol_vol_frac, ctab_mass=ctab_mass_conc, f127_mass=f127_mass_conc)
    sample.calculate_reactant_volumes()

    composition_dict = {
    'teos_volume':sample.teos_volume,
    'ammonia_volume':sample.ammonia_volume,
    'water_volume':sample.water_volume,
    'ethanol_volume':sample.ethanol_volume,
    'ctab_volume':sample.ctab_volume,
    'f127_volume':sample.f127_volume
    }

    # return the next sample to make
    return selected_sample_uuid, composition_dict




