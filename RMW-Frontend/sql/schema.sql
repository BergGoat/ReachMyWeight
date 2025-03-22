-- Gebruikers tabel (voor inloggen)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

-- Profielen tabel
CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    gender TEXT NOT NULL,
    height REAL NOT NULL,
    age INTEGER NOT NULL,
    activity_level TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Gewichtsgegevens tabel
CREATE TABLE IF NOT EXISTS weights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    weight REAL NOT NULL,
    goal_weight REAL NOT NULL,
    date TEXT DEFAULT CURRENT_DATE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Eén testgebruiker
INSERT OR IGNORE INTO users (username, password) VALUES ('test', 'test123');

-- Testprofiel
INSERT OR IGNORE INTO profiles (user_id, gender, height, age, activity_level) 
VALUES (1, 'male', 180, 30, 'moderate');