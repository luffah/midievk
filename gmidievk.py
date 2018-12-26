#!/usr/bin/python3
"""
Gtk GUI to configure midievk
Require xdotool, python3-tk
"""
import logging
from math import floor, log10
from midiev import (MidiKeyboard, MIDITYPE,
                    CONTROLLER, NOTEON, NOTEOFF, CHANNEL)
from midievk import MidiToXdo
from options import (OPTIONS, NB_CTL_STEPS_IDX, get_all_midi_devices, DEVICE,
                     CONFIG_FILE, CONFIG_FORMAT, CONFIG_LOADER, TITLE,
                     NOTE_PRESSURE_MIDDLE_DELTA, NOTE_PRESSURE_STRONG_DELTA,
                     CTL_DECREASING)

try:
    import Tkinter as tk
    import tkMessagebox as messagebox
    import tkFont
    import ttk
except ImportError:  # Python 3
    import tkinter as tk
    from tkinter import messagebox
    import tkinter.font as tkFont
    import tkinter.ttk as ttk

GUI_DESC_MODE = {
    'Note-on': ['keydown', 'key'],
    'Note-on(middle)': ['keydown', 'key'],
    'Note-on(strong)': ['keydown', 'key'],
    'Note-off': ['keyup', 'key'],
    'CC+': ['relative', 'absolute'],
    'CC-': ['relative', 'absolute']
}


