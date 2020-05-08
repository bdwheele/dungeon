import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import re
import sys
from .uiutils import ChildFinder
from .keypadwidget import KeypadWidget

# Misc dialog boxes for the application

class DialogUser(Gtk.Widget):

    def message_box(self, dialog_type, title, message, window_title=None):
        dialog = Gtk.MessageDialog(self.get_toplevel(), 0, dialog_type,
                                   Gtk.ButtonsType.OK, title)
        if window_title is None:
            window_title = title
        dialog.set_title(window_title)
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def complex_dialog(self, children, window_title):
        dialog = Gtk.Dialog()
        dialog.add_button("OK", Gtk.ResponseType.OK)
        dialog.set_title(window_title)
        dialog.set_modal(True)
        content = dialog.get_content_area()
        content.add(children)
        content.show()
        dialog.run()
        dialog.destroy()


    def ok_cancel_dialog(self, dialog_type, title, message, window_title=None):
        dialog = Gtk.MessageDialog(self.get_toplevel(), 0, dialog_type,
                                   Gtk.ButtonsType.OK_CANCEL, title)
        if window_title is None:
            window_title = title
        dialog.set_title(window_title)
        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def input_dialog(self, title, message=None, default=None, check=None, multiline=False, window_title=None):
        while True:
            default_height = 150 if multiline else 100
            window_title = title if window_title is None else window_title
            dialog = Gtk.Dialog(title, self.get_toplevel(), 0,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK),
                title=window_title, resizable=False,
                default_height=default_height, default_width=150)
            box = dialog.get_content_area()
            vbox = Gtk.VBox(margin_top=10, margin_bottom=10, margin_start=10, margin_end=10)
            box.add(vbox)
            if message is not None:
                vbox.add(Gtk.Label(message))
            if not multiline:
                entry = Gtk.Entry(margin_top=5, margin_bottom=5)
                vbox.add(entry)
                if default is not None:
                    entry.set_text(str(default))

                # make enter key work
                entry.set_activates_default(True)
                okButton = dialog.get_widget_for_response(response_id=Gtk.ResponseType.OK)
                okButton.set_can_default(True)
                okButton.grab_default()
            else:
                tv = Gtk.TextView()
                vbox.pack_start(tv, True, True, 0)
                entry = tv.get_buffer()
                if default is not None:
                    entry.set_text(str(default))
                
            dialog.show_all()
            response = dialog.run()
            if not multiline:
                text = entry.get_text()
            else:
                start, end = entry.get_bounds()
                text = entry.get_text(start, end, False)
            dialog.destroy()
            if response == Gtk.ResponseType.CANCEL:
                return None
            else:
                if check is None:
                    return text
                elif callable(check):
                    msg = check(text)
                elif isinstance(check, re.Pattern):
                    if check.fullmatch(text) is not None:
                        msg = None
                    else:
                        msg = f"Did not match regular expression '{check.pattern}'"
                if msg is None:
                    return text
                else:
                    self.message_box(Gtk.MessageType.ERROR, "Validation Error", msg)
                    default = text

    def keypad_input(self, title, message, window_title=None, length=4, default=None):
        window_title = title if window_title is None else window_title
        dialog = Gtk.Dialog(title, self.get_toplevel(), 0,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK),
            title=window_title, resizable=False) #,
            #default_height=default_height, default_width=150)
        box = dialog.get_content_area()
        vbox = Gtk.VBox(margin_top=10, margin_bottom=10, margin_start=10, margin_end=10)
        box.add(vbox)
        if message is not None:
            vbox.add(Gtk.Label(message))
        self.keypad = KeypadWidget(length=length, default=default)
        vbox.add(self.keypad)
        dialog.show_all()
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.CANCEL:
            return None
        else:
            return self.keypad.result()

    def file_dialog(self, mode='r', title='File', suggested_name="untitled.dgn"):
        action = Gtk.FileChooserAction.OPEN if mode == 'r' else Gtk.FileChooserAction.SAVE
        dialog = Gtk.FileChooserDialog(title, self.window, action,  #pylint: disable=no-member
                                       ("_Cancel", Gtk.ResponseType.CANCEL,
                                        "_OK", Gtk.ResponseType.OK))
        if mode != 'r' and suggested_name is not None:
            dialog.set_filename(suggested_name)

        for x in (("Dungeon Files", "*.dgn"), ("All Files", "*")):
            filter = Gtk.FileFilter()
            filter.set_name(x[0])
            filter.add_pattern(x[1])
            dialog.add_filter(filter)
        response = dialog.run()
        new_filename = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            return new_filename
        else:
            return None
