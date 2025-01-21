from time import sleep
from api import *


# Define global variables
LOADING_FLAG_NAME = "LoadingPage"

# Define tank names and commands
tanks = [
    'C21',
    'C22',
    'C23',
    'C24',
    'C25',
    'C26',
    'F31',
    'F32',
    'F33',
    'F34',
    'F35',
    'W11',
    'W12',
    'M50',
]


tank_commands = ["Lock", "Pause", "Stop", "Zero", "QtyF.Play"]
hopper_commands = ["Lock", "Pause", "Stop", "Zero"]
hopper_qty_commands = {
    "Hopper1" : "QtyF",
    "Hopper2" : "QtyW1",
    "Hopper3" : "QtyW2",
    "Hopper4" : "QtyW3",
    "Hopper5" : "QtyW4",
                        
}

has_sel = ["Stop", "Lock"]
values = ["Sel", "Cmd", "Per", "On"]
read_values = ["Sel", "Per"]
write_values = ["Cmd"]

# Define float values and their corresponding PLC tags
float_values = {
    "Req": "Dem",
    "Actual": "Act",
    "Total": "ActT",
    "Remaining": "Rest",
}

read_float_values = [
    "Actual",
    "Total",
    "Remaining",
]

write_float_values = [
    "Req",
]




def strip_dot(name:str) -> str:
    if '.' in name:
        return name.split('.')[-1]
    return name

def generate_load_tank_values():
    m = Macro('LoadTankValues', 'Resets all the values for the tank screen')
    
    m.prepare()

    t = Variable('t', 'bool', True)
    f = Variable('f', 'bool', True)
    zero = Variable('zero', 'float', 0.0)

    m.write(
        COMMENT('Set loading flag'),
        SetData(t, HMI_NAME, LOADING_FLAG_NAME),
        DELAY(2000),
    )
    
    for command in tank_commands:
        for value in values:
            if value == "Sel" and command not in has_sel:
                continue
            hmi_tag = f"Tank{strip_dot(command)}{value}"
            m.write(
                SetData(f, HMI_NAME, hmi_tag),
            )
    m.write(EMPTY())
    
    # Add float values for each tank
    for hmi_part, plc_suffix in float_values.items():
        hmi_tag = f"Tank{hmi_part}"
        m.write(
            SetData(zero, HMI_NAME, hmi_tag),
        )
    m.write(EMPTY())

    m.end()
    m.display()

def generate_update_tank_values():
    m = Macro('UpdateTankValues', 'Updates the values for the tank screen')
    
    m.prepare()
    plcVal = vbool('plcVal')
    f = vbool('f', False)
    plcFloat = vfloat('plcFloat')
    plcMax = vfloat('plcMax')
    plcReqMax = vfloat('plcReqMax')
    tankSelected = vbool('tankSelected')
    
    for tank in tanks:
        m.write(
            COMMENT(f'{tank} Tank'),
            GetData(tankSelected, HMI_NAME, tank),
            C_IF(tankSelected.as_literal()),
        )
        
        for command in tank_commands:
            for value in read_values:
                plc_val = value
                hmi_val = value
                # 'Sel' and 'On' was ambiguous. On PLC 'Sel' is used as a status and 'On' is used internally
                # On HMI 'On' is is used as status unless 'Sel' was declared.
                # This is due to a misunderstanding of the tags, and it would take a bit to modify
                # so this is just a patch
                if command not in has_sel:
                    if value == "Sel":
                        hmi_val = "On"
                    if value == "On":
                        continue
                plc_tag = f"{tank}.{command}.{plc_val}"
                hmi_tag = f"Tank{strip_dot(command)}{hmi_val}"
                m.write(
                    GetData(plcVal, PLC_NAME, plc_tag),
                    SetData(plcVal, HMI_NAME, hmi_tag)
                )
            m.write(EMPTY())
        # Read float values
        for hmi_part, plc_suffix in float_values.items():
            if hmi_part not in read_float_values:
                continue
            plc_tag = f"{tank}.QtyF.{plc_suffix}"
            hmi_tag = f"Tank{hmi_part}"
            var = plcFloat
            if hmi_part == "Total":
                var = plcReqMax
            m.write(
                GetData(var, PLC_NAME, plc_tag),
                SetData(var, HMI_NAME, hmi_tag),
            )
        m.write(
            GetData(plcMax, PLC_NAME, f'{tank}.HLimit'),
            plcReqMax.set(plcMax - plcReqMax),
            SetData(plcReqMax, HMI_NAME, 'TankReqMax'),
            COMMENT('Reset loading flag'),
            ASYNC_TRIG_MACRO('ResetLoadingFlag1S'),
            RETURN(),
            C_END_IF(),
        )

    m.end()
    m.display()

