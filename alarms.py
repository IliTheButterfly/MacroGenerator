import csv
from enum import StrEnum
import json
from pathlib import Path
from typing import Dict, List, Tuple, Union
from unicodedata import category

import pyperclip

HEADER = """VERSION	3	HARDWARE_VERSION	134																																																																																																																																																																														
Category	Priority	Address Type	PLC Name (Read)	Device Type (Read)	System Tag (Read)	User-defined Tag (Read)	Address (Read)	Index (Read)	Data Format (Read)	Enable Notification	Set ON (Notification)	PLC Name (Notification)	Device Type (Notification)	System Tag (Notification)	User-defined Tag (Notification)	Address (Notification)	Index (Notification)	Condition	Trigger Value	Content	Use Label Library	Label Name	Font	Color	Acknowledge Value	Enable Sound	Sound Library Name	Sound Index	No. of Multi-watch	PLC Name (WATCH1)	Device Type (WATCH1)	System Tag (WATCH1)	User-defined Tag (WATCH1)	Address (WATCH1)	Index (WATCH1)	Data Format (WATCH1)	Word No. (WATCH1)	PLC Name (WATCH2)	Device Type (WATCH2)	System Tag (WATCH2)	User-defined Tag (WATCH2)	Address (WATCH2)	Index (WATCH2)	Data Format (WATCH2)	Word No. (WATCH2)	PLC Name (WATCH3)	Device Type (WATCH3)	System Tag (WATCH3)	User-defined Tag (WATCH3)	Address (WATCH3)	Index (WATCH3)	Data Format (WATCH3)	Word No. (WATCH3)	PLC Name (WATCH4)	Device Type (WATCH4)	System Tag (WATCH4)	User-defined Tag (WATCH4)	Address (WATCH4)	Index (WATCH4)	Data Format (WATCH4)	Word No. (WATCH4)	PLC Name (WATCH5)	Device Type (WATCH5)	System Tag (WATCH5)	User-defined Tag (WATCH5)	Address (WATCH5)	Index (WATCH5)	Data Format (WATCH5)	Word No. (WATCH5)	PLC Name (WATCH6)	Device Type (WATCH6)	System Tag (WATCH6)	User-defined Tag (WATCH6)	Address (WATCH6)	Index (WATCH6)	Data Format (WATCH6)	Word No. (WATCH6)	PLC Name (WATCH7)	Device Type (WATCH7)	System Tag (WATCH7)	User-defined Tag (WATCH7)	Address (WATCH7)	Index (WATCH7)	Data Format (WATCH7)	Word No. (WATCH7)	PLC Name (WATCH8)	Device Type (WATCH8)	System Tag (WATCH8)	User-defined Tag (WATCH8)	Address (WATCH8)	Index (WATCH8)	Data Format (WATCH8)	Word No. (WATCH8)	Continuous Beep	Stop Condition of Continuous Beep 	Time Interval of Beeps	Send eMail when Event Triggered	Send eMail when Event Cleared	To Recipents (Triggered)	Cc Recipents (Triggered)	Bcc Recipents (Triggered)	Subject as Event (Triggered)	Subject (Triggered)	Use Label Library (Subject)	Label Name (Subject)	Opening (Triggered)	Use Label Librray (Opening)	Label Name (Opening)	Ending (Triggered)	Use Label Library (Ending)	Label Name (Ending)	Window Screenshot	To Recipents (Cleared)	Cc Recipents (Cleared)	Bcc Recipents (Cleared)	Subject as Event (Cleared)	Subject (Cleared)	Use Label Library (Subject)	Label Name (Subject)	Opening (Cleared)	Use Label Librray (Opening)	Label Name (Opening)	Ending (Cleared)	Use Label Library (Ending)	Label Name (Ending)	Delay Time	Dynamic Condition	PLC Name (Condition)	Device Type (Condition)	System Tag (Condition)	User-defined Tag (Condition)	Address (Condition)	Index (Condition)	Save To History	Occurrence	PLC Name (Occurrence)	Device Type (Occurrence)	System Tag (Occurrence)	User-defined Tag (Occurrence)	Address (Occurrence)	Index (Occurrence)	Data Format (Occurrence)	In Tolerance	Out Tolerance	Follow	Use String Table	Section ID	Dynamic	String ID	PLC Name (String ID)	Device Type (String ID)	System Tag (String ID)	User-defined Tag (String ID)	Address (String ID)	Index (String ID)	Data Format (String ID)	Push Notification	Elapsed Time	PLC Name (Elapsed Time)	Device Type (Elapsed Time)	System Tag (Elapsed Time)	User-defined Tag (Elapsed Time)	Address (Elapsed Time)	Index (Elapsed Time)	Data Format (Elapsed Time)	Background Color	Color (Background Color)	Subcategory 1	Subcategory 2	Control (Enable/Disable)	Set ON (Enable/Disable)	PLC Name (Enable/Disable)	Device Type (Enable/Disable)	System Tag (Enable/Disable)	User-defined Tag (Enable/Disable)	Address (Enable/Disable)	Index (Enable/Disable)"""

