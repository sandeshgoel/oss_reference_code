from collections import Counter

class OSS:
    func_calls = Counter()
    num_actions = Counter()
    
    def experiment_init(self, name: str):
        print("OSS.experiment_init called (stub)")
        return 1

    def experiment_end(self, exp_id: int):
        print("OSS.experiment_end called (stub)\n")
        for f in self.func_calls.keys():
            print(f"{f:25}: {self.func_calls[f]:4} calls, {self.num_actions[f]:4} actions")
            
    def load(self, exp_id: int, vol: int, solution, dest_id):
        print("OSS.load called (stub)")
        self.func_calls['load'] += 1
        self.num_actions['load'] += len(dest_id) if isinstance(dest_id, list) else 1

    def discard(self, exp_id: int, vol: int, source_id, release_labware: bool = False):
        print("OSS.discard called (stub)")
        self.func_calls['discard'] += 1
        self.num_actions['discard'] += 1

    def transfer(self, exp_id: int, vol: int, source_id, dest_id, discard_tip: bool = True, dest_id_list=None):
        print("OSS.transfer called (stub)")
        self.func_calls['transfer'] += 1
        self.num_actions['transfer'] += len(dest_id) if isinstance(dest_id, list) else 1

    def mix(self, exp_id: int, dest_id, vol: int, mix_count: int = 3):
        print("OSS.mix called (stub)")
        self.func_calls['mix'] += 1
        self.num_actions['mix'] += len(dest_id) if isinstance(dest_id, list) else 1

    def incubate(self, exp_id: int, target_id, temperature: int, duration: int, dark: bool = False):
        print("OSS.incubate called (stub)")
        self.func_calls['incubate'] += 1
        self.num_actions['incubate'] += 1

    def measure_absorbance(self, exp_id: int, target_id, wavelength_range, blank_id=None, scan_step: int = 5,
                           reference_wavelength: int = 0, wait_time: int = 10, read_direction: str = 'row',
                           read_location: str = 'top', temperature='ambient', plate_reader_shake_mode: str = 'endpoint',
                           shake: str = "auto", shake_frequency='auto', shake_amplitude: int = 2,
                           shake_duration='auto', mix_settle_time: int = 10, retain_cover: bool = False):
        print("OSS.measure_absorbance called (stub)")
        self.func_calls['measure_absorbance'] += 1
        self.num_actions['measure_absorbance'] += 1
        