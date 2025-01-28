import itertools
from time import sleep
from typing import Dict
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
    
    m.begin()

    t = Variable('t', 'bool', True)
    f = Variable('f', 'bool', True)
    zero = Variable('zero', 'float', 0.0)

    m.write(
        COMMENT('Set loading flag'),
        SetData(t, HMI_NAME, LOADING_FLAG_NAME),
        # DELAY(2000),
        EMPTY(),
        COMMENT('Reset Command values'),
    )
    
    for command in tank_commands:
        for value in values:
            if value == "Sel" and command not in has_sel:
                continue
            hmi_tag = f"Tank{strip_dot(command)}{value}"
            # m.write(SetData(f, HMI_NAME, hmi_tag))
            
    m.write(EMPTY())
    
    # Add float values for each tank
    for hmi_part, plc_suffix in float_values.items():
        hmi_tag = f"Tank{hmi_part}"
        if hmi_part in write_float_values:
            continue
        # m.write(SetData(zero, HMI_NAME, hmi_tag))
    m.write(EMPTY())

    m.end()
    m.display()
    m.clipboard()

def generate_update_tank_values():
    m = Macro('UpdateTankValues', 'Updates the values for the tank screen')
    
    m.begin()
    plcVal = vbool('plcVal')
    f = vbool('f', False)
    plcFloat = vfloat('plcFloat')
    total = vfloat('total')
    maxReq = vfloat('maxReq')
    minReq = vfloat('minReq')
    req = vfloat('req')
    tankSelected = vbool('tankSelected')
    loading = vbool('loading')
    
    for tank in tanks:
        m.write(
            COMMENT(f'{tank} Tank'),
            GetData(tankSelected, HMI_NAME, tank),
            C_IF(tankSelected),
            COMMENT('Update commands'),
        )
        
        m.write(
            EMPTY(),
            COMMENT('Update Qty Values'),
            GetData(total, PLC_NAME, f'{tank}.QtyF.ActT'),
            GetData(maxReq, PLC_NAME, f'{tank}.HLimit'),
            GetData(minReq, PLC_NAME, f'Program:{tank[0:2]}x.{tank}_F0.Over'),
            GetData(req, PLC_NAME, f'{tank}.QtyF.Dem'),
            maxReq.set(maxReq - total),
            SetData(maxReq, HMI_NAME, 'TankReqMax'),
            SetData(minReq, HMI_NAME, 'TankReqMin'),
            IF(maxReq < minReq)(maxReq.set(minReq)),
            EMPTY(),
            COMMENT('Alarm'),
            GetData(plcVal, PLC_NAME, f'{tank}.Alarms.21'),
            SetData(plcVal, HMI_NAME, f'TankAlarm'),
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
                    CONDITIONAL(command == 'QtyF.Play' and value == 'Per',
                        [plcVal.set(plcVal & (req < maxReq))]),
                    SetData(plcVal, HMI_NAME, hmi_tag),
                )
            m.write(EMPTY())


        # Read float values
        for hmi_part, plc_suffix in float_values.items():
            plc_tag = f"{tank}.QtyF.{plc_suffix}"
            hmi_tag = f"Tank{hmi_part}"
            if hmi_part in read_float_values:
                m.write(
                    GetData(plcFloat, PLC_NAME, plc_tag),
                    SetData(plcFloat, HMI_NAME, hmi_tag),
                )
            elif hmi_part in write_float_values:
                m.write(
                    COMMENT('Read req value'),
                    GetData(loading, HMI_NAME, LOADING_FLAG_NAME),
                    IF(loading)(
                        GetData(plcFloat, PLC_NAME, plc_tag),
                        SetData(plcFloat, HMI_NAME, hmi_tag),
                    ),
                )
        m.write(
            COMMENT('Reset loading flag'),
            ASYNC_TRIG_MACRO('ResetLoadingFlag1S'),
            RETURN(),
            C_END_IF(),
        )

    m.end()
    m.display()
    m.clipboard()

