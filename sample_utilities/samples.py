import uuid
import numpy as np
import json


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

    def __init__(self, reactants, teos_vol_frac, ammonia_vol_frac, water_vol_frac, target_volume, reactant_fp):
        
        self.reactants = reactants
        self.teos_vol_frac = teos_vol_frac
        self.ammonia_vol_frac = ammonia_vol_frac
        self.water_vol_frac = water_vol_frac
        self.target_volume = target_volume

        self.uuid = uuid.uuid4()


        with open(reactant_fp, 'rt') as f:
            constants = json.load(f)

        # load TEOS
        reactant_data = constants['TEOS']
        self.teos = Reactant('teos', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'])

        # Load ammonia
        reactant_data = constants['ammonia']
        self.ammonia = Reactant('ammonia', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'])

        # Load water
        reactant_data = constants['water']
        self.water = Reactant('water', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'])

        # Load ethanol
        reactant_data = constants['ethanol']
        self.ethanol = Reactant('ethanol', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'])





    def generate_random_sample(self):

        return
    
    def calculate_reactant_volumes(self):
        """calculate the target volumes for each reactant from volume fraction and target volume"""

        # calculate ethanol volume

        return

    def calculate_concentration(self):
        """
        Calculate the concentration of the sample
        """
    

def generate_sample_table():
    """
    probably want something to take in a list of samples and put together a single table for all of them
    """



def generate_random_sample(sample):
        """
        Generates a sample with random volume fractions of each component, within that components min and max volume fraction constraints

        Independently selects composition of TEOS, water, and ammonia. Makes up the difference with ethanol

        Samples from a uniform distribution
        """

        teos_sample_scale = np.random.uniform()
        ammonia_sample_scale = np.random.uniform()
        water_sample_scale = np.random.uniform()

        teos_fraction = ((sample.teos.maximum_volume_fraction - sample.teos.minimum_volume_fraction)*teos_sample_scale)+sample.teos.minimum_volume_fraction

        ammonia_fraction = ((sample.ammonia.maximum_volume_fraction - sample.teos.minimum_volume_fraction)*ammonia_sample_scale)+sample.ammonia.minimum_volume_fraction

        water_fraction = ((sample.water.maximum_volume_fraction - sample.water.minimum_volume_fraction)*water_sample_scale)+sample.water.minimum_volume_fraction

        ethanol_fraction = 1 - teos_fraction - ammonia_fraction - water_fraction

        return {'teos_volume_fraction':teos_fraction, 'ammonia_volume_fraction':ammonia_fraction, 'water_volume_fraction':water_fraction, 'ethanol_volume_fraction':ethanol_fraction}



        return