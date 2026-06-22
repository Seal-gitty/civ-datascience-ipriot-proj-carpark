import unittest
import json 
import sys,os
from pathlib import Path
cwd = Path(os.path.dirname(__file__))
parent = str(cwd.parent)

sys.path.append(parent + "/smartpark")


class TestConfigParsing(unittest.TestCase):
    def test_parse_config_has_correct_location_and_spaces(self):
        config_string = '''
        {
            "CarParks": [
                {
                    "name": "raf-park-international",
                    "total-spaces": 130,
                    "location": "moondalup"
                }
            ]
        }
        '''
        config = json.loads(config_string)
        parking_lot = config["CarParks"] [0]
        self.assertEqual(parking_lot['location'], "moondalup")
        self.assertEqual(parking_lot['total-spaces'], 130)

if __name__=="__main__":
    unittest.main()