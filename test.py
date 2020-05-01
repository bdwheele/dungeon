#!/bin/env python
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
from dungeon.ui.dialogs import DialogUser

class TestWindow(Gtk.Window, DialogUser):
    def __init__(self):
        Gtk.Window.__init__(self, title="Test Window")
        box = Gtk.VBox()
        self.add(box)

        #self.kpw = KeypadWidget(length=3)
        #box.add(self.kpw)

        self.set_border_width(6)
        button = Gtk.Button(label="Test dialog")
        button.connect("clicked", self.on_button_clicked)
        box.add(button)



    def on_button_clicked(self, widget):
        #print(self.kpw.result())
        print(self.file_dialog())

        #dialog = DialogKeypad("title", "Enter the key code for this lock")
        #response = dialog.run()

        #if response == Gtk.ResponseType.OK:
        #    print("The OK button was clicked")
        #elif response == Gtk.ResponseType.CANCEL:
        #    print("The Cancel button was clicked")
        #else:
        #    print("Done.")
        #dialog.destroy()


win = TestWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()