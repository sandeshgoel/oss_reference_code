import datetime
import operator_lib
import lh_lib
from oss_utils import Location, LocationId, Equipment, Labware, Reagent
from oss_utils import LH_MAX_SLOTS, WELLPLATE_MAX_WELLS, WORKBENCH_MAX_SLOTS
from oss_utils import well_id_int_to_str, well_id_str_to_int, logger
import time

# ===================================================================
# Experiment class definition    

class Experiment:
    """
    @private
    """
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
        
    # find an empty slot in the workbench
    def get_empty_workbench_slot(self) -> int | None:
        """
        Find an empty slot in the workbench.

        Returns:
        int | None: The empty slot number if found, None otherwise.
        """
        for slot in range(WORKBENCH_MAX_SLOTS):
            if slot not in self.location_map:
                return slot
        return None
    
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
    _next_exp_id = 0
    _exp_list = {}
    _operator = operator_lib.Operator()
    _lh = lh_lib.LiquidHandler()
    _waste_reservoir = Location(Equipment.liquid_handler, 0, Labware.waste_reservoir, "")
    _results_not_ready = False
    _incubation_not_complete = False
              
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
        OSS._next_exp_id += 1
        logger.info(f"OSS: Experiment {OSS._next_exp_id}: Start {name}")
        new_exp = Experiment(OSS._next_exp_id, name)
        OSS._exp_list[OSS._next_exp_id] = new_exp
        return OSS._next_exp_id

    def experiment_end(self, exp_id: int):
        """
        Terminate an experiment.

        Args:
            exp_id (int): Experiment ID

        Returns:
            None
        """
        logger.info(f"OSS: Experiment {exp_id}: End")
        if exp_id in OSS._exp_list:
            del OSS._exp_list[exp_id]
        else:
            raise Exception("Experiment does not exist")

    # ---------------------------------------------------------------
    # internal helper functions
    
    def __get_experiment(self, exp_id: int):
        if exp_id in OSS._exp_list:
            return OSS._exp_list[exp_id]
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
    def load(self, exp_id: int, vol: int, solution: Reagent, dest_id: LocationId):
        """
        Load a given volume of a solution to a specified location id. 
        The physical location is always a reservoir, which is placed in an
        empty slot in a liquid handler.

        Args:
            exp_id (int): Experiment id
            vol (int): Volume of the solution to load
            solution (Reagent): Name of the solution to load
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
            self._operator.command(f'Move in place {dest}')
    
        # operator: bring reagent from store to reservoir
        #self.operator.move(vol, solution, exp.get_location(dest_id))
        self._operator.command(f'Move {vol}ul of {solution} to {exp.get_location(dest_id)}')

    def discard(self, exp_id: int, vol: int, source_id: LocationId, release_labware: bool = False):
        """
        Discard a given volume of a liquid from a specified location id, and optionally release the labware.

        Args:
            exp_id (int): Experiment id
            vol (int): Volume of the liquid to be discarded
            source_id (LocationId): Location id of the source to be discarded
            release_labware (bool, optional): Whether to release the labware from the source location. Defaults to False.

        Raises:
            Exception: Source location does not exist
        """

        logger.info(f"OSS: Experiment {exp_id}: Discard {source_id}")
        exp = self.__get_experiment(exp_id)

        if not exp.is_exist_location(source_id):
            raise Exception("Source location does not exist")

        if exp.get_location(source_id).equipment == Equipment.liquid_handler:
            # if source is in LH, transfer within LH
            self._lh.move_pipette(exp.get_location(source_id))
            self._lh.aspirate(vol)
            self._lh.move_pipette(self._waste_reservoir)
            self._lh.dispense(vol)
        else:
            # Ask operator to discard the contents
            self._operator.command(f'Discard {exp.get_location(source_id)} contents to waste reservoir')
        
        if release_labware:
            # Ask operator to return labware to storage
            self._operator.command(f'Return {exp.get_location(source_id)} to storage')
            # Release the location
            exp.remove_location(source_id)
        
    def transfer(self, exp_id: int, vol: int, source_id: LocationId, 
                 dest_id: LocationId | list[LocationId], discard_tip:bool = True, 
                 dest_id_list: list[LocationId] | None = None):
        """
        Transfer a given volume of a solution from a source location id to a destination location id (or a list of destination location ids).
        
        Use a wellplate if multiple destinations are specified, otherwise use the best
        fitting labware.

        Args:
            exp_id (int): Experiment id
            vol (int): Volume of the solution to transfer
            source_id (LocationId): Location id of the source
            dest_id (LocationId | list[LocationId]): Location id of the destination(s)
            discard_tip (bool, optional): Whether to discard the tip after the transfer. Defaults to True.
            dest_id_list (list[LocationId], optional): If a single dest_id is provided, but it is a part of a list, then the list is passed here. Defaults to None.

        Raises:
            Exception: Source location does not exist
        """
        # dest_id could be a single location id or a list of location ids 
        # always convert dest_id to list for uniform handling from here on
        if not isinstance(dest_id, list):
            dest_id = [dest_id]

        logger.info(f"OSS: Experiment {exp_id}: Transfer {vol}ul from {source_id} to {[str(id) for id in dest_id]}")

        exp = self.__get_experiment(exp_id)
        
        if not exp.is_exist_location(source_id):
            raise Exception("Source location does not exist")
        
        # TODO: get tip rack and attach tip to pipette if needed
        
        # for each dest_id, map it to physical location if needed
        for id in dest_id:
            if not exp.is_exist_location(id):
                dest, is_new = self.__decide_location(exp, vol, len(dest_id) if dest_id_list is None else len(dest_id_list))
                exp.set_location(id, dest)

                # operator: prepare the destination
                if is_new: 
                    #self.operator.place(dest)
                    self._operator.command(f'Move in place {dest}')
                    
            # LH: move solution from source to destination
            self._lh.move_pipette(exp.get_location(source_id))
            self._lh.aspirate(vol)
            self._lh.move_pipette(exp.get_location(id))
            self._lh.dispense(vol)
        
        # discard tip if required
        if discard_tip: self._lh.discard_tip()
        

    def mix(self, exp_id: int, dest_id: LocationId, vol: int, mix_count: int = 3):
        """
        Mix a specified volume of liquid at a given destination location a certain number of times.

        The function ensures the destination is within a liquid handler. If not, it moves the 
        destination to the liquid handler, performs the mix operation the specified number of times, and then returns the destination to its original location if necessary.

        Discard the tip after the mix operation.
        
        Args:
            exp_id (int): Experiment ID.
            dest_id (LocationId): The location ID where the mixing should occur.
            vol (int): Volume of the liquid to be mixed.
            mix_count (int, optional): Number of times the mixing should occur. Defaults to 3.

        Raises:
            Exception: If the destination location does not exist.
        """

        logger.info(f"OSS: Experiment {exp_id}: Mix {dest_id} {mix_count} times")
        exp = self.__get_experiment(exp_id)
        
        if not exp.is_exist_location(dest_id):
            raise Exception("Destination location does not exist")
        
        # mix happens in an LH, so if the destination is not in the LH, move it there
        lh_dest = dest = exp.get_location(dest_id)
        if  dest.equipment != Equipment.liquid_handler:
            lh_dest, is_new = self.__decide_location(exp, vol, 1)
            exp.set_location(dest_id, lh_dest)            
            if is_new: self._operator.command(f'Move in place {lh_dest}')
            self._operator.command(f'Move {dest} to {lh_dest}')
            
        # TODO: check if pipette tip can handle vol
        
        # mix it now
        self._lh.move_pipette(lh_dest)
        for i in range(mix_count):
            self._lh.aspirate(vol)
            self._lh.dispense(vol)
            
        # move it back to original location
        if dest.equipment != Equipment.liquid_handler:
            exp.set_location(dest_id, dest)
            self._operator.command(f'Move {lh_dest} to {dest}')    
            
        # discard tip
        self._lh.discard_tip()    
        
    def incubate(self, exp_id: int, target_id: list[LocationId], temperature: int, duration: int, dark:bool = False):
        """
        Incubate a list of target location ids at a given temperature for a given duration of time.

        The function waits for the incubation to complete before returning.

        Args:
            exp_id (int): Experiment id
            target_id (list[LocationId]): List of location ids to incubate
            temperature (int): Temperature to incubate at
            duration (int): Duration of incubation in minutes
            dark (bool, optional): Whether to incubate in the dark. Defaults to False.

        Raises:
            Exception: If experiment id does not exist
        """
        logger.info(f"OSS: Experiment {exp_id}: Incubate {[str(id) for id in target_id]} at {temperature} degrees for {duration} minutes")
        exp = self.__get_experiment(exp_id)
        
        self._operator.command(f'Incubate {[str(id) for id in target_id]} at {temperature} degrees for {duration} minutes')

        # Wait for incubation to complete
        while(self._incubation_not_complete):
            time.sleep(1)
                    
    def measure_absorbance(self, exp_id: int, target_id: list[LocationId], 
                           wavelength_range: tuple[int, int], 
                           blank_id: list[LocationId] = [],
                           quantification_wavelength: int = 0,
                           quantify_concentration: bool = False,
                           reference_wavelength: int = 0,
                           scan_resolution: int = 5,
                           measurement_mode: str = 'endpoint',
                           averaging_time: int = 10,
                           read_direction: str = 'row',
                           read_location: str = 'top',
                           temperature: int | str= 'ambient',
                           equilibration_time: int = 10,
                           plate_reader_mix: str = "auto",
                           plate_reader_mix_mode: str = 'auto',
                           plate_reader_mix_rate: int | str = 'auto',
                           plate_reader_mix_time: int | str = 'auto',
                           mix_settle_time: int = 10,
                           retain_cover: bool = False,
                           num_readings: int = 1
                           ) -> list[int]:
        """
        Measure absorbance of a specified wavelength range of the targets in the experiment.

        The function moves the target locations to the spectroscope, sets the parameters using the spectroscope's UI, and waits for the measurement to finish.

        If all target locations are in the same well plate, the function measures all at once. Otherwise, it measures one by one by transferring to a cuvette.
        
        After measurement, the original labware is placed on the workbench.

        Args:
            exp_id (int): Experiment id
            target_id (list[LocationId]): List of location ids of the targets to be measured
            wavelength_range (tuple[int, int]): Tuple of two integers representing the start and end of the wavelength range in nm
            blank_id (list[LocationId], optional): List of location ids of the blank wells to be measured. Defaults to [].
            quantification_wavelength (int, optional): Wavelength in nm at which the concentration should be quantified. Defaults to 0.
            quantify_concentration (bool, optional): Whether to quantify the concentration. Defaults to False.
            reference_wavelength (int, optional): Reference wavelength in nm. Defaults to 0.
            scan_resolution (int, optional): Scan resolution in nm used in dual wavelength correction. Defaults to 5.
            measurement_mode (str, optional): Measurement mode. Possible values: 'endpoint', 'kinetic', 'spectrum', 'dualread'. Defaults to 'endpoint'.
            averaging_time (int, optional): Averaging time in seconds. Defaults to 10.
            read_direction (str, optional): Read direction. Possible values: 'row', 'column', 'serpentinerow', 'serpentinecolumn'. Defaults to 'row'.
            read_location (str, optional): Read location. Possible values: 'top', 'bottom', 'auto'. Defaults to 'top'.
            temperature (int | str, optional): Temperature at which the measurement should be taken in degrees Celsius. Defaults to 'ambient'.
            equilibration_time (int, optional): Equilibration time in seconds. Defaults to 10.
            plate_reader_mix (str, optional): Plate reader mix. Possible values: 'auto', 'true', 'false'. Defaults to "auto".
            plate_reader_mix_mode (str, optional): Plate reader mix mode. Possible values: 'auto', 'orbital', 'doubleorbital', 'linear'. Defaults to 'auto'.
            plate_reader_mix_rate (int | str, optional): Plate reader mix rate in range 100-700 RPM. Defaults to 'auto'.
            plate_reader_mix_time (int | str, optional): Plate reader mix time in range 1-3600 seconds. Defaults to 'auto'.
            mix_settle_time (int, optional): Mix settle time in seconds. Defaults to 10.
            retain_cover (bool, optional): Whether to retain the cover. Defaults to False.
            num_readings (int, optional): Number of replicate readings. Defaults to 1.

        Returns:
            list[int]: List of measured absorbance values corresponding to the target locations
        """
        logger.info(f"OSS: Experiment {exp_id}: Measure absorbance of {[str(id) for id in target_id]} at {wavelength_range} nm")
        exp = self.__get_experiment(exp_id)
        
        # add blank well ids to the list of targets for measurement
        target_id = target_id + blank_id
        
        # check if all target locations exist
        if any([not exp.is_exist_location(id) for id in target_id]): 
            raise Exception("Some Target location does not exist")

        results = []
        
        # check if all target locations are in the same well plate
        if all([exp.get_location(id).labware == Labware.wellplate for id in target_id]):
            # assume a single well plate, raise exception if not
            if len(set([exp.get_location(id).slot for id in target_id])) > 1:
                raise Exception("All target locations must be in the same well plate")
            else:
                dest = exp.get_location(target_id[0])
                # if a single well plate, measure all at once
                self._operator.command(f'Move {dest} to spectroscope')
                self._operator.command(f'Select absorbance spectroscopy')
                self._operator.command(f'Set all parameters using spectroscope"s UI')
                self._operator.command(f'Press start button and wait for measurement to finish')
                self._operator.command(f'Upload results to data folder when ready')

                # Wait for result file to be ready
                while(self._results_not_ready):
                    time.sleep(1)
                    
                # download the result file and map it back to logical ids
                results = [1] * len(target_id)
                
                # transfer wellplate to workbench
                dest.equipment = Equipment.workbench
                dest.slot = exp.get_empty_workbench_slot()
                if dest.slot is None:
                    raise Exception("No empty workbench slot")

                # update location mapping for all location ids                
                for id in target_id:
                    dest.well_id = exp.get_location(id).well_id
                    exp.release_location(id)
                    exp.set_location(id, dest)

                self._operator.command(f'Move wellplate to {dest}')
        else:
            # if not a single well plate, move each target to cuvette 
            # and measure one by one
            for id in target_id:
                dest = exp.get_location(id)
                # trasfer to cuvette and measure
                self._operator.command(f'Move {dest} to cuvette')
                self._operator.command(f'Move cuvette to spectroscope')
                self._operator.command(f'Select absorbance spectroscopy')
                self._operator.command(f'Set all parameters using spectroscope"s UI')
                self._operator.command(f'Press start button and wait for measurement to finish')
                self._operator.command(f'Upload results to data folder when ready')

                # Wait for result file to be ready
                while(self._results_not_ready):
                    time.sleep(1)
                    
                # download the result file and map it back to logical ids
                results.append(1)
                
                # find available slot in workbench 
                dest.equipment = Equipment.workbench
                dest.slot = exp.get_empty_workbench_slot()
                if dest.slot is None:
                    raise Exception("No empty workbench slot")
                exp.release_location(id)
                exp.set_location(id, dest)
                
                # transfer back to labware and move to workbench
                self._operator.command(f'Move cuvette to {dest}')
                
        return results
    
    # ---------------------------------------------------------------
    
# ===================================================================
