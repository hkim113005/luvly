import sqlite3

db = sqlite3.connect("data.db")

cursor = db.cursor()

cursor.execute("DROP TABLE IF EXISTS `users`")
cursor.execute("""CREATE TABLE `users` (
               `user_id` char(8) NOT NULL, 
               `username` varchar(500) DEFAULT NULL, 
               `full_name` varchar(500) DEFAULT NULL, 
               `dob` date DEFAULT NULL, 
               `email` varchar(500) NOT NULL, 
               `password_hash` text, 
               PRIMARY KEY (`user_id`))""")