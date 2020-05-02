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


    def __init__(self, dungeon, dobject):
        Gtk.Box.__init__(self)
        self.dungeon = dungeon
        self.dobject = dobject        
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

        for b in self.buttons:
            self.set_button_state(b, False)
        dobject = self.dobject
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
                self.set_button_state('btnUnstick', dobject.stuck_found, dobject.is_stuck)

        if dobject.is_a('Lockable'):
            if dobject.has_lock:
                if dobject.is_locked:
                    self.set_button_state('btnPick', True, True)
                self.set_button_state('btnLock', True, dobject.is_locked)            
 
        if dobject.is_a('Room'):
            self.set_button_state('btnRest', True, True)

        if dobject.is_a('Container'):
            if not dobject.can_contain or not dobject.contents:
                self.contents_exp.hide()
            else:
                logger.debug(f"There are {len(dobject.contents)} items in this container: {dobject.contents}")
                o = dobject.container_open or dobject.is_a('Room')
                self.contents_exp.set_expanded(o)
                # remove all existing children
                for c in self.contents_list.get_children():
                    print(f"Removing {c}")
                    self.contents_list.remove(c)
                # add the children back
                for c in dobject.contents:
                    print(f"Adding {c}")
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
                self.contents_exp.show()
        else:
            # no contents, so hide the widget
            self.contents_exp.hide()

        # set the object's description
        if dobject.description:
            d = list(dobject.description)
            desc = bullet + f"\n{bullet}".join(d)
            self.description.set_label(desc)    

    @Gtk.Template.Callback()
    def onPickUp(self, caller):
        print("On pick up")

    @Gtk.Template.Callback()
    def onInspect(self, caller):
        print("On inspect")

    @Gtk.Template.Callback()
    def onBreak(self, caller):
        print("On break")

    @Gtk.Template.Callback()
    def onDisarm(self, caller):
        print("On disarm")

    @Gtk.Template.Callback()
    def onKill(self, caller):
        print("On kill")

    @Gtk.Template.Callback()
    def onFlee(self, caller):
        print("On flee")

    @Gtk.Template.Callback()
    def onSpeak(self, caller):
        print("On speak")


    @Gtk.Template.Callback()
    def onLock(self, caller):
        print("On lock")

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
                                         "Use the character's strength roll to bodyslam the door to open or close it",
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
    def onContainerOpen(self, caller):
        print("On container open")


    def onUpdateData(self, caller):
        print(f"on update data {self}")
        self.emit('update_data')

    def onUpdateTime(self, caller, time):
        print(f"on update time {self} {time}")
        self.emit('update_time')
