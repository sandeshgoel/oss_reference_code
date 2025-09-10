from oss_utils import LocationId, CustomReagent
import oss_lib

# instantiate the class OSS
oss = oss_lib.OSS()

# initialize the experiment
exp_id = oss.experiment_init('Game of Life')

# parameters of the experiment
num_rows = 8
num_cols = 8
initial_live = [(3, 3), (4, 4),(3,4), (5,5), (4,5)]
live_sol = CustomReagent('live solution')
dead_sol = CustomReagent('dead solution')
vol = 10
num_generations = 10
absorbance_threshold = 5
wavelength = 600

# create a list of id's, one for each well
loc_id = []
for i in range(num_rows): 
    for j in range(num_cols): 
        loc_id.append(LocationId(str(i)+str(j)))

# create id's for base and stock reservoirs
live_id = LocationId('live')
dead_id = LocationId('dead')

# initialize wells grid
wells = []
for i in range(num_rows):
    wells.append([0 for j in range(num_cols)])
    
for i in range(num_rows):
    for j in range(num_cols):
        if (i,j) in initial_live:
            wells[i][j] = 1

# load live and dead solutions into reservoirs
oss.load(exp_id, vol*num_rows*num_cols, live_sol, live_id)
oss.load(exp_id, vol*num_rows*num_cols, dead_sol, dead_id)

# start generations loop
for gen in range(num_generations):
    # visualize the grid
    for i in range(num_rows):
        for j in range(num_cols):
            if wells[i][j] == 1:
                print("X", end=" ")
            else:
                print(".", end=" ")
        print()
    print()
    
    # transfer live solution in live cells and dead solution in dead cells
    for i in range(num_rows):
        for j in range(num_cols):
            if wells[i][j] == 1:
                oss.transfer(exp_id, vol, live_id, loc_id[i*num_cols+j])
            else:
                oss.transfer(exp_id, vol, dead_id, loc_id[i*num_cols+j])
                    
    # measure absorbance in each cell
    absorbance = oss.measure_absorbance(exp_id, loc_id, (wavelength, wavelength))         
    for i in range(num_rows):
        for j in range(num_cols):
            if absorbance[i*num_cols+j]  > absorbance_threshold:
                wells[i][j] = 1
            else:
                wells[i][j] = 0
    
    # compute next generation based on neighbors
    for i in range(num_rows):
        for j in range(num_cols):
            live_neighbors = 0
            for k in range(-1, 2):
                for l in range(-1, 2):
                    if k == 0 and l == 0:
                        continue
                    if i+k < 0 or i+k >= num_rows or j+l < 0 or j+l >= num_cols:
                        continue
                    if wells[i+k][j+l] == 1:
                        live_neighbors += 1
            if live_neighbors < 2 or live_neighbors > 3:
                wells[i][j] = 0
            elif live_neighbors == 3:
                wells[i][j] = 1
            
    # discard solutions from all wells    
    for i in range(num_rows):
        for j in range(num_cols):
            oss.discard(exp_id, vol, loc_id[i*num_cols+j], release_labware=True)
            
# terminate the experiment
oss.experiment_end(exp_id)  
