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
