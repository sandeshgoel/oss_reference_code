import enum
import logging

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('oss.log'), logging.StreamHandler()]
    )
logger = logging.getLogger()

class Equipment(enum.Enum):
    liquid_handler = 1,
    incubator = 2,
    spectrocope = 3
    
    def __str__(self) -> str:
        return self.name
    
LH_MAX_SLOTS = 12

class Labware (enum.Enum):
    reservoir = 1,
    wellplate = 2,
    testtube = 3,
    cuvette = 4

    def max_capacity(self) -> int:
        if self == Labware.reservoir:
            return 1000
        elif self == Labware.wellplate:
            return 50
        elif self == Labware.testtube:
            return 100
        elif self == Labware.cuvette:
            return 100
        else:
            raise Exception("Unknown labware")
        
    def min_capacity(self) -> int:
        if self == Labware.reservoir:
            return 50
        elif self == Labware.wellplate:
            return 10
        elif self == Labware.testtube:
            return 10
        elif self == Labware.cuvette:
            return 10
        else:
            raise Exception("Unknown labware")
        
    def __str__(self) -> str:
        return self.name

WELLPLATE_MAX_WELLS = 96
WELLPLATE_ROW_SIZE = 8  

def well_id_str_to_int(well_id: str) -> int:
    return int(well_id[1:]) + ord(well_id[0].upper()) - ord('A') * WELLPLATE_ROW_SIZE

def well_id_int_to_str(well_id: int) -> str:
    return chr(well_id // WELLPLATE_ROW_SIZE + ord('A')) + str(well_id % WELLPLATE_ROW_SIZE)

class Location:
    def __init__(self, equipment: Equipment, slot: int, labware: Labware, well_id: str):
        self.equipment = equipment
        self.slot = slot
        self.labware = labware
        self.well_id = well_id
        
    def __str__(self):
        return f"[{self.equipment}:slot {self.slot}:{self.labware}:{self.well_id}]"
        
class LocationId:
    def __init__(self, id: str):
        self.id = id
        
    def __str__(self):
        return f'id {self.id}'