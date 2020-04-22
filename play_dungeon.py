#!/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
from pathlib import Path
from dungeon.dungeon import Dungeon
import yaml
import logging
import argparse
import sys
from dungeon.ui.doorwidget import DoorWidget
from dungeon.ui.dialogs import DialogUser
from dungeon.ui.monsterwidget import MonsterWidget
from dungeon.utils import roll_dice
import tempfile
import subprocess
import os

logger = logging.getLogger()

class PlayDungeon(Gtk.Application, DialogUser):
    def __init__(self):
        Gtk.Application.__init__(self)
        builder = Gtk.Builder()
        builder.add_objects_from_file(sys.path[0] + "/ui/windows.glade", ('mainWindow',))
        builder.connect_signals(self)
        # find the objects we care about
        self.window = builder.get_object('mainWindow')
        self.mapImage = builder.get_object('mapImage')
        self.mapImage.modify_bg(Gtk.StateType.NORMAL, Gdk.Color.parse("white")[1])
        self.roomLabel = builder.get_object('roomLabel')
        self.exitsVbox = builder.get_object('exitsVbox')
        self.roomDescription = builder.get_object('roomDescription')
        self.contentsLabel = builder.get_object('contentsLabel')
        self.contentsBox = builder.get_object('contentsBox')
        self.dungeonTime = builder.get_object('dungeonTime')
        self.monsterBox = builder.get_object('monsterBox')
        self.featuresBox = builder.get_object('featuresBox')
        self.dungeon = None
        self.dungeon_filename = None
        self.window.show_all()
        
    def onFileNew(self, caller):
        print("on file new")


    def _add_filters(self, dialog):
        filter = Gtk.FileFilter()
        filter.set_name("Dungeon Files")
        filter.add_pattern("*.dng")
        dialog.add_filter(filter)

        filter = Gtk.FileFilter()
        filter.set_name("Any File")
        filter.add_pattern("*")
        dialog.add_filter(filter)

    def onFileOpen(self, caller):
        dialog = Gtk.FileChooserDialog("Choose a dungeon file", self,
                                        Gtk.FileChooserAction.OPEN,
                                        (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                         Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        self._add_filters(dialog)
        response = dialog.run()
        new_filename = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            # open the dungeon
            try: 
                self.load_dungeon(new_filename)
            except Exception as e:
                dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                           Gtk.ButtonsType.OK, "Exception when opening")
                dialog.format_secondary_text(e)
                dialog.run()
                dialog.destroy()
            self.update_display()

    def onFileSave(self, caller):
        new_name = self.dungeon_filename
        if new_name is None:
               self.onFileSaveAs(caller, 'untitled.dng')
        else:
            try: 
                with open(new_name, 'w') as f:
                    yaml.safe_dump(self.dungeon.save(), stream=f)
                self.dungeon_filename = new_name
                self.window.set_title(f"Play Dungeon: {new_name}")
            except Exception as e:
                dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                           Gtk.ButtonsType.OK, "Exception when opening")
                dialog.format_secondary_text(e)
                dialog.run()
                dialog.destroy()

    def onFileSaveAs(self, caller, suggested=None):
        dialog = Gtk.FileChooserDialog(title="Choose a dungeon file", parent=self.window,
                                        action=Gtk.FileChooserAction.SAVE)
