import enum
import logging

# -------------------------------------------------------------------
# Logger initialization

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s %(message)s',
    handlers=[logging.FileHandler('oss.log'), logging.StreamHandler()]
    )
logger = logging.getLogger()

# -------------------------------------------------------------------
# Equipment class

class Equipment(enum.Enum):
    workbench = 0,
    liquid_handler = 1,
    incubator = 2,
    spectroscope = 3
    
    def __str__(self) -> str:
        return self.name
    
WORKBENCH_MAX_SLOTS = 20
LH_MAX_SLOTS = 12

# -------------------------------------------------------------------
# Labware class

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

# -------------------------------------------------------------------
# Location class

class Location:
    def __init__(self, equipment: Equipment, slot: int, labware: Labware, well_id: str):
        self.equipment = equipment
        self.slot = slot
        self.labware = labware
        self.well_id = well_id
        
    def __str__(self):
        if self.labware == Labware.wellplate:
            return f"[{self.equipment}:slot-{self.slot}:{self.labware}:{self.well_id}]"
        else:
            return f"[{self.equipment}:slot-{self.slot}:{self.labware}]"

# -------------------------------------------------------------------
# Location id class
        
class LocationId:
    def __init__(self, id: str):
        self.id = id
        
    def __str__(self):
        return f'id {self.id}'
    
# -------------------------------------------------------------------
# Reagent class

from abc import ABC

class Reagent(ABC):
    """Abstract base class for all reagents"""
    
    def __init__(self, name: str):
        self.name = name
    
    def __str__(self) -> str:
        return f"{self.name}"
    
class StandardReagent(Reagent):
    """Predefined standard reagents"""
    
    # Predefined list of standard reagents
    STANDARD_REAGENTS = [
        'Water',
        'Acetone',
        'Ethanol',
        'Benzene',
        'Toluene',
        'Hexane',
        'Heptane',
        'Octane',
    ]
    
    def __init__(self, name: str):
        if name not in self.STANDARD_REAGENTS:
            raise ValueError(f"'{name}' is not a standard reagent. "
                           f"Available reagents: {self.STANDARD_REAGENTS}")
        super().__init__(name)
    
    @classmethod
    def list_available(cls) -> list[str]:
        """Return list of available standard reagents"""
        return cls.STANDARD_REAGENTS.copy()


class CustomReagent(Reagent):
    """User-defined custom reagents"""
    
    def __init__(self, name: str):
        super().__init__('custom-'+name)
        
# -------------------------------------------------------------------