# Generate WriteCmd Script
def generate_write_tank_values():
    m = Macro('WriteTankValues', 'Writes the modified values for the tank screen')
    
    m.begin()
    hmiFloat = vfloat('hmiFloat')
    f = vbool('f', False)
    t = vbool('t', True)
    hmiVal = vbool('hmiVal')
    tankSelected = vbool('tankSelected')
    
    for tank in tanks:
        m.write(
            COMMENT(f'{tank} Tank'),
            GetData(tankSelected, HMI_NAME, tank),
            C_IF(tankSelected),
        )
        for command in tank_commands:
            for value in write_values:
                plc_tag = f"{tank}.{command}.{value}"
                hmi_tag = f"Tank{strip_dot(command)}{value}"
                m.write(
                    GetData(hmiVal, HMI_NAME, hmi_tag),
                    IF(hmiVal)(
                        SetData(t, PLC_NAME, plc_tag),
                        SetData(f, HMI_NAME, hmi_tag),
                        RETURN(),
                    )
                )
            
        for hmi_part, plc_part in float_values.items():
            if hmi_part not in write_float_values:
                continue
            plc_tag = f"{tank}.QtyF.{plc_part}"
            hmi_tag = f"Tank{hmi_part}"
            m.write(
                GetData(hmiFloat, HMI_NAME, hmi_tag),
                SetData(hmiFloat, PLC_NAME, plc_tag),
            )
        m.write(
            RETURN(),
            C_END_IF(),
            EMPTY(),
        )
        
    m.end()
    m.display()
    m.clipboard()

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
    m = Macro('LoadHopperValues', 'Resets all the values for the hopper screen')

    m.begin()

    f = vbool('f', False)
    t = vbool('t', True)
    zero = vfloat('zero', 0.0)


    m.write(
        COMMENT('Set loading flag'),
        SetData(t, HMI_NAME, LOADING_FLAG_NAME),
        # DELAY(2000),
        EMPTY(),
        COMMENT('Reset Command values'),
    )
    
    for command in hopper_commands:
        for value in values:
            hmi_tag = f"Hopper{command}{value}"
            # m.write(SetData(f, HMI_NAME, hmi_tag))

    m.write(
        EMPTY(),
        COMMENT('Reset Hopper Command values'),
    )
    
    for hmi_part, plc_part in hopper_qty_commands.items():
        m.write(COMMENT(hmi_part))
        
        for value in values:
            hmi_tag = f"{hmi_part}Play{value}"
            # m.write(SetData(f, HMI_NAME, hmi_tag))

        for hmi_part2, plc_part2 in float_values.items():
            if hmi_part2 in write_float_values:
                continue
            hmi_tag = f"{hmi_part}{hmi_part2}"
            # m.write(SetData(zero, HMI_NAME, hmi_tag))
        m.write(EMPTY())
        
    m.end()
    m.display()
    m.clipboard()

