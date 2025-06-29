from oss_utils import Location, logger

class LiquidHandler:

    def move_pipette(self, location: Location):
        logger.debug(f'LH: move pipette to {location}')
        
    def aspirate(self, vol:int):
        logger.debug(f'LH: aspirate {vol}ul')
        
    def dispense(self, vol:int):
        logger.debug(f'LH: dispense {vol}ul')   
        
    def discard_tip(self):
        logger.debug(f'LH: discard tip')