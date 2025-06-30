### app_serial_dilution.py
    This is the python script which represents the researcher code for
    the serial dilution experiment. This can be executed with the 
    following command

        python app_serial_dilution.py

### app_game_of_life.py
    This is the python script which represents the researcher code for
    the game of life experiment. This can be executed with the 
    following command

        python app_game_of_life.py

### app_gradient_mixing.py
    This is the python script which represents the researcher code for
    the gradient mixing experiment. This can be executed with the 
    following command

        python app_gradient_mixing.py

### oss_lib.py
    This implements the main OSS library including the technician API. 
    Following APIs are supported:
    
        experiment_init
        experiment_end
        load
        transfer
        mix
        incubate
        measure_absorbance


### oss_utils.py
    This includes some utility class definitions and other functions which 
    support the main libraries


### operator_lib.py
    This is a stub for the operator API, and includes all the commands
    executed by the human operator. Following APIs are supported:
    
        command

### lh_lib.py
    This is a stub for the Liquid Handler API, and includes all the commands 
    executed by the robotic liquid handler. Following APIs are supported:
    
        move_pipette
        aspirate
        dispense
        discard_tip
        attach_tip

