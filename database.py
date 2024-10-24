import sqlite3

db = sqlite3.connect("data.db")

cursor = db.cursor()

# cursor.execute("DROP TABLE IF EXISTS `users`")
cursor.execute("""CREATE TABLE IF NOT EXISTS `users` (
               `user_id` char(8) NOT NULL, 
               `username` varchar(500) DEFAULT NULL, 
               `full_name` varchar(500) DEFAULT NULL, 
               `dob` date DEFAULT NULL, 
               `email` varchar(500) NOT NULL, 
               `password_hash` text, 
               PRIMARY KEY (`user_id`))""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id char(8) NOT NULL,
    latitude REAL,
    longitude REAL,
    date_time TEXT
)
""")
# Create a table to store user matches
# cursor.execute("DROP TABLE IF EXISTS `near_luvs`")
cursor.execute("""
CREATE TABLE IF NOT EXISTS near_luvs (
    user_id char(8) NOT NULL,
    luv_id char(8) NOT NULL,
    distance REAL,
    date_time TEXT
)
""")


# cursor.execute("DROP TABLE IF EXISTS `user_luvs`")
cursor.execute("""CREATE TABLE IF NOT EXISTS `user_luvs` (
               `user_id` char(8) NOT NULL, 
               `luv_id` char(8) NOT NULL)""")