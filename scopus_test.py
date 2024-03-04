#!/usr/bin/env python3

from dotenv import load_dotenv

# Load environment variables from '.env' file.
load_dotenv()

from academics.catalogs.scopus import get_scopus_publication_data

out = get_scopus_publication_data(doi='10.1186/s12872-023-03623-y')

print(out)
