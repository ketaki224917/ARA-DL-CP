"""Generate and validate the three checked-in ARA example reports."""

import logging

from ara.generative.example_reports import main

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
