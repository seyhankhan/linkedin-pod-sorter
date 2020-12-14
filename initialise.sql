DROP TABLE IF EXISTS users;
CREATE TABLE users (
    userID serial NOT NULL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    linkedinURL TEXT NOT NULL,
    optedIn BOOLEAN NOT NULL,
    timezone TEXT NOT NULL
);

-- INSERT INTO users (username, password) VALUES ('Michelle', 'test_pw1');
-- INSERT INTO users (username, password) VALUES ('Jasmine', 'test_pw2');
