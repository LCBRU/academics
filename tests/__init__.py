import warnings
from dotenv import load_dotenv

# Filter out deprecation warnings from dependencies that we have no control over
warnings.filterwarnings("ignore", module="flask_admin.contrib", lineno=2)
warnings.filterwarnings("ignore", module="pkg_resources", lineno=2558)
warnings.filterwarnings("ignore", module="pyasn1.codec.ber.encoder", lineno=952)

# Load environment variables from '.env' file.
load_dotenv()
