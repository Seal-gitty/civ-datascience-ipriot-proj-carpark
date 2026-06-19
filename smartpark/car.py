"""Defines the Car class, used by CarparkManager to track vehicles
currently parked in the carpark.
"""
import time


class Car:
    """Represents a single vehicle's stay in the carpark.

    Attributes
    ----------
    license_plate : str
        The unique identifier for this vehicle.
    entry_time : time.struct_time
        The local time the car entered the carpark.
    exit_time : time.struct_time or None
        The local time the car left the carpark. None while the car
        is still parked.
    """

    def __init__(self, license_plate: str):
        """Create a new Car record at the moment it enters the carpark.

        Parameters
        ----------
        license_plate : str
            The license plate identifying this car. Used as the unique
            key for tracking the car while it is parked.
        """
        self.license_plate = license_plate
        self.entry_time = time.localtime()
        self.exit_time = None

    def mark_departed(self):
        """Record the current time as this car's exit time.

        Should be called exactly once, when the car leaves the carpark.
        """
        self.exit_time = time.localtime()

    @property
    def duration_seconds(self):
        """Return how long the car has been parked, in seconds.

        If the car has already left, this is the total length of stay.
        If the car is still parked, this is the time elapsed so far.

        Returns
        -------
        float
            The number of seconds between entry and exit (or now,
            if the car hasn't left yet).
        """
        end = self.exit_time if self.exit_time is not None else time.localtime()
        return time.mktime(end) - time.mktime(self.entry_time)

    def __repr__(self):
        status = "parked" if self.exit_time is None else "departed"
        return f"Car({self.license_plate!r}, {status})"