# Generate UpdateHopperOnPer Script
def generate_update_hopper_values():
    m = Macro('UpdateHopperValues', 'Updates the values for the hopper screen')
    
    m.begin()
    plcVal = vbool('plcVal')
    f = vbool('f', False)
    t = vbool('t', True)
    e1 = vshort('e1')
    e2 = vshort('e2')
    e3 = vshort('e3')
    plcFloat = vfloat('plcFloat')
    total = vfloat('total')
    maxReq = vfloat('maxReq')
    minReq = vfloat('minReq')
    hopperSelected = vbool('hopperSelected')
    loading = vbool('loading')
    
    for hopper in hoppers:
        m.write(
            COMMENT(f'{hopper} Hopper'),
            GetData(hopperSelected, HMI_NAME, hopper),
            C_IF(hopperSelected),
            COMMENT('Update commands'),
        )
        
        # Update commands (Lock, Pause, Stop, Zero)
        for command in hopper_commands:
            for value in read_values:
                plc_tag = f"{hopper}.{command}.{value}"
                hmi_tag = f"Hopper{strip_dot(command)}{value}"
                m.write(
                    GetData(plcVal, PLC_NAME, plc_tag),
                    SetData(plcVal, HMI_NAME, hmi_tag),
                )
            m.write(EMPTY())

        # Update Qty values
        m.write(
            EMPTY(),
            COMMENT('Update Qty Values'),
            GetData(total, PLC_NAME, f'{hopper}.Kg'),
            GetData(maxReq, PLC_NAME, f'{hopper}.HLimit'),
            maxReq.set(maxReq - total),
            IF(maxReq < 0)(maxReq.set(0)),
            SetData(maxReq, HMI_NAME, 'TankReqMax'),
            GetData(minReq, PLC_NAME, f'Program:H4x.{hopper}_F0.Over'),
            SetData(minReq, HMI_NAME, 'Hopper1ReqMin'),
            *itertools.chain(*[(
                    GetData(minReq, PLC_NAME, f'Program:H4x.{hopper}_w{ii}.Over'), 
                    SetData(minReq, HMI_NAME, f'Hopper{ii}ReqMin')
                ) for ii in range(1, hopper_feed_counts[hopper] + 1)]),
            EMPTY(),
            COMMENT('Alarms'),
            GetData(plcVal, PLC_NAME, f'{hopper}.Alarms.21'),
            SetData(plcVal, HMI_NAME, 'Hopper1Alarm'),
            *itertools.chain(*[(GetData(plcVal, PLC_NAME, f'{hopper}.Alarms.1{a}'), SetData(plcVal, HMI_NAME, f'Hopper{a+1}Alarm')) for a in range(1, hopper_feed_counts[hopper] + 1)]),
        )
        i = 0
        for hmi_part, plc_part in hopper_qty_commands.items():
            if i > hopper_feed_counts[hopper]:
                break
            
            i += 1
            for value in read_values:
                plc_tag = f"{hopper}.{plc_part}.Play.{value}"
                hmi_tag = f"{hmi_part}Play{value}"
                m.write(
                    GetData(plcVal, PLC_NAME, plc_tag),
                    SetData(plcVal, HMI_NAME, hmi_tag),
                )
            
            for hmi_part2, plc_part2 in float_values.items():
                plc_tag = f"{hopper}.{plc_part}.{plc_part2}"
                hmi_tag = f"{hmi_part}{hmi_part2}"
                if hmi_part2 in read_float_values:
                    m.write(
                        GetData(plcFloat, PLC_NAME, plc_tag),
                        SetData(plcFloat, HMI_NAME, hmi_tag),
                    )
                elif hmi_part2 in write_float_values:
                    m.write(
                        COMMENT('Read req value'),
                        GetData(loading, HMI_NAME, LOADING_FLAG_NAME),
                        IF(loading)(
                            GetData(plcFloat, PLC_NAME, plc_tag),
                            SetData(plcFloat, HMI_NAME, hmi_tag),
                        ),
                    )
            
        m.write(
            EMPTY(),
            COMMENT('Update Field visibility'),
        )
        errors = [e1, e2, e3]
        for i, ii in enumerate(range(3, 6)):
            hmi_tag = f"Hopper{ii}Present"
            if ii - 1 > (hopper_feed_counts[hopper]):
                m.write(
                    SetDataEx(f, HMI_NAME, hmi_tag),
                    GetError(errors[i])
                )
            else:
                m.write(
                    SetDataEx(t, HMI_NAME, hmi_tag),
                    GetError(errors[i])
                )
        m.write(
            EMPTY(),
            COMMENT('Reset loading flag'),
            IF(AND(e1 == 0, e2 == 0, e3 == 0))(
                ASYNC_TRIG_MACRO("ResetLoadingFlag2S")
            ),
            RETURN(),
            C_END_IF(),
            EMPTY(),
        )

    m.end()
    m.display()
    m.clipboard()

