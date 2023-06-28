DROP TABLE IF EXISTS breeds;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS cats;
DROP TABLE IF EXISTS likes;
DROP TABLE IF EXISTS photos;

CREATE TABLE breeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    login TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

CREATE TABLE cats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    breed_id INTEGER NOT NULL,
    gender TEXT NOT NULL CHECK(gender IN ('М', 'Ж')),
    birth_date TEXT NOT NULL,
    owner_phone TEXT NOT NULL CHECK(LENGTH(owner_phone) = 10),
    city TEXT NOT NULL,
    published_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    comments TEXT,
    FOREIGN KEY(breed_id) REFERENCES breeds(id),
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE likes (
    main_cat_id INTEGER NOT NULL,
    liked_cat_id INTEGER NOT NULL,
    FOREIGN KEY(main_cat_id) REFERENCES cats(id),
    FOREIGN KEY(liked_cat_id) REFERENCES cats(id),
    PRIMARY KEY(main_cat_id, liked_cat_id)
);

CREATE TABLE photos (
    cat_id INTEGER NOT NULL,
    photo_name TEXT NOT NULL
);

INSERT INTO breeds (id, name) VALUES (
  (1, 'Сиамская'),
  (2, 'Мейн-кун'),
  (3, 'Британская короткошерстная'),
  (4, 'Сфинкс'),
  (5, 'Русская голубая'),
  (6, 'Бенгальская кошка'),
  (7, 'Скоттиш фолд'),
  (8, 'Персидская'),
  (9, 'Норвежская лесная '),
  (10, 'Рагдолл')
);
