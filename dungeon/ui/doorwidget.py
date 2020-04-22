import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject
import sys
from .uiutils import ChildFinder, get_handler_id_for_signal
from .dialogs import DialogUser
from ..edge import Edge
import logging
import re

logger = logging.getLogger()

@Gtk.Template(filename=sys.path[0] + "/dungeon/ui/doorwidget.glade")
class DoorWidget(Gtk.Box, ChildFinder, DialogUser):
    __gtype_name__ = "DoorWidget"
    __gsignals__ = {
        'refresh_data': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'update_time': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (int,))
    }

    def __init__(self, dungeon, edge):
        Gtk.Box.__init__(self)
        self.dungeon = dungeon
        self.edge = edge
        
        title = self.find_child('doorTitle')
        check = "\u2714" if self.edge.attributes['state']['visited'] else ""
        # set the initial states for the widgets
        self.buttons = {x: self.find_child(x) for x in ['trapButton', 'openButton', 'lockedButton', 'stuckButton']}
        if edge.type == Edge.PASSAGE:
            title.set_label(f"Passage {self.edge.id} {check}")
        elif edge.type == Edge.DOOR:
            title.set_label(f"Door {self.edge.id} {check}")
        self.refresh_buttons()
        description = self.find_child('doorDescription')
        description.set_label("\u2022 " + "\n\u2022 ".join(self.edge.attributes['description']))


    def set_button_state(self, button, state):
        button = self.buttons[button]
        button.set_inconsistent(state is None)
        if state is not None:
            with button.handler_block(get_handler_id_for_signal(button, 'clicked')):
                button.set_active(state)

    def refresh_buttons(self):
        if self.edge.type == Edge.PASSAGE:
            for b in self.buttons.values():
                b.set_sensitive(False)
        elif self.edge.type == Edge.DOOR:
            self.set_button_state('trapButton', None if not self.edge.trap_found() else self.edge.has_trap())
            if self.edge.has_lock():
                self.set_button_state('lockedButton', self.edge.is_locked())
            else:
                self.buttons['lockedButton'].set_sensitive(False)
            self.set_button_state('openButton', self.edge.is_open())
            self.set_button_state('stuckButton', None if not self.edge.stuck_found() else self.edge.is_stuck())



    @Gtk.Template.Callback()
    def onTrap(self, caller):
        print("on trap")
        if not self.edge.trap_found():
            perception = self.input_dialog('Check Trap', "Enter the checking character's Wisdom (perception)", 0, re.compile(r"\d+"))
            if perception is None:
                return
            perception = int(perception)
            success, why = self.edge.detect_trap(perception)
            logger.debug(f"Checking for trap on door {self.edge.id}: {success} : {why}")
        elif self.edge.has_trap():
            dexterity = self.input_dialog('Disarm Trap', "Enter the disarming character's Dexterity (using thief's tools)", 0, re.compile(r"\d+"))
            if dexterity is None:
                return
            dexterity = int(dexterity)
            success, why = self.edge.disarm_trap(dexterity)
            logger.debug(f"Trying to disarm trap on {self.edge.id}: {success} : {why}")
            # TODO: HAndle the trap!
        else:
            # the trap is already disarmed or doesn't exist..
            pass
        self.refresh_buttons()

    @Gtk.Template.Callback()
    def onLocked(self, caller):
        key = self.input_dialog("Use key to (un)lock the door",
                                "Enter the ID of the key to (un)lock the door")
        self.emit('update_time', 1)
        if key is not None and key != '':
            if self.edge.is_locked():
                # unlocking
                success, why = self.edge.unlock(key)
                logger.debug(f"Trying to unlock lock on {self.edge.id}: {success} : {why}")
                if not success:
                    self.message_box(Gtk.MessageType.INFO, "Lock cannot be unlocked", why)
            else:
                # locking
                success, why = self.edge.lock(key)
                logger.debug(f"Trying to unlock lock on {self.edge.id}: {success} : {why}")
                if not success:
                    self.message_box(Gtk.MessageType.INFO, "Lock cannot be locked", why)
        self.refresh_buttons()

    @Gtk.Template.Callback()
    def onOpen(self, caller):
        if self.edge.is_open():
            # door is open...close it.
            success, why = self.edge.close()
            logger.debug(f"Trying to close on {self.edge.id}: {success} : {why}")
            if not success:
                self.message_box(Gtk.MessageType.INFO, "Cannot close door", why)
        else:
            # door is closed, open it
            success, why = self.edge.open()
            logger.debug(f"Trying to open on {self.edge.id}: {success} : {why}")
            if not success:
                self.message_box(Gtk.MessageType.INFO, "Cannot open door", why)
        self.refresh_buttons()

    @Gtk.Template.Callback()
    def onStuck(self, caller):
        if not self.edge.stuck_found():
            # we dont' know anything about it, so we will do nothing.
            return
        if self.edge.is_stuck():
            # door is stuck...that must mean the user is trying to force it open
            strength = self.input_dialog("(Un)stick a door via a bodyslam",
                                         "Use the character's strength roll to bodyslam the door to open or close it",
                                         '0', re.compile(r'\d+'))
            if strength is None:
                return
            strength = int(strength)
            self.emit('update_time', 1)
            if not self.edge.is_open():
                success, why, new_room = self.edge.force_open(strength, self.dungeon.state['current_room'])
                logger.debug(f"Trying to force open on {self.edge.id}: {success} : {why}")
                if success:
                    self.dungeon.map.get_node(new_room).visit()
                    self.dungeon.state['current_room'] = new_room
                    self.emit('refresh_data')
                    return    
                else:
                    self.message_box(Gtk.MessageType.INFO, "Cannot force door open", why)

            else:
                success, why = self.edge.force_close(strength)
                logger.debug(f"Trying to force close on {self.edge.id}: {success} : {why}")
                if not success:
                    self.message_box(Gtk.MessageType.INFO, "Cannot force door closed", why)
        else:
            # door is unstuck...try to stick it into position
            success, why = self.edge.make_stuck()
            logger.debug(f"Trying to make stuck on {self.edge.id}: {success} : {why}")
        self.refresh_buttons()        

    @Gtk.Template.Callback()
    def onUse(self, caller):
        success, why, new_room = self.edge.use(self.dungeon.state['current_room'])
        logger.debug(f"Trying to use on {self.edge.id}: {success} : {why}")
        if not success:
            self.message_box(Gtk.MessageType.INFO, "Cannot use door", why)
            self.refresh_buttons()
        else:
            self.dungeon.map.get_node(new_room).visit()
            self.dungeon.state['current_room'] = new_room
            self.emit('refresh_data')