class Category(StrEnum):
    TANK = '0: Bassin'
    HOPPER = '1: Hopper'
    MIX = '2: Mélange'
    HARDWARE = '3: Hardware'
    
class SubCategory1(StrEnum):
    BOTTOM = '0: Premier étage'
    TOP = '1: Deuxième étage'
    DEO = '2: Deo'
    OTHER = ''
    
class SubCategory2(StrEnum):
    C21 = '0: C21'
    C22 = '1: C22'
    C23 = '2: C23'
    C24 = '3: C24'
    C25 = '4: C25'
    C26 = '5: C26'
    F31 = '6: F31'
    F32 = '7: F32'
    F33 = '8: F33'
    F34 = '9: F34'
    F35 = '10: F35'
    W11 = '11: W11'
    H41 = '13: H41'
    H42 = '14: H42'
    H43 = '15: H43'
    H44 = '16: H44'
    W12 = '18: W12'
    M50 = '12: M50'
    D801 = '17: D801'
    OTHER = ''
    
    
class Priority(StrEnum):
    LOW = 'Low'
    NORMAL = 'Normal'
    MIDDLE = 'Middle'
    HIGH = 'High'
    EMERGENCY = 'Emergency'
    
    
Valve_Alarms = {
    'HMI.25' : 'PLC Module Fault',
    'HMI.28' : 'Channel value low',
    'HMI.29' : 'Channel value high',
    'HMI.30' : 'Channel value no variation',
}

TEMPLATE = '{category}	{priority}	Bit	Rockwell EtherNet/IP (CompactLogix)	BOOL	False	False	{address}	null	 	False	False			False	False		null	bt: 1	0	{message}	False		Arial	0:0:0	11	False		0	0			False	False		null					False	False		null					False	False		null					False	False		null					False	False		null					False	False		null					False	False		null					False	False		null			False	NONE	10	False	False																												1	0	Rockwell EtherNet/IP (CompactLogix)	BOOL	False	False	{address}	null	True	False	Local HMI	LW	False	False	0	null	16-bit Unsigned			False	False					False	False		null			False	False			False	False		null		False		{sub1}	{sub2}	False	True			False	False		null'

class Alarm:
    def __init__(self, category:Category, priority:Priority, address:str, message:str, sub1:SubCategory1, sub2:SubCategory2):
        self.category = category
        self.priority = priority
        self.address = address
        self.message = message
        self.sub1 = sub1
        self.sub2 = sub2
        
    def format(self) -> str:
        return TEMPLATE.format(**self.__dict__)
    
    def __str__(self):
        return self.format()

Transmitters = {
    'WT02251' : 'C22',
    'WT04151' : 'H41',
    'WT04251' : 'H42',
    'WT04351' : 'H43',
    'WT04451' : 'H44',
    'LT80101' : 'D801',
    'LT80401' : '',
    'FT80101' : '',
    'FT80102' : '',
    'FT80103' : 'F35',
    'FT80201' : '',
    'FT80401' : '',
    'MP80101' : '',
    'MP80102' : '',
}

