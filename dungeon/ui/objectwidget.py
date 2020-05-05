import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject
from .dialogs import DialogUser
from .uiutils import ChildFinder, get_handler_id_for_signal
import sys
import logging

logger = logging.getLogger()

@Gtk.Template(filename=sys.path[0] + "/dungeon/ui/objectwidget.glade")  
class ObjectWidget(Gtk.Box, ChildFinder, DialogUser):
    __gtype_name__ = "ObjectWidget"
    __gsignals__ = {
        'update_data': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'update_time': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (int,))
    }


    def __init__(self, dungeon, dobject, controls=True):
        Gtk.Box.__init__(self)
        self.dungeon = dungeon
        self.dobject = dobject
        self.controls = controls        
        # find the widgets we'll need
        self.description = self.find_child('lblDescription')
        self.contents_exp = self.find_child('expContents')
        #self.contents_label = self.find_child('lblContents')
        self.contents_list = self.find_child('lstContents')
        self.buttons = {}
        for b in ('btnPickUp', 'btnInspect', 'btnBreak', 'btnDisarm',
                  'btnKill', 'btnFlee', 'btnLock', 'btnOpen', 'btnUse',
                  'btnSpeak', 'btnUnstick', 'btnRest', 'btnPick'):
            self.buttons[b] = self.find_child(b)
        self.show_all()
        self.reset_widget()

    def set_button_state(self, button, visible=True, state=None):
        button = self.buttons[button]
        button.set_visible(visible)
        button.set_sensitive(state is not None)
        if state is not None:
            if hasattr(button, "set_active"):
                handler_id = get_handler_id_for_signal(button, 'toggled')
                with button.handler_block(handler_id):
                        button.set_active(state)


    def reset_widget(self):
        bullet = "\u2022 "
        dobject = self.dobject

        for b in self.buttons:
            self.set_button_state(b, False)

        if dobject.is_a('Container'):
            # TODO:  does inspect make this thing visible for non-rooms?
            if not dobject.can_contain or not dobject.contents:
                
                self.contents_exp.hide()
            else:
                logger.debug(f"There are {len(dobject.contents)} items in this container: {dobject.contents}")
                # remove all existing children
                for c in self.contents_list.get_children():
                    self.contents_list.remove(c)
                # add the children back
                for c in dobject.contents:
                    if dobject.is_a('Room'):
                        if c.is_a('Monster') or c.is_a('Door'):
                            continue
                    frame = Gtk.Frame()
                    frame.set_label(f"{c.class_label()} {c.id}")

                    ow = ObjectWidget(self.dungeon, c)
                    ow.set_margin_start(12)
                    ow.connect('update_data', self.onUpdateData)
                    ow.connect('update_time', self.onUpdateTime)
                    ow.show()
                    frame.add(ow)
                    frame.show()
                    self.contents_list.pack_start(frame, True, True, 0)
                self.contents_list.show()
                # expand or contract the expander based on the state of the container.
                #print(f"Reset_widget: {dobject.container_open=}, {self.contents_exp.get_expanded()=}")
                handler_id = get_handler_id_for_signal(self.contents_exp, 'notify::expanded')
                with self.contents_exp.handler_block(handler_id):                              
                    self.contents_exp.set_expanded(dobject.container_open)

                self.contents_exp.show()
                    
        else:
            # no contents, so hide the widget
            self.contents_exp.hide()

        # set the object's description
        if dobject.description:
            d = list(dobject.description)
            desc = bullet + f"\n{bullet}".join(d)
            self.description.set_label(desc)    
        

        if not self.controls:
            return

        if dobject.is_a('Thing', 'Key') and dobject.is_portable:
            self.set_button_state('btnPickUp', True, True)

        if dobject.is_a('Breakable') and dobject.is_breakable:
            self.set_button_state('btnBreakable', True, None if dobject.is_broken else True)
        
        if dobject.is_a('Inspectable') and dobject.is_inspectable:
            self.set_button_state('btnInspect', True, True)

        if dobject.is_a('Trappable'):
            # btnDisarm
            # has_trap
            # trap_found
            pass

        if dobject.is_a('Monster'):
            for b in ('btnKill', 'btnFlee', 'btnSpeak'):
                self.set_button_state(b, True, True)
            self.description.set_label(dobject.description[0])

        if dobject.is_a('Door'):
            self.set_button_state('btnUse', True, True)
            if not dobject.is_passage:
                self.set_button_state('btnOpen', True, dobject.is_open)
                self.set_button_state('btnUnstick', dobject.stuck_found and dobject.stuck_dc > 0, dobject.is_stuck)

        if dobject.is_a('Lockable'):
            if dobject.has_lock:
                if dobject.is_locked:
                    self.set_button_state('btnPick', True, True)
                self.set_button_state('btnLock', True, dobject.is_locked)            
 
        if dobject.is_a('Room'):
            self.set_button_state('btnRest', True, True)


    @Gtk.Template.Callback()
    def onPickUp(self, caller):
        parent = self.dobject.location
        parent.discard(self.dobject)
        self.dungeon.inventory.store(self.dobject)
        logger.info(f"Player inventory: {self.dungeon.inventory.contents}")
        self.emit('update_data')

    @Gtk.Template.Callback()
    def onInspect(self, caller):
        print("On inspect")

    @Gtk.Template.Callback()
    def onBreak(self, caller):
        strength = self.keypad_input("Break this object",
                                        "Use the character's strength roll to\nbreak the object",
                                        length=2)
        if strength is None:
            return
        if self.dobject.break_object(strength):
            pass
        else:
            self.message_box(Gtk.MessageType.INFO, "Break object", "Object was not broken")
        

    @Gtk.Template.Callback()
    def onDisarm(self, caller):
        print("On disarm")

    @Gtk.Template.Callback()
    def onKill(self, caller):
        print("On kill")
        self.dobject.kill(self.dungeon)
        self.emit('update_data')


    @Gtk.Template.Callback()
    def onFlee(self, caller):
        print("On flee")
        door = self.dobject.flee()
        if door is None:
            self.message_box(Gtk.MessageType.INFO, "Monster Flees", "There are no open doors that the\nmonster can flee through!")
        else:
            self.message_box(Gtk.MessageType.INFO, "Monster Flees", f"The monster has fled through {door.id}")

        self.emit('update_data')

    @Gtk.Template.Callback()
    def onSpeak(self, caller):
        print("On speak")


    @Gtk.Template.Callback()
    def onLock(self, caller):
        print(f"On lock {self}")
        lock = self.dobject
        key_wanted = lock.lock_key
        can_unlock = False
        if self.dungeon.state.get('skeleton_key', False):
            can_unlock = True
        else:
            # look in the player's keys to see if it's there...
            if key_wanted in self.dungeon.inventory.contents:
                can_unlock = True
            
        if not can_unlock:
            self.message_box(Gtk.MessageType.INFO, "Lock", f"You do not have the key for this lock\n{lock.get_key_description()[0]}")
        else:
            self.emit('update_time', 1)
            lock.is_locked = not lock.is_locked
        self.reset_widget()


    @Gtk.Template.Callback()
    def onOpen(self, caller):
        door = self.dobject
        if door.is_open:
            # door is open...close it.
            success, why = door.close()
            logger.debug(f"Trying to close on {door.id}: {success} : {why}")
            if not success:
                self.message_box(Gtk.MessageType.INFO, "Cannot close door", why)
        else:
            # door is closed, open it
            success, why = door.open()
            logger.debug(f"Trying to open on {door.id}: {success} : {why}")
            if not success:
                self.message_box(Gtk.MessageType.INFO, "Cannot open door", why)
        self.reset_widget() 

    @Gtk.Template.Callback()
    def onUse(self, caller):
        door = self.dobject
        success, why, new_room = door.use(self.dungeon.state['current_room'])
        logger.debug(f"Trying to use on {door.id}: {success} : {why}")
        if not success:
            self.message_box(Gtk.MessageType.INFO, "Cannot use door", why)
            self.reset_widget()
        else:
            new_room.visited = True
            self.dungeon.state['current_room'] = new_room
            self.emit('update_data')

    @Gtk.Template.Callback()
    def onUnstick(self, caller):
        door = self.dobject
        if door.is_stuck:
            # door is stuck...that must mean the user is trying to force it open
            strength = self.keypad_input("(Un)stick a door via a bodyslam",
                                         "Use the character's strength roll to\nbodyslam the door to open or close it",
                                         length=2)
            if strength is None:
                return
            self.emit('update_time', 1)
            if not door.is_open:
                success, why, new_room = door.force_open(strength, self.dungeon.state['current_room'])
                logger.debug(f"Trying to force open on {door.id}: {success} : {why}")
                if success:
                    new_room.visited = True
                    self.dungeon.state['current_room'] = new_room
                    self.emit('update_data')
                    return    
                else:
                    self.message_box(Gtk.MessageType.INFO, "Cannot force door open", why)

            else:
                success, why = door.force_close(strength)
                logger.debug(f"Trying to force close on {door.id}: {success} : {why}")
                if not success:
                    self.message_box(Gtk.MessageType.INFO, "Cannot force door closed", why)
        else:
            # door is unstuck...try to stick it into position
            success, why = door.make_stuck()
            logger.debug(f"Trying to make stuck on {door.id}: {success} : {why}")
        self.reset_widget()  


    @Gtk.Template.Callback()
    def onRest(self, caller):
        print("On rest")

    @Gtk.Template.Callback()
    def onPick(self, caller):
        print("On pick")


    @Gtk.Template.Callback()
    def onContainerOpen(self, caller, state):
        dobject = self.dobject
        state = bool(state)
        if not dobject.container_open:
            if dobject.is_a('Lockable') and dobject.is_locked:
                handler_id = get_handler_id_for_signal(caller, 'notify::expanded')
                with caller.handler_block(handler_id):                              
                    caller.set_expanded(False)
                self.message_box(Gtk.MessageType.INFO, "Locked", "This is locked")
            else:
                dobject.container_open = not dobject.container_open
                self.reset_widget()
        else:
            # closing is just fine.
            dobject.container_open = not dobject.container_open
            self.reset_widget()


    def onUpdateData(self, caller):
        self.emit('update_data')

    def onUpdateTime(self, caller, time):
        self.emit('update_time')
