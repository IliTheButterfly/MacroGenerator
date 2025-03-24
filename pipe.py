from __future__ import annotations
from abc import abstractmethod
from enum import Enum, Flag
import enum
from functools import cache, cached_property
import itertools
from typing import Callable, Dict, Iterable, Literal, Optional, Set, Tuple, TypeVar, Union, List
import pyperclip
from pyvis.network import Network
from api import AND, LITERAL, NOT, OR, EXPRESSION

P = None

class Node:
    ID = 0
    def __init__(self, name:str, nodeType:NodeType):
        self.neighbors: Set[Node] = set()
        self._name = name
        self.nodeType = nodeType
        self.id = Node.ID
        Node.ID += 1
        
    def attach(self, node:Node):
        if node is P:
            node = Point()
        if self == node:
            return
        self.neighbors.add(node)
        node.neighbors.add(self)
        
    def detach(self, node:Node):
        if node not in self.neighbors:
            return
        self.neighbors.remove(node)
        node.neighbors.remove(self)
        
    def __gt__(self, node:Node) -> Node:
        if node is P:
            node = Point()
        self.attach(node)
        return node
    
    def __ge__(self, node:Node) -> Node:
        if node is P:
            node = Point()
        self.attach(node)
        return self
    
    def __hash__(self):
        return hash(self.id)
    
    def __add__(self, node:Node) -> Node:
        res = Point()
        res.attach(self)
        res.attach(node)
        return res
    
    def __getitem__(self, branches:Iterable[Tuple[Node, Callable[[Node], Node]]]) -> Node:
        for b in branches:
            if b[0] is None:
                b[0] = Point()
            self.attach(b[0])
            b[1](b[0])
        return self
            
    def __setitem__(self, branches:Iterable[Tuple[Node, Callable[[Node], Node]]], tail:Node) -> Node:
        if tail is None:
            tail = Point()
        for b in branches:
            if b[0] is None:
                b[0] = Point()
            self.attach(b[0])
            b[1](b[0]).attach(tail)
        return tail
    
    def __eq__(self, node:Node):
        if node is None:
            return False
        return self.id == node.id
    
    def __ne__(self, node:Node):
        if node is None:
            return False
        return self.id != node.id
    
    @property
    def name(self) -> str:
        return self._name
    
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return f'{self.name}->[{", ".join([repr(x) for x in self.neighbors])}]'
    
    
class NodeType(Enum):
    POINT = enum.auto()
    DEO_INPUT = enum.auto()
    DEO_TANK = enum.auto()
    PUMP = enum.auto()
    HOPPER = enum.auto()
    HOPPER_INPUT = enum.auto()
    TANK = enum.auto()
    
class BranchType(Enum):
    UNKNOWN = enum.auto()
    DEO = enum.auto()
    HOPPER = enum.auto()
    PUMP = enum.auto()
    TANK = enum.auto()
        
class Device(Node):
    def __init__(self, name:str, nodeType:NodeType):
        super().__init__(name, nodeType)
        
    def __repr__(self):
        return self.name
    
class Point(Node):
    def __init__(self):
        super().__init__(None, NodeType.POINT)
        self._name = f'P{self.id}'
        
    def __repr__(self):
        return str(self)
        
class BranchInfo:
    def __init__(self, branchType:BranchType = BranchType.UNKNOWN):
        self.branchType = branchType
        self.inputs:Set[Node] = set()
        self.outputs:Set[Node] = set()
        
    def __repr__(self):
        inputs = ", ".join([node.name for node in self.inputs])
        outputs = ", ".join([node.name for node in self.outputs])
        return f"BranchType: {self.branchType.name}, Inputs: [{inputs}], Outputs: [{outputs}]"

    
class Branch:
    def __init__(self, head: Node, tail: Node):
        self.head = head
        self.tail = tail
        
    def __eq__(self, branch:Branch):
        if branch is None:
            return False
        return ((self.head.id == branch.head.id or self.head.id == branch.tail.id) and 
                (self.tail.id == branch.head.id or self.tail.id == branch.tail.id))
        
    def __hash__(self):
        return hash(f"{min(self.head.id, self.tail.id)}->{max(self.head.id, self.tail.id)}")
        
    @property
    def name(self) -> str:
        return f'{self.head.name}_{self.tail.name}'
    
    def __str__(self):
        return f"{self.name}: from {self.head.name} to {self.tail.name}"
    
    def __repr__(self):
        return f"{self.name}: {repr(self.head)} to {repr(self.tail)}"


