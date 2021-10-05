#!/usr/bin/env python
from dotenv import load_dotenv

# Load environment variables from '.env' file.
load_dotenv()

from migrate.versioning.shell import main
from academics.config import BaseConfig

if __name__ == "__main__":
    main(repository="migrations", url=BaseConfig.SQLALCHEMY_DATABASE_URI, debug="True")
