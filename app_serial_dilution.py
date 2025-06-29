from oss_utils import LocationId
import oss_lib

# instantiate the class OSS
oss = oss_lib.OSS()

# initialize the experiment
exp_id = oss.experiment_init('Serial Dilution')

# parameters of the experiment
num_wells = 8
base = 'base_solvent'
stock = 'my_reagent'
base_vol = 9
stock_vol = 1
study_type = 'absorbance'
wavelength = 900

# create a list of id's, one for each well
well_id = []
for i in range(num_wells): 
    well_id.append(LocationId(str(i)))
    
# transfer base solvent to each well
for i in range(num_wells):     
    oss.load(exp_id, base_vol, base, well_id[i])

# transfer stock solution to first well and mix
oss.load(exp_id, stock_vol, stock, well_id[0])
oss.mix(exp_id, well_id[0])

# serial dilute up to the second last well
for i in range(num_wells-2):
    oss.transfer(exp_id, stock_vol, well_id[i], well_id[i+1])
    oss.mix(exp_id, well_id[i+1])
    
# conduct spectroscopy study of all wells
#oss.spectroscopy_study(exp_id, study_type, wavelength)

# terminate the experiment
oss.experiment_end(exp_id)


