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
from dungeon.ui.dialogs import DialogUser
from dungeon.ui.objectwidget import ObjectWidget
from dungeon.utils import roll_dice
from dungeon.ui.uiutils import frame_wrap
import tempfile
import subprocess
import os

logger = logging.getLogger()

class PlayDungeon(Gtk.Application, DialogUser):
    def __init__(self):
        Gtk.Application.__init__(self)
        builder = Gtk.Builder()
        builder.add_objects_from_file(sys.path[0] + "/ui/windows.glade", 
                                      ('mainWindow', 'imgParty', 'imgInventory',
                                       'imgTree', 'imgMap', 'imgSkeletonKey',
                                       'inventoryWindow', 'treeWindow', 'imgRun'))
        builder.connect_signals(self)
        self.builder = builder
        # find the objects we care about
        self.window = builder.get_object('mainWindow')
        self.mapImage = builder.get_object('mapImage')
        #self.mapImage.modify_bg(Gtk.StateType.NORMAL, Gdk.Color.parse("white")[1])
        self.mapImage.modify_bg(Gtk.StateType.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 1.0).to_color())
        self.roomLabel = builder.get_object('roomLabel')
        self.visitedLabel = builder.get_object('visitedLabel')
        self.detailsPanel = builder.get_object('detailsPanel')
        self.exitsPanel = builder.get_object('exitsPanel')
        self.monstersPanel = builder.get_object('monstersPanel')
        self.dungeonTime = builder.get_object('dungeonTime')
        # variables
        self.dungeon = None
        self.dungeon_filename = None
        self.all_map = False
        
        self.window.show()


    def onNew(self, caller):
        print("on file new")

    def onOpen(self, caller):
        new_filename = self.file_dialog(mode='r', title="Choose a dungeon file")
        if new_filename is not None:
            try:
                self.load_dungeon(new_filename)
            except Exception as e:
                self.message_box(Gtk.MessageType.ERROR, "Open Failed", e)

    def onSave(self, caller):
        new_name = self.dungeon_filename
        if new_name is None:
               self.onSaveAs(caller, 'untitled.dng')
        else:
            try: 
                with open(new_name, 'w') as f:
                    yaml.dump(self.dungeon, stream=f)
                self.dungeon_filename = new_name
                self.window.set_title(f"Play Dungeon: {new_name}")
            except Exception as e:
                self.message_box(Gtk.MessageType.ERROR, "Save Failed", e)

    def onSaveAs(self, caller, suggested=None):
        new_filename = self.file_dialog(mode='w', suggested_name=suggested, title="Save Dungeon")
        if new_filename is not None:
            self.dungeon_filename = new_filename
            self.onSave(caller)

    def onParty(self, caller):
        print("on party")

    def onInventory(self, caller):
        if not self.dungeon.inventory.contents:
            self.message_box(Gtk.MessageType.INFO, "Inventory", "There are no items in the inventory")
            return

        value = self.dungeon.inventory.get_value()
        window = self.builder.get_object('inventoryWindow')
        print(f"Got window object {window}")
        label = self.builder.get_object('lblInventory')
        label.set_markup(f"<b>Inventory (value: {value:0.2f}gp)</b>")
        box = self.builder.get_object('boxInventory')
        print(f"  box: {box}")
        for o in box.get_children():
            box.remove(o)

        for i in self.dungeon.inventory.contents:
            ow = ObjectWidget(self.dungeon, i, controls=False)
            frame = frame_wrap(ow, f"{i.class_label()} {i.id}",
                               hpad=5, vpad=0, hmargin=10, vmargin=5)
            box.pack_start(frame, True, True, 0)
        window.show()
        window.run()
        window.hide()
        

    def onMap(self, caller):
        self.all_map = caller.get_active()
        print(f"OnMap: {self.all_map}")
        self.onUpdateData(caller)


    def onTree(self, caller):
        print("On tree")
        window = self.builder.get_object("treeWindow")
        image = self.builder.get_object("treeImage")
        tmp = tempfile.mktemp() + ".png"
        dot = self.dungeon.generate_object_graph_dot().encode('utf-8')
        subprocess.run(['neato', '-Tpng', '-o', tmp], input=dot, check=True)
        image.set_from_file(tmp)
        os.unlink(tmp)
        window.show()
        window.run()
        window.hide()


    def onSkeletonKey(self, caller):
        print(f"onSkeletonKey: {self.dungeon.state.get('skeleton_key', None)}")
        self.dungeon.state['skeleton_key'] = caller.get_active()


    def onRunTo(self, caller):
        # update the run-to menu
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        flowbox = Gtk.FlowBox()
        flowbox.set_valign(Gtk.Align.START)
        flowbox.set_max_children_per_line(5)
        flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled.add(flowbox)
        menu = Gtk.Popover()
        menu.set_size_request(240, 150)
        menu.add(scrolled)
        if self.all_map:
            rooms = [x for x in self.dungeon.objects.values() if x.is_a('Room')]
        else:
            rooms = [x for x in self.dungeon.objects.values() if x.is_a('Room') and x.visited]
        for r in sorted(rooms, key=lambda x: int(x.id[1:])):
            x = Gtk.Button(label=r.id)
            x.connect('clicked', self.onRunToChoice)
            flowbox.add(x)
        menu.set_relative_to(caller)
        menu.set_position(Gtk.PositionType.BOTTOM)
        menu.show_all()
        menu.popup()
        self.runtopopup = menu

    def onRunToChoice(self, caller):
        logger.debug(f"User has run to room {caller.get_label()}")
        self.dungeon.state['current_room'] = self.dungeon.objects[caller.get_label()]
        self.dungeon.state['current_room'].visited = True
        self.runtopopup.popdown()
        self.onUpdateData(caller)

    def onDestroyWindow(self, caller, something):
        print(f"Destroy!  {something}")
        if self.ok_cancel_dialog(Gtk.MessageType.QUESTION, "Quit Application?", 
                                 "Any progress you have made since the last save will be lost"):
            Gtk.main_quit()
        return True

    def load_dungeon(self, filename):
        with open(filename, 'r') as f:
            self.dungeon = yaml.load(f, Loader=yaml.FullLoader)
        self.dungeon_filename = filename
        self.window.set_title(f"Play Dungeon: {filename}")
        self.onUpdateData(None)

    def onUpdateData(self, caller):
        """ Update all of the data elements """
        if self.dungeon == None:
            return

        # generate the map image
        tmp = tempfile.mktemp() + ".png"
        dot = self.dungeon.generate_map_dot(all_rooms=self.all_map).encode('utf-8')
        subprocess.run(['neato', '-Tpng', '-o', tmp], input=dot, check=True)
        self.mapImage.set_from_file(tmp)
        os.unlink(tmp)

        # update the panels.
        current_room = self.dungeon.state['current_room']
        panels = [
            [self.detailsPanel, [current_room], False],
            [self.exitsPanel, list(x for x in current_room.contents if x.is_a('Door')), True],
            [self.monstersPanel, list(x for x in current_room.contents if x.is_a('Monster')), True]
        ]
        for panel, contents, use_frame in panels:
            for c in panel.get_children():
                panel.remove(c)
            for c in contents:
                ow = ObjectWidget(self.dungeon, c)
                ow.connect('update_data', self.onUpdateData)
                ow.connect('update_time', self.onUpdateTime)
                ow.show()
                if use_frame:
                    frame = Gtk.Frame()
                    flag = ""
                    if c.is_a('Door') and c.visited:
                        flag = " \u2714 "
                    frame.set_label(f"{c.class_label()} {c.id}{flag}")
                    frame.add(ow)
                    frame.show()
                    panel.add(frame)
                else:
                    panel.add(ow)

        # update other information
        self.roomLabel.set_label(f"{current_room.class_label()} {current_room.id}")
        count = 0
        visited = 0
        for o in self.dungeon.objects.values():
            if o.is_a('Room'):
                count += 1
                if o.visited:
                    visited += 1
        self.visitedLabel.set_label(f"Rooms visited: {visited}/{count}")




    def onUpdateTime(self, caller, time):
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
    Gtk.main()


if __name__ == "__main__":
    main()

