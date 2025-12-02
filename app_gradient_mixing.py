from oss_utils import LocationId, ResearcherMaterial
import oss_lib

# instantiate the class OSS
oss = oss_lib.OSS()

# initialize the experiment
exp_id = oss.experiment_init('Gradient Mixing')

# parameters of the experiment
sol1 = ResearcherMaterial('solution 1')
sol2 = ResearcherMaterial('solution 2')
tot_vol = 100
num_mixes = 8
lowest_percent = 10
step_percent = 10
wavelength = 600

# create a list of id's, one for each well
loc_id = []
for i in range(num_mixes): 
    loc_id.append(LocationId(str(i)))
    
# create id's for 2 solutions
sol1_id = LocationId('sol1')
sol2_id = LocationId('sol2')

# load solutions
oss.load(exp_id, tot_vol*num_mixes, sol1, sol1_id)
oss.load(exp_id, tot_vol*num_mixes, sol2, sol2_id)

# prepare multiple mixes
for i in range(num_mixes):
    sol1_vol = tot_vol * (lowest_percent + step_percent * i) // 100
    sol2_vol = tot_vol - sol1_vol
    oss.transfer(exp_id, sol1_vol, sol1_id, loc_id[i])
    oss.transfer(exp_id, sol2_vol, sol2_id, loc_id[i])
    oss.mix(exp_id, loc_id[i], tot_vol)
    
# analyze each well
absorbance = oss.measure_absorbance(exp_id, loc_id, (wavelength, wavelength))

# terminate the experiment
oss.experiment_end(exp_id)