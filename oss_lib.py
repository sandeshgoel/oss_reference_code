import datetime
import operator_lib
import lh_lib
from oss_utils import Location, LocationId, Equipment, Labware
from oss_utils import LH_MAX_SLOTS, WELLPLATE_MAX_WELLS, WELLPLATE_ROW_SIZE
from oss_utils import well_id_int_to_str, well_id_str_to_int, logger

# ===================================================================
# Experiment class definition    

class Experiment:
    def __init__(self, exp_id: int, name:str):
        logger.info(f"Experiment {exp_id} created")
        self.exp_id = exp_id
        self.name = name
        self.create_time = datetime.datetime.now()
        self.location_map = {}
        self.lh_slots_used = []
        
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
            if location.equipment == Equipment.liquid_handler:
                self.lh_slots_used.append(location.slot)
            
    def release_location(self, loc_id: LocationId):
        logger.info(f"Experiment {self.exp_id}: Release location {loc_id}")
        if self.is_exist_location(loc_id):
            if self.location_map[loc_id].equipment == Equipment.liquid_handler:
                self.lh_slots_used.remove(self.location_map[loc_id].slot)
            del self.location_map[loc_id]
        else:
            raise Exception("Location does not exist")
        
    # find an empty slot in the liquid handler
    def get_empty_slot(self) -> int | None:
        for slot in range(LH_MAX_SLOTS):
            if slot not in self.lh_slots_used:
                return slot
        return None
        
    # find an empty well in a wellplate already inside a liquid handler
    def get_empty_well(self) -> Location | None:
        slot_well_list = {}
        for id in self.location_map:
            if self.location_map[id].equipment == Equipment.liquid_handler and \
                self.location_map[id].labware == Labware.wellplate:
                    if slot_well_list.get(self.location_map[id].slot, None) is None:
                        slot_well_list[self.location_map[id].slot] = []
                    slot_well_list[self.location_map[id].slot].append(
                         self.location_map[id].well_id)
        
        for slot in slot_well_list:
            for well in range(WELLPLATE_MAX_WELLS):
                well_str = well_id_int_to_str(well)
                if well_str not in slot_well_list[slot]:
                    return Location(Equipment.liquid_handler, slot, Labware.wellplate, well_str)
        return None
        
              
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
        
    def __decide_location(self, exp: Experiment, vol: int, num_dests: int) -> tuple[Location, bool]:
        # Rule: pick the smallest capacity labware that can handle the vol. 
        # If destination is unitary, use test tube. 
        # Else use well plate, with the smallest well-plate size 
        # that can handle the list.
        
        if num_dests > 1 and Labware.wellplate.max_capacity() > vol:
            best_fit = Labware.wellplate
        else:
            best_fit = None
            for labware in Labware:
                if labware.max_capacity() >= vol:
                    if (not best_fit) or (labware.max_capacity() < best_fit.max_capacity()): 
                        best_fit = labware
            if not best_fit:
                raise Exception("No labware can hold the volume")
                        
        empty_slot = exp.get_empty_slot()
        if best_fit == Labware.wellplate:
            # check is wellplate is already present with empty well
            empty_well = exp.get_empty_well()
            if empty_well:
                return empty_well, False
            else:
                # add a new wellplate in an empty slot
                if empty_slot is None:
                    raise Exception("No empty slot in liquid handler")
                return Location(equipment=Equipment.liquid_handler, slot=empty_slot, 
                                labware=best_fit, well_id='A0'), True
        else:
            if empty_slot is None:
                raise Exception("No empty slot in liquid handler")
            return Location(equipment=Equipment.liquid_handler, slot=empty_slot, 
                            labware=best_fit, well_id='A0'), True
                
    # ---------------------------------------------------------------
    # Experiment actions 
    
    def load(self, exp_id: int, vol: int, solution: str, dest_id: LocationId | list[LocationId]):
        logger.info(f"OSS: Experiment {exp_id}: Load {vol}ul of {solution} to {dest_id}")

        # dest_id could be a single location id or a list of location ids 
        # always convert dest_id to list for uniform handling from here on
        if not isinstance(dest_id, list):
            dest_id = [dest_id]

        exp = self.__get_experiment(exp_id)

        # map any ids which are seen for the first time to physical locations
        for id in dest_id:
            if not exp.is_exist_location(id):
                dest, is_new = self.__decide_location(exp, vol, len(dest_id))
                exp.set_location(id, dest)

                # operator: prepare the destination
                if is_new: self.operator.place(dest)
        
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
                dest, is_new = self.__decide_location(exp, vol, len(dest_id))
                exp.set_location(id, dest)

                # operator: prepare the destination
                if is_new: self.operator.place(dest)
        
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
