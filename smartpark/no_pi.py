"""The following code is used to provide an alternative to students who do not have a Raspberry Pi.
If you have a Raspberry Pi, or a SenseHAT emulator under Debian, you do not need to use this code.

You need to split the classes here into two files, one for the CarParkDisplay and one for the CarDetector.
Attend to the TODOs in each class to complete the implementation."""
from interfaces import CarparkSensorListener
from interfaces import CarparkDataProvider
import threading
import time
import logging
import tkinter as tk
from config_parser import parse_config
from typing import Iterable
from carpark_manager import CarparkManager
import mocks

# ------------------------------------------------------------------------------------#
# You don't need to understand how to implement this class.                           #
# ------------------------------------------------------------------------------------#


class WindowedDisplay:
    """Displays values for a given set of fields as a simple GUI window. Use .show() to display the window; use .update() to update the values displayed.
    """

    DISPLAY_INIT = '– – –'
    SEP = ':'  # field name separator

    def __init__(self, root, title: str, display_fields: Iterable[str]):
        """Creates a Windowed (tkinter) display to replace sense_hat display. To show the display (blocking) call .show() on the returned object.

        Parameters
        ----------
        title : str
            The title of the window (usually the name of your carpark from the config)
        display_fields : Iterable
            An iterable (usually a list) of field names for the UI. Updates to values must be presented in a dictionary with these values as keys.
        """
        self.window = tk.Toplevel(root)
        self.window.title(f'{title}: Parking')
        self.window.geometry('800x400')
        self.window.resizable(False, False)
        self.display_fields = display_fields

        self.gui_elements = {}
        for i, field in enumerate(self.display_fields):

            # create the elements
            self.gui_elements[f'lbl_field_{i}'] = tk.Label(
                self.window, text=field+self.SEP, font=('Arial', 50))
            self.gui_elements[f'lbl_value_{i}'] = tk.Label(
                self.window, text=self.DISPLAY_INIT, font=('Arial', 50))

            # position the elements
            self.gui_elements[f'lbl_field_{i}'].grid(
                row=i, column=0, sticky=tk.E, padx=5, pady=5)
            self.gui_elements[f'lbl_value_{i}'].grid(
                row=i, column=2, sticky=tk.W, padx=10)

    def show(self):
        """Display the GUI. Blocking call."""
#        self.window.mainloop()

    def update(self, updated_values: dict):
        """Update the values displayed in the GUI. Expects a dictionary with keys matching the field names passed to the constructor."""
        for field in self.gui_elements:
            if field.startswith('lbl_field'):
                field_value = field.replace('field', 'value')
                self.gui_elements[field_value].configure(
                    text=updated_values[self.gui_elements[field].cget('text').rstrip(self.SEP)])
        self.window.update()

# -----------------------------------------#
# TODO: STUDENT IMPLEMENTATION STARTS HERE #
# -----------------------------------------#

class CarParkDisplay:
    """Provides a simple display of the car park status. This is a skeleton only. The class is designed to be customizable without requiring and understanding of tkinter or threading."""
    # determines what fields appear in the UI
    fields = ['Available bays', 'Temperature', 'At']

    def __init__(self,root):
        self.window = WindowedDisplay(root,
            'Moondalup', CarParkDisplay.fields)
        self._update_signal = threading.Event()   # NEW
        updater = threading.Thread(target=self.check_updates)
        updater.daemon = True
        updater.start()
        self.window.show()
        self._provider=None
        self.btn_show_parked = tk.Button(
            self.window.window, text='Show Currently Parked',
            font=('Arial', 20), command=self.show_parked_cars)
        self.btn_show_parked.grid(row=10, column=0, columnspan=3, pady=20)
    
    @property
    def data_provider(self):
        return self._provider
    @data_provider.setter
    def data_provider(self,provider):
        if isinstance(provider,CarparkDataProvider):
            self._provider=provider
    
    def notify_update(self):
        """Call this whenever the underlying data changes, to refresh
        the display immediately instead of waiting for the next poll."""
        self._update_signal.set()
    
    def show_parked_cars(self):
        """Open a small popup window listing every car currently parked."""
        if self._provider is None:
            return

        popup = tk.Toplevel(self.window.window)
        popup.title('Currently Parked')
        popup.geometry('400x400')

        parked = self._provider.parked_cars
        if not parked:
            tk.Label(popup, text='No cars currently parked.',
                     font=('Arial', 14)).pack(pady=10)
        else:
            for plate, car in parked.items():
                entry_str = time.strftime('%H:%M:%S', car.entry_time)
                tk.Label(popup, text=f'{plate} — entered {entry_str}',
                         font=('Arial', 14)).pack(anchor='w', padx=10)

    def update_display(self):
        temp = self._provider.temperature
        temp_display = f'{temp:.0f}℃' if temp is not None else '– – –'
        field_values = dict(zip(CarParkDisplay.fields, [
            f'{self._provider.available_spaces:03d}',
            temp_display,
            time.strftime("%H:%M:%S",self._provider.current_time)
        ]))
        self.window.update(field_values)

    def check_updates(self):
        while True:
            self._update_signal.wait()   # blocks here until notify_update() is called
            self._update_signal.clear()  # reset so we can wait again next time
            if self._provider is not None:
                self.update_display()


