#!/usr/bin/env python3

from dotenv import load_dotenv

# Load environment variables from '.env' file.
load_dotenv()

from academics import create_app

application = create_app()

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=8000)
