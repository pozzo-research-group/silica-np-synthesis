%load_ext autoreload
%autoreload 2

import requests
import pandas as pd
from science_jubilee import Machine as science_jubilee
from science_jubilee.tools import HTTPSyringe as syringe
from science_jubilee.tools import pipette
import time

url = 'http://192.168.1.5:5000'
volume = {'volume': 5}
r = requests.post(url + '/get_status', json = {'name': '1cc_2'})
r.content

jubilee = Jub.Machine(address = '192.168.1.2', simulated = False)
# jubilee.home_all()
deck = jubilee.load_deck('lab_automation_deck_AFL_bolton.json')


## Load labware
samples = jubilee.load_labware('septavialrev1_44_holder_2000ul.json, 2')
samples.manual_offset([(19.8,178.1),(132.5,177.6),(132.5,106.6)])

stocks = jubilee.load_labware('20mlscintillation_12_wellplate_18000ul.json', 4)
stocks.manual_offset([(31.3,268.1),(117.6, 267),(117.9, 210.9)])

tiprack = jubilee.load_labware('opentron_96_tiprack_300ul.json', 0)
tiprack.manual_offset([(28,77.3),(127.1, 76.8),(127.8, 14.5)])

trash = jubilee.load_labware('agilent_1_reservoir_290ml.json', 1)

## Load tools
P300 = Pipette.Pipette.from_config(0, 'Pipette', 'P300_config.json')
jubilee.load_tool(P300)
P300.add_tiprack(tiprack)
P300.trash = trash[0]
# xxx.from_config(#, etc), the # relate to the tool number in the main page of science jubilee
syringe_10 = syringe.HTTPSyringe.from_config(1, "src/science_jubilee/tools/configs/10cc_syringe.json")
syringe_1_1 = syringe.HTTPSyringe.from_config(2, "src/science_jubilee/tools/configs/1cc_1_syringe.json")
syringe_1_2 = syringe.HTTPSyringe.from_config(3, "src/science_jubilee/tools/configs/1cc_2_syringe.json")
syringe_1_3 = syringe.HTTPSyringe.from_config(4, "src/science_jubilee/tools/configs/1cc_3_syringe.json")

jubilee.load_tool(syringe_10)
jubilee.load_tool(syringe_1_1)
jubilee.load_tool(syringe_1_2)
jubilee.load_tool(syringe_1_3)

mix_syringe = syringe_10
water_syringe = syringe_1_1
ammonia_syringe = syringe_1_2
teos_syringe = syringe_1_3

df = pd.read_csv('xxx.csv')
# assign and name the list with the heading 'ethanol ratio' in df as ethanol_ratio
ethanol_vol = list(df['ethanol_volume'])
ammonia_vol = list(df['ammonia_volume'])
water_vol = list(df['water_volume'])
TEOS_vol = list(df['TEOS_volume'])
mix_vol = 1990
wells = list(df['well'])

# define location of the stocks
ethanol_stock = stocks[0]
ammonia_stock = stocks[1]
water_stock = stocks[2]
TEOS_stock = stocks[3]
wash_stock_1 = stocks[4]
wash_stock_2 = stocks[5]



# this is for etoh
def add_etoh(volumes, stocks, wells):
    jubilee.pickup_tool(P300)
    P300.pickup_tip()
    # The maximum volume that a P300 pipette can handle is 300 μL
    max_pipette_volume = 300
    for volume in volumes:
        for well_name in wells:
            dispense_loc = samples[well_name]
    # Check if the volume is larger than 300
            if volume > max_pipette_volume:
        # Calculate how many parts the volume should be divided into
                parts = (volume // max_pipette_volume) + (1 if volume % max_pipette_volume > 0 else 0)
        
        # Calculate the volume per part
                divided_volume = volume / parts
        
        #print(f"Dividing {volume} μL into {parts} parts, each {divided_volume:.2f} μL.")
        
        # Simulate aspirating each divided volume using the P300 pipette
                for i in range(parts):
                    P300.aspirate(divided_volume, stocks)
                    jubilee.move(dz = 60)
                    P300.dispense(divided_volume, dispense_loc.bottom(+15))
                    jubilee.move(dz = 60)
                    time.sleep(2)
            #print(f"Aspirating {divided_volume:.2f} μL with P300 pipette (Part {i+1}/{parts})")
             else:
        # If the volume is 300 or less, just aspirate it directly
                P300.aspirate(volume, stocks)
                jubilee.move(dz = 60)
                P300.dispense(volume, dispense_loc.bottom(+15))
                jubilee.move(dz = 60)
                time.sleep(2)
        #print(f"Aspirating {volume} μL with P300 pipette.")
    P300.return_tip()
    jubilee.park_tool()

# for ammonia, water and TEOS
def add_reactants(syringe, volumes, stocks, wash_stock, well):
    jubilee.pickup_tool(syringe)

    for volume in volumes:
        for well_name in well:
            dispense_location = samples[well_name]

            if volume < syringe.remaining_volume:
                syringe.dispense(volume, dispense_location)
                time.sleep(3)
            else:
                jubilee.move(dz = 60)
                jubilee.move_to(wash_stock)
                jubilee.move(dz = -60)
                jubilee.move(dz = 60)
                time.sleep(15)
                aspirate_vol = 995-syringe.remaining_volume
            
                syringe.aspirate(aspirate_vol, stocks, s = 10)
                syringe.dispense(volume, dispense_location)
                time.sleep(3)
    jubilee.park_tool()

def first_mix(mix_vol, well, wash_stock_1, wash_stock_2):
    jubilee.pickup_tool(mix_syringe)
    
    for well_name in well:
        mix_loc = samples[well_name]
        mix_syringe.aspirate(5, mix_loc.bottom(+5))
        mix_syringe.mix(mix_vol, 5, mix_loc, t_hold = 3)
        
        mix_syringe.aspirate(5, wash_stock_1)
    
        for k in range(2):
            wash_loc = stocks[k+1]
            mix_syringe.mix(mix_vol, 3, wash_loc, t_hold = 3)
    jubilee.park_tool()



        
add_etoh(ethanol_vol, ethanol_stock, wells)
#add_reactants(syringe, volumes, stocks, well)
add_reactants(ammonia_syringe, ammonia_vol, ammonia_stock, wash_stock_1, wells)
add_reactants(water_syringe, water_vol, water_stock, wash_stock_1, wells)