class Graph:
    def __init__(self, start:Node):
        self.start = start
        options = """{
        "nodes": {
            "borderWidth": null,
            "borderWidthSelected": null,
            "opacity": null,
            "size": null
        },
        "edges": {
            "color": {
            "inherit": true
            },
            "selfReferenceSize": null,
            "selfReference": {
            "angle": 0.7853981633974483
            },
            "smooth": false
        },
        "manipulation": {
            "enabled": true
        },
        "physics": {
            "enabled": false,
            "barnesHut": {
            "centralGravity": 0,
            "springConstant": 0,
            "damping": 0
            },
            "minVelocity": 0.75
        }
        }"""
        self.net = net = Network(notebook = True, cdn_resources = "remote",
                bgcolor = "#222222",
                font_color = "white",
                height = "750px",
                width = "100%",
                select_menu = True,
                filter_menu = True,
        )
        # self.net.show_buttons()
        # self.net.set_options(options)
        self.branches:Set[Branch] = self._find_branches()
    
    def node2shape(self, node:Node) -> str:
        mapping = {
            Point : 'dot',
            Device : 'elipse',
        }
        for k, v in mapping.items():
            if isinstance(node, k):
                return v
        return 'dot'
        
    def add_node(self, node:Node):
        self.net.add_node(node.id, node.name, self.node2shape(node), )
    
    def add_branch(self, branch:Branch):
        self.net.add_edge(branch.head.id, branch.tail.id, title=branch.name)
        
    def _find_branches(self) -> Set[Branch]:
        brs:Set[Branch] = set()
        explored:Set[Node] = set()
        discovered:Set[Node] = set()
        discovered.add(self.start)
        while len(discovered - explored) > 0:
            s = discovered - explored
            for n in s:
                for nn in n.neighbors:
                    n1 = n if n.id < nn.id else nn
                    n2 = n if n.id > nn.id else nn
                    brs.add(Branch(n1, n2))
                discovered.update(n.neighbors)
                explored.add(n)
                
        for n in discovered:
            self.add_node(n)

        for b in brs:
            self.add_branch(b)
        
        return brs
    
    def elements(self):
        explored:Set[Node] = set()
        discovered:Set[Node] = set()
        discovered.add(self.start)
        while len(discovered - explored) > 0:
            s = discovered - explored
            for n in s:
                yield n
                discovered.update(n.neighbors)
                explored.add(n)
        
    def print(self):
        for b in self.branches:
            print(str(b))
            
        self.net.show('graph.html')
    
    def with_id(self, id:int) -> Node:
        explored:Set[Node] = set()
        discovered:Set[Node] = set()
        discovered.add(self.start)
        while len(discovered - explored) > 0:
            s = discovered - explored
            for n in s:
                if n.id == id:
                    return n
                discovered.update(n.neighbors)
                explored.add(n)
    
    def branch_with_name(self, name:str) -> Optional[Branch]:
        for b in self.branches:
            if b.name == name:
                return b
        return None
    
    def branch_with_nodes(self, n1:Node, n2:Node) -> Optional[Branch]:
        b = Branch(n1, n2)
        for bb in self.branches:
            if b == bb:
                return bb
        return None
    
    def with_name(self, name:str) -> Node:
        explored:Set[Node] = set()
        discovered:Set[Node] = set()
        discovered.add(self.start)
        while len(discovered - explored) > 0:
            s = discovered - explored
            for n in s:
                if n.name == name:
                    return n
                discovered.update(n.neighbors)
                explored.add(n)
                
    def explore(self, start: Node, ignoreNodes:Iterable[Node], ignoreTypes:Iterable[NodeType], goalTypes:Iterable[NodeType]):
        branch_map:Dict[Node, Set[Node]] = dict()
        
        def recur_explore(b_map:Dict[Node, Set[Node]], node:Node, explored:Set[Node]):
            for n in node.neighbors.copy() - explored:
                if n.nodeType in [*ignoreTypes]:
                    continue
                if n.nodeType in [*goalTypes]:
                    if node not in b_map.keys():
                        b_map[node] = set()
                    b_map[node].add(n)
                    b_map[n] = {n}
                    continue
                explored.add(n)
                recur_explore(b_map, n, explored)
                if node not in b_map.keys():
                    b_map[node] = set()
                b_map[node].update(b_map[n])
                
        recur_explore(branch_map, start, {*ignoreNodes})
        return branch_map

Deo = Device("DEO", NodeType.DEO_INPUT)
D801 = Device("D801", NodeType.DEO_TANK)
P80101 = Device("P80101", NodeType.PUMP)
P80102 = Device("P80102", NodeType.PUMP)
PumpMerge = Point()

