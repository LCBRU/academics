#!/usr/bin/env python3

from dotenv import load_dotenv
from academics import create_app

# Load environment variables from '.env' file.
load_dotenv()

from academics.catalogs.scival import get_scival_publication_institutions

application = create_app()
application.app_context().push()

out = get_scival_publication_institutions(scopus_id='85181250295', log_data=True)
