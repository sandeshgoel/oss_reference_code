from oss_utils import LocationId, logger
import oss_lib
import time

class ResearcherLib:
    
    _oss = oss_lib.OSS()
        
    def wash(self, exp_id: int, target_id: list[LocationId], wash_buffer: LocationId, 
             wash_volume: int, wash_cycles: int = 3, soak_time: float = 0.0,
             mix_after_soak: bool = False, mix_cycles: int = 0, mix_volume: int | None = None):
        """
        Wash the specified target location id.

        Args:
            exp_id (int): Experiment id
            target_id (list[LocationId]): List of target location ids
            wash_buffer (LocationId): Wash buffer location id
            wash_volume (int): Wash volume
            wash_cycles (int, optional): Number of wash cycles. Defaults to 3.
            soak_time (float, optional): Soak time in seconds. Defaults to 0.0.
            mix_after_soak (bool, optional): Whether to mix after the soak. Defaults to False.
            mix_cycles (int, optional): Number of mix cycles. Defaults to 0.
            mix_volume (int, optional): Mix volume. Defaults to None.

        Raises:
            Exception: If the target location does not exist
        """
        logger.info(f"Researcher: Experiment {exp_id}: Wash {[str(id) for id in target_id]}")
        
        for cycle in range(wash_cycles):
            for id in target_id:
                # Step 1: Dispense wash buffer
                self._oss.transfer(exp_id, wash_volume, wash_buffer,  id)

                # Step 2: Optional soak
                if soak_time:
                    time.sleep(soak_time)

                # Step 3: Mix in well
                if mix_volume is None:
                    mix_volume = wash_volume
                self._oss.mix(exp_id, id, mix_volume, mix_cycles)

                # Step 4: Discard to waste
                self._oss.discard(exp_id, id)
                
