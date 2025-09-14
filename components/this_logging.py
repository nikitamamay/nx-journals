
import typing

import os
import logging


LOG_FILE = os.path.join(os.path.dirname(__file__), "components.log")

logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, format="[%(asctime)s] %(levelname)s:%(name)s: %(message)s")

getLogger = logging.getLogger


logger = logging.getLogger()
