import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log environment info
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Directory contents: {os.listdir('.')}")
logger.info(f"Python path: {sys.path}")

# Add the current directory to the Python path if it's not already there
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    logger.info(f"Added {current_dir} to Python path")

# Import the Flask application
try:
    from app import app as application
    logger.info("Successfully imported Flask application")
except ImportError as e:
    logger.error(f"Failed to import app: {str(e)}")
    # Try alternate import method
    try:
        sys.path.insert(0, os.getcwd())
        from app import app as application
        logger.info("Successfully imported Flask application using alternate method")
    except ImportError as e:
        logger.error(f"Failed to import app again: {str(e)}")
        raise

# Display useful debug information
logger.info(f"Application routes: {[rule.rule for rule in application.url_map.iter_rules()]}")

if __name__ == "__main__":
    application.run()
