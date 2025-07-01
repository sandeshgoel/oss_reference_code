from oss_utils import Location, logger

class LiquidHandler:

    def attach_tip(self):
        logger.debug(f'\tLH: attach tip')
        
    def move_pipette(self, location: Location):
        logger.debug(f'\tLH: move pipette to {location}')
        
    def aspirate(self, vol:int):
        logger.debug(f'\tLH: aspirate {vol}ul')
        
    def dispense(self, vol:int):
        logger.debug(f'\tLH: dispense {vol}ul')   
        
    def discard_tip(self):
        logger.debug(f'\tLH: discard tip')