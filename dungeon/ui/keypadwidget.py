import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from .uiutils import ChildFinder
import sys

@Gtk.Template(filename=sys.path[0] + "/dungeon/ui/keypadwidget.glade")   
class KeypadWidget(Gtk.Box, ChildFinder):
    __gtype_name__ = "KeypadWidget"

    def __init__(self, length=5, default=None):
        Gtk.Box.__init__(self)        
        self.value = self.find_child('value')
        if default is not None:
            self.value.set_label(default)
        else:
            self.value.set_label('')
        self.length = length
        self.show_all()

    def result(self):
        return int(self.value.get_label())

    @Gtk.Template.Callback()
    def onClick(self, caller):
        lbl = self.value.get_label()
        if lbl.startswith('0'):
            lbl = lbl[1:]
        if len(lbl) < self.length:
            lbl += caller.get_label()
            self.value.set_label(lbl)

    @Gtk.Template.Callback()
    def onBackspace(self, caller):
        lbl = self.value.get_label()
        if lbl:
            lbl = lbl[:-1]
        self.value.set_label(lbl)

    @Gtk.Template.Callback()
    def onClear(self, caller):
        self.value.set_label("")

    @Gtk.Template.Callback()
    def onKeyPress(self, caller, event):
        if ord(event.string[0]) == 8:
            self.onBackspace(caller)
        elif ord(event.string[0]) == 27:
            self.onClear(caller)
        elif '0' <= event.string <= '9':
            lbl = self.value.get_label()
            if len(lbl) < self.length:
                lbl += event.string
                self.value.set_label(lbl)


