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
        """
        Initialize an Experiment object.

        Parameters:
        exp_id (int): Experiment ID
        name (str): Experiment name

        Returns:
        None
        """
        
        logger.info(f"Experiment {exp_id} created")
        self.exp_id = exp_id
        self.name = name
        self.create_time = datetime.datetime.now()
        self.location_map = {}
        self.lh_slots_used = []
        # TODO: add more experiment state here
        
    def is_exist_location(self, loc_id: LocationId):
        """
        Check if a location ID exists in the experiment's location map.

        Args:
        loc_id (LocationId): The location ID to check.

        Returns:
        bool: True if the location ID exists, False otherwise.
        """

        return loc_id in self.location_map
    
    def get_location(self, loc_id: LocationId):
        """
        Retrieve the physical location of a given location ID.

        Args:
        loc_id (LocationId): The location ID to retrieve the physical location for.

        Returns:
        Location: The physical location corresponding to the given location ID.

        Raises:
        Exception: Location ID does not exist in the experiment's location map.
        """
        return self.location_map[loc_id]
    
    def set_location(self, loc_id: LocationId, location: Location):
        """
        Set a location ID to a physical location.

        Args:
        loc_id (LocationId): The location ID to set.
        location (Location): The physical location to set the location ID to.

        Raises:
        Exception: Location ID already exists in the experiment's location map.
        """
        logger.info(f"Experiment {self.exp_id}: Set location {loc_id} to {location}")
        if self.is_exist_location(loc_id):
            raise Exception("Location already exists")
        else:
            self.location_map[loc_id] = location
            if location.equipment == Equipment.liquid_handler:
                self.lh_slots_used.append(location.slot)
            
    def release_location(self, loc_id: LocationId):
        """
        Release a location ID from the location map.
        
        Args:
        loc_id (LocationId): The location ID to release.
        
        Raises:
        Exception: Location ID does not exist in the experiment's location map.
        """
        logger.info(f"Experiment {self.exp_id}: Release location {loc_id}")
        if self.is_exist_location(loc_id):
            if self.location_map[loc_id].equipment == Equipment.liquid_handler:
                self.lh_slots_used.remove(self.location_map[loc_id].slot)
            del self.location_map[loc_id]
        else:
            raise Exception("Location does not exist")
        
    # find an empty slot in the liquid handler
    def get_empty_slot(self) -> int | None:
        """
        Find an empty slot in the liquid handler.

        Returns:
        int | None: The empty slot number if found, None otherwise.
        """
        for slot in range(LH_MAX_SLOTS):
            if slot not in self.lh_slots_used:
                return slot
        return None
        
    # find an empty well in a wellplate already inside a liquid handler
    def get_empty_well(self) -> Location | None:
        """
        Find an empty well in a wellplate that is already inside a liquid handler.

        Returns:
        Location | None: A Location object representing the empty well if found, 
        otherwise None if no empty well is available.
        """

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
        """
        Create a new experiment.

        Args:
            name (str): Name of the experiment

        Returns:
            int: Experiment ID
        """
        OSS.next_exp_id += 1
        logger.info(f"OSS: Experiment {OSS.next_exp_id}: Start {name}")
        new_exp = Experiment(OSS.next_exp_id, name)
        OSS.exp_list[OSS.next_exp_id] = new_exp
        return OSS.next_exp_id

    def experiment_end(self, exp_id: int):
        """
        Terminate an experiment.

        Args:
            exp_id (int): Experiment ID

        Returns:
            None
        """
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
        """
        Decide the best location for a liquid to be dispensed.
        Use a wellplate if multiple destinations are specified, otherwise use the best
        fitting labware.

        Parameters:
        exp (Experiment): Experiment object
        vol (int): Volume of the liquid
        num_dests (int): Number of destinations

        Returns:
        tuple[Location, bool]: A Location object and a boolean indicating whether a new labware needs to be placed.
        """
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
    
    #
    def load(self, exp_id: int, vol: int, solution: str, dest_id: LocationId):
        """
        Load a given volume of a solution to a specified location id. 
        The physical location is always a reservoir.

        Args:
        exp_id (int): Experiment id
        vol (int): Volume of the solution to load
        solution (str): Name of the solution to load
        dest_id (LocationId): Location id of the destination

        Raises:
        Exception: No empty slot in liquid handler
        """
        logger.info(f"OSS: Experiment {exp_id}: Load {vol}ul of {solution} to {dest_id}")

        exp = self.__get_experiment(exp_id)

        # map location id seen for the first time to physical locations
        if not exp.is_exist_location(dest_id):
            empty_slot = exp.get_empty_slot()
            if empty_slot is None:
                raise Exception("No empty slot in liquid handler")
            
            dest = Location(equipment=Equipment.liquid_handler, slot=empty_slot, 
                            labware=Labware.reservoir, well_id='A0')
            exp.set_location(dest_id, dest)

            # operator: prepare the destination
            self.operator.command(f'Move in place {dest}')
    
        # operator: bring reagent from store to reservoir
        #self.operator.move(vol, solution, exp.get_location(dest_id))
        self.operator.command(f'Move {vol}ul of {solution} to {exp.get_location(dest_id)}')

    def transfer(self, exp_id: int, vol: int, source_id: LocationId, 
                 dest_id: LocationId | list[LocationId], discard_tip:bool = True):
        """
        Transfer a given volume of a solution from a source location id to a destination location id (or a list of destination location ids).

        Args:
        exp_id (int): Experiment id
        vol (int): Volume of the solution to transfer
        source_id (LocationId): Location id of the source
        dest_id (LocationId | list[LocationId]): Location id of the destination(s)
        discard_tip (bool, optional): Whether to discard the tip after the transfer. Defaults to True.

        Raises:
        Exception: Source location does not exist
        """
        logger.info(f"OSS: Experiment {exp_id}: Transfer {vol}ul from {source_id} to {dest_id}")

        # dest_id could be a single location id or a list of location ids 
        # always convert dest_id to list for uniform handling from here on
        if not isinstance(dest_id, list):
            dest_id = [dest_id]

        exp = self.__get_experiment(exp_id)
        
        if not exp.is_exist_location(source_id):
            raise Exception("Source location does not exist")
        
        # TODO: attach tip to pipette if needed
        
        # for each dest_id, map it to physical location if needed
        for id in dest_id:
            if not exp.is_exist_location(id):
                dest, is_new = self.__decide_location(exp, vol, len(dest_id))
                exp.set_location(id, dest)

                # operator: prepare the destination
                if is_new: 
                    #self.operator.place(dest)
                    self.operator.command(f'Move in place {dest}')
                    
            # LH: move solution from source to destination
            self.lh.move_pipette(exp.get_location(source_id))
            self.lh.aspirate(vol)
            self.lh.move_pipette(exp.get_location(id))
            self.lh.dispense(vol)
        
        # discard tip if required
        if discard_tip: self.lh.discard_tip()
        

    def mix(self, exp_id: int, dest_id: LocationId):
        logger.info(f"OSS: Experiment {exp_id}: Mix {dest_id}")
        exp = self.__get_experiment(exp_id)
        # TODO: procedure
    
    def wash(self, exp_id: int, target_id: LocationId):
        logger.info(f"OSS: Experiment {exp_id}: Wash {target_id}")
        exp = self.__get_experiment(exp_id)
        # TODO: procedure
                
    def incubate(self, exp_id: int, target_id: list[LocationId], temperature: int, time: int, dark:bool = False):
        logger.info(f"OSS: Experiment {exp_id}: Incubate {[str(id) for id in target_id]} at {temperature} degrees for {time} minutes")
        exp = self.__get_experiment(exp_id)
        # TODO: procedure
        
    def measure_absorbance(self, exp_id: int, target_id: list[LocationId], wavelength: int) -> list[int]:
        logger.info(f"OSS: Experiment {exp_id}: Measure absorbance of {[str(id) for id in target_id]} at {wavelength} nm")
        exp = self.__get_experiment(exp_id)
        # TODO: procedure

        return [1] * len(target_id)

    # ---------------------------------------------------------------
    
# ===================================================================
