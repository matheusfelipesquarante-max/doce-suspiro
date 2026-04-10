import os
import sys

class Config:
    SECRET_KEY = "LAMBARY_SECRET_2026"

    if getattr(sys, 'frozen', False):
        BASE_DIR = sys._MEIPASS
    else:
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    DATABASE_PATH = os.path.join(BASE_DIR, "database.db")

    DEBUG = False