class Main:
    def __init__(self, inFile:str, outFile:str):
        self.inFile = Path(inFile)
        self.outFile = Path(outFile)
        self.data:Dict[str, Union[Dict, List, str, int, float, bool]] = {}
        self.alarms:List[Alarm] = []
    
    def parse(self):
        with self.inFile.open('r') as rd:
            f = rd.read()
            self.data = json.loads(f)
    
    def name2address(self, name:str) -> str:
        res = name.replace('_', '.')
        pref = res.rstrip('0123456789')
        suff = res.removeprefix(pref)
        return f'{pref}.{suff}'
    
    def grab(self):
        for tag in self.data['tags']:
            tag:Dict[str, Union[Dict, List, str, int, float, bool]]
            if 'alarms' not in tag.keys():
                continue
            alm = Alarm(Category.TANK, Priority.LOW, self.name2address(tag['name']), tag['alarms'][0]['message'])
            self.alarms.append(alm)
        
    def write(self):
        with self.outFile.open('w') as wr:
            rows = [*[l.split('\t') for l in HEADER.split('\n')],
                    *[str(ll).split('\t') for ll in self.alarms]]
            s = '\n'.join(['\t'.join(r) for r in rows])
            wr.write(s)

    def get_categories(self, tank:str, valve:str) -> Tuple[SubCategory1, SubCategory2]:
        if tank == '':
            tank = 'OTHER'
        if tank[0] in 'HFW':
            return SubCategory1.TOP, SubCategory2[tank]
        if tank[0] in 'CM':
            return SubCategory1.TOP, SubCategory2[tank]
        if tank[0] in 'D':
            return SubCategory1.DEO, SubCategory2[tank]
        
        return SubCategory1.OTHER, SubCategory2[tank]
            
    def write_valves(self):
        from generate import TANK_VALVES_MAP, valves
        from pipe import HOPPER_CONNECTIONS
        vlvs = []
        alarms:List[Alarm] = []
        for hopper, connection in HOPPER_CONNECTIONS.items():
            for _, t in connection.items():
                vlvs.append(t[0])
                vlvs.append(t[1])
                for tag, msg in Valve_Alarms.items():
                    alarms.append(Alarm(Category.HARDWARE, Priority.HIGH, f'{t[0]}.{tag}', f'{t[0]} Error: {msg}', *self.get_categories(hopper, t[0])))
                    alarms.append(Alarm(Category.HARDWARE, Priority.HIGH, f'{t[1]}.{tag}', f'{t[1]} Error: {msg}', *self.get_categories(hopper, t[1])))
            
        for tank, valve in TANK_VALVES_MAP.items():
            vlvs.append(valve)
            for tag, msg in Valve_Alarms.items():
                alarms.append(Alarm(Category.HARDWARE, Priority.HIGH, f'{valve}.{tag}', f'{valve} Error: {msg}', *self.get_categories(tank, valve)))
                
        for hardware, tank in Transmitters.items():
            vlvs.append(valve)
            for tag, msg in Valve_Alarms.items():
                alarms.append(Alarm(Category.HARDWARE, Priority.HIGH, f'{valve}.{tag}', f'{valve} Error: {msg}', *self.get_categories(tank, hardware)))
            
        with self.outFile.open('w') as wr:
            rows = [*[str(ll).split('\t') for ll in alarms]]
            s = '\n'.join(['\t'.join(r) for r in rows])
            wr.write(s)
            pyperclip.copy(s)
    
    def run(self):
        self.parse()
        self.grab()
        self.write()
        


if __name__ == "__main__":
    # main = Main('MacroGenerator\\tagl.json', 'MacroGenerator\\out.csv')
    main = Main('tagl.json', 'out2.csv')
    # main.run()
    main.write_valves()