class CarDetectorWindow:
    """Provides a couple of simple buttons that can be used to represent a sensor detecting a car. This is a skeleton only."""

    def __init__(self,root):
        self.root=root
        self.root.title("Car Detector ULTRA")

        self.btn_incoming_car = tk.Button(
            self.root, text='🚘 Incoming Car', font=('Arial', 50), cursor='right_side', command=self.incoming_car)
        self.btn_incoming_car.grid(padx=10, pady=5,row=0,columnspan=2)
        self.btn_outgoing_car = tk.Button(
            self.root, text='Outgoing Car 🚘',  font=('Arial', 50), cursor='bottom_left_corner', command=self.outgoing_car)
        self.btn_outgoing_car.grid(padx=10, pady=5,row=1,columnspan=2)
        self.listeners=list()
        self.temp_label=tk.Label(
            self.root, text="Temperature", font=('Arial', 20)
        )
        self.temp_label.grid(padx=10, pady=5,column=0,row=2)
        self.temp_var=tk.StringVar()
        self.temp_var.trace_add("write",lambda x,y,v: self._on_temp_var_write())
        self.temp_box=tk.Entry(
            self.root,font=('Arial', 20),textvariable=self.temp_var
        )
        self.temp_box.grid(padx=10, pady=5,column=1,row=2)

        self.plate_label=tk.Label(
            self.root, text="License Plate", font=('Arial', 20)
        )
        self.plate_label.grid(padx=10, pady=5,column=0,row=3)
        self.plate_var=tk.StringVar()
        self.plate_box=tk.Entry(
            self.root,font=('Arial', 20),textvariable=self.plate_var
        )
        self.plate_box.grid(padx=10, pady=5,column=1,row=3)
    
    @property
    def current_license(self):
        return self.plate_var.get()

    def add_listener(self,listener):
        if isinstance(listener,CarparkSensorListener):
            self.listeners.append(listener)

    def incoming_car(self):
#        print("Car goes in")
        for listener in self.listeners:
            listener.incoming_car(self.current_license)

    def outgoing_car(self):
#        print("Car goes out")
        for listener in self.listeners:
            listener.outgoing_car(self.current_license)
    
    def _on_temp_var_write(self):
        """Called on every keystroke in the temperature box. While
        typing, the text is often briefly invalid (empty, just '-',
        just '.') so we only fire temperature_changed once it parses
        as a real number."""
        try:
            value = float(self.temp_var.get())
        except ValueError:
            return
        self.temperature_changed(value)

    def temperature_changed(self,temp):
        for listener in self.listeners:
            listener.temperature_reading(temp)


if __name__ == '__main__':
    root = tk.Tk()

    display=CarParkDisplay(root)

    manager=CarparkManager('samples_and_snippets/config.json', on_change=display.notify_update)
    display.data_provider=manager

    detector=CarDetectorWindow(root)
    detector.add_listener(manager)

    print("Currently parked:")
    for plate, car in manager.parked_cars.items():
        print(f"  {plate} (entered {time.strftime('%H:%M:%S', car.entry_time)})")

    print("\nFull activity log:")
    for line in manager.get_activity_log():
        print(line.strip())

    root.mainloop()
