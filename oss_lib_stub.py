from oss_utils import logger
from collections import Counter

class OSS:
    func_calls = Counter()
    num_actions = Counter()
    material_required = Counter()
    
    def experiment_init(self, name: str):
        logger.info("OSS.experiment_init called (stub)")
        return 1

    def experiment_end(self, exp_id: int):
        logger.info("OSS.experiment_end called (stub)\n")
        for f in self.func_calls.keys():
            logger.debug(f"{f:25}: {self.func_calls[f]:4} calls, {self.num_actions[f]:4} actions")
        for m in self.material_required.keys():
            logger.info(f"Material {m:30}: {self.material_required[m]:4} units required")
            
    def load(self, exp_id: int, vol: int, solution, dest_id):
        logger.debug("OSS.load called (stub)")
        self.func_calls['load'] += 1
        self.num_actions['load'] += len(dest_id) if isinstance(dest_id, list) else 1
        self.material_required[solution.name] += vol if not isinstance(dest_id, list) else vol*len(dest_id)

    def discard(self, exp_id: int, vol: int, source_id, release_labware: bool = False):
        logger.debug("OSS.discard called (stub)")
        self.func_calls['discard'] += 1
        self.num_actions['discard'] += 1

    def transfer(self, exp_id: int, vol: int, source_id, dest_id, discard_tip: bool = True, dest_id_list=None):
        logger.debug("OSS.transfer called (stub)")
        self.func_calls['transfer'] += 1
        self.num_actions['transfer'] += len(dest_id) if isinstance(dest_id, list) else 1

    def mix(self, exp_id: int, dest_id, vol: int, mix_count: int = 3):
        logger.debug("OSS.mix called (stub)")
        self.func_calls['mix'] += 1
        self.num_actions['mix'] += len(dest_id) if isinstance(dest_id, list) else 1

    def incubate(self, exp_id: int, target_id, temperature: int, duration: int, dark: bool = False):
        logger.debug("OSS.incubate called (stub)")
        self.func_calls['incubate'] += 1
        self.num_actions['incubate'] += 1

    def measure_absorbance(self, exp_id: int, target_id, wavelength_range, blank_id=None, scan_step: int = 5,
                           reference_wavelength: int = 0, wait_time: int = 10, read_direction: str = 'row',
                           read_location: str = 'top', temperature='ambient', plate_reader_shake_mode: str = 'endpoint',
                           shake: str = "auto", shake_frequency='auto', shake_amplitude: int = 2,
                           shake_duration='auto', mix_settle_time: int = 10, retain_cover: bool = False):
        logger.debug("OSS.measure_absorbance called (stub)")
        self.func_calls['measure_absorbance'] += 1
        self.num_actions['measure_absorbance'] += 1