(Deo>D801>Point())[[
    (P80101, lambda n: n),
    (P80102, lambda n: n)
]] = PumpMerge
PrePumpSplit = D801.neighbors.intersection(P80101.neighbors).pop()
# P80101>PumpMerge
# P80102>PumpMerge

PumpSplit = PumpMerge>Point()

OL109 = Device("OL109", NodeType.HOPPER_INPUT)
OL002 = Device("OL002", NodeType.HOPPER_INPUT)
OL054 = Device("OL054", NodeType.HOPPER_INPUT)

H41Split = PumpSplit>Point()
H41 = H41Split>Device("H41", NodeType.HOPPER)
((H41+OL109)+OL002)>OL054

OL056 = Device("OL056", NodeType.HOPPER_INPUT)
OL110 = Device("OL110", NodeType.HOPPER_INPUT)
OL016 = Device("OL016", NodeType.HOPPER_INPUT)
OL020 = Device("OL020", NodeType.HOPPER_INPUT)

H42Split = H41Split>Point()
H42 = H42Split>Device("H42", NodeType.HOPPER)
(((H42+OL056)+OL110)+OL016)>OL020

OL041 = Device("OL041", NodeType.HOPPER_INPUT)
OL050 = Device("OL050", NodeType.HOPPER_INPUT)

H43Split = H42Split>Point()
H43 = H43Split>Device("H43", NodeType.HOPPER)
(H43+OL041)>OL050

OL013 = Device("OL013", NodeType.HOPPER_INPUT)

H44 = H43Split>Device("H44", NodeType.HOPPER)
H44>OL013

LowerSplit = PumpSplit>Point()
LowerLowerSplit = LowerSplit>Point()

F31Split = (LowerSplit>Point())>=Device("F31", NodeType.TANK)
F32Split = (F31Split>Point())>=Device("F32", NodeType.TANK)
F33Split = (F32Split>Point())>=Device("F33", NodeType.TANK)
F34Split = (F33Split>Point())>=Device("F34", NodeType.TANK)
F34Split>Device("F35", NodeType.TANK)

C21Split = (LowerSplit>Point())>=Device("C21", NodeType.TANK)
C22Split = (C21Split>Point())>=Device("C22", NodeType.TANK)
C23Split = (C22Split>Point())>=Device("C23", NodeType.TANK)
C24Split = (C23Split>Point())>=Device("C24", NodeType.TANK)
C25Split = (C24Split>Point())>=Device("C25", NodeType.TANK)
C25Split>Device("C26", NodeType.TANK)

(((LowerLowerSplit>=Device("W12", NodeType.TANK))>Point())>=Device("W11", NodeType.TANK))>Device("V80150", NodeType.TANK)


HOPPER_CONNECTIONS = {
    'H41' : {
        'OL109' : ('V40141', 'VP40100'),
        'OL002' : ('V40241', 'VP40200'),
        'OL054' : ('V43041', 'VP43000'),
    },
    'H42' : {
        'OL056' : ('V41042', 'VP41000'),
        'OL110' : ('V41242', 'VP41200'),
        'OL016' : ('V41342', 'VP41300'),
        'OL020' : ('V42142', 'VP42100'),
    },
    'H43' : {
        'OL041' : ('V40443', 'VP40400'),
        'OL050' : ('V41143', 'VP41100'),
    },
    'H44' : {
        'OL013' : ('V40344', 'VP40300'),
    },
}


_T = TypeVar("_T")
def group(it:Iterable[_T], length:int) -> List[List[_T]]:
    iterator = iter(it)
    res:List[List[_T]] = []
    for i in itertools.count(0):
        res.append([])
        for _ in range(length):
            try:
                res[i].append(next(iterator))
                
            except StopIteration:
                return res
    return res

def get_branch_connections(b_map:Dict[Node, Set[Node]], b:Branch):
    if b.head not in b_map.keys() and b.tail not in b_map.keys():
        return None
    if b.head not in b_map.keys():
        s = b_map[b.tail]
    elif b.tail not in b_map.keys():
        s = b_map[b.head]
    else:
        s = b_map[b.head].intersection(b_map[b.tail])
        if len(s) == 0:
            s = b_map[b.head].union(b_map[b.tail])
    if len(s) == 0:
        return None
    return s

