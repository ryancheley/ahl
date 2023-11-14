#!/bin/bash

# get the data
/Users/ryan/Documents/testbed/ahl/venv/bin/python /Users/ryan/Documents/testbed/ahl/program.py

# publish the data
datasette publish vercel /Users/ryan/Documents/testbed/ahl/games.db --project=ahl-data