-- ReachMYWeight Database Frontend
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

-- Gewichtsgegevens tabel
CREATE TABLE weights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    weight REAL NOT NULL,
    goal_weight REAL NOT NULL,
    date TEXT DEFAULT CURRENT_DATE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Eén testgebruiker
INSERT INTO users (username, password) VALUES ('test', 'test123');