def generate_code(g:Graph):
    from generate import header, HMI_NAME, PLC_NAME, hoppers, valves
    # Print header and declare variables
    print(header)
    script =   "macro_command main()\n"
    script +=  "    // Declare constants\n"
    script +=  "    bool f = false\n"
    script +=  "    bool t = true\n"
    script +=  "    unsigned short speed = 5\n"
    script +=  "    \n"
    script +=  "    // Declare macro variables\n"
    script +=  "    bool v\n"
    script +=  "    unsigned short speedBCD\n"
    script +=  "    BIN2BCD(speed, speedBCD)\n"
    script +=  "    unsigned short setSpeedBCD\n"
    script +=  "    float floatValue\n"
    script +=  "    \n"
    
    
    
    
    script += f"    // Declare Valve variables\n"
    
    def nodes2valves(nodes:Iterable[Node]) -> Iterable[str]:
        tanks = filter(lambda n: n.nodeType in [NodeType.TANK, NodeType.HOPPER], nodes)
        for t in tanks:
            yield f"V801{t.name[-2:]}"
            
    def nodes2valves_hoppers(nodes:Iterable[Node], hopper:Literal['H41' , 'H42', 'H43', 'H44']) -> Iterable[Tuple[str, str]]:
        inputs = filter(lambda n: n.nodeType in [NodeType.HOPPER_INPUT], nodes)
        for i in inputs:
            yield HOPPER_CONNECTIONS[hopper][i.name]
        
    # valve_names = list(nodes2valves(g.elements()))
    valve_names = valves
    
    for v in group(valve_names, 5):
        if len(v) == 0:
            continue
        script += f"    bool {', '.join(v)}\n"
    
    script += f"    \n"
    script += f"    \n"
    
    script += f"    \n"
    script += f"    \n"
    
    hopper_valve_names = {}
    hopper_pump_names = {}
    for h, inp in HOPPER_CONNECTIONS.items():
        hopper_valve_names[h] = list([x[0] for x in inp.values()])
        hopper_pump_names[h] = list([x[1] for x in inp.values()])
        
    for h in hoppers:
        # script += f"    // Declare {h} Valves\n"
        # script += f"    bool {', '.join(hopper_valve_names[h])}\n"
        script += f"    // Declare {h} Pumps\n"
        script += f"    bool {', '.join(hopper_pump_names[h])}\n"
        script += f"    \n"
        
    script += f"    \n"
    script += f"    \n"
        
    script += f"    // Read Valves\n"
    for v in itertools.chain(valve_names, *hopper_valve_names.values()):
        script += f'    GetData({v}, "{PLC_NAME}", "{v}.HMI.14", 1)\n'
    script += f"    \n"
    script += f"    \n"
    
    script += f"    // Read Main Pumps\n"
    for p in ['MP80101', 'MP80102']:
        script += f'    GetData({p}, "{PLC_NAME}", "{p}.HMI.14", 1)\n'
    script += f"    \n"
    script += f"    \n"
    
    script += f"    // Read Hopper Pumps\n"
    for p in itertools.chain(*hopper_pump_names.values()):
        script += f'    GetData({p}, "{PLC_NAME}", "{p}.HMI.14", 1)\n'
    print(script)
    script = ""
    
    script += f"    \n"
    script += f"    \n"
    script += f"    // Read D801\n"
    script += f'    GetData(floatValue, "{PLC_NAME}", "D801.HLimit", 1)\n'
    script += f'    SetData(floatValue, "{HMI_NAME}", "D801_H", 1)\n'
    script += f'    GetData(floatValue, "{PLC_NAME}", "D801.LLimit", 1)\n'
    script += f'    SetData(floatValue, "{HMI_NAME}", "D801_L", 1)\n'
    script += f'    floatValue = 10\n'
    script += f'    SetData(floatValue, "{HMI_NAME}", "D801_AL", 1)\n'
    print(script)
    script = ""
    
    
    script += f"    \n"
    script += f"    \n"
    script += f"    // Write HMI Pipe values\n"
    
    main_b_map = g.explore(g.start, [g.start], [NodeType.PUMP], [NodeType.HOPPER, NodeType.TANK])
    
    hopper_maps = {
        H41: [H41, H41Split],
        H42: [H42, H42Split],
        H43: [H43, H43Split],
        H44: [H44, H43Split],
    }
    
        
    for p in g.branches:
        if p.head not in main_b_map.keys() or p.tail not in main_b_map.keys():
            continue
        s = get_branch_connections(main_b_map, p)
        if s is None:
            continue
        
        pump = OR(LITERAL("MP80101"), LITERAL("MP80102"))
            
        script += f"    v = {AND((pump), OR(*[LITERAL(valve) for valve in nodes2valves(s)]))}\n"
        script += f'    setSpeedBCD = speedBCD * v\n'
        script += f'    SetData(v, "{HMI_NAME}", "{p.name}", 1)\n'
        script += f'    SetData(setSpeedBCD, "{HMI_NAME}", "{p.name}Speed", 1)\n'
    print(script)
    script = ""
    
    for hopper, ignore in hopper_maps.items():
        script += f"    // Hopper {hopper.name}\n"
        b_map = g.explore(hopper, ignore, [], [NodeType.HOPPER_INPUT])
        for p in g.branches:
            if p.head not in b_map.keys() or p.tail not in b_map.keys():
                continue
            s = get_branch_connections(b_map, p)
            if s is None:
                continue
            script += f"    v = {OR(*[AND(LITERAL(valve[0]), LITERAL(valve[1])) for valve in nodes2valves_hoppers(s, hopper.name)])}\n"
            script += f'    setSpeedBCD = speedBCD * v\n'
            script += f'    SetData(v, "{HMI_NAME}", "{p.name}", 1)\n'
            script += f'    SetData(setSpeedBCD, "{HMI_NAME}", "{p.name}Speed", 1)\n'
        script += f'    \n'
        print(script)
        script = ""
        
    script += f'    // Other pipes\n'
    other_pipes = {
        g.branch_with_nodes(Deo, D801) : LITERAL('V80100'),
        g.branch_with_nodes(D801, PrePumpSplit) : OR(LITERAL('MP80101'), LITERAL('MP80102')),
        g.branch_with_nodes(PrePumpSplit, P80101) : LITERAL('MP80101'),
        g.branch_with_nodes(PrePumpSplit, P80102) : LITERAL('MP80102'),
        g.branch_with_nodes(PumpMerge, P80101) : AND(LITERAL('MP80101'), OR(*[LITERAL(f'V801{str(i).zfill(2)}') for i in [11,12,22,23,24,25,26,31,32,33,34,35,50]])),
        g.branch_with_nodes(PumpMerge, P80102) : AND(LITERAL('MP80102'), OR(*[LITERAL(f'V801{str(i).zfill(2)}') for i in [41,42,43,44]])),
    }
    for pipe, expression in other_pipes.items():
        script += f"    v = {expression}\n"
        script += f'    setSpeedBCD = speedBCD * v\n'
        script += f'    SetData(v, "{HMI_NAME}", "{pipe.name}", 1)\n'
        script += f'    SetData(setSpeedBCD, "{HMI_NAME}", "{pipe.name}Speed", 1)\n'
    
    script += "\nend macro_command\n\n"
    print(script)