# Generate WriteCmd Script
def generate_write_tank_values():
    print(header)
    script = "// Writes the modified values for the tank screen\n"
    script += "macro_command main()\n"
    script += "    // Declare variables\n"
    script += "    float hmiFloat\n"
    script += "    bool f = false\n"
    script += "    bool t = true\n"
    script += "    bool hmiVal, tankSelected\n\n"
    
    for tank in tanks:
        script += f"    // {tank} Tank\n"
        script += f"    GetData(tankSelected, \"{HMI_NAME}\", \"{tank}\", 1)\n"
        script +=  "    if tankSelected then\n"
        for command in tank_commands:
            for value in write_values:
                plc_tag = f"{tank}.{command}.{value}"
                hmi_tag = f"Tank{strip_dot(command)}{value}"
                script += f"        GetData(hmiVal, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
                script += f"        if hmiVal then\n"
                script += f"            SetData(t, \"{PLC_NAME}\", \"{plc_tag}\", 1)\n"
                script += f"            SetData(f, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
                script += f"            return\n"
                script += f"        end if\n\n"
            
        for hmi_part, plc_part in float_values.items():
            if hmi_part not in write_float_values:
                continue
            plc_tag = f"{tank}.QtyF.{plc_part}"
            hmi_tag = f"Tank{hmi_part}"
            script += f"        GetData(hmiFloat, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
            script += f"        SetData(hmiFloat, \"{PLC_NAME}\", \"{plc_tag}\", 1)\n"
                
        script += f"        return\n"
        script += "    end if\n\n"
        print(script)
        script = ''
    script += "end macro_command\n"
    print(script)

# Define hopper names and commands
hoppers = ["H41", "H42", "H43", "H44"]
hopper_feed_counts = {
    'H41' : 3,
    'H42' : 4,
    'H43' : 2,
    'H44' : 1,
}

# Generate LoadHopperValues Script
def generate_load_hopper_values():
    print(header)
    script = "// Resets all the values for the hopper screen\n"
    script += "macro_command main()\n"
    script += "    // Declare variables for data from PLC\n"
    script += "    bool plcVal\n"
    script += "    bool f = false\n"
    script += "    bool t = true\n"
    script += "    float zero = 0\n"
    script += "    bool hopperSelected\n"
    script += "    float plcFloat\n\n"
    
    script += f"    // Set loading flag\n"
    script += f'    SetData(t, "{HMI_NAME}", "{LOADING_FLAG_NAME}", 1)\n\n'
    script += f'    DELAY(2000)\n'
    
    
    # Disable commands (Lock, Pause, Stop, Zero)
    script += f"    // Reset Command values\n"
    for command in hopper_commands:
        for value in values:
            hmi_tag = f"Hopper{command}{value}"
            script += f"    SetData(f, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"


    script += f"    \n"
    script += f"    // Reset Hopper Command values\n\n"
    for hmi_part, plc_part in hopper_qty_commands.items():
        script += f"    // {hmi_part}\n"
        
        for value in values:
            hmi_tag = f"{hmi_part}Play{value}"
            script += f"    SetData(f, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"

        for hmi_part2, plc_part2 in float_values.items():
            hmi_tag = f"{hmi_part}{hmi_part2}"
            script += f"    SetData(zero, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
        script += f"    \n"
    print(script)
    script = ''
    script += "end macro_command\n"
    print(script)