# Generate WriteHopperReq Script
def generate_write_hopper_values():
    m = Macro('SendHopperValues', 'Writes the modified values for the hopper screen')
    
    m.begin()
    
    hmiVal = vbool('hmiVal')
    f = vbool('f', False)
    t = vbool('t', True)
    hmiFloat = vfloat('hmiFloat')
    hopperSelected = vbool('hopperSelected')
    
    for hopper in hoppers:
        m.write(
            COMMENT(f'{hopper} Hopper'),
            GetData(hopperSelected, HMI_NAME, hopper),
            C_IF(hopperSelected),
        )
        
        # Write commands (Lock, Pause, Stop, Zero)
        for command in hopper_commands:
            for value in write_values:
                plc_tag = f"{hopper}.{command}.{value}"
                hmi_tag = f"Hopper{strip_dot(command)}{value}"
                m.write(
                    GetData(hmiVal, HMI_NAME, hmi_tag),
                    IF(hmiVal)(
                        SetData(t, PLC_NAME, plc_tag),
                        SetData(f, HMI_NAME, hmi_tag),
                        RETURN(),
                    ),
                    EMPTY(),
                )
                
        # Write Qty values
        i = 0
        for hmi_part, plc_part in hopper_qty_commands.items():
            if i > hopper_feed_counts[hopper]:
                break
            i += 1
            for value in write_values:
                plc_tag = f"{hopper}.{plc_part}.Play.{value}"
                hmi_tag = f"{hmi_part}Play{value}"
                m.write(
                    GetData(hmiVal, HMI_NAME, hmi_tag),
                    IF(hmiVal)(
                        SetData(t, PLC_NAME, plc_tag),
                        SetData(f, HMI_NAME, hmi_tag),
                        RETURN()
                    ),
                    EMPTY(),
                )
                
            for hmi_part2, plc_part2 in float_values.items():
                if hmi_part2 not in write_float_values:
                    continue
                plc_tag = f"{hopper}.{plc_part}.{plc_part2}"
                hmi_tag = f"{hmi_part}{hmi_part2}"
                m.write(
                    GetData(hmiFloat, HMI_NAME, hmi_tag),
                    SetData(hmiFloat, PLC_NAME, plc_tag),
                )
        m.write(
            C_END_IF(),
            EMPTY(),
        )
    m.end()
    m.display()
    m.clipboard()

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
    m = Macro('LoadValveValues', 'Resets all the values for the valve screen')
    
    m.begin()
    
    t = vbool('t', True)
    f = vbool('f', False)
    
    m.write(
        COMMENT('Set loading flag'),
        SetData(t, HMI_NAME, LOADING_FLAG_NAME),
    )
    
    # for hmi_tag, plc_suffix in valve_read_values.items():
    #     m.write(SetData(f, HMI_NAME, hmi_tag))
    # for hmi_tag, plc_suffix in valve_write_values.items():
    #     m.write(SetData(f, HMI_NAME, hmi_tag))
    
    m.end()
    m.display()
    m.clipboard()
    
def read_valve_values():
    m = Macro('UpdateValveValues', 'Reads the values for the valve screen')
    
    m.begin()
    
    plcVal = vbool('plcVal')
    f = vbool('f', False)
    t = vbool('t', True)
    valveSelected = vbool('valveSelected')
    
    for valve in valves:
        m.write(
            COMMENT(f'{valve} Valve'),
            GetData(valveSelected, HMI_NAME, valve),
            C_IF(valveSelected),
        )
        for hmi_tag, plc_suffix in valve_read_values.items():
            m.write(
                GetData(plcVal, PLC_NAME, f'{valve}.{plc_suffix}'),
                SetData(plcVal, HMI_NAME, hmi_tag),
            )
        m.write(
            COMMENT('Reset loading flag'),
            ASYNC_TRIG_MACRO('ResetLoadingFlag0S'),
            RETURN(),
            C_END_IF(),
            EMPTY(),
        )
    m.end()
    m.display()
    m.clipboard()

