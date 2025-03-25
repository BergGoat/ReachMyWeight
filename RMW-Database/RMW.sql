
    -- RMW.sql schema file
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );

    -- Profiles table
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        gender TEXT NOT NULL DEFAULT 'male',
        height REAL NOT NULL DEFAULT 170,
        age INTEGER NOT NULL DEFAULT 30,
        activity_level TEXT NOT NULL DEFAULT 'moderate',
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

    -- Weights table
    CREATE TABLE IF NOT EXISTS weights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        weight REAL NOT NULL,
        goal_weight REAL NOT NULL,
        date TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );

    -- Create a test user if none exist
    INSERT OR IGNORE INTO users (username, password) 
    VALUES ('test', 'password');

    -- Create profile for test user
    INSERT OR IGNORE INTO profiles (user_id, gender, height, age, activity_level) 
    VALUES (1, 'male', 180, 35, 'moderate');
    