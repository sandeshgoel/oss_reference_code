app_serial_dilution.py
    This is the python script which represent the researcher code for
    the serial dilution experiment. This can be executed with the 
    following command

        python app_serial_dilution.py


oss_lib.py
    This implements the main OSS library including the technician API. 
    Following APIs are supported:
        experiment_init
        experiment_end
        bring
        transfer
        mix


oss_utils.py
    This includes some utility class definitions and other functions which 
    support the main libraries


operator_lib.py
    This implements the Operaror library, which includes all the commands
    executed by the human operator. Following APIs are supported:
        place
        move

lh_lib.py
    This implements the Liquid Handler library, which includes all the 
    commands executed by the robotic liquid handler. Following APIs are supported:
        move_pipette
        aspirate
        dispense
        discard_tip