def send_valve_values():
    m = Macro('SendValveValues', 'Writes the modified values for the valve screen')
    
    m.begin()
    
    hmiVal = vbool('hmiVal')
    f = vbool('f', False)
    t = vbool('t', True)
    valveSelected = vbool('valveSelected')
    
    for valve in valves:
        m.write(
            COMMENT(f'{valve} Valve'),
            GetData(valveSelected, HMI_NAME, valve),
            C_IF(valveSelected),
        )
        
        for hmi_tag, plc_suffix in valve_write_values.items():
            m.write(
                GetData(hmiVal, HMI_NAME, hmi_tag),
                SetData(hmiVal, PLC_NAME, f'{valve}.{plc_suffix}'),
                SetData(f, HMI_NAME, hmi_tag),
            )
        m.write(
            RETURN(),
            C_END_IF(),
            EMPTY(),
        )
    m.end()
    m.display()
    m.clipboard()

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
    m = Macro('ResetValues', 'Resets the selection flags for the screen')
    
    m.begin()
    
    f = vbool('f', False)
    
    m.write(
        *[SetData(f, HMI_NAME, v) for v in vars],
    )
    
    m.end()
    m.display()
    m.clipboard()

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
    'M50' : 'V80150',
}


def generate_tank_consts():
    
    print(header)
    script =  f''
    for i, t in enumerate(tanks):
        script += f'short G_{t} = {i}'
    print(script)

