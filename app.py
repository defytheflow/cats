import os
from http import HTTPStatus

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, abort, g
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from auth import login_required
from db import get_db, close_db

load_dotenv()

app = Flask(__name__)
app.teardown_appcontext(close_db)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["UPLOAD_FOLDER"] = os.path.join("static", "photos")


@app.before_request
def load_user():
    if request.path.startswith("/static/"):
        return

    if "user_id" not in session:
        g.user = None
        return

    db = get_db()
    user = db.execute(
        "SELECT id, login FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    g.user = user


@app.route("/")
def index():
    search = request.args.get("search", "").strip()

    query = """
        SELECT
            cats.id,
            cats.name,
            breeds.name AS breed,
            photos.photo_name AS photo,
            CASE
                WHEN cats.gender = 'М' THEN 'Мужской'
                WHEN cats.gender = 'Ж' THEN 'Женский'
                ELSE ''
            END AS gender
        FROM
            cats
        INNER JOIN
            photos
        ON
            cats.id = photos.cat_id
        INNER JOIN
            breeds
        ON
            cats.breed_id = breeds.id
    """

    db = get_db()

    if search:
        cats = db.execute(
            query + " WHERE cats.name LIKE ? LIMIT 100", (f"%{search}%",)
        ).fetchall()
    else:
        cats = db.execute(query + " LIMIT 100").fetchall()

    return render_template("index.html", cats=cats, search=search)


@app.route("/register", methods=("GET", "POST"))
def register():
    if g.user is not None:
        return redirect(url_for("account"))

    errors = {}

    if request.method == "POST":
        login = request.form.get("login")
        password = request.form.get("password")
        password_confirm = request.form.get("password-confirm")

        if not login:
            errors["login"] = "Login is required"
        elif len(login) < 2:
            errors["login"] = "Login length must be at least 2 characters"

        if not password:
            errors["password"] = "Password is required"
        elif len(password) < 8:
            errors["password"] = "Password length must be at least 8 characters"

        if not password_confirm:
            errors["password_confirm"] = "Password Confirm is required"
        elif password_confirm != password:
            errors["password_confirm"] = "пароли не совпадают"

        if len(errors) == 0:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (login, password) VALUES (?, ?)",
                    (login, generate_password_hash(password)),  # type: ignore
                )
                db.commit()
            except db.IntegrityError:
                errors["login"] = "Имя пользователя уже существует"
            else:
                return redirect(url_for("index"))

    return render_template("register.html", errors=errors)


@app.route("/login", methods=("GET", "POST"))
def login():
    if g.user is not None:
        return redirect(url_for("account"))

    errors = {}

    if request.method == "POST":
        login = request.form.get("login")
        password = request.form.get("password")

        if not login:
            errors["login"] = "Login is required"

        if not password:
            errors["password"] = "Password is required"

        if len(errors) == 0:
            db = get_db()
            user = db.execute(
                "SELECT id, login, password FROM users WHERE login = ?", (login,)
            ).fetchone()

            if user is None or not check_password_hash(user["password"], password):
                errors["form"] = "Invalid Имя пользователя or Password"
            else:
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("account"))

    return render_template("login.html", errors=errors)


@app.route("/logout", methods=("POST",))
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/account")
@login_required
def account():
    db = get_db()
    cats = db.execute(
        """
            SELECT
                cats.id,
                cats.name,
                breeds.name AS breed,
                photos.photo_name AS photo,
                CASE
                    WHEN cats.gender = 'М' THEN 'Мужской'
                    WHEN cats.gender = 'Ж' THEN 'Женский'
                    ELSE ''
                END AS gender
            FROM
                cats
            INNER JOIN
                photos
            ON
                cats.id = photos.cat_id
            INNER JOIN
                breeds
            ON
                cats.breed_id = breeds.id
            WHERE
                cats.user_id = ?
        """,
        (g.user["id"],),
    ).fetchall()

    return render_template("account.html", cats=cats)