#                                        buttons=Gtk.ButtonsType.OK_CANCEL)
        dialog.set_filename(self.dungeon_filename if suggested is None else suggested)
        self._add_filters(dialog)
        response = dialog.run()
        new_filename = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            # save the dungeon
            try: 
                with open(new_filename, 'w') as f:
                    yaml.safe_dump(self.dungeon.save(), stream=f)
                self.dungeon_filename = new_filename
                self.window.set_title(f"Play Dungeon: {new_filename}")
            except Exception as e:
                dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                           Gtk.ButtonsType.OK, "Exception when opening")
                dialog.format_secondary_text(e)
                dialog.run()
                dialog.destroy()


    def onFileQuit(self, caller):
        if self.ok_cancel_dialog(Gtk.MessageType.QUESTION, "Quit Application?", 
                                 "Any progress you have made since the last save will be lost"):
            Gtk.main_quit()

    def onHelpAbout(self, caller):
        #self.message_box()
        pass

    def onDestroyWindow(self, caller, something):
        print(f"Destroy!  {something}")
        if self.ok_cancel_dialog(Gtk.MessageType.QUESTION, "Quit Application?", 
                                 "Any progress you have made since the last save will be lost"):
            Gtk.main_quit()
        return True


    def load_dungeon(self, filename):
        with open(filename, 'r') as f:
            data = yaml.safe_load(f)
        dungeon = Dungeon.load(data)
        # now that we have a dungeon, we can replace the one we had before.
        self.dungeon = dungeon
        self.dungeon_filename = filename
        self.window.set_title(f"Play Dungeon: {filename}")

    def update_display(self, caller=None):
        """ Update all of the data elements """
        print("Update display")

        if self.dungeon == None:
            return

        # generate the map image
        known_nodes = [x.id for x in self.dungeon.map.get_nodes() if x.attributes['state']['visited'] is True]
        tmp = tempfile.mktemp() + ".png"
        dot = self.dungeon.map.dump_graphviz(known_nodes=known_nodes, 
                                             current_node=self.dungeon.state['current_room']).encode('utf-8')
        subprocess.run(['dot', '-Tpng', '-o', tmp], input=dot, check=True)
        self.mapImage.set_from_file(tmp)
        os.unlink(tmp)

        current_room = self.dungeon.state['current_room']
        node = self.dungeon.map.get_node(current_room)

        # fill in the room description
        self.roomDescription.set_label("\u2022" + "\n\u2022".join(node.attributes['description']))
        
        # fill in the features
        self.onFeaturesRefresh()
        # fill in the traps

        self.onContentsRefresh()
        
        



        # Refresh the exits panel
        for c in self.exitsVbox.get_children():
            self.exitsVbox.remove(c)
        for e_id in node.exits:
            d = DoorWidget(self.dungeon, self.dungeon.map.get_edge(e_id))
            d.connect('refresh_data', self.update_display)
            d.connect('update_time', self.onTimeUpdate)

            self.exitsVbox.add(d)        


        # monsters.
        self.onMonstersRefresh()


    def onRest(self, caller):
        times = [0, 8, 4]
        mode = caller.get_active()
        txt = caller.get_active_text()
        if mode > 0:
            wm_percent = self.dungeon.parameters['wandering_monster_percent_per_hour']
            node = self.dungeon.map.get_node(self.dungeon.state['current_room'])
            is_open = False
            for ex in node.exits:
                edge = self.dungeon.map.get_edge(ex)
                is_open |= edge.is_open()
            for c in range(times[mode]):
                d = roll_dice('1d100')
                m = self.dungeon.get_wandering_monster()
                #print(f"d: {d}, wm%: {wm_percent}, open: {is_open}, monster: {m.attributes['name']}")                

                if is_open and (d <= wm_percent) and m is not None:
                    # a wandering monster will arrive.
                    m.set_location(self.dungeon.state['current_room'])
                    self.message_box(Gtk.MessageType.INFO, f"{txt} Rest Interrupted!", f"A {m.attributes['name']} has wandered into the room afer {c} hours")
                    self.onMonstersRefresh()
                    break
                else:
                    self.onTimeUpdate(None, 60)
            else:        
                self.message_box(Gtk.MessageType.INFO, f"{txt} Rest", f"The characters have taken a {txt} rest")
            caller.set_active(0)

    def onRoomInvestigate(self, caller):
        print("Players to investigate room -- find hidden things in the room")
 


    def onTimeUpdate(self, caller, time):
        self.dungeon.state['current_time'] += time
        total = self.dungeon.state['current_time']
        days = total // (24 * 60)
        total -= days * (24 * 60)
        hours = total // 60
        mins = total - hours * 60
        if days:
            t = f"{days}+{hours:02d}:{mins:02d}"
        else:
            t = f"{hours:02d}:{mins:02d}"
        self.dungeonTime.set_label(t)


    def onContentsRefresh(self, caller=None):
        # clear then fill in the contents
        print("onContentsRefresh")
        for child in self.contentsBox:
            self.contentsBox.remove(child)
        node = self.dungeon.map.get_node(self.dungeon.state['current_room'])
        contents = node.attributes['state']['contents']
        self.contentsLabel.set_label(f"<b>Contents ({len(contents)})</b>")
        self.contentsBox.add(self._make_content_item("<i>Leave an item in this room</i>", add=True))
        for c in contents:
            self.contentsBox.add(self._make_content_item(c))
        self.contentsBox.show_all()

    def _modify_contents(self, caller, text):
        node = self.dungeon.map.get_node(self.dungeon.state['current_room'])
        contents = node.attributes['state']['contents']
        if text is None:
            text = self.input_dialog("Leave an item in this room", "Type the description of the item", multiline=True)
            if text is not None:
                contents.append(text.strip())
        else:
            contents.remove(text)        
        self.onContentsRefresh()

    def _make_content_item(self, text, add=False):
        hbox = Gtk.HBox()
        b = Gtk.Button.new_from_icon_name('list-add' if add else 'list-remove', Gtk.IconSize.BUTTON)
        b.connect('clicked', self._modify_contents, None if add else text)
        hbox.pack_start(b, False, False, 0)
        hbox.add(Gtk.Label(label=text, wrap=True, use_markup=True, xalign=0.1, margin_left=3))
        return hbox


    def onMonstersRefresh(self, caller=None):
        for m in self.monsterBox:
            self.monsterBox.remove(m)

        for m in self.dungeon.get_monsters_for_room(self.dungeon.state['current_room']):
            mon = MonsterWidget(self.dungeon, m)
            mon.connect('refresh_monsters', self.onMonstersRefresh)
            mon.connect('refresh_contents', self.onContentsRefresh)
            mon.connect('refresh_features', self.onFeaturesRefresh)
            self.monsterBox.pack_start(mon, True, True, 5)

    def onFeaturesRefresh(self, caller=None):
        node = self.dungeon.map.get_node(self.dungeon.state['current_room'])
        features = node.attributes['state']['features']        
        for f in self.featuresBox:
            self.featuresBox.remove(f)
        for f in features:
            self.featuresBox.add(Gtk.Label(label=f))




def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dungeon", metavar="<dungeon>", nargs='?', default=None, help="Load a dungeon at start")
    parser.add_argument("--debug", default=False, action='store_true', help="Turn on debugging")
    args = parser.parse_args()

    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
    log_handler =logging.StreamHandler(sys.stderr)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_handler.setFormatter(log_formatter)
    logger.addHandler(log_handler)

    app = PlayDungeon()
    if args.dungeon is not None:
        app.load_dungeon(args.dungeon)
        app.update_display()        
    Gtk.main()


if __name__ == "__main__":
    main()