def generate_sim_tank(part:int):
    m = Macro('SimTank', 'Simulates the behavior of a tank')
    
    m.begin()
    
    f = vbool('f', False)
    t = vbool('t', True)
    PlayOn = vbool('PlayOn')
    PlaySel = vbool('PlaySel')
    PlayPer = vbool('PlayPer')
    PlayCmd = vbool('PlayCmd')
    LockOn = vbool('LockOn')
    LockSel = vbool('LockSel')
    LockPer = vbool('LockPer')
    LockCmd = vbool('LockCmd')
    PauseOn = vbool('PauseOn')
    PauseSel = vbool('PauseSel')
    PausePer = vbool('PausePer')
    PauseCmd = vbool('PauseCmd')
    StopOn = vbool('StopOn')
    StopSel = vbool('StopSel')
    StopPer = vbool('StopPer')
    StopCmd = vbool('StopCmd')
    ZeroOn = vbool('ZeroOn')
    ZeroSel = vbool('ZeroSel')
    ZeroPer = vbool('ZeroPer')
    ZeroCmd = vbool('ZeroCmd')
    
    On = vbool('On')
    InjOn = vbool('InjOn')
    
    # QtyF Variables
    F0_On = vbool('F0_On')
    F0_End = vbool('F0_End')
    F0_Off = vbool('F0_Off')
    F0_Raz = vbool('F0_Raz')
    F0_ReqOk = vbool('F0_ReqOk')
    F0_ReqBad = vbool('F0_ReqBad')
    
    zero = vfloat('zero', 0.0)
    Actual = vfloat('Actual')
    Total = vfloat('Total')
    Dem = vfloat('Dem')
    Req = vfloat('Req')
    Rem = vfloat('Rem')
    HLimit = vfloat('HLimit', 500)
    HLAL = vfloat('HLAL', 550)
    id = vshort('id')
    Flow = vfloat('Flow')
    FlowLow = vfloat('FlowLow', 50.0)
    Alarm0 = vbool('Alarm0')
    Alarm10 = vbool('Alarm10')
    
    # Timers
    F0_Traz = TIMER('Traz')
    F0_Tcorr = TIMER('Tcorr')
    
    # F0 map
    F0_map:Dict[str, Variable] = {
        'On' : F0_On,
        'End' : F0_End,
        'Off' : F0_Off,
        'Raz' : F0_Raz,
        'ReqOk' : F0_ReqOk,
        'ReqBad' : F0_ReqBad,
    }
    
    # All commands
    all_values_map:Dict[str, Variable[bool]] = {
        'On' : On,
        'InjOn' : InjOn,
        'Alarms.0' : Alarm0,
        'Alarms.10' : Alarm10,
    }
    
    # Commands read by HMI
    read_commands_map:Dict[str, Variable[bool]] = {}
    
    # Commands written by the HMI
    write_commands_map:Dict[str, Variable[bool]] = {}
    float_map = {
        f"QtyF.{float_values['Actual']}" : Actual,
        f"QtyF.{float_values['Remaining']}" : Rem,
        f"QtyF.{float_values['Req']}" : Req,
        f"QtyF.{float_values['Total']}" : Total,
        'QtyF.Dem' : Dem,
    }
    
    mirror_map = {
        'L' : Total,
        'HLimit' : HLimit,
        'HLAL' : HLAL,
    }
    
    
    for cmd in tank_commands:
        trunc_cmd = cmd.replace('QtyF.', '')
        for a in values:
            all_values_map[f'{cmd}.{a}'] = eval(f'{trunc_cmd}{a}')
        for a in read_values:
            read_commands_map[f'{cmd}.{a}'] = eval(f'{trunc_cmd}{a}')
        for a in write_values:
            write_commands_map[f'{cmd}.{a}'] = eval(f'{trunc_cmd}{a}')
    
    m.write(
        GetData(id, HMI_NAME, 'SIM_id'),
        EMPTY(),
    )
    
    for i, tank in enumerate(tanks[:7] if part == 0 else tanks[7:]):
        m.write(
            COMMENT(tank),
            C_IF(id == i),
            COMMENT('Read values'),
        )
        
        for plc_suffix, var in all_values_map.items():
            m.write(
                GetData(var, PLC_NAME, f'{tank}.{plc_suffix}')
            )
        
        m.write(EMPTY())
        
        for plc_suffix, var in float_map.items():
            m.write(
                GetData(var, PLC_NAME, f'{tank}.{plc_suffix}'),
            )
        
        m.write(EMPTY())
        for plc_suffix, var in F0_map.items():
            m.write(
                GetData(var, PLC_NAME, f'Program:{tank[:2]}x.{tank}_F0.{plc_suffix}')
            )
            
        m.write(EMPTY())
        for index, timer in { '0':F0_Traz, '1':F0_Tcorr}.items():
            m.write(*timer.GetData(f'{tank}.T.{index}'))
        
        m.write(
            EMPTY(),
            COMMENT('Tank behavior'),
            EMPTY(),
            COMMENT('QtyF behavior'),
            F0_ReqOk.set(Dem != 0),
            F0_ReqBad.set(~F0_ReqOk & (Dem != 0)),
            PlayPer.set(F0_ReqOk & ~F0_Traz.TT & ~LockSel),
            IF(PlayPer & PlayCmd)(
                PlaySel.set(True),
                PauseSel.set(False),
                IF(~F0_On)(
                    Actual.set(0),
                    F0_On.set(True),
                    F0_End.set(False),
                    F0_Off.set(False),
                    F0_Raz.set(False),
                ),
            ),
            IF((PlaySel | F0_End) & ~F0_Off)(
                COMMENT('Flow per 100ms'),
                Actual.set(Actual + (Flow / 600)),
                Total.set(Total + Flow / 600),
                SetData(Flow, PLC_NAME, 'FT80101.PV'),
                Rem.set(Dem - Actual),
                IF(Rem <= 0)(
                    F0_End.set(True),
                    PlaySel.set(True),
                ),
            ).ELSE()( SetData(zero, PLC_NAME, 'FT80101.PV') ),
            F0_Tcorr.PRE.set(3000),
            F0_Tcorr.EN.set(F0_End & ~F0_Off),
            F0_Tcorr.TON(),
            IF(F0_End & ~F0_Off & F0_Tcorr.DN)(
                F0_Off.set(True),
            ),
            F0_Traz.EN.set(~PlaySel & ~PauseSel & ~LockSel),
            F0_Traz.PRE.set(5000),
            IF(~PlaySel & ~PauseSel & ~LockSel & F0_Traz.DN & ~F0_Raz)(
                Actual.set(0.0),
                Rem.set(0.0),
                F0_Raz.set(True),
                F0_On.set(False),
            ),
            IF(F0_Raz & ZeroSel)(
                Actual.set(0.0),
                Total.set(0.0),
                Rem.set(0.0),
                F0_On.set(False),
                F0_End.set(False),
                F0_Off.set(False),
                F0_Raz.set(False),
            ),
            IF(PauseSel | LockSel)( PlaySel.set(False) ),
            EMPTY(),
            COMMENT('Pause command'),
            PausePer.set(On),
            IF(On & PauseCmd) ( PauseSel.set(True) ),
            EMPTY(),
            COMMENT('Stop command'),
            StopPer.set(PauseSel | LockSel),
            IF(StopPer & StopCmd)(
                PauseSel.set(False),
                LockSel.set(False),
            ),
            EMPTY(),
            COMMENT('Zero and Lock commands'),
            StopSel.set(~On & ~PauseSel & ~LockSel),
            ZeroPer.set(StopSel),
            LockPer.set(StopSel),
            ZeroSel.set(ZeroPer & ZeroCmd),
            IF(LockPer & LockCmd) ( LockSel.set(True) ),
            EMPTY(),
            COMMENT('Reset commands'),
            *[v.set(False) for v in [PlayCmd, PauseCmd, StopCmd, ZeroCmd, LockCmd]],
            EMPTY(),
            COMMENT('Status'),
            On.set(F0_On),
            PlayOn.set(On & PlaySel),
            InjOn.set(PlayOn),
            *[k.set(v) for k, v in {PauseSel : PauseOn, StopSel : StopOn, ZeroSel : ZeroOn, LockSel : LockOn}.items()],
            EMPTY(),
            COMMENT('Alarms'),
            Alarm0.set(F0_ReqBad),
            IF(F0_ReqBad)( PauseCmd.set(True) ),
            IF(PlayOn & (Flow <= FlowLow))(
                Alarm10.set(True),
                PauseCmd.set(True),
            ).ELSE()( Alarm10.set(False) ),
        )
        
        m.write(
            EMPTY(),
            COMMENT('Write values'),
        )
        
        for plc_suffix, var in all_values_map.items():
            m.write(
                SetData(var, PLC_NAME, f'{tank}.{plc_suffix}')
            )
        
        m.write(EMPTY())
        
        for plc_suffix, var in float_map.items():
            m.write(
                SetData(var, PLC_NAME, f'{tank}.{plc_suffix}'),
            )
        
        for plc_suffix, var in mirror_map.items():
            m.write(
                SetData(var, PLC_NAME, f'{tank}.{plc_suffix}'),
            )
            
        m.write(EMPTY())
        for index, timer in { '0':F0_Traz, '1':F0_Tcorr}.items():
            m.write(*timer.SetData(f'{tank}.T.{index}'))
            
        m.write(
            C_END_IF(),
            EMPTY(),
        )
    
    m.end()
    m.display()
    m.clipboard()
        
        
