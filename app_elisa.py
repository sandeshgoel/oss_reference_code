from oss_utils import LocationId
import oss_lib

# instantiate the class OSS
oss = oss_lib.OSS()

# initialize the experiment
exp_id = oss.experiment_init('Gradient Mixing')

# parameters of the experiment
num_samples = 8

capture_antibody = 'capture antibody'
capture_antibody_vol = 10

wash_buffer = 'wash buffer'
wash_buffer_vol = 10

blocking_buffer = 'blocking buffer'
blocking_buffer_vol = 10

detection_antibody = 'detection antibody'
detection_antibody_vol = 10

sample = 'sample'
sample_vol = 10

conjugate = 'conjugate'
conjugate_vol = 10

substrate = 'substrate'
substrate_vol = 10

stop_solution = 'stop solution'
stop_solution_vol = 10

incubate_temp = 37
incubate_time = 60
wavelength = 600

# create a list of id's, one for each well
loc_id = []
for i in range(num_samples): 
    loc_id.append(LocationId(str(i)))
    
# create id's for solutions
capture_id = LocationId('capture')
wash_id = LocationId('wash')
blocking_id = LocationId('blocking')
detection_id = LocationId('detection')
sample_id = LocationId('sample')
conjugate_id = LocationId('conjugate')
substrate_id = LocationId('substrate')
stop_id = LocationId('stop')

# load solutions
oss.load(exp_id, capture_antibody_vol*num_samples, capture_antibody, capture_id)
oss.load(exp_id, wash_buffer_vol*num_samples, wash_buffer, wash_id)
oss.load(exp_id, blocking_buffer_vol*num_samples, blocking_buffer, blocking_id)
oss.load(exp_id, detection_antibody_vol*num_samples, detection_antibody, detection_id)
oss.load(exp_id, sample_vol*num_samples, sample, sample_id)
oss.load(exp_id, conjugate_vol*num_samples, conjugate, conjugate_id)    
oss.load(exp_id, substrate_vol*num_samples, substrate, substrate_id)    
oss.load(exp_id, stop_solution_vol*num_samples, stop_solution, stop_id)

# coat plate with capture antibody
oss.transfer(exp_id, capture_antibody_vol, capture_id, loc_id)
    
# wash plate
for i in range(num_samples):
    oss.wash(exp_id, loc_id[i])
    
# block nonspecific sites
oss.transfer(exp_id, blocking_buffer_vol, blocking_id, loc_id)
oss.incubate(exp_id, loc_id, incubate_temp, incubate_time)
    
# wash plate again
for i in range(num_samples):
    oss.wash(exp_id, loc_id[i])

# add samples
oss.transfer(exp_id, sample_vol, sample_id, loc_id)
oss.incubate(exp_id, loc_id, incubate_temp, incubate_time)
    
# wash plate
for i in range(num_samples):
    oss.wash(exp_id, loc_id[i])

# add detection antibody
oss.transfer(exp_id, detection_antibody_vol, detection_id, loc_id)
oss.incubate(exp_id, loc_id, incubate_temp, incubate_time)

# wash plate
for i in range(num_samples):
    oss.wash(exp_id, loc_id[i])

# add enzyme-conjugate
oss.transfer(exp_id, conjugate_vol, conjugate_id, loc_id)
oss.incubate(exp_id, loc_id, incubate_temp, incubate_time)
    
# wash plate
for i in range(num_samples):
    oss.wash(exp_id, loc_id[i])

# add substrate
oss.transfer(exp_id, substrate_vol, substrate_id, loc_id)
oss.incubate(exp_id, loc_id, incubate_temp, incubate_time, dark=True)

# stop reaction
oss.transfer(exp_id, stop_solution_vol, stop_id, loc_id)
    
# measure absorbance
absorbance = oss.measure_absorbance(exp_id, loc_id, wavelength)

# terminate the experiment
oss.experiment_end(exp_id)