import datetime
import operator_lib
import lh_lib
from  oss_utils import Location, LocationId, Equipment, Labware, logger

# ===================================================================
# Experiment class definition    

class Experiment:
    def __init__(self, exp_id: int, name:str):
        self.exp_id = exp_id
        self.name = name
        self.create_time = datetime.datetime.now()
        self.location_map = {}
        logger.info(f"Experiment {exp_id} created")
        
    def is_exist_location(self, loc_id: LocationId):
        return loc_id in self.location_map
    
    def get_location(self, loc_id: LocationId):
        return self.location_map[loc_id]
    
    def set_location(self, loc_id: LocationId, location: Location):
        logger.info(f"Experiment {self.exp_id}: Set location {loc_id} to {location}")
        if self.is_exist_location(loc_id):
            raise Exception("Location already exists")
        else:
            self.location_map[loc_id] = location
        
# ===================================================================
# OSS class definition

class OSS:
    
    # ---------------------------------------------------------------
    # OSS state
    next_exp_id = 0
    exp_list = {}
    operator = operator_lib.Operator()
    lh = lh_lib.LiquidHandler()
    
    # ---------------------------------------------------------------
    # Experiment control functions

    def experiment_init(self, name: str):
        OSS.next_exp_id += 1
        logger.info(f"OSS: Experiment {OSS.next_exp_id}: Start {name}")
        new_exp = Experiment(OSS.next_exp_id, name)
        OSS.exp_list[OSS.next_exp_id] = new_exp
        return OSS.next_exp_id

    def experiment_end(self, exp_id: int):
        logger.info(f"OSS: Experiment {exp_id}: End")
        if exp_id in OSS.exp_list:
            del OSS.exp_list[exp_id]
        else:
            raise Exception("Experiment does not exist")

    # ---------------------------------------------------------------
    # internal helper functions
    
    def __get_experiment(self, exp_id: int):
        if exp_id in OSS.exp_list:
            return OSS.exp_list[exp_id]
        else:
            raise Exception("Experiment does not exist")
        
    def __decide_location(self, vol: int, num_dests: int) -> Location:
        # logic to decide which location to choose
        # Rule: pick the smallest capacity labware that can handle the vol. 
        # If destination is unitary, use test tube. 
        # Else use well plate, with the smallest well-plate size 
        # that can handle the list.
        return Location(equipment=Equipment.liquid_handler, slot=1, 
                        labware=Labware.wellplate, well_id='A1')
    
    # ---------------------------------------------------------------
    # Experiment actions 
    
    def bring(self, exp_id: int, vol: int, solution: str, dest_id: LocationId | list[LocationId]):
        logger.info(f"OSS: Experiment {exp_id}: Bring {vol}ul of {solution} to {dest_id}")

        # dest_id could be a single location id or a list of location ids 
        # always convert dest_id to list for uniform handling from here on
        if not isinstance(dest_id, list):
            dest_id = [dest_id]

        exp = self.__get_experiment(exp_id)

        # map any ids which are seen for the first time to physical locations
        for id in dest_id:
            if not exp.is_exist_location(id):
                dest = self.__decide_location(vol, len(dest_id))
                exp.set_location(id, dest)

                # operator: prepare the destination
                self.operator.place(dest)
        
            # operator: bring reagent from store to reservoir
            self.operator.move(vol, solution, exp.get_location(id))

    def transfer(self, exp_id: int, vol: int, source_id: LocationId, 
                 dest_id: LocationId | list[LocationId], discard_tip:bool = True):
        logger.info(f"OSS: Experiment {exp_id}: Transfer {vol}ul from {source_id} to {dest_id}")

        # dest_id could be a single location id or a list of location ids 
        # always convert dest_id to list for uniform handling from here on
        if not isinstance(dest_id, list):
            dest_id = [dest_id]

        exp = self.__get_experiment(exp_id)
        
        if not exp.is_exist_location(source_id):
            raise Exception("Source location does not exist")
        
        # attach tip to pipette if needed: TODO
        
        for id in dest_id:
            if not exp.is_exist_location(id):
                dest = self.__decide_location(vol, len(dest_id))
                exp.set_location(id, dest)

                # operator: prepare the destination
                self.operator.place(dest)
        
            # LH: move solution from source to destination
            self.lh.move_pipette(exp.get_location(source_id))
            self.lh.aspirate(vol)
            self.lh.move_pipette(exp.get_location(id))
            self.lh.dispense(vol)
        
        if discard_tip: self.lh.discard_tip()
        

    def mix(self, exp_id: int, dest_id: LocationId):
        logger.info(f"OSS: Experiment {exp_id}: Mix {dest_id}")
        exp = self.__get_experiment(exp_id)
    
    # ---------------------------------------------------------------
    
# ===================================================================
