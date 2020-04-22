from .map import Map
from .node import Node
from .edge import Edge
from .monster import Encounter, Monster
from pathlib import Path
import subprocess
import math
from .utils import generate_avg_list
import random

# THE DUNGEON!



class Dungeon:
    def __init__(self):
        self.map = Map()
        self.state = {
            'current_room': 1,
            'current_time': 0
        }
        self.monsters = {}
        self.parameters = {
            'characters': [
                # information about the playing characters, especially passive perception
            ],
            'wandering_monster_percent_per_hour': 3
        }

    @staticmethod
    def load(data):
        d = Dungeon()
        d.map = Map.load(data['map'])
        d.state = data['state']
        m = {}
        for k,v in data['monsters'].items():
            m[k] = Monster.load(v)
        d.monsters = m
        d.parameters = data['parameters']
        return d

    def save(self):
        m = {}
        for k, v in self.monsters.items():
            m[k] = v.save()
        return {
            'map': self.map.save(),
            'state': self.state,
            'monsters': m,
            'parameters': self.parameters,
        }

    def generate(self, tables, room_count=10, character_levels=[1, 1, 1, 1],
                 monster_sources=['mm'], monster_types=[], monster_alignments=[],
                 encounter_average_difficulty=Encounter.MEDIUM,
                 encounter_room_percent=25, wandering_monsters=6): 

        # set the wandering monster per hour percent
        self.parameters['wandering_monster_percent_per_hour'] = int(tables.lookup('settings', 'monsters', 'wandering_percent_per_hour'))


        # get the overall dungeon settings
        environments = tables.lookup("settings", "monsters", "environments")

        # generate the map and decorate the rooms
        self.map.generate(tables, room_count)
        for e in self.map.get_edges():
            e.decorate(tables)
        for n in self.map.get_nodes():
            n.decorate(tables)

        # distribute the keys in locations where they can be found.
        self.map.hide_door_keys()


        encounter = Encounter(tables, character_levels, source_filter=monster_sources, 
                              type_filter=monster_types, alignment_filter=monster_alignments,
                              environment_filter=environments)
        encounter_count = math.ceil(room_count * (encounter_room_percent / 100))
        difficulties = generate_avg_list(encounter_average_difficulty, encounter_count, Encounter.EASY, Encounter.DEADLY)
        # get all of the rooms (but not corridors or the start room)
        non_monster_rooms = set([x for x in self.map.get_nodes() if x.type == Node.ROOM])
        for d in difficulties:
            e = encounter.create_encounter(d)
            r = random.choice(list(non_monster_rooms))
            for m in e:
                m.set_location(r.id)
                m.decorate(tables)
                self.monsters[m.id] = m
            non_monster_rooms.remove(r)
            print(f"Wanted difficulty {d}, got encounter {e}, placed in room {r.id}")
            
        # generate the wandering mosnters
        difficulties = generate_avg_list(encounter_average_difficulty, wandering_monsters, Encounter.EASY, Encounter.DEADLY)
        for difficulty in difficulties:
            wm = encounter.create_wandering_monster(difficulty)
            wm.set_location(None)
            wm.decorate(tables)
            self.monsters[wm.id] = wm


    def get_monsters_for_room(self, room_id):
        r = []
        for mon in self.monsters.values():
            if mon.is_alive() and mon.get_location() == room_id:
                r.append(mon)
        return r

    def get_wandering_monster(self):
        wms = [m for m in self.monsters.values() if m.is_alive() and m.get_location() is None]
        if wms:
            return random.choice(wms)
        else:
            return None        






    def render_html(self, directory, dot_cmd):
        directory = Path(directory)
        # first, render the map
        map_file = directory.joinpath("map.png")
        dot = self.map.dump_graphviz().encode('utf-8')
        subprocess.run([dot_cmd, '-Tpng', '-o', map_file], input=dot, check=True)
        imap_file = directory.joinpath("map.imap")
        subprocess.run([dot_cmd, '-Tcmapx', '-o', imap_file], input=dot, check=True)

        html = "<html><head>"
        html += "<title>A dungeon dump</title>"
        html += "</head><body>"
        html += "<h2>A dungeon</h2>"
        html += "<img src=map.png usemap=#dungeon_map>"
        with open(imap_file) as f:
            html += f.read()



        html += "<hr>"
        for node in sorted(self.map.get_nodes(), key=lambda x: x.id):
            print(f"{node.id}: {node.attributes}")
            html += f"<a name={node.id}></a>"
            html += "<table border=1 width=100%>"
            if node.type == Node.ROOM:
                html += f"<tr><td colspan=2><b>Room {node.id}</b></td></tr>"
            elif node.type == Node.CORRIDOR:
                html += f"<tr><td colspan=2><b>Corridor {node.id}</b></td></tr>"
            else:
                html += f"<tr><td colspan=2><b>Starting Room {node.id}</b></td></tr>"

            html += "<tr><td>Description</td><td><ul>"
            for d in node.attributes['description']:
                html += f"<li>{d}</li>"
            html += "</ul></td></tr>"

            html += "<tr><td>Contents</td><td><ul>"
            for d in node.attributes['contents']:
                html += f"<li>{d}</li>"
            html += "</ul></td></tr>"

            html += "<tr><td>Flags</td><td><ul>"
            for d in node.attributes['flags']:
                html += f"<li>{d}</li>"
            html += "</ul></td></tr>"

            html += "<tr><td>Exits</td><td><ul>"
            for d in node.exits:
                edge = self.map.get_edge(d)
                if edge.left == node.id:
                    to = edge.right
                else:
                    to = edge.left
                e = f"<a href=#{to}>Leads to room/corridor {to}</a>"
                e += "<ul>"
                for i in edge.attributes['description']:
                    e += f"<li>{i}</li>"
                e += "</ul>"
                html += f"<li>{e}</li>"
            html += "</ul></td></tr>"
            html += "</table>"
        html += "</body></html>"

        with open(directory.joinpath("index.html"), "w") as f:
            f.write(html)