class TkWindow(tk.Frame):
    """TkWindow"""

    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.midikb = None
        self.midixdo = MidiToXdo()
        self._programming_mode = tk.IntVar()
        # self._programming_mode_live = False
        self._tree_selection = None
        self.init_gui()
        self.read_configs()
        if len(self._cbox_device.get()):
            self.connect_to_device(None)

    def init_gui(self):
        """init_gui"""
        self.parent.title(TITLE)
        self.pack(fill="both", expand=True)

        frame1 = ttk.Frame(self)
        frame1.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        frame1_1 = ttk.Frame(frame1)
        frame1_1.pack(side="bottom", fill="both", expand=True)
        frame1_2 = ttk.Frame(frame1)
        frame1_2.pack(side="top", fill="both", expand=False)

        frame2 = ttk.Frame(self)
        frame2.pack(side="right", fill="y", expand=False, padx=5, pady=5)

        tree_headers = [
            ('Type', 90),
            ('Channel', 10),
            ('Keybind', 90),
            ('Mode', 5)
        ]
        self._tree = ttk.Treeview(
            frame1_1,
            columns=[name for name, _ in tree_headers],
            show="headings",
            height=20
        )
        self._tree.pack(side='left', fill='both', expand=True)
        self._tree.bind('<<TreeviewSelect>>', self.selected_item)
        self._tree.bind('<<TreeviewClose>>', self._on_mouse_click)
        self._tree.bind('<<TreeviewOpen>>', self._on_mouse_click)
        self._tree.bind('<KeyPress>', self._on_key_press)
        for column, width in tree_headers:
            self._tree.heading(column, text=column)
            self._tree.column(
                column,
                width=(
                    tkFont.Font().measure(column) +
                    width),
                anchor='w')

        vsb = ttk.Scrollbar(
            frame2,
            orient="vertical",
            command=self._tree.yview)
        vsb.pack(side='right', fill='y')
        self._tree.configure(yscrollcommand=vsb.set)

        ttk.Label(frame1_2,
                  text="Device : ").pack(side='left', padx=5, pady=5)
        self._cbox_device = tk.StringVar()
        try:
            device_options = get_all_midi_devices()
            cbox = ttk.Combobox(
                frame1_2,
                textvariable=self._cbox_device,
                values=device_options,
            )
            cbox.pack(side='left', padx=5, pady=5)
            cbox.set(DEVICE or device_options.split()[0])
            cbox.bind("<<ComboboxSelected>>", self.connect_to_device)
        except IndexError:
            messagebox.showwarning(
                TITLE, "No midi device detected ! Leave...")
            exit()

        ttk.Checkbutton(frame1_2, text='Programming mode',
                        variable=self._programming_mode
                        ).pack(side='left', padx=5, pady=5)

        ttk.Button(frame1_2, text='Quit',
                   command=self.on_closing
                   ).pack(side='right', padx=5, pady=5)

        ttk.Button(frame1_2, text='Save configs',
                   command=self.save_configs
                   ).pack(side='right', padx=5, pady=5)

        self._programming_mode.set(0)

    def connect_to_device(self, event):
        """connect_to_device"""
        self.midikb = MidiKeyboard(self._cbox_device.get())
        self.midixdo.set_midi_device(self.midikb)

    def read_configs(self, file_format=CONFIG_FORMAT, file_name=CONFIG_FILE):
        """read_configs

        :param file_format:
        :param file_name:
        """
        if file_format in CONFIG_LOADER:
            conf_exists = self.midixdo.read_configs(
                file_format,
                file_name,
                config_line_process=self._gui_insert
            )
            if not conf_exists:
                self._programming_mode.set(1)
            else:
                self.sort_treeview(column=1)
                self.sort_treeview(column=0)
                self.sort_treeview(column=1)

    def save_configs(self, file_format=CONFIG_FORMAT, file_name=CONFIG_FILE):
        """save_configs

        :param file_format:
        :param file_name:
        """
        self.midixdo.save_configs(file_format, file_name)

    def sort_treeview(self, column=0, reverse=False):
        """sort_treeview

        :param column:
        :param reverse:
        """
        new_treeview = [
            (self._tree.set(child, column), child)
            for child in self._tree.get_children('')]
        new_treeview.sort(reverse=reverse)

        # rearrange items in sorted positions
        for index, (_, child) in enumerate(new_treeview):
            self._tree.move(child, '', index)

    def selected_item(self, tree_item):
        """selected_item

        :param tree_item:
        """
        if tree_item:
            self._tree_selection = self._tree.selection()

    def _gui_insert(self, midikey, values):
        """_gui_ins

        :param midikey:
        :param values:
        """
        typ = values['type']
        key_note = values['channel']
        keybind = values['keybind']
        keymode = values['mode']
        mod = None
        val = None
        if keybind:
            keybind_tab = keybind.split('+')
            mod = '+'.join(keybind_tab[0:-1])
            val = keybind_tab[-1]
        mod = mod or ''
        val = val or '<Undefined>'
        self._tree.insert(
            '', 'end', midikey, tags=midikey,
            values="{} {} {} {}".format(
                typ, key_note,
                mod + val,
                GUI_DESC_MODE[typ][keymode] if typ in GUI_DESC_MODE else ''
            )
        )

    def _ins(self, midikey, values):
        """_ins

        :param midikey:
        :param values:
        """
        valuest = {'type': values[0],
                   'channel': values[1],
                   'keybind': None,
                   'mode': 0
                   }

        self._gui_insert(midikey, valuest)
        self.midixdo.insert(midikey, valuest)

    def _update(self, midikey, values):
        """_update

        :param midikey:
        :param values:
        """
        valuest = {'type': values[0],
                   'channel': values[1],
                   'keybind': None,
                   'mode': 0
                   }

        self._gui_insert(midikey, valuest)
        self.midixdo.insert(midikey, valuest)

    def check_item(self, tree_item):
        """check_item

        :param tree_item:
        """
        if tree_item:
            key = int(tree_item[0])
            keytype = self.midixdo.get_key_type(key)
            if keytype in GUI_DESC_MODE:
                keyoption = self.midixdo.get_key_mode(key)
                keyoption = int(not (keyoption or 0))
                self._tree.set(tree_item, 3, GUI_DESC_MODE[keytype][keyoption])
                self.midixdo.set_key_mode(key, keyoption)

    def _on_mouse_click(self, event):
        """_on_mouse_click

        :param event:
        """
        if event is not None:
            self.check_item(self._tree_selection)

    def _on_key_press(self, event):
        """_on_key_press

        :param event:
        """
        key = event.__dict__['keysym']
        # if not (self._programming_mode.get() or self._programming_mode_live):
        if not self._programming_mode.get():
            # if key == 'Return':
                # self._programming_mode_live=True
            if key == 'BackSpace':
                self.set_current_key('', '<Undefined>')
            return
        if self._tree_selection:
            midikey = int(self._tree_selection[0], 16)
            keyoption = self.midixdo.get_key_mode(midikey)
            # if note off and no event raised on note off ,then do nothing
            if midikey >> 8 == 0x8 and not (keyoption or False):
                return

            state = event.__dict__['state']
            modifier = ""
            if state & (1 << 2):
                modifier = "Ctrl+"
            if state & (1 << 3) or state & (1 << 7):
                modifier = modifier + "Alt+"
            if state & (1 << 0):
                modifier = modifier + "Shift+"
            if state & (1 << 6):
                modifier = modifier + "Super+"

            # for child in self._tree.get_children():
                # if key == self._tree.item(child, option="values")[2]:
                # self._tree.set(child, 2, "<Undefined>")
