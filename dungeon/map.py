import logging
import random
from .node import Node
from .edge import Edge
import textwrap
from .utils import gen_id, array_random
from random import randint


logger = logging.getLogger()


class Map:
    def __init__(self):
        self.start = None
        self.nodes = {}
        self.edges = {}

    @staticmethod
    def load(data):
        "restore a map from a dict"
        m = Map()
        for n in [Node.load(n) for n in data['nodes']]:
            m.nodes[n.id] = n
        for e in [Edge.load(e) for e in data['edges']]:
            m.edges[e.id] = e
        return m
        
    def save(self):
        "render the map into a dict"
        return {
            'start': self.start,
            'nodes': [n.save() for n in self.nodes.values()],
            'edges': [e.save() for e in self.edges.values()]
        }

    def generate(self, tables, node_count):
        # generate the structure
        self.gen_graph(tables, node_count)
        # classify rooms vs corridors
        self.classify_nodes(tables)
        # classify passages vs doors
        self.classify_edges(tables)


    def gen_graph(self, tables, node_count):
        """
        Generate an undirected graph which represents the dungeon map.
        The process boils down to:
            * generate a start node
            * attach <n> new nodes to start node
            * add nodes to the tree until we've got enough nodes
        """
        if node_count < 4:
            raise ValueError("Too few nodes for generation")
        
        # clear the current map.
        self.edges = {}
        self.nodes = {}
        self.start = None

        # create our  start node and children.
        start = Node(Node.START)
        self.nodes[start.id] = start
        self.start = start.id
        for i in range(tables.random('map', 'start_exits')):
            n = Node(Node.UNTYPED, depth=1, exit_goal=tables.random('map', 'node_exits'))
            self.nodes[n.id] = n
            logger.debug(f"adding {n.id} to start node {start.id}")
            self._connect_nodes(start, n)

        # keep adding new nodes at different places in the tree 
        while node_count > len(self.nodes):
            logger.debug(f"iterating through: have {len(self.nodes)}, want {node_count}")
            available = [x for x in self.nodes.values() if x.may_add_exit()]
            if not available:
                # shit, need to pick a random node with less than
                # the maximum number of exits and increase the
                # goal by one (as long as it isn't 4)
                available = [x for x in self.nodes.values() if x.exit_goal < 4]
                if not available:
                    raise ValueError("Map is full")
                n = random.choice(available)
                n.exit_goal += 1
                logger.debug(f"extending {n.id} to {n.exit_goal}")
            else:
                for a in available:
                    logger.debug(f"processing {a.id} -- have {a.exit_count()} want {a.exit_goal}")
                    for i in range(a.exit_goal - a.exit_count()):
                        logger.debug(f"adding exit, iteration {i}")
                        if tables.random('map', 'node_connect_local'):
                            # connect to an existing node (if possible)
                            # that's at the same depth or nearly so
                            distance = tables.random('map', 'node_connect_local_distance')
                            up = max(1, a.depth - distance)
                            down = a.depth + distance
                            near = [x for x in self.nodes.values() if x.exit_count() <= x.exit_goal and (up <= x.depth <= down)]
                            if near:
                                n = random.choice(near)
                                if self._connect_nodes(a, n):
                                    logger.debug(f"connecting {a.id} to near node {n.id} with edge")
                                else:
                                    logger.debug(f"failed to connect {a.id} to {n.id}")
                            else:
                                logger.debug(f"no nodes nearby to {a.id}")
                        else:
                            # create a new node that's one deeper.
                            n = Node(Node.UNTYPED, depth=a.depth + 1, exit_goal=tables.random('map', 'node_exits'))
                            self.nodes[n.id] = n
                            self._connect_nodes(a, n)
                            logger.debug(f"connecting {a.id} to new node {n.id}")
                            
        self.map = start

    def _connect_nodes(self, n1, n2):
        if n1.id == n2.id:
            logger.debug(("Cannot add exit to yourself!"))
            return False

        for e in n1.exits:
            if self.edges[e].connects(n1.id, n2.id):
               logger.debug(f"Found duplicate edge: {self.edges[e].id}")
               return False

        if not n1.can_add_exit() or not n2.can_add_exit():
            logger.debug("either this node or the other is full")
            return False

        logger.debug(f"Edge added successfully")
        edge = Edge(n1.id, n2.id)
        self.edges[edge.id] = edge
        n1.add_exit(edge.id)
        n2.add_exit(edge.id)
        return True


    def classify_nodes(self, tables):
        """
        split up nodes into corridors and rooms
        """
        t = {'room': Node.ROOM,
             'corridor': Node.CORRIDOR}
        for n in self.nodes.values():
            if n.type != Node.START:
                n.type = t[tables.random('map', 'node_type')]

    def classify_edges(self, tables):
        """
        Every edge is either an open passage or a door of some sort.
        """
        t = {'door': Edge.DOOR,
             'passage': Edge.PASSAGE}
        for e in self.edges.values():
            l = self.nodes[e.left]
            r = self.nodes[e.right]
            if l.type == r.type:
                if l.type == Node.ROOM or l.type == Node.START:
                    m = "room_to_room"
                else:
                    m = "corridor_to_corridor"
            else:
                m = "room_to_corridor"


            e.type = t[tables.random('map', m)]


    def dump_graphviz(self, known_nodes=None, current_node=None):
        dot = ["graph dungeon_map {",
               "  rankdir = LR;"]
        shapes = {
            Node.START: 'octagon',
            Node.UNTYPED: 'oval',
            Node.ROOM: 'house',
            Node.CORRIDOR: 'rectangle'
        }

        lines = {
            Edge.UNTYPED: 'dotted',
            Edge.DOOR: 'dashed',
            Edge.PASSAGE: 'solid'
        }

        if known_nodes is None:
            known_nodes = self.nodes.keys()
    
        show_nodes = [self.get_node(x) for x in known_nodes]
        seen_edges = set()
        for n in show_nodes:
            #logging.debug(f"Dump graph node for {n.id}")
            if current_node is not None and n.id == current_node:
                dot.append(f'{n.id} [label="{n.id}", style="filled", shape="{shapes[n.type]}", URL="#{n.id}"];')
            else:
                dot.append(f'{n.id} [label="{n.id}", shape="{shapes[n.type]}", URL="#{n.id}"];')

            for e in n.exits:
                if e not in seen_edges:
                    seen_edges.add(e)
                    edge = self.get_edge(e)
                    if edge.attributes['state']['visited']:
                        start = edge.left
                        end = edge.right
                    else:
                        # this means that one end isn't connected.
                        start = "x" + str(gen_id("map_unknown_node"))
                        dot.append(f'{start} [label="?", shape="circle"];')
                        end = edge.left if edge.left in show_nodes else edge.right
                    dot.append(f'{start} -- {end} [label="{edge.id}", style="{lines[edge.type]}"];')
        dot.append("}")
        return "\n".join(dot)



    

    def get_nodes(self):
        return self.nodes.values()
    
    def get_node(self, id):
        return self.nodes[id]

    def get_edges(self):
        return self.edges.values()

    def get_edge(self, id):
        return self.edges[id]


    def hide_door_keys(self):
        """ Place door keys in various rooms around the dungeon,
            making sure that the dungeon can be solved... """
        room_count = len(self.nodes)
        room_access = set([1])
        hidden_keys = set()
        keys = set()
        while len(room_access) < room_count:
            needed_keys = set()
            new_room_access = set()
            for room in room_access:
                node = self.nodes[room]
                keys = keys.union(node.get_keys())
                for e in node.exits:
                    edge = self.edges[e]
                    if not edge.has_lock() or edge.get_key()[0] in keys:
                        new_room_access.add(edge.left)
                        new_room_access.add(edge.right)
                    else:
                        k = edge.get_key()
                        if k not in hidden_keys:
                            needed_keys.add(edge.get_key())

            if needed_keys:
                for k in needed_keys:
                    r = random.choice(list(new_room_access))
                    self.get_node(r).hide_key(k)
                    hidden_keys.add(k)

            room_access = new_room_access

