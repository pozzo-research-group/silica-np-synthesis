import uuid
import numpy as np
import json
import pandas as pd


class Reactant:

    def __init__(self, name, concentration, density, molecular_weight, minimum_volume_fraction, maximum_volume_fraction, source, manufacturer, lot_number):

        self.name = name
        self.concentration = concentration
        self.density = density
        self.molecular_weight = molecular_weight
        self.minimum_volume_fraction = minimum_volume_fraction
        self.maximum_volume_fraction = maximum_volume_fraction
        self.source = source
        self.manufacturer = manufacturer
        self.lot_number = lot_number



class SolidSilicaSample:

    def __init__(self, target_volume, reactant_fp = None, teos_vol_frac = None, ammonia_vol_frac = None, water_vol_frac = None, reactants = None):
        
        self.target_volume = target_volume

        self.uuid = uuid.uuid4()

        if reactant_fp is None and teos_vol_frac is None:
            raise AssertionError('Must pass reactant filepath or reactant objects')
        
        if reactant_fp is not None:
            # Load from file pathway


            with open(reactant_fp, 'rt') as f:
                constants = json.load(f)

            # load TEOS
            reactant_data = constants['TEOS']
            self.teos = Reactant('teos', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'])

            # Load ammonia
            reactant_data = constants['ammonia']
            self.ammonia = Reactant('ammonia', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'])

            # Load water
            reactant_data = constants['water']
            self.water = Reactant('water', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'])

            # Load ethanol
            reactant_data = constants['ethanol']
            self.ethanol = Reactant('ethanol', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'])

            reactants = {'teos':self.teos, 'ammonia':self.ammonia, 'water':self.water, 'ethanol':self.ethanol}

        if reactants is not None:
            # manual definition pathway
            self.teos = reactants['teos']
            self.ammonia = reactants['ammonia']
            self.water = reactants['water']
            self.ethanol = reactants['ethanol']
            self.reactants = reactants



    
    def calculate_reactant_volumes(self):
        """calculate the target volumes for each reactant from volume fraction and target volume"""

        # calculate ethanol volume
        self.teos_volume = self.target_volume*self.teos_vol_frac
        self.ammonia_volume = self.target_volume * self.ammonia_vol_frac
        self.water_volume = self.target_volume * self.water_vol_frac
        self.ethanol_volume = self.target_volume * self.ethanol_vol_frac

        return

    def calculate_concentration(self):
        """
        Calculate the concentration of the sample. Not implemented
        """
        return None


    def generate_random_vol_fractions(self):
        """
        Generates a sample with random volume fractions of each component, within that components min and max volume fraction constraints

        Independently selects composition of TEOS, water, and ammonia. Makes up the difference with ethanol

        Samples from a uniform distribution
        """

        teos_sample_scale = np.random.uniform()
        ammonia_sample_scale = np.random.uniform()
        water_sample_scale = np.random.uniform()

        teos_fraction = ((self.teos.maximum_volume_fraction - self.teos.minimum_volume_fraction)*teos_sample_scale)+self.teos.minimum_volume_fraction

        ammonia_fraction = ((self.ammonia.maximum_volume_fraction - self.teos.minimum_volume_fraction)*ammonia_sample_scale)+self.ammonia.minimum_volume_fraction

        water_fraction = ((self.water.maximum_volume_fraction - self.water.minimum_volume_fraction)*water_sample_scale)+self.water.minimum_volume_fraction

        ethanol_fraction = 1 - teos_fraction - ammonia_fraction - water_fraction

        self.teos_vol_frac = teos_fraction
        self.ammonia_vol_frac = ammonia_fraction
        self.water_vol_frac = water_fraction
        self.ethanol_vol_frac = ethanol_fraction

    

def generate_synthesis_table(samples):
    """
    probably want something to take in a list of samples and put together a single table for all of them

    samples: list of dictionaries 
    """

    sample_dicts = []

    for sample in samples:
        sample_dict = {}
        sample_dict['uuid'] = sample.uuid
        sample_dict['teos_volume'] = sample.teos_volume
        sample_dict['ammonia_volume'] = sample.ammonia_volume
        sample_dict['water_volume'] = sample.water_volume
        sample_dict['ethanol_volume'] = sample.ethanol_volume
        sample_dicts.append(sample_dict)

    
    sample_table = pd.DataFrame(sample_dicts)

    return sample_table


    