#
            # self._programming_mode_live=False
            self.set_current_key(modifier, key)

    def set_current_key(self, modifier, key):
        """set_current_key

        :param modifier:
        :param key:
        """
        self._tree.set(self._tree_selection, 2, modifier+key)
        self.midixdo.set_keybind(
            int(self._tree.item(self._tree_selection, option="tag")[0]),
            modifier + key
        )

    def _update_type(self, midikey, name):
        """set_current_key

        :param modifier:
        :param key:
        """
        self._tree.set(midikey, 0, name)
        self.midixdo.set_key_type(midikey, name)

    def update_keys_list(self, command, midikey):
        """update_keys_list

        :param code:
        """
        miditype = command[MIDITYPE]
        name = None
        if miditype == NOTEOFF:
            name = "Note-off"
        elif miditype == NOTEON:
            name = "Note-on" + (
                "(middle)"
                if midikey >> 12 == NOTE_PRESSURE_MIDDLE_DELTA
                else
                "(strong)"
                if midikey >> 12 == NOTE_PRESSURE_STRONG_DELTA
                else ""
            )
        elif miditype == CONTROLLER:
            if OPTIONS[NB_CTL_STEPS_IDX] > 0:
                ndigits = "%0" + \
                    str(int(floor(log10(OPTIONS[NB_CTL_STEPS_IDX]) + 1))) + "d"
                name = "CC" + ndigits % (midikey >> 12) + \
                    '/' + str(OPTIONS[NB_CTL_STEPS_IDX])
            else:
                name = "CC" + ('-' if midikey >> 12 == CTL_DECREASING else '+')

        if midikey not in self.midixdo:
            channel = command[CHANNEL]
            self._ins(midikey, (name, channel))
        else:
            self._update_type(midikey, name)

        self.sort_treeview(column=0)
        self.sort_treeview(column=1)

    def check_midi_device(self):
        """check_midi_device"""
        if self.midikb:
            if self.midikb.is_running():
                self.after(1, self.check_midi_device)
            else:
                print("Midi device is currently not monitored")
                self.after(1000, self.check_midi_device)
                return
        else:
            print("Midi device disappeared")
            exit()
        (command, key) = self.midixdo.parse_midi()
        if key is not None:
            if self._programming_mode.get():
                # print key, command
                self.update_keys_list(command, key)
                idx = self._tree.index(key)
                treeitem = self._tree.get_children()
                movement = float((idx - 5) / len(treeitem))
                self._tree.yview('moveto', movement)
                self._tree.selection_set(key)
            else:
                try:
                    self._tree.selection_set(key)
                except:
                    pass
                self.midixdo.send_keystroke(command, key)
            logging.debug('Key: %s %s', key, command)

    def on_closing(self):
        """on_closing"""
        logging.debug('User want to close the app')
        self.after(500, self.midikb.stop_thread)
        self.after(1000, self.parent.destroy)
        logging.debug('Thanks for using this app :)')


def main():
    """main"""
    # logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.INFO)
    root = tk.Tk()
    # root.geometry("400x300")
    app = TkWindow(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.after(500, app.check_midi_device)
    root.mainloop()


if __name__ == '__main__':
    main()
