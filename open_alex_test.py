#!/usr/bin/env python3

from dotenv import load_dotenv

# Load environment variables from '.env' file.
load_dotenv()

from academics.catalogs.open_alex import get_open_alex


get_open_alex()