def generate_sim_tank_valves():
    m = Macro('SimTankValve', 'Simulates the behavior of a tank valve')
    
    m.begin()
    
    f = vbool('f', False)
    t = vbool('t', True)
    valveSelected = vbool('valveSelected')
    
    # All commands
    all_values_map:Dict[str, Variable[bool]] = {
    }
    
    for tank, valve in TANK_VALVES_MAP.items():
        m.write(
            COMMENT(f'{valve} ({tank})'),
            GetData(valveSelected, HMI_NAME, valve),
            C_IF(valveSelected),
            COMMENT('Read values'),
        )
        
        for plc_suffix, var in all_values_map.items():
            m.write(
                GetData(var, PLC_NAME, f'{valve}.{plc_suffix}')
            )
        
        m.write(EMPTY())
    
        
def test_simple_macro():
    m = Macro("Test", "A test macro")
    
    m.begin()
    
    tankSelected:Variable[bool] = Variable('tankSelected', 'bool')
    
    for tank in tanks:
        m.write(
            COMMENT(f'{tank} Tank'),
            GetData(tankSelected, HMI_NAME, tank),
            IF(tankSelected)(
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
    # generate_update_tank_values()
    # generate_write_tank_values()
    # reset_values(tanks)

    # Output the new scripts for hoppers
    # generate_load_hopper_values()
    generate_update_hopper_values()
    # generate_write_hopper_values()
    # reset_values(hoppers)

    # load_valve_values()
    # read_valve_values()
    # send_valve_values()
    # reset_values(valves)
    
    # generate_sim_tank(0)
    # input()
    # generate_sim_tank(1)
    
    # test_simple_macro().display()
