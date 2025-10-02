import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

DEBUG_MODE = os.getenv("DEBUG_MODE")

SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
