from db import get_db

with open("schema.sql", encoding="utf-8") as file:
    get_db().executescript(file.read())
