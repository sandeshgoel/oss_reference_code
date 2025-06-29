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
    
class Labware (enum.Enum):
    reservoir = 1,
    wellplate = 2,
    testtube = 3,
    cuvette = 4

    def __str__(self) -> str:
        return self.name
    
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