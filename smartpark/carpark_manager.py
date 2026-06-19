"""CarparkManager: tracks cars entering/leaving a carpark and reports
availability, temperature, and time to a display.

Replaces mocks.MockCarparkManager with a real implementation.
"""
import logging
import time

from interfaces import CarparkSensorListener, CarparkDataProvider
from config_parser import parse_config
from car import Car


class CarparkFullError(Exception):
    """Raised when a car tries to enter a carpark that has no free spaces."""
    pass


class UnrecognisedCarError(Exception):
    """Raised when outgoing_car is called for a plate that was never
    recorded as having entered the carpark. This prevents a phantom
    exit from incorrectly freeing up a parking space.
    """
    pass


class DuplicateEntryError(Exception):
    """Raised when incoming_car is called for a plate that is already
    recorded as parked (e.g. a sensor double-fire, or a typo'd plate
    that happens to match a car already inside).
    """
    pass


class CarparkManager(CarparkSensorListener, CarparkDataProvider):
    """Tracks live carpark occupancy, temperature, and time, and serves
    that data to a display via the CarparkDataProvider interface.
    Receives sensor events via the CarparkSensorListener interface.

    Maintains a dictionary of currently-parked Car objects keyed by
    license plate, so lookups for "is this car already in?" and
    "is this car actually here?" are O(1) and unambiguous.

    Note on config fields: this is a proof-of-concept and sensors are
    simulated (via the GUI buttons in no_pi.py), not read from real
    hardware over MQTT. The "broker", "port", "Sensors", and "Displays"
    entries in the config file describe the eventual real deployment
    but are not used by this class yet.

    Parameters
    ----------
    config_file : str
        Path to the JSON config file. Must contain "total-spaces".
        May contain "name", "location", and "total-cars" (see
        config_parser.parse_config).
    log_file : str
        Path to the file activity should be logged to.
    on_change : callable, optional
        A zero-argument callback invoked after every state change
        (car in, car out, temperature update). Intended to let a
        display (e.g. CarParkDisplay.notify_update) refresh immediately
        instead of polling. If None, no callback is made.
    """

    def __init__(self, config_file: str, log_file: str = "carpark.log", on_change=None):
        config = parse_config(config_file)
        self.name = config.get("name", "Unnamed Carpark")
        self.location = config.get("location", "Unknown Location")
        self.total_spaces = config["total-spaces"]

        # Dict keyed by license plate -> Car. Only contains cars
        # currently parked; departed cars are removed.
        self._parked_cars = {}

        self._temperature = None
        self.on_change = on_change

        self._log_file = log_file   # NEW: remember the path so we can read it back later
        self._logger = logging.getLogger(f"CarparkManager.{id(self)}")
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s"))
            self._logger.addHandler(handler)

        self._logger.info(
            f"CarparkManager started for '{self.name}' ({self.location}) "
            f"with {self.total_spaces} spaces (config: {config_file})"
        )

        # Seed starting occupancy from the config, e.g. carried over
        # from a previous run. We don't know the real plates for these
        # pre-existing cars, so we seed placeholder entries
        # ("UNKNOWN-1", "UNKNOWN-2", ...) purely to make
        # available_spaces correct from startup. These placeholders
        # are indistinguishable from a real plate to outgoing_car, so
        # if a real sensor reports one of these cars leaving, use the
        # matching UNKNOWN-n placeholder rather than its real plate.
        starting_cars = config.get("total-cars", 0)
        for i in range(starting_cars):
            placeholder_plate = f"UNKNOWN-{i + 1}"
            self._parked_cars[placeholder_plate] = Car(placeholder_plate)
        if starting_cars:
            self._logger.info(
                f"Seeded {starting_cars} pre-existing car(s) from config "
                f"total-cars (placeholder plates)"
            )

    # ---------------------------------------------------------------
    # CarparkSensorListener implementation
    # ---------------------------------------------------------------

    def incoming_car(self, license_plate):
        """Record that a car has entered the carpark.

        Raises
        ------
        CarparkFullError
            If there are no available spaces.
        DuplicateEntryError
            If this license plate is already recorded as parked.
        """
        if license_plate in self._parked_cars:
            self._logger.warning(
                f"Duplicate incoming_car for already-parked plate '{license_plate}'")
            raise DuplicateEntryError(
                f"Car '{license_plate}' is already recorded as parked.")

        if self.available_spaces <= 0:
            self._logger.warning(
                f"Rejected incoming_car for '{license_plate}': carpark full")
            raise CarparkFullError(
                f"No available spaces in '{self.location}'.")

        self._parked_cars[license_plate] = Car(license_plate)
        self._logger.info(f"Car IN: {license_plate} "
                           f"({self.available_spaces} spaces left)")
        self._notify()

    def outgoing_car(self, license_plate):
        """Record that a car has left the carpark.

        Raises
        ------
        UnrecognisedCarError
            If this license plate was not recorded as parked. This is
            the key safeguard against an unrecognised car incorrectly
            freeing up a space.
        """
        if license_plate not in self._parked_cars:
            self._logger.warning(
                f"Rejected outgoing_car for unrecognised plate '{license_plate}'")
            raise UnrecognisedCarError(
                f"Car '{license_plate}' is not recorded as parked here.")

        car = self._parked_cars.pop(license_plate)
        car.mark_departed()
        self._logger.info(f"Car OUT: {license_plate} "
                           f"({self.available_spaces} spaces left)")
        self._notify()

    def temperature_reading(self, reading):
        """Record a new temperature reading.

        Parameters
        ----------
        reading : float
            The temperature in degrees Celsius.
        """
        self._temperature = reading
        self._logger.info(f"Temperature reading: {reading}")
        self._notify()

    # ---------------------------------------------------------------
    # CarparkDataProvider implementation
    # ---------------------------------------------------------------

    @property
    def available_spaces(self):
        """int: Spaces currently free. Never negative: derived from
        total_spaces minus the count of currently-parked cars, rather
        than incremented/decremented independently, so it can't drift
        out of sync or go below zero."""
        return max(0, self.total_spaces - len(self._parked_cars))

    @property
    def temperature(self):
        """float or None: Most recent temperature reading, in Celsius.
        None if no reading has been received yet."""
        return self._temperature

    @property
    def current_time(self):
        """time.struct_time: The current local time."""
        return time.localtime()

    @property
    def parked_cars(self):
        """dict: License plate -> Car, for every car currently parked.
        Returns a copy so callers can't accidentally mutate internal state."""
        return dict(self._parked_cars)
    
    def get_activity_log(self):
        """Return every line from the log file, oldest first. Returns
        -------
        list[str]
            Each line of the log file, as a string (including the
            timestamp and message). Empty list if the log file
            doesn't exist or hasn't been written to yet.
        """
        try:
            with open(self._log_file) as f:
                return f.readlines()
        except FileNotFoundError:
            return []

    # ---------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------

    def _notify(self):
        """Call the on_change callback, if one was provided."""
        if self.on_change is not None:
            self.on_change()
