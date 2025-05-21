import uuid
import numpy as np
import json
import pandas as pd


class Reactant:


    def __init__(self, name, concentration, density, molecular_weight, minimum_volume_fraction, maximum_volume_fraction, source, manufacturer, lot_number, dilution_ratio = None, **kwargs):
        """
        Dilution ratio: how many times reactant is diluted (ie 6x dilution is 5 parts ethanol/1 part reactant)
        """

        self.name = name
        self.concentration = concentration
        self.density = density
        self.molecular_weight = molecular_weight
        self.minimum_volume_fraction = minimum_volume_fraction
        self.maximum_volume_fraction = maximum_volume_fraction
        self.source = source
        self.manufacturer = manufacturer
        self.lot_number = lot_number

        for key, value in kwargs.items():
            setattr(self, key, value)

        if dilution_ratio is None:
            dilution_ratio = 1
        self.dilution_ratio = dilution_ratio



class SolidSilicaSample:
    
    silica_molecular_weight = 60.08 #g/mol
    
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
            self.teos = Reactant('teos', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'], dilution_ratio=reactant_data['dilution_ratio'])

            # Load ammonia
            reactant_data = constants['ammonia']
            self.ammonia = Reactant('ammonia', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'], dilution_ratio=reactant_data['dilution_ratio'])

            # Load water
            reactant_data = constants['water']
            self.water = Reactant('water', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'], dilution_ratio=reactant_data['dilution_ratio'])

            # Load ethanol
            reactant_data = constants['ethanol']
            self.ethanol = Reactant('ethanol', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'], dilution_ratio=reactant_data['dilution_ratio'])

            self.reactants = {'teos':self.teos, 'ammonia':self.ammonia, 'water':self.water, 'ethanol':self.ethanol}

        if reactants is not None:
            # manual definition pathway
            self.teos = reactants['teos']
            self.ammonia = reactants['ammonia']
            self.water = reactants['water']
            self.ethanol = reactants['ethanol']
            self.reactants = reactants

        if teos_vol_frac is not None:
            self.teos_vol_frac = teos_vol_frac
            self.ammonia_vol_frac = ammonia_vol_frac
            self.water_vol_frac = water_vol_frac
            self.ethanol_vol_frac = 1 - (teos_vol_frac + ammonia_vol_frac + water_vol_frac)



    
    def calculate_reactant_volumes(self):
        """calculate the target volumes for each reactant from volume fraction and target volume"""

        
        dilution_ethanol_volume = 0
        # calculate ethanol volume
        self.teos_volume = self.target_volume*self.teos_vol_frac*self.teos.dilution_ratio
        teos_etoh_vol = self.teos_volume*(self.teos.dilution_ratio-1)/self.teos.dilution_ratio
        dilution_ethanol_volume += teos_etoh_vol
        #print(teos_etoh_vol)


        self.ammonia_volume = self.target_volume * self.ammonia_vol_frac*self.ammonia.dilution_ratio
        dilution_ethanol_volume += self.ammonia_volume * (self.ammonia.dilution_ratio-1)/self.ammonia.dilution_ratio

        self.water_volume = self.target_volume * self.water_vol_frac*self.water.dilution_ratio
        dilution_ethanol_volume += self.water_volume * (self.water.dilution_ratio - 1)/self.water.dilution_ratio

        print(dilution_ethanol_volume)

        self.ethanol_volume = self.target_volume * self.ethanol_vol_frac - dilution_ethanol_volume

        return

    def calculate_silica_mass_concentration(self):
        """
        Calculate the silica mass concentration of the sample. Not implemented
        """
        
        
        self.silica_mass_conc = self.teos_vol_frac*self.teos.concentration*self.silica_molecular_weight
    

    def calculate_dilution_volumefraction(self, target_si_concentration):
        """
        Calculate the volume fraction of sample to use in measurement cell to reach target_si_concentration
        """
        self.dilution_volumefraction = target_si_concentration/(self.teos.concentration*self.teos_vol_frac)

    def calculate_silica_mass_fraction(self):
        


        teos_mass = self.teos_vol_frac * self.teos.density
        ammonia_mass = self.ammonia_vol_frac * self.ammonia.density
        water_mass = self.water_vol_frac * self.water.density
        ethanol_mass = self.ethanol_vol_frac * self.ethanol.density

        silica_mols = teos_mass/self.teos.molecular_weight
        silica_mass = silica_mols * self.silica_molecular_weight
        total_sample_mass = ammonia_mass + teos_mass + ethanol_mass + water_mass

        self.silica_mass_fraction = silica_mass/total_sample_mass




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

        if hasattr(sample, 'dilution_volumefraction'):
            sample_dict['dilution_volume_fraction'] = sample.dilution_volumefraction

        else:
            sample_dict['dilution_volume_fraction'] = None

        if hasattr(sample, 'silica_mass_conc'):
            sample_dict['silica_mass_conc'] = sample.silica_mass_conc

        else:
            sample_dict['silica_mass_conc'] = None

        if hasattr(sample, 'silica_mass_fraction'):
            sample_dict['silica_mass_fraction'] = sample.silica_mass_fraction
        else:
            sample_dict['silica_mass_fraction'] = None


    
    sample_table = pd.DataFrame(sample_dicts)

    return sample_table


class MesoporousSample:

    silica_molecular_weight = 60.08 #g/mol
    
    def __init__(self, target_volume, reactant_fp = None, teos_vol_frac = None, ammonia_vol_frac = None, water_vol_frac = None, ethanol_vol_frac = None, ctab_mass = None, f127_mass = None, reactants = None, uuid_val = None):
        
        self.target_volume = target_volume

        if uuid_val is None:
            self.uuid = uuid.uuid4()
        else:
            self.uuid = uuid_val

        if reactant_fp is None and teos_vol_frac is None:
            raise AssertionError('Must pass reactant filepath or reactant objects')
        
        if reactant_fp is not None:
            # Load from file pathway


            with open(reactant_fp, 'rt') as f:
                constants = json.load(f)

            # load TEOS
            reactant_data = constants['TEOS']
            self.teos = Reactant('teos', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'], dilution_ratio=reactant_data['dilution_ratio'])

            # Load ammonia
            reactant_data = constants['ammonia']
            self.ammonia = Reactant('ammonia', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'], dilution_ratio=reactant_data['dilution_ratio'])

            # Load water
            reactant_data = constants['water']
            self.water = Reactant('water', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'], dilution_ratio=reactant_data['dilution_ratio'])

            # Load ethanol
            reactant_data = constants['ethanol']
            self.ethanol = Reactant('ethanol', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'], dilution_ratio=reactant_data['dilution_ratio'])

            # load ctab
            reactant_data = constants['ctab']
            self.ctab = Reactant('ctab', reactant_data['stock_concentration_mg_uL'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'], dilution_ratio=reactant_data['dilution_ratio'], stock_concentration_mg_uL=reactant_data['stock_concentration_mg_uL'])

            # load f127
            reactant_data = constants['f127']
            self.f127 = Reactant('f127', reactant_data['stock_concentration'], density = reactant_data['density'], molecular_weight = reactant_data['molecular_weight'], minimum_volume_fraction=reactant_data['minimum_volume_fraction'], maximum_volume_fraction=reactant_data['maximum_volume_fraction'], source=reactant_data['stock_source'], manufacturer = reactant_data['manufacturer'], lot_number=reactant_data['lot_number'], dilution_ratio=reactant_data['dilution_ratio'], stock_concentration_mg_uL=reactant_data['stock_concentration_mg_uL'])
            


            self.reactants = {'teos':self.teos, 'ammonia':self.ammonia, 'water':self.water, 'ethanol':self.ethanol, 'ctab':self.ctab, 'f127':self.f127}

        if reactants is not None:
            # manual definition pathway
            self.teos = reactants['teos']
            self.ammonia = reactants['ammonia']
            self.water = reactants['water']
            self.ethanol = reactants['ethanol']
            self.ctab = reactants['ctab']
            self.f127 = reactants['f127']
            self.reactants = reactants

        if teos_vol_frac is not None:
            self.teos_vol_frac = teos_vol_frac
            self.ammonia_vol_frac = ammonia_vol_frac
            self.water_vol_frac = water_vol_frac
            self.ethanol_vol_frac = ethanol_vol_frac
            self.ctab_concentration_mg_uL = ctab_mass
            self.f127_concentration_mg_uL = f127_mass

    def calculate_reactant_volumes(self):
        """calculate the target volumes for each reactant from volume fraction and target volume"""

        
        solvent_ethanol_volume = 0
        solvent_water_volume = 0
        # calculate ethanol volume
        self.teos_volume = self.target_volume*self.teos_vol_frac*self.teos.dilution_ratio
        teos_etoh_vol = self.teos_volume*(self.teos.dilution_ratio-1)/self.teos.dilution_ratio
        solvent_ethanol_volume += teos_etoh_vol
        #print(teos_etoh_vol)


        self.ammonia_volume = self.target_volume * self.ammonia_vol_frac*self.ammonia.dilution_ratio
        solvent_ethanol_volume += self.ammonia_volume * (self.ammonia.dilution_ratio-1)/self.ammonia.dilution_ratio

        
        print(solvent_ethanol_volume)
        
        self.ctab_volume = self.ctab_concentration_mg_uL * self.target_volume / self.ctab.stock_concentration_mg_uL
        solvent_water_volume += self.ctab_volume
        self.f127_volume = self.f127_concentration_mg_uL * self.target_volume / self.f127.stock_concentration_mg_uL
        solvent_water_volume += self.f127_volume



        self.ethanol_volume = self.target_volume * self.ethanol_vol_frac - solvent_ethanol_volume
        self.water_volume = self.target_volume * self.water_vol_frac - solvent_water_volume
        return
        
        
    