@app.route("/cats/new", methods=("GET", "POST"))
@login_required
def new_cat():
    error = ""
    db = get_db()

    if request.method == "POST":
        name = request.form.get("name")
        breed = request.form.get("breed")
        gender = request.form.get("gender")
        city = request.form.get("city")
        contact_phone = request.form.get("contact_phone")
        date_of_birth = request.form.get("date_of_birth")

        comments = request.form.get("comments")
        if (
            "" not in [name, breed, gender, city, contact_phone, date_of_birth]
            and len(contact_phone) == 10
        ):
            breed = db.execute(
                "SELECT * FROM breeds where name = ?", (breed,)
            ).fetchone()

            db.execute(
                """
                    INSERT INTO
                        cats (name, breed_id, birth_date, gender, owner_phone, user_id, city, comments)
                    VALUES
                        (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    breed["id"],
                    date_of_birth,
                    gender,
                    contact_phone,
                    g.user["id"],
                    city,
                    comments,
                ),
            )
            db.commit()

            photo = request.files["photo"]

            if photo.filename != "":
                filename = secure_filename(photo.filename)
                photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

                cat = db.execute(
                    "SELECT * FROM cats WHERE name = ? AND birth_date = ?",
                    (name, date_of_birth),
                ).fetchone()

                db.execute(
                    "INSERT INTO photos (cat_id, photo_name) VALUES (?, ?)",
                    (cat["id"], photo.filename),
                )
                db.commit()

            return redirect(url_for("account"))

        elif None in [
            name,
            breed,
            gender,
            city,
            contact_phone,
            date_of_birth,
        ] or "" in [name, breed, gender, city, contact_phone, date_of_birth]:
            error = "Все поля должны быть заполнены"
        else:
            error = "Введите номер телефона без кода страны"

    breeds = db.execute("SELECT name FROM breeds").fetchall()

    return render_template("new-cat.html", breeds=breeds, error=error)


@app.route("/cats/<int:cat_id>", methods=("GET", "POST"))
@login_required
def cat_profile(cat_id):
    db = get_db()

    cat = db.execute(
        """
        SELECT
            cats.id,
            cats.name,
            cats.birth_date,
            cats.comments AS detail,
            cats.user_id,
            cats.city,
            cats.breed_id,
            cats.owner_phone,
            breeds.name AS breed,
            photos.photo_name AS photo,
            CASE
                WHEN cats.gender = 'М' THEN 'Мужской'
                WHEN cats.gender = 'Ж' THEN 'Женский'
                ELSE ''
            END AS gender
        FROM
            cats
        INNER JOIN
            photos
        ON
            cats.id = photos.cat_id
        INNER JOIN
            breeds
        ON
            cats.breed_id = breeds.id
        WHERE
            cats.id = ?
        """,
        (cat_id,),
    ).fetchone()

    if cat is None:
        abort(HTTPStatus.NOT_FOUND)

    if cat["user_id"] != g.user["id"]:
        return render_template("cat-profile.html", cat=cat)

    liked_cats_ids = set(
        map(
            lambda x: x["liked_cat_id"],
            db.execute(
                "SELECT liked_cat_id FROM likes WHERE main_cat_id = ?", (cat["id"],)
            ).fetchall(),
        )
    )

    asked_cats_ids = set(
        map(
            lambda x: x["main_cat_id"],
            db.execute(
                "SELECT main_cat_id FROM likes WHERE liked_cat_id = ?", (cat["id"],)
            ),
        )
    )

    only_liked_ids = liked_cats_ids.difference(asked_cats_ids)
    only_asked_ids = asked_cats_ids.difference(liked_cats_ids)
    only_matched_ids = liked_cats_ids.intersection(asked_cats_ids)
    liked_and_asked_cats_ids = liked_cats_ids.union(asked_cats_ids)

    query = f"""
       SELECT
           cats.id,
           cats.name,
           cats.comments AS detail,
           cats.city,
           cats.owner_phone,
           breeds.name AS breed,
           photos.photo_name AS photo,
            CASE
                WHEN cats.gender = 'М' THEN 'Мужской'
                WHEN cats.gender = 'Ж' THEN 'Женский'
                ELSE ''
            END AS gender
       FROM
           cats
       INNER JOIN
           photos
       ON
           cats.id = photos.cat_id
       INNER JOIN
           breeds
       ON
           cats.breed_id = breeds.id
    """

    liked_cats = db.execute(
        f'{query} WHERE cats.id IN ({",".join("?" for _ in only_liked_ids)})',
        tuple(only_liked_ids),
    ).fetchall()

    asked_cats = db.execute(
        f'{query} WHERE cats.id IN ({",".join("?" for _ in only_asked_ids)})',
        tuple(only_asked_ids),
    ).fetchall()

    matched_cats = db.execute(
        f'{query} WHERE cats.id IN ({",".join("?" for _ in only_matched_ids)})',
        tuple(only_matched_ids),
    ).fetchall()

    maybe_cats = db.execute(
        f"""
          SELECT
              cats.id,
              cats.name,
              cats.comments AS detail,
              cats.city,
              breeds.name AS breed,
              photos.photo_name AS photo,
                CASE
                    WHEN cats.gender = 'М' THEN 'Мужской'
                    WHEN cats.gender = 'Ж' THEN 'Женский'
                    ELSE ''
                END AS gender
          FROM
              cats
          INNER JOIN
              photos
          ON
              cats.id = photos.cat_id
          INNER JOIN
              breeds
          ON
              cats.breed_id = breeds.id
          WHERE
              breed_id = ? AND user_id != ? AND cats.id NOT IN ({",".join("?" for _ in liked_and_asked_cats_ids)})
        """,
        (cat["breed_id"], g.user["id"], *liked_and_asked_cats_ids),
    ).fetchall()

    return render_template(
        "cat-profile.html",
        cat=cat,
        maybe_cats=maybe_cats,
        liked_cats=liked_cats,
        asked_cats=asked_cats,
        matched_cats=matched_cats,
    )


@app.route("/add_maybe/<int:cat_id>/<int:liked_cat_id>", methods=("POST",))
@login_required
def add_maybe(cat_id, liked_cat_id):
    db = get_db()
    try:
        db.execute(
            "INSERT INTO likes (main_cat_id, liked_cat_id) VALUES (?, ?)",
            (cat_id, liked_cat_id),
        )
        db.commit()
    except db.IntegrityError:
        pass
    return redirect(url_for("cat_profile", cat_id=cat_id))


@app.route("/cats/delete/<int:cat_id>", methods=("POST",))
@login_required
def delete_cat(cat_id):
    db = get_db()

    result = db.execute(
        "SELECT 1 FROM cats WHERE id = ? AND user_id = ?",
        (cat_id, g.user["id"]),
    ).fetchone()

    if result is None:
        abort(HTTPStatus.FORBIDDEN)

    db.execute(
        "DELETE from likes where main_cat_id = ? OR liked_cat_id = ?",
        (cat_id, cat_id),
    )

    photos = db.execute("SELECT * from photos WHERE cat_id = ?", (cat_id,)).fetchall()
    db.execute("DELETE FROM photos WHERE cat_id = ?", (cat_id,))

    for photo in photos:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], photo["photo_name"]))
        except FileNotFoundError:
            pass
        except PermissionError:
            pass
        except OSError:
            pass

    db.execute("DELETE FROM cats WHERE id = ?", (cat_id,))
    db.commit()

    return redirect(url_for("account"))
