import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject
import sys
from .uiutils import ChildFinder, get_handler_id_for_signal
from .dialogs import DialogUser
from ..monster import Monster
import logging
import re
import random

logger = logging.getLogger()

@Gtk.Template(filename=sys.path[0] + "/dungeon/ui/monsterwidget.glade")
class MonsterWidget(Gtk.Box, ChildFinder, DialogUser):
    __gtype_name__ = "MonsterWidget"
    __gsignals__ = {
        'refresh_data': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'update_time': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (int,)),
        'refresh_monsters': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'refresh_features': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'refresh_contents': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ())
    }

    def __init__(self, dungeon, monster):
        Gtk.Box.__init__(self)
        self.monster = monster
        self.dungeon = dungeon
        
        self.monsterName = self.find_child('monsterName')
        self.monsterAlignment = self.find_child('monsterAlignment')
        self.monsterType = self.find_child('monsterType')
        self.monsterXP = self.find_child('monsterXP')
        self.monsterSource = self.find_child('monsterSource')

        a = self.monster.get_attributes()
        self.monsterName.set_label(f"<b>{a['name']} ({self.monster.id})</b>")
        self.monsterSource.set_label(f"{a['source']}/{a['page']}")
        self.monsterType.set_label(a['type'])
        self.monsterXP.set_label(str(a['xp']))
        self.monsterAlignment.set_label({
            'LG': 'Lawful Good',
            'LN': 'Lawful Neutral',
            'LE': 'Lawful Evil',
            'N': 'Neutral',
            'NE': 'Neutral Evil',
            'NG': 'Neutral Good',
            'CE': 'Chaotic Evil',
            'CN': 'Chaotic Neutral',
            'CG': 'Chaotic Good'}.get(a['alignment'], a['alignment']))


    @Gtk.Template.Callback()
    def onFled(self, caller):
        # find a place to flee (if possible)
        node = self.dungeon.map.get_node(self.monster.get_location())
        choices = []
        for ex in node.exits:
            edge = self.dungeon.map.get_edge(ex)
            if edge.is_open():
                if edge.left == self.monster.get_location():
                    choices.append([edge.id, edge.right])
                else:
                    choices.append([edge.id, edge.left])
        # if we have a choice...run to one of the open doors
        if choices:
            edge_id, new_room = random.choice(choices)
            logger.info(f"Monster {self.monster.attributes['name']} ({self.monster.id}) in {self.monster.get_location()} fleeing to room {new_room} via {edge_id}")
            self.monster.set_location(new_room)
            self.message_box(Gtk.MessageType.INFO, "Fleeing Monster", f"{self.monster.attributes['name']} ({self.monster.id}) has fled into room {new_room} via exit {edge_id}")

        self.emit('refresh_monsters')

    @Gtk.Template.Callback()
    def onKilled(self, caller):
        self.monster.kill()
        attrs = self.monster.get_attributes()
        node = self.dungeon.map.get_node(self.monster.state['location'])
        if attrs['size'][0].lower() in ['t', 's', 'm']:
            # it's small, we'll make it so the players can pick it up
            node.add_content(f"The smelly corpse of {attrs['name']} ({self.monster.id})")
        else:
            # otherwise, it becomes a feature (one does not simply pick up an ancient dragon corpse)
            node.add_feature(f"The smelly, unmovable corpse of {attrs['name']} ({self.monster.id})")

        for p in self.monster.get_property():
            node.add_content(p)

        self.emit('refresh_contents')
        self.emit('refresh_monsters')
        self.emit('refresh_features')
