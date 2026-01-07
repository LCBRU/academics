import warnings
from dotenv import load_dotenv

# Filter out deprecation warnings from dependencies that we have no control over
warnings.filterwarnings("ignore", module="pyasn1.codec.ber.encoder", lineno=952)

# Load environment variables from '.env' file.
load_dotenv()
