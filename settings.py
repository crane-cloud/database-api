import os
from dotenv import load_dotenv

current_dir = os.path.dirname(__file__)

dotenv_path = os.path.join(current_dir, '.env')

load_dotenv(dotenv_path)