def gen_bit_address(start:int):
    for major in itertools.count(start):
        for minor in range(16):
            yield f"{major}{str(minor).zfill(2)}"
def generate_vars(g:Graph):
    import pyperclip
    s = ""
    
    
    pipes = g.branches
    
    hopper_maps = {
        H41: [H41, H41Split],
        H42: [H42, H42Split],
        H43: [H43, H43Split],
        H44: [H44, H43Split],
    }
    
    main_b_map = g.explore(g.start, [g.start], [NodeType.PUMP], [NodeType.HOPPER, NodeType.TANK])
    for hopper, ignore in hopper_maps.items():
        b_map = g.explore(hopper, ignore, [], [NodeType.HOPPER_INPUT])
        main_b_map.update(b_map)
    
    bit_it = iter(gen_bit_address(300))
    word_it = iter(itertools.count(400))
    for p in pipes:
        conns = get_branch_connections(main_b_map, p)
        connections = (', '.join([n.name for n in conns]) 
            if conns is not None and len(conns) != 0
            else 'Other')
        s += f"{p.name}\tLocal HMI\tLW_Bit\t{next(bit_it)}\tConnects to '{connections}'\tUndesignated\t\t\t\t\t\n"
        s += f"{p.name}Col\tLocal HMI\tLW_Bit\t{next(bit_it)}\tColor for {p.name}\tUndesignated\tConversionTag\t16-bit Signed\tFluidColor\t\t0\n"
        s += f"{p.name}Speed\tLocal HMI\tLW\t{next(word_it)}\tSpeed for {p.name}\t16-bit BCD\t\t\t\t\t\n"
    pyperclip.copy(s)

def generate_bit_addresses(start:int, count:int):
    import pyperclip
    it = iter(gen_bit_address(start))
    addresses = list([next(it) for _ in range(count)])
    s = '\n'.join(addresses)
    pyperclip.copy(s)
    


if __name__ == "__main__":
    # g = Graph(PumpMerge)
    print()
    print()
    print()
    
    # g.print()

    # x = g.explore()
    # print(x)

    # generate_code(g)
    # generate_vars(g)
    generate_bit_addresses(173, 12)