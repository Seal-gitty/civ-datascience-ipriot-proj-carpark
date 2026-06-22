import unittest
import sys,os
from pathlib import Path
cwd = Path(os.path.dirname(__file__))
parent = str(cwd.parent)

sys.path.append(parent + "/smartpark")

#Change the line below to import your manager class
from carpark_manager import CarparkManager

class TestConfigParsing(unittest.TestCase):

    def test_fresh_carpark(self):
        """
        Testing how many spaces are available in total in the car park
        """
        carpark = CarparkManager("samples_and_snippets/config.json")
        # assert
        self.assertEqual(130,carpark.available_spaces)

if __name__=="__main__":
#    print("cwd: " + parent + "/smartpark")
    unittest.main()
