import pyperclip
from neutronplotter import NeutronPlotter
import math

try:
    # Python 2
    import Tkinter as tk
except ModuleNotFoundError:
    # Python 3
    import tkinter as tk

class Neutron(tk.Frame):

    def __init__(self, master, global_data, **kw):
        tk.Frame.__init__(self, master, **kw)
        self.globals = global_data
        self.globals.neutron = self
        self.plotter = NeutronPlotter(self.globals)
        self.route_ready = False

        # --- NEW: manual navigation state (index of NEXT target in route) ---
        self.current_index = 0  # points to the "next system to copy"
        self.route = []         # ensured to exist even before calculation

        self.setup()

    def update_clipboard(self, arrived_to):
        """Called by EDMC when Journal says we arrived to a system.
        Finds this system in self.route and copies the NEXT one to clipboard.
        Also updates current_index so +/- buttons stay in sync.
        """
        self.globals.logger.debug("Neutron -> Updating system clipboard")
        # Check none
        if self.checkbox_status is not None or self.checkbox_clipboard is None:
            # Check for route ready and checkbox
            if self.route_ready and self.checkbox_status.get() == 1:
                self.globals.logger.debug("Neutron -> Route is ready and clipboard checkbox is checked")
                try:
                    index = self.route.index(arrived_to)
                    total = len(self.route)
                    # compute progress based on ARRIVED index
                    percent = float(float(((index + 1)) / float(total)) * float(100))
                    percent = math.floor(percent * 100) / 100.0

                    # copy NEXT target (if any) and sync current_index
                    if index + 1 < total:
                        next_target = self.route[index + 1]
                        pyperclip.copy(next_target)
                        self.current_index = index + 1
                        self.globals.logger.debug("Neutron -> system clipboard changed to {}".format(next_target))
                        self.update_status("Clipboard updated to: ")
                        self.status_append(next_target)
                    else:
                        # reached end of route
                        self.current_index = total - 1
                        self.update_status("Route complete")
                    # show progress line
                    self.status_append("")
                    self.status_append("{}/{} ({:.2f}%)".format(index + 1, total, percent))
                    self._refresh_nav_buttons()
                except Exception as e:
                    print(e)
                    self.globals.logger.debug("Neutron -> clipboard update failed > {}".format(str(e)))
                    pass

    # --- NEW: helpers for status text updates ---
    def status_append(self, status_text):
        if self.label_status is not None:
            self.globals.logger.debug("Neutron -> Appening {} to status text".format(status_text))
            self.label_status["text"] = self.label_status["text"] + "\n" + status_text
            self.label_status.update()

    def update_status(self, status_text):
        if self.label_status is not None:
            self.globals.logger.debug("Neutron -> setting status text to {}".format(status_text))
            self.label_status["text"] = status_text
            self.label_status.update()

    def calculate_path(self):
        self.globals.logger.debug("Neutron -> calculating path")
        origin = self.entry_origin.get()
        dest = self.entry_destination.get()
        eff = -1
        range = -1.0

        self.update_status("")

        try:
            eff = int(self.entry_efficiency.get())
            range = float(self.entry_range.get())
        except ValueError:
            pass

        # If origin is empty, use current system
        if len(origin) < 1:
            self.globals.logger.debug("Neutron -> origin is not set, using current system {}".format(self.globals.current_system))
            origin = self.globals.current_system

        # Check for data validation
        if len(origin) < 1:
            self.globals.logger.debug("Neutron -> Origin cannot be empty (error)")
            self.status_append("ERROR: Origin must not be empty!")
        if len(dest) < 1:
            self.globals.logger.debug("Neutron -> Destination cannot be empty (error)")
            self.status_append("ERROR: Destination must not be empty!")
        if eff < 1 or eff > 100:
            self.globals.logger.debug("Neutron -> Efficiency must be number between 1 and 100! (error)")
            self.status_append("ERROR: Efficiency must be number between 1 and 100!")
        if range < 0:
            self.globals.logger.debug("Neutron -> Range must be decimal and not empty! (error)")
            self.status_append("ERROR: Range must be decimal and not empty!")

        # Check for errors
        if len(self.label_status["text"]) > 0:
            self.globals.logger.debug("Neutron -> Errors were detected, calculation will not start (error)")
            self.route_ready = False
            return False

        self.update_status("Calculating..")

        # request calculation
        self.globals.logger.debug("Neutron -> Requesting route..")
        route = self.plotter.request_calculation(origin, dest, eff, range)

        self.update_status("Processing data..")

        # Process json for system names
        self.globals.logger.debug("Neutron -> Processing data")
        self.route = list()
        for record in route["result"]["system_jumps"]:
            self.globals.logger.debug("Neutron -> system found {}".format(record["system"]))
            self.route.append(record["system"])

        # Mark as ready
        if len(self.route) > 0:
            self.globals.logger.debug("Neutron -> Route is ready")
            self.update_status("Route calculated..")
            self.route_ready = True
            # reset manual index to start of "next target"
            self.current_index = 0 if len(self.route) == 1 else 1
            # simulate arrival to origin to seed clipboard with next hop
            self.update_clipboard(self.route[0])
            self._refresh_nav_buttons()
        else:
            self.globals.logger.debug("Neutron -> Route is less than one system away = destination is origin (error)")
            self.update_status("ERROR: Route has less than one system")
            self.route_ready = False
            self.current_index = 0
            self._refresh_nav_buttons()

    # --- NEW: manual +/- controls ---
    def _copy_current_target(self):
        """Copy the system at current_index to clipboard and refresh status."""
        if not self.route or not self.route_ready:
            return
        if self.checkbox_status is not None and self.checkbox_status.get() != 1:
            # auto-copy disabled; just show status
            pass
        try:
            total = len(self.route)
            # current_index points to NEXT target
            target = self.route[self.current_index]
            pyperclip.copy(target)
            self.globals.logger.debug("Neutron -> manual copy to {}".format(target))
            self.update_status("Clipboard updated to: ")
            self.status_append(target)
            # compute progress line relative to "arrived" = current_index
            percent = float(float((self.current_index) / float(total)) * float(100))
            percent = math.floor(percent * 100) / 100.0
            self.status_append("")
            self.status_append("{}/{} ({:.2f}%)".format(self.current_index, total, percent))
        except Exception as e:
            self.globals.logger.debug("Neutron -> manual copy failed > {}".format(str(e)))
        self._refresh_nav_buttons()

    def step_prev(self):
        if not self.route or not self.route_ready:
            return
        if self.current_index > 0:
            self.current_index -= 1
            self._copy_current_target()

    def step_next(self):
        if not self.route or not self.route_ready:
            return
        if self.current_index < len(self.route) - 1:
            self.current_index += 1
            self._copy_current_target()

    def _refresh_nav_buttons(self):
        # Disable/enable +/- depending on bounds
        try:
            if not hasattr(self, "button_prev") or not hasattr(self, "button_next"):
                return
            if not self.route or not self.route_ready:
                self.button_prev.configure(state=tk.DISABLED)
                self.button_next.configure(state=tk.DISABLED)
                return
            if self.current_index <= 0:
                self.button_prev.configure(state=tk.DISABLED)
            else:
                self.button_prev.configure(state=tk.NORMAL)
            if self.current_index >= len(self.route) - 1:
                self.button_next.configure(state=tk.DISABLED)
            else:
                self.button_next.configure(state=tk.NORMAL)
        except Exception as e:
            self.globals.logger.debug("Neutron -> _refresh_nav_buttons failed > {}".format(str(e)))

    def setup(self):
        # Unified width
        width = 16

        self.globals.logger.debug("Neutron -> Creating neutron plotter GUI")

        # Label origin
        self.label_origin = tk.Label(self, text="Origin: ", justify=tk.LEFT)
        self.label_origin.grid(row=0, column=0, sticky=tk.W, pady=(10, 0))

        # Entry origin
        self.entry_origin = tk.Entry(self, width=width)
        self.entry_origin.grid(row=0, column=1, sticky=tk.E, pady=(10, 0))

        # Label destination
        self.label_destination = tk.Label(self, text="Destination: ", justify=tk.LEFT)
        self.label_destination.grid(row=1, column=0, sticky=tk.W)

        # Entry destination
        self.entry_destination = tk.Entry(self, width=width)
        self.entry_destination.grid(row=1, column=1, sticky=tk.E)

        # Label range
        self.label_range = tk.Label(self, text="Range (LY): ", justify=tk.LEFT)
        self.label_range.grid(row=2, column=0, sticky=tk.W)

        # Entry range
        range_default = tk.DoubleVar(value=50.0)
        self.entry_range = tk.Entry(self, width=width, textvariable=range_default)
        self.entry_range.grid(row=2, column=1, sticky=tk.E)

        # Label efficiency
        self.label_efficiency = tk.Label(self, text="Efficiency (%): ", justify=tk.LEFT)
        self.label_efficiency.grid(row=3, column=0, sticky=tk.W)

        # Efficiency entry
        efficiency_default = tk.IntVar(value=60)
        self.entry_efficiency = tk.Spinbox(self, from_=1, to=100, width=width - 2,
                                           textvariable=efficiency_default)
        self.entry_efficiency.grid(row=3, column=1, sticky=tk.E)

        # Checkbox clipboard
        self.checkbox_status = tk.IntVar(value=1)
        self.checkbox_clipboard = tk.Checkbutton(self, text="Auto-copy to clipboard", variable=self.checkbox_status)
        self.checkbox_clipboard.grid(row=4, column=0, columnspan=2, sticky=tk.W)

        # --- CHANGED: Control buttons row: [-] [Calculate] [+] ---
        button_row = tk.Frame(self)
        button_row.grid(row=5, column=0, columnspan=2, pady=(3, 0), sticky=tk.EW)

        # [-]
        self.button_prev = tk.Button(button_row, text="−", width=3, command=self.step_prev)
        self.button_prev.grid(row=0, column=0, padx=(0, 6))

        # [Calculate] (unchanged handler)
        self.button_calculate = tk.Button(button_row, text="Calculate", command=self.calculate_path)
        self.button_calculate.grid(row=0, column=1)

        # [+]
        self.button_next = tk.Button(button_row, text="+", width=3, command=self.step_next)
        self.button_next.grid(row=0, column=2, padx=(6, 0))

        # Label Status
        self.label_status = tk.Label(self, text="Ready.. ", justify=tk.CENTER)
        self.label_status.grid(row=6, column=0, columnspan=2, pady=(0, 10))

        # Frame layout
        self.columnconfigure(6, weight=1)

        # initialize +/- buttons state
        self._refresh_nav_buttons()

        self.globals.logger.debug("Neutron -> neutron plotter GUI completed")
