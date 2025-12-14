import json
import queue
import requests
import threading
import tkinter as tk

from PlaceHolder import PlaceHolder


class AutoCompleter(PlaceHolder):
    def __init__(self, parent, placeholder, **kw):

        self.parent = parent

        self.lb = tk.Listbox(self.parent, selectmode=tk.SINGLE, **kw)
        self.lb_up = False
        self.has_selected = False
        self.queue = queue.Queue()
        self._running = True

        PlaceHolder.__init__(self, parent, placeholder, **kw)
        self.var_traceid = self.var.trace_add('write', self.changed)
        
        # Stop update loop when widget is destroyed
        self.bind("<Destroy>", self._on_destroy)

        # Create right click menu
        self.menu = tk.Menu(self.parent, tearoff=0)
        self.menu.add_command(label="Cut")
        self.menu.add_command(label="Copy")
        self.menu.add_command(label="Paste")

        self.bind("<Any-Key>", self.keypressed)
        self.lb.bind("<Any-Key>", self.keypressed)
        self.bind('<Control-KeyRelease-a>', self.select_all)
        self.bind('<Button-3>', self.show_menu)
        self.lb.bind("<ButtonRelease-1>", self.selection)
        self.bind("<FocusOut>", self.ac_foc_out)
        self.lb.bind("<FocusOut>", self.ac_foc_out)

        self.update_me()

    def ac_foc_out(self, event=None):
        x, y = self.parent.winfo_pointerxy()
        widget_under_cursor = self.parent.winfo_containing(x, y)
        if (widget_under_cursor != self.lb and widget_under_cursor != self) or event is None:
            self.foc_out()
            self.hide_list()

    def show_menu(self, e):
        self.foc_in()
        w = e.widget
        self.menu.entryconfigure("Cut", command=lambda: w.event_generate("<<Cut>>"))
        self.menu.entryconfigure("Copy", command=lambda: w.event_generate("<<Copy>>"))
        self.menu.entryconfigure("Paste", command=lambda: w.event_generate("<<Paste>>"))
        self.menu.tk.call("tk_popup", self.menu, e.x_root, e.y_root)

    def keypressed(self, event):
        key = event.keysym
        if key == 'Down':
            self.down(event.widget.widgetName)
        elif key == 'Up':
            self.up(event.widget.widgetName)
        elif key in ['Return', 'Right']:
            if self.lb_up:
                self.selection()
        elif key in ['Escape', 'Tab', 'ISO_Left_Tab'] and self.lb_up:
            self.hide_list()

    def select_all(self, event):
        event.widget.event_generate('<<SelectAll>>')

    def changed(self, name=None, index=None, mode=None):
        value = self.var.get()
        if len(value) < 3 and self.lb_up or self.has_selected:
            self.hide_list()
            self.has_selected = False
            if len(value) >= 3:
                # Validate system name even if we're not showing the list
                t = threading.Thread(target=self.validate_system, args=[value])
                t.start()
        else:
            t = threading.Thread(target=self.query_systems, args=[value])
            t.start()

    def selection(self, event=None):
        if self.lb_up:
            self.has_selected = True
            index = self.lb.curselection()
            self.var.trace_remove("write", self.var_traceid)
            selected_system = self.lb.get(index)
            self.var.set(selected_system)
            self.hide_list()
            self.icursor(tk.END)
            # Set green color for valid selection
            self['fg'] = 'green'
            self.var_traceid = self.var.trace_add('write', self.changed)

    def up(self, widget):
        if self.lb_up:
            if self.lb.curselection() == ():
                index = '0'
            else:
                index = self.lb.curselection()[0]
            if index != '0':
                self.lb.selection_clear(first=index)
                index = str(int(index) - 1)
                self.lb.selection_set(first=index)
                if widget != "listbox":
                    self.lb.activate(index)

    def down(self, widget):
        if self.lb_up:
            if self.lb.curselection() == ():
                index = '0'
            else:
                index = self.lb.curselection()[0]
                if int(index + 1) != tk.END:
                    self.lb.selection_clear(first=index)
                    index = str(int(index + 1))

            self.lb.selection_set(first=index)
            if widget != "listbox":
                self.lb.activate(index)
        else:
            self.changed()

    def show_results(self, results):
        if results:
            self.lb.delete(0, tk.END)
            for w in results:
                self.lb.insert(tk.END, w)

            self.show_list(len(results))
            
            # Check if current text exactly matches a result
            current_text = self.var.get().strip()
            if current_text in results:
                self['fg'] = 'green'
            else:
                self.set_default_style()
        else:
            if self.lb_up:
                self.hide_list()
            # No results means invalid system
            current_text = self.var.get().strip()
            if len(current_text) >= 3 and current_text != self.placeholder:
                self['fg'] = 'red'

    def show_list(self, height):
        self.lb["height"] = min(height, 8)  # Max 8 items visible
        if not self.lb_up and self.parent.focus_get() in [self, self.lb]:
            info = self.grid_info()
            if info:
                self.lb.grid(row=int(info["row"]) + 1, column=int(info["column"]), columnspan=info.get("columnspan", 1), sticky="ew")
                self.lb_up = True

    def hide_list(self):
        if self.lb_up:
            self.lb.grid_remove()
            self.lb_up = False

    def query_systems(self, inp):
        inp = inp.strip()
        if inp != self.placeholder and len(inp) >= 3:
            url = "https://spansh.co.uk/api/systems"
            try:
                results = requests.get(
                    url,
                    params={'q': inp},
                    headers={'User-Agent': 'EDMC-PlanetPOI/1.0'},
                    timeout=3
                )

                lista = json.loads(results.content)
                if lista:
                    self.write(lista)
                else:
                    self.write([])
            except Exception as e:
                print(f"PlanetPOI: Failed to query system from Spansh API: {e}")

    def validate_system(self, inp):
        """Validate system name without showing dropdown"""
        inp = inp.strip()
        if inp != self.placeholder and len(inp) >= 3:
            url = "https://spansh.co.uk/api/systems"
            try:
                results = requests.get(
                    url,
                    params={'q': inp},
                    headers={'User-Agent': 'EDMC-PlanetPOI/1.0'},
                    timeout=3
                )

                lista = json.loads(results.content)
                # Check if exact match exists
                if lista and inp in lista:
                    self.after(0, lambda: self.config(fg='green'))
                else:
                    self.after(0, lambda: self.config(fg='red'))
            except Exception as e:
                print(f"PlanetPOI: Failed to validate system from Spansh API: {e}")

    def write(self, lista):
        self.queue.put(lista)

    def clear(self):
        self.queue.put(None)

    def _on_destroy(self, event=None):
        self._running = False

    def update_me(self):
        if not self._running:
            return
        try:
            while 1:
                lista = self.queue.get_nowait()
                self.show_results(lista)
                self.update_idletasks()
        except queue.Empty:
            pass
        if self._running:
            self.after(100, self.update_me)

    def set_text(self, text: str, placeholder_style: bool = True):
        if placeholder_style:
            self['fg'] = self.placeholder_color
        else:
            self.set_default_style()

        try:
            self.var.trace_remove("write", self.var_traceid)
        except Exception:
            pass
        finally:
            self.delete(0, tk.END)
            self.insert(0, text)
            self.var_traceid = self.var.trace_add('write', self.changed)