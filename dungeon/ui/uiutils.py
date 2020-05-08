import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

class ChildFinder:
    def find_child(self, name):
        return ChildFinder._find_child(self, name)

    @staticmethod
    def _find_child(current, name):
        #print(f"Scanning: {current} / {current.get_name()}")
        if current.get_name() == name:
            return current
        if hasattr(current, 'get_child') and callable(current.get_child):
            return ChildFinder._find_child(current.get_child(), name)
        elif hasattr(current, 'get_children') and callable(current.get_children):
            for c in current.get_children():
                n = ChildFinder._find_child(c, name)
                if n:
                    return n
        return None


def get_handler_id_for_signal(widget, signal):
    signal_id, detail = GObject.signal_parse_name(signal, widget, True)
    handler_id = GObject.signal_handler_find(widget, GObject.SignalMatchType.ID, signal_id, detail, None, None, None)
    return handler_id

def frame_wrap(widget, title=None, hmargin=5, vmargin=5, hpad=5, vpad=5):
    frame = Gtk.Frame()
    frame.set_label(title)
    frame.set_margin_start(hmargin)
    frame.set_margin_end(hmargin)
    frame.set_margin_top(vmargin)
    frame.set_margin_bottom(vmargin)
    widget.set_margin_start(hpad)
    widget.set_margin_end(hpad)
    widget.set_margin_top(vpad)
    widget.set_margin_bottom(vpad)
    frame.add(widget)
    frame.show()
    widget.show()
    return frame
