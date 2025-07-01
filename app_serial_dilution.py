from oss_utils import LocationId, CustomReagent
import oss_lib

# instantiate the class OSS
oss = oss_lib.OSS()

# initialize the experiment
exp_id = oss.experiment_init('Serial Dilution')

# parameters of the experiment
num_wells = 8
base = CustomReagent('base_solvent')
stock = CustomReagent('my_reagent')
base_vol = 9
stock_vol = 1
wavelength = 900

# create a list of id's, one for each well
loc_id = []
for i in range(num_wells): 
    loc_id.append(LocationId(str(i)))
    
# create id's for base and stock reservoirs
base_id = LocationId('base')
stock_id = LocationId('stock')

# load base solvent and stock solution 
oss.load(exp_id, base_vol*num_wells, base, base_id)
oss.load(exp_id, stock_vol, stock, stock_id)
    
# transfer base solvent to each well
for i in range(num_wells):     
    oss.transfer(exp_id, base_vol, base_id, loc_id[i])

# transfer stock solution to first well and mix
oss.transfer(exp_id, stock_vol, stock_id, loc_id[0])
oss.mix(exp_id, loc_id[0], base_vol+stock_vol)

# serial dilute up to the second last well
for i in range(num_wells-2):
    oss.transfer(exp_id, stock_vol, loc_id[i], loc_id[i+1])
    oss.mix(exp_id, loc_id[i+1], base_vol+stock_vol)
    
# conduct spectroscopy study of all wells
result = oss.measure_absorbance(exp_id, loc_id, wavelength)

# terminate the experiment
oss.experiment_end(exp_id)


