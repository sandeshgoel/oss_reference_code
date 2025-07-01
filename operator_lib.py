from  oss_utils import Location, LocationId, Equipment, Labware, logger

# Operator class definition
class Operator:
    
    def command(self, command: str):
        logger.debug("\tOP: %s", command)
        
    # def place(self, dest: Location):
    #     logger.debug("OP: place %s", dest) 
        
    # def move(self, vol: int, solution: str, dest: Location):
    #     logger.debug("OP: move %dul of %s from storage to %s", vol, solution, dest)