# Generate UpdateHopperOnPer Script
def generate_update_hopper_values():
    print(header)
    script = "// Updates the values for the hopper screen\n"
    script += "macro_command main()\n"
    script += "    // Declare variables for PLC values\n"
    script += "    bool plcVal\n"
    script += "    bool f = false\n"
    script += "    bool t = true\n"
    script += "    short e1, e2, e3\n"
    script += "    float plcFloat\n"
    script += "    float total, maxReq\n"
    script += "    bool hopperSelected\n\n"
    
    for hopper in hoppers:
        script += f"    // {hopper} Hopper\n"
        script += f"    GetData(hopperSelected, \"{HMI_NAME}\", \"{hopper}\", 1)\n"
        script += f"    if hopperSelected then\n"
        
        script += f"        // Update commands\n"
        # Update commands (Lock, Pause, Stop, Zero)
        for command in hopper_commands:
            for value in read_values:
                plc_tag = f"{hopper}.{command}.{value}"
                hmi_tag = f"Hopper{strip_dot(command)}{value}"
                script += f"        GetData(plcVal, \"{PLC_NAME}\", \"{plc_tag}\", 1)\n"
                script += f"        SetData(plcVal, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"

        # Update Qty values
        i = 0
        script += f"        \n"
        script += f"        // Update Qty Values\n"
        script += f"        GetData(total, \"{PLC_NAME}\", \"{hopper}.Kg\", 1)\n"
        script += f"        GetData(maxReq, \"{PLC_NAME}\", \"{hopper}.HLimit\", 1)\n"
        script += f"        maxReq = maxReq - total\n"
        script += f"        SetData(maxReq, \"{HMI_NAME}\", \"TankReqMax\", 1)\n"
        for hmi_part, plc_part in hopper_qty_commands.items():
            if i > hopper_feed_counts[hopper]:
                break
            
            i += 1
            for value in read_values:
                plc_tag = f"{hopper}.{plc_part}.Play.{value}"
                hmi_tag = f"{hmi_part}Play{value}"
                script += f"        GetData(plcVal, \"{PLC_NAME}\", \"{plc_tag}\", 1)\n"
                script += f"        SetData(plcVal, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"

            for hmi_part2, plc_part2 in float_values.items():
                if hmi_part2 not in read_float_values:
                    continue
                plc_tag = f"{hopper}.{plc_part}.{plc_part2}"
                hmi_tag = f"{hmi_part}{hmi_part2}"
                script += f"        GetData(plcFloat, \"{PLC_NAME}\", \"{plc_tag}\", 1)\n"
                script += f"        SetData(plcFloat, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
            print(script)
            script = ''
            
        
        script += f"        \n"
        script += f"        // Update Field visibility\n"
        for i, ii in enumerate(range(3, 6)):
            hmi_tag = f"Hopper{ii}Present"
            if ii - 1 > (hopper_feed_counts[hopper]):
                script += f"        SetDataEx(f, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
                script += f'        GetError(e{i+1})\n'
            else:
                script += f"        SetDataEx(t, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
                script += f'        GetError(e{i+1})\n'
        script += f"        \n"
        script += f"        // Reset loading flag\n"
        script += f'        if e1 == 0 and e2 == 0 and e3 == 0 then\n'
        script += f'            ASYNC_TRIG_MACRO("ResetLoadingFlag2S")\n'
        script += f'        end if\n'
        script += f'        return\n'
        script += "    end if\n\n"
        print(script)
        script = ''
    script += "end macro_command\n"
    print(script)

# Generate WriteHopperReq Script
def generate_write_hopper_values():
    print(header)
    script = "// Writes the modified values for the hopper screen\n"
    script += "macro_command main()\n"
    script += "    // Declare variable\n"
    script += "    bool hmiVal\n"
    script += "    bool f = false\n"
    script += "    bool t = true\n"
    script += "    float hmiFloat\n"
    script += "    bool hopperSelected\n\n"
    
    
    for hopper in hoppers:
        script += f"    // {hopper} Hopper\n"
        script += f"    GetData(hopperSelected, \"{HMI_NAME}\", \"{hopper}\", 1)\n"
        script += f"    if hopperSelected then\n"
        
        # Write commands (Lock, Pause, Stop, Zero)
        for command in hopper_commands:
            for value in write_values:
                plc_tag = f"{hopper}.{command}.{value}"
                hmi_tag = f"Hopper{strip_dot(command)}{value}"
                script += f"        GetData(hmiVal, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
                script += f"        if hmiVal then\n"
                script += f"            SetData(t, \"{PLC_NAME}\", \"{plc_tag}\", 1)\n"
                script += f"            SetData(f, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
                script += f"            return\n"
                script += f"        end if\n\n"
                
        # Write Qty values
        i = 0
        for hmi_part, plc_part in hopper_qty_commands.items():
            if i > hopper_feed_counts[hopper]:
                break
            i += 1
            for value in write_values:
                plc_tag = f"{hopper}.{plc_part}.Play.{value}"
                hmi_tag = f"{hmi_part}Play{value}"
                script += f"        GetData(hmiVal, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
                script += f"        if hmiVal then\n"
                script += f"            SetData(t, \"{PLC_NAME}\", \"{plc_tag}\", 1)\n"
                script += f"            SetData(f, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
                script += f"            return\n"
                script += f"        end if\n\n"
                
            for hmi_part2, plc_part2 in float_values.items():
                if hmi_part2 not in write_float_values:
                    continue
                plc_tag = f"{hopper}.{plc_part}.{plc_part2}"
                hmi_tag = f"{hmi_part}{hmi_part2}"
                script += f"        GetData(hmiFloat, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
                script += f"        SetData(hmiFloat, \"{PLC_NAME}\", \"{plc_tag}\", 1)\n"
        script += "    end if\n\n"
        print(script)
        script = ''
    script += "end macro_command\n"
    print(script)

valves = [
    'V80100',
    'V80121',
    'V80122',
    'V80123',
    'V80124',
    'V80125',
    'V80126',
    'V80112',
    'V80111',
    'V80131',
    'V80132',
    'V80133',
    'V80134',
    'V80135',
    'V80401',
    'V80150',
    
    'V80141',
    'V40141',
    'V40241',
    'V43041',
    
    'V80142',
    'V41042',
    'V41242',
    'V41342',
    'V42142',

    'V80143',
    'V40443',
    'V41143',
    
    'V80144',
    'V40344',
    
    'MP80101',
    'MP80102',
]

valve_read_values = {
    'ValveLock' : 'HMI.18',
    'ValveAuto' : 'HMI.16',
    'ValveOpen' : 'HMI.19',
    'ValveClose' : 'HMI.20',
}

valve_write_values = {
    'ValveWriteLock' : 'HMI.2',
    'ValveWriteAuto' : 'HMI.0',
    'ValveWriteOpen' : 'HMI.3',
    'ValveWriteClose' : 'HMI.4',
}

def load_valve_values():
    print(header)
    script = "// Resets all the values for the valve screen\n"
    script += "macro_command main()\n"
    script += "    // Declare variable\n"
    script += "    bool t = true\n"
    script += "    bool f = false\n"
    
    script += f"    // Set loading flag\n"
    script += f'    SetData(t, "{HMI_NAME}", "{LOADING_FLAG_NAME}", 1)\n'
    
    for hmi_tag, plc_suffix in valve_read_values.items():
        script += f"    SetData(f, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
    for hmi_tag, plc_suffix in valve_write_values.items():
        script += f"    SetData(f, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
    print(script)
    script = ''
    
    script += "end macro_command\n"
    print(script)
    
def read_valve_values():
    print(header)
    script = "// Reads the values for the valve screen\n"
    script += "macro_command main()\n"
    script += f"    // Declare variable\n"
    script += f"    bool plcVal\n"
    script += f"    bool f = false\n"
    script += f"    bool t = true\n"
    script += f"    bool valveSelected\n\n"
    
    for valve in valves:
        script += f"    // {valve} Valve\n"
        script += f"    GetData(valveSelected, \"{HMI_NAME}\", \"{valve}\", 1)\n"
        script += f"    if valveSelected then\n"
        for hmi_tag, plc_suffix in valve_read_values.items():
            script += f"        GetData(plcVal, \"{PLC_NAME}\", \"{valve}.{plc_suffix}\", 1)\n"
            script += f"        SetData(plcVal, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
        script += f"        // Reset loading flag\n"
        script += f'        ASYNC_TRIG_MACRO("ResetLoadingFlag0S")\n'
        script += f"        return\n"
        script += f"    end if\n\n"
        print(script)
        script = ''
    
    script += "end macro_command\n"
    print(script)

def send_valve_values():
    print(header)
    script = "// Writes the modified values for the valve screen\n"
    script += "macro_command main()\n"
    script += "    // Declare variable\n"
    script += "    bool hmiVal\n"
    script += "    bool f = false\n"
    script += "    bool t = true\n"
    script += "    bool valveSelected\n\n"
    
    for valve in valves:
        script += f"    // {valve} Valve\n"
        script += f"    GetData(valveSelected, \"{HMI_NAME}\", \"{valve}\", 1)\n"
        script += f"    if valveSelected then\n"
        for hmi_tag, plc_suffix in valve_write_values.items():
            script += f"        GetData(hmiVal, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
            script += f"        SetData(hmiVal, \"{PLC_NAME}\", \"{valve}.{plc_suffix}\", 1)\n"
            script += f"        SetData(f, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
        script += f"        return\n"
        script += f"    end if\n\n"
        print(script)
        script = ''
    
    script += "end macro_command\n"
    print(script)

def generate_tank_lock_load():
    print(header)
    script = "// Resets all the values for the tank_lock screen\n"
    script += "macro_command main()\n"
    script += "    // Declare variable\n"
    script += "    bool t = true\n"
    script += "    bool f = false\n"
    script += "    \n"
    
    script += f"    // Set loading flag\n"
    script += f'    SetData(t, "{HMI_NAME}", "{LOADING_FLAG_NAME}", 1)\n'
    
    for hmi_tag, plc_suffix in valve_read_values.items():
        script += f"    SetData(f, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
    for hmi_tag, plc_suffix in valve_write_values.items():
        script += f"    SetData(f, \"{HMI_NAME}\", \"{hmi_tag}\", 1)\n"
    print(script)
    script = ''
    
    script += "\nend macro_command\n\n"
    print(script)
    

def generate_tank_lock_update():
    print(header)
    script = "// Resets the selection flags for the screen\n"
    script += "macro_command main()\n"
    
    script += "\nend macro_command\n\n"
    print(script)

def generate_tank_lock_write():
    print(header)
    script = "// Resets the selection flags for the screen\n"
    script += "macro_command main()\n"
    
    script += "\nend macro_command\n\n"
    print(script)

def reset_values(vars:list):
    print(header)
    script = "// Resets the selection flags for the screen\n"
    script += "macro_command main()\n"
    script += "    // Reset all selection values\n"
    script += "    bool f = false\n\n"
    for v in vars:
        script += f"    SetData(f, \"{HMI_NAME}\", \"{v}\", 1)\n"
        
    script += "\nend macro_command\n\n"
    print(script)

TANK_VALVES_MAP = {
    'C21' : 'V80121',
    'C22' : 'V80122',
    'C23' : 'V80123',
    'C24' : 'V80124',
    'C25' : 'V80125',
    'C26' : 'V80126',
    'F31' : 'V80131',
    'F32' : 'V80132',
    'F33' : 'V80133',
    'F34' : 'V80134',
    'F35' : 'V80135',
    'W11' : 'V80111',
    'W12' : 'V80112',
    'M50' : 'V80150',
}


def generate_tank_consts():
    print(header)
    script =  f''
    for i, t in enumerate(tanks):
        script += f'short G_{t} = {i}'
    print(script)

def generate_sim_tank():
    print(header)
    script =  f"// Resets all the values for the tank_lock screen\n"
    script += f"macro_command main()\n"
    script += f"    // Declare variable\n"
    script += f"    bool t = true\n"
    script += f"    bool f = false\n"
    script += f"    float level\n"
    script += f"    float dem\n"
    script += f"    short id\n"
    script += f"    \n"
    
    
    script += f'    id = GetValue()'
    
    for i, t in enumerate|(tanks):
        script += f'    if id == i'
        
def test_simple_macro():
    m = Macro("Test", "A test macro")
    
    m.prepare()
    
    tankSelected:Variable[bool] = Variable('tankSelected', 'bool')
    
    for tank in tanks:
        m.write(
            COMMENT(f'{tank} Tank'),
            GetData(tankSelected, HMI_NAME, tank),
            IF(tankSelected.as_literal())(
                COMMENT(f'{tank} selected'),
            ),
            EMPTY(),
        )
    m.end()
    
    return m

    
if __name__ == "__main__":
    # Output the scripts
    sleep(1)
    print()
    print()
    
    # TODO Add W11, W12 and M50
    # generate_load_tank_values()
    generate_update_tank_values()
    # generate_write_tank_values()
    # reset_values(tanks)

    # Output the new scripts for hoppers
    # generate_load_hopper_values()
    # generate_update_hopper_values()
    # generate_write_hopper_values()
    # reset_values(hoppers)


    # load_valve_values()
    # read_valve_values()
    # send_valve_values()
    # reset_values(valves)
    
    # test_simple_macro().display()
