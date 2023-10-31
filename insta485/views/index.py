"""
Insta485 index (main) view.

URLs include:
/
"""
import pathlib
import uuid
import hashlib
import arrow
import flask
import insta485
import insta485.config


@insta485.app.route('/')
def show_index():
    """Display / route."""
    # flask.session.clear()
    if 'username' not in flask.session:
        # Redirect to the login page
        return flask.redirect('/accounts/login/')
    user = flask.session['username']
    [users, posts, likes, comments, liked_ids, following] = get_data(user)
    # perform operations on posts
    posts_setup(posts)
    modify_posts(posts, likes, comments, users, following)
    # Add database info to context and render template
    context = {"posts": posts, "logname": user, "liked_posts": liked_ids}
    return flask.render_template("index.html", **context)


def get_data(user):
    """Get data for the posts."""
    # Connect to database
    connection = insta485.model.get_db()
    # pull data from sql database
    user_cur = connection.execute(
        "SELECT username, filename "
        "FROM users "
        # "WHERE username = ?,",(user,)
    )
    users = user_cur.fetchall()
    post_cur = connection.execute(
        "SELECT postid, filename, owner, created "
        "FROM posts "
    )
    posts = post_cur.fetchall()
    following = connection.execute(
        "SELECT username2 "
        "FROM following "
        "WHERE username1 = ? ", (user, )
    )
    following = following.fetchall()

    like_cur = connection.execute(
        "SELECT postid, owner FROM likes "
    )
    likes = like_cur.fetchall()
    comment_cur = connection.execute(
        "SELECT postid, owner, text, commentid FROM comments "
    )
    comments = comment_cur.fetchall()
    # get posts that the current user has liked
    liked = connection.execute(
        "SELECT postid FROM likes WHERE owner = ?", (user,)
    )
    liked_posts = liked.fetchall()
    liked_ids = []
    for liked in liked_posts:
        liked_ids.append(liked["postid"])
    # sort data
    comments = sorted(comments, key=lambda comment: comment["commentid"])
    posts = sorted(posts, key=lambda post: post["postid"], reverse=True)
    return [users, posts, likes, comments, liked_ids, following]


def posts_setup(posts):
    """Get the posts for html."""
    for post in posts:
        # initialize dictionary entries
        post["likes"] = 0
        post["comments"] = []
        post["display"] = 0
        # fix time formatting
        post_time = arrow.get(post["created"])
        post["created"] = post_time.humanize()
    return posts


def modify_posts(posts, likes, comments, users, following):
    """Modify the posts so they display correctly."""
    # Tag which posts the logname doesn't follow
    for post in posts:
        for follow in following:
            # if follow["username2"] in [post["owner"], :
            #     post["display"] = 1
            #     break
            user = flask.session['username']
            follow = follow["username2"]
            if post["owner"] in [user, follow]:
                post["display"] = 1
                break
    # iterate through likes and for each like
    # increment the likes dictonary value for the
    # post with the same postid
    for like in likes:
        for post in posts:
            if post["postid"] == like["postid"]:
                post["likes"] += 1
                break
    # iterate through comments and add them to posts
    for comment in comments:
        for post in posts:
            if post["postid"] == comment["postid"]:
                post["comments"].append(comment)
                break
    # iterate through users profile pictures and add them to posts
    for user in users:
        for post in posts:
            if post["owner"] == user["username"]:
                post["profile_picture"] = user["filename"]


@insta485.app.route('/uploads/<filename>')
def get_file(filename):
    """Return the file to the specified html page."""
    # abort if no logged in user
    if "username" not in flask.session.keys():
        flask.abort(403)
    return flask.send_from_directory(insta485.config.UPLOAD_FOLDER, filename)


@insta485.app.route('/likes/', methods=['POST'])
def update_likes():
    """Like and unlike buttons."""
    if flask.request.form.get("operation") == "like":
        # insert user's like into database
        connection = insta485.model.get_db()
        # check to see if the post is already likes
        like_check = connection.execute(
            "SELECT owner "
            "FROM likes "
            "WHERE owner = ? AND postid = ? ",
            (flask.session["username"], flask.request.form["postid"])
        )
        like_check = like_check.fetchall()
        if len(like_check) != 0:
            flask.abort(409)
        connection.execute(
            "INSERT INTO likes "
            "(owner, postid) "
            "VALUES (?,?)",
            (flask.session["username"], flask.request.form["postid"])
        )
    elif flask.request.form.get("operation") == "unlike":
        # insert user's like into database
        connection = insta485.model.get_db()
        # check to see if the post has a like
        like_check = connection.execute(
            "SELECT owner "
            "FROM likes "
            "WHERE owner = ? AND postid = ? ",
            (flask.session["username"], flask.request.form["postid"])
        )
        like_check = like_check.fetchall()
        if len(like_check) == 0:
            flask.abort(409)
        connection.execute(
            "DELETE FROM likes "
            "WHERE owner = ? AND postid = ?",
            (flask.session["username"], flask.request.form["postid"])
        )
    target = flask.request.args.get("target")
    return flask.redirect(target)


@insta485.app.route('/comments/', methods=['POST'])
def update_comments():
    """Delete and create comments."""
    if flask.request.form.get("operation") == "create":
        # trying to create an empty comment
        if flask.request.form["text"] == "":
            flask.abort(400)
        connection = insta485.model.get_db()
        connection.execute(
            "INSERT INTO comments "
            "(owner, postid, text) "
            "VALUES (?,?,?)",
            (flask.session["username"],
                flask.request.form["postid"], flask.request.form["text"], )
        )
    elif flask.request.form.get("operation") == "delete":
        connection = insta485.model.get_db()
        # check to make sure the logged in user owns the comment
        comment_cur = connection.execute(
            "SELECT owner FROM comments WHERE commentid = ?",
            (flask.request.form["commentid"],)
        )
        owner = comment_cur.fetchall()
        if owner[0]["owner"] != flask.session["username"]:
            flask.abort(403)
        connection.execute(
            "DELETE FROM comments WHERE commentid = ?",
            (flask.request.form["commentid"], )
        )
    target = flask.request.args.get("target")
    if target:
        return flask.redirect(target)
    return flask.redirect("/")


# Setting secret key from config.py
insta485.app.secret_key = insta485.config.SECRET_KEY


@insta485.app.route('/accounts/login/', methods=['GET'])
def handle_login():
    """Display the login page."""
    # If the user is logged in, redirect to index page
    if 'username' in flask.session:
        return flask.redirect("/")
    # Redirect to the login page
    return flask.render_template("login.html")


@insta485.app.route("/accounts/create/", methods=["GET"])
def show_create():
    """Display the login page."""
    # if user is already loggin in, redirect to /accounts/edit/
    if flask.request.method == "GET":
        return flask.render_template("create.html")
    # make sure all fields are filled in (file does this automatically)
    if flask.request.files["password"] == '':
        flask.abort(400)
    if flask.request.files["fullname"] == '':
        flask.abort(400)
    if flask.request.files["username"] == '':
        flask.abort(400)
    if flask.request.files["email"] == '':
        flask.abort(400)
    # hash password
    salt = uuid.uuid4().hex
    hash_obj = hashlib.new('sha512')
    password_salted = salt + flask.request.files["password"]
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join(['sha512', salt, password_hash])
    # check if username already exists
    connection = insta485.model.get_db()
    user_cur = connection.execute(
        "SELECT username FROM users"
    )
    users = user_cur.fetchall()
    for user in users:
        if user["username"] == flask.request.files["username"]:
            flask.abort(400)
    # change filename to UUID filename
    stem = uuid.uuid4().hex
    suffix = pathlib.Path(flask.request.files["file"].filename).suffix.lower()
    uuid_basename = f"{stem}{suffix}"
    # save file to disk
    path = insta485.config.UPLOAD_FOLDER/uuid_basename
    flask.request.files["file"].save(path)
    # insert user into database
    user_cur = connection.execute(
        "INSERT INTO users "
        "(filename, fullname, username, email, password) "
        "VALUES (?,?,?,?,?)",
        (uuid_basename, flask.request.files["fullname"],
            flask.request.files["username"], flask.request.files["email"],
            password_db_string, )
    )
    # update session
    flask.session["username"] = flask.request.files["username"]
    return flask.redirect(flask.request.args.get("target"))


@insta485.app.route("/users/<user>/", methods=["GET"])
def show_users(user):
    """Display the userts page."""
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for("handle_login"))
    # Connect to database
    connection = insta485.model.get_db()
    # pull data from sql database
    user_cur = connection.execute(
        "SELECT fullname "
        "FROM users "
        "WHERE username = ? ", (user, )
    )
    fullname = user_cur.fetchall()
    if len(fullname) == 0:
        flask.abort(404)
    posts_cur = connection.execute(
        "SELECT postid, filename "
        "FROM posts "
        "WHERE owner = ? ", (user, )
    )
    posts = posts_cur.fetchall()
    follow_cur = connection.execute(
        "SELECT username1 "
        "FROM following "
        "WHERE username2 = ? ", (user, )
    )
    followers = follow_cur.fetchall()
    follow_cur = connection.execute(
        "SELECT username2 "
        "FROM following "
        "WHERE username1 = ? ", (user, )
    )
    following = follow_cur.fetchall()
    context = {"followers": followers}
    context["following"] = following
    context["posts"] = posts
    context["logname"] = flask.session['username']
    context["user"] = user
    context["fullname"] = fullname
    return flask.render_template("users.html", **context)


@insta485.app.route("/users/<user>/followers/", methods=["GET"])
def show_followers(user):
    """Display the users followers."""
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for("handle_login"))
    connection = insta485.model.get_db()
    user_cur = connection.execute(
        "SELECT username "
        "FROM users "
    )
    users = user_cur.fetchall()
    found = False
    for person in users:
        if person["username"] == user:
            found = True
            break
    if found is not True:
        flask.abort(404)
    # Connect to database
    connection = insta485.model.get_db()
    follow_cur = connection.execute(
        "SELECT username, filename "
        "FROM following JOIN users ON (users.username = following.username1) "
        "WHERE username2 = ? ", (user, )
    )
    followers = follow_cur.fetchall()
    follow_cur = connection.execute(
        "SELECT username2 "
        "FROM following "
        "WHERE username1 = ? ", (flask.session['username'], )
    )
    who_logname_follows = follow_cur.fetchall()

    for follow in followers:
        for target in who_logname_follows:
            if follow["username"] == target["username2"]:
                follow["following"] = 1
                break
            follow["following"] = 0
    context = {"followers": followers}
    context["logname"] = flask.session['username']
    context["user"] = user
    return flask.render_template("followers.html", **context)


@insta485.app.route("/posts/<postid_url_slug>/", methods=["GET"])
def show_post(postid_url_slug):
    """Display the specified post."""
    connection = insta485.model.get_db()
    post_cur = connection.execute(
        "SELECT * FROM posts WHERE postid = ?",
        (postid_url_slug, )
    )
    post = post_cur.fetchall()
    if len(post) == 0:
        return flask.redirect("/accounts/login/")
    # fix time formatting
    post_time = arrow.get(post[0]["created"])
    post[0]["created"] = post_time.humanize()
    user_cur = connection.execute(
        "SELECT * FROM users WHERE username = ?",
        (post[0]["owner"], )
    )
    user = user_cur.fetchall()
    likes_cur = connection.execute(
        "select * FROM likes WHERE postid = ?",
        (postid_url_slug, )
    )
    likes = likes_cur.fetchall()
    comments_cur = connection.execute(
        "select * FROM comments WHERE postid = ?",
        (postid_url_slug, )
    )
    comments = comments_cur.fetchall()
    # get posts that the current user has liked
    liked = connection.execute(
        "select * FROM likes WHERE owner = ? AND postid = ?",
        (flask.session['username'], postid_url_slug,)
    )
    liked_post = liked.fetchall()
    context = {
        "logname": flask.session['username'],
        "post": post[0],
        "user": user[0],
        "likes": likes,
        "comments": comments,
        "liked_post": liked_post
    }
    return flask.render_template("post.html", **context)


@insta485.app.route("/users/<user>/following/", methods=["GET"])
def show_following(user):
    """Display who the user is following."""
    if 'username' not in flask.session:
        return flask.redirect(flask.url_for("handle_login"))
    # Connect to database
    connection = insta485.model.get_db()
    user_cur = connection.execute(
        "SELECT username "
        "FROM users "
    )
    users = user_cur.fetchall()
    found = False
    for person in users:
        if person["username"] == user:
            found = True
            break
    if found is not True:
        flask.abort(404)
    follow_cur = connection.execute(
        "SELECT username, filename "
        "FROM following JOIN users ON (users.username = following.username2) "
        "WHERE username1 = ? ", (user, )
    )
    following = follow_cur.fetchall()
    follow_cur = connection.execute(
        "SELECT username2 "
        "FROM following "
        "WHERE username1 = ? ", (flask.session['username'], )
    )
    who_logname_follows = follow_cur.fetchall()
    for follow in following:
        for target in who_logname_follows:
            if follow["username"] == target["username2"]:
                follow["following"] = 1
                break
            follow["following"] = 0
    context = {"following": following}
    context["logname"] = flask.session['username']
    context["user"] = user
    return flask.render_template("following.html", **context)


@insta485.app.route("/accounts/edit/", methods=["GET"])
def edit_account():
    """Display the edit account page."""
    logname = flask.session['username']
    # Connect to database
    connection = insta485.model.get_db()
    user_cur = connection.execute(
        "SELECT username, fullname, email, filename "
        "FROM users "
        "WHERE username = ? ", (logname, )
    )
    user = user_cur.fetchall()
    context = {"user": user}
    context["logname"] = logname
    return flask.render_template("edit.html", **context)


@insta485.app.route("/accounts/password/", methods=["GET"])
def change_password():
    """Display the change password page."""
    context = {"logname": flask.session['username']}
    return flask.render_template("password.html", **context)


@insta485.app.route("/accounts/delete/", methods=["GET"])
def account_delete():
    """Display the account delete page."""
    context = {"logname": flask.session['username']}
    return flask.render_template("account-delete.html", **context)


@insta485.app.route("/explore/", methods=["GET"])
def show_explore():
    """Display the explore page."""
    logname = flask.session['username']
    # Connect to database
    connection = insta485.model.get_db()
    follow_cur = connection.execute(
        "SELECT DISTINCT users.username "
        "FROM following JOIN users ON (users.username = following.username2) "
        "WHERE username1 = ? ", (logname, )
    )
    logname_follows = follow_cur.fetchall()
    user_cur = connection.execute(
        "SELECT username, filename "
        "FROM users "
        "WHERE username != ?", (logname, )
    )
    users = user_cur.fetchall()
    for person in users:
        person["logname_follows"] = 0
        for target in logname_follows:
            if person["username"] == target["username"]:
                person["logname_follows"] = 1
                break

    context = {"users": users}
    context["logname"] = logname
    return flask.render_template("explore.html", **context)


@insta485.app.route('/posts/', methods=['POST'])
def update_posts():
    """Create or delete posts."""
    if flask.request.form.get("operation") == "create":
        # Unpack flask object
        fileobj = flask.request.files["file"]
        filename = fileobj.filename
        # Abort(400) if the file is empty
        if not fileobj:
            flask.abort(400)

        stem = uuid.uuid4().hex
        suffix = pathlib.Path(filename).suffix.lower()
        uuid_basename = f"{stem}{suffix}"
        # Save to disk
        path = insta485.app.config["UPLOAD_FOLDER"]/uuid_basename
        fileobj.save(path)
        # Connect to database
        connection = insta485.model.get_db()
        # Insert post into database
        connection.execute(
            "INSERT INTO posts "
            "(filename, owner) "
            "VALUES (?,?)",
            (uuid_basename, flask.session["username"],)
        )

        # redirect to target URL
        target = flask.request.args.get("target")
        if target is not None:
            return flask.redirect(target)

    elif flask.request.form.get("operation") == "delete":
        # Get postid
        post_id = flask.request.form.get("postid")

        # Connect to database
        connection = insta485.model.get_db()

        # Get the filename
        file_cur = connection.execute(
            "SELECT filename, owner "
            "from posts "
            "WHERE postid = ?", (post_id, )
        )
        file = file_cur.fetchall()

        # Check that they aren't deleting a post they don't own
        if file[0]["owner"] != flask.session['username']:
            flask.abort(403)

        # Delete the file using pathlib:
        # https://www.jquery-az.com/python-delete-file-directory-os-pathlib-shutil/
        pathobj = insta485.app.config["UPLOAD_FOLDER"] / file[0]["filename"]
        pathlib.Path(pathobj).unlink()

        # Delete from posts table in database
        connection.execute(
            "DELETE FROM posts "
            "WHERE postid = ?", (post_id, )
        )

        # Delete from comments table in database
        connection.execute(
            "DELETE FROM comments "
            "WHERE postid = ?", (post_id, )
        )

        # Delete from likes table in database
        connection.execute(
            "DELETE FROM likes "
            "WHERE postid = ?", (post_id, )
        )

        # redirect to target URL
        target = flask.request.args.get("target")
        if target is not None:
            return flask.redirect(target)

    return flask.redirect(
        flask.url_for("show_users", user=flask.session['username']))


@insta485.app.route('/following/', methods=['POST'])
def handle_follow():
    """Follow and unfollow people."""
    if flask.request.form.get("operation") == "follow":

        want_to_follow = flask.request.form.get("username")

        # insert user's follow into database
        connection = insta485.model.get_db()

        # check to see logname already follows want_to_follow
        follow_cur = connection.execute(
            "SELECT username2 "
            "FROM following "
            "WHERE username1 = ? ", (flask.session["username"], )
        )
        following = follow_cur.fetchall()

        for person in following:
            if person["username2"] == want_to_follow:
                flask.abort(409)

        # Insert the new follow relationship into the database
        connection.execute(
            "INSERT INTO following "
            "(username1, username2) "
            "VALUES (?,?)",
            (flask.session["username"],
                flask.request.form["username"])
        )

    elif flask.request.form.get("operation") == "unfollow":
        want_to_unfollow = flask.request.form.get("username")

        # insert user's follow into database
        connection = insta485.model.get_db()

        # check to see logname already follows want_to_follow
        follow_cur = connection.execute(
            "SELECT username2 "
            "FROM following "
            "WHERE username1 = ? ", (flask.session["username"], )
        )
        following = follow_cur.fetchall()

        logname_follows = False

        for person in following:
            if person["username2"] == want_to_unfollow:
                logname_follows = True

        # Check to see if they are trying
        # to unfollow someone they are already unfollowing
        if logname_follows is False:
            flask.abort(409)

        # Delete from following table in database
        connection.execute(
            "DELETE FROM following "
            "WHERE username1 = ? and username2 = ? ",
            (flask.session["username"], want_to_unfollow, )
        )

    # redirect to target URL
    target = flask.request.args.get("target")
    if target is not None:
        return flask.redirect(target)
    return flask.redirect("/")


@insta485.app.route("/accounts/", methods=["POST"])
def handle_account():
    """Create and delete and modify the account."""
    if flask.request.form.get("operation") == "login":
        account_login()
        if flask.request.args.get("target") is not None:
            return flask.redirect(flask.request.args.get("target"))

    elif flask.request.form.get("operation") == "create":

        account_create()
        if flask.request.args.get("target") is not None:
            return flask.redirect(flask.request.args.get("target"))

    elif flask.request.form.get("operation") == "delete":

        delete_account()
        if flask.request.args.get("target") is not None:
            return flask.redirect(flask.request.args.get("target"))

    elif flask.request.form.get("operation") == "edit_account":

        account_edit()
        if flask.request.args.get("target") is not None:
            return flask.redirect(flask.request.args.get("target"))

    elif flask.request.form.get("operation") == "update_password":

        account_update_password()
        if flask.request.args.get("target") is not None:
            return flask.redirect(flask.request.args.get("target"))

    return flask.redirect('/')


def account_update_password():
    """Handle updating the password."""
    # user not logged in
    if 'username' not in flask.session:
        flask.abort(403)

    if flask.request.form["password"] == "":
        flask.abort(400)
    if flask.request.form["new_password1"] == "":
        flask.abort(400)
    if flask.request.form["new_password2"] == "":
        flask.abort(400)

    pycode_temp1 = flask.request.form["new_password1"]
    pycode_temp2 = flask.request.form["new_password2"]

    # Verify that both of the passwords are the same
    if pycode_temp1 != pycode_temp2:
        flask.abort(401)

    # Get old password from db
    # DB connection
    connection = insta485.model.get_db()

    password = connection.execute(
        "SELECT password "
        "from users "
        "WHERE username = ? ", (flask.session['username'], )
    )
    password_cur = password.fetchall()

    password_cur = password_cur[0]["password"].split('$')

    password_cur_hash = password_cur[2]

    # Hash input password to check against
    algorithm = 'sha512'
    salt = password_cur[1]
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + flask.request.form["password"]
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, salt, password_hash])

    if password_hash != password_cur_hash:
        flask.abort(403)

    # To encrypt new password (password1/2)
    algorithm = 'sha512'
    salt = uuid.uuid4().hex
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + flask.request.form["new_password1"]
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, salt, password_hash])

    connection.execute(
        "UPDATE users "
        "SET password = ? "
        "WHERE username = ? ",
        (password_db_string, flask.session['username'], )
    )


def account_edit():
    """Handle editing the account information."""
    # user not logged in
    if 'username' not in flask.session:
        flask.abort(403)

    # abort if fullname or email isn't filled in
    if flask.request.form.get("fullname") == "":
        flask.abort(400)
    if flask.request.form.get("email") == "":
        flask.abort(400)

    # DB connection
    connection = insta485.model.get_db()

    # Update fullname and email
    connection.execute(
        "UPDATE users "
        "SET fullname = ?, email = ? "
        "WHERE username = ? ",
        (flask.request.form.get("fullname"),
            flask.request.form.get("email"),
            flask.session["username"],)
    )

    # Unpack flask object for profile picture
    fileobj = flask.request.files["file"]
    filename = fileobj.filename

    # Update the profile pic file
    if filename != "":

        # Get the filename
        file_cur = connection.execute(
            "SELECT filename "
            "from users "
            "WHERE username = ?", (flask.session['username'], )
        )
        file = file_cur.fetchall()

        # os.remove
        # Delete the file using pathlib:
        # https://www.jquery-az.com/python-delete-file-directory-os-pathlib-shutil/
        file = file[0]["filename"]
        pathobj = insta485.app.config["UPLOAD_FOLDER"] / file
        pathlib.Path(pathobj).unlink()

        # Compute base name (filename without directory).
        # We use a UUID to avoid
        # clashes with existing files, and ensure
        # that the name is compatible with the
        # filesystem. For best practive,
        # we ensure uniform file extensions (e.g.
        # lowercase).
        stem = uuid.uuid4().hex
        suffix = pathlib.Path(filename).suffix.lower()
        uuid_basename = f"{stem}{suffix}"

        # Save to disk
        path = insta485.app.config["UPLOAD_FOLDER"]/uuid_basename
        fileobj.save(path)
        # Update file
        connection.execute(
            "UPDATE users "
            "SET filename = ? "
            "WHERE username = ?",
            (uuid_basename, flask.session['username'], )
        )


def delete_account():
    """Delete everything about the account."""
    # user not logged in
    if 'username' not in flask.session:
        flask.abort(403)
    # Delete everything related to the user in db
    connection = insta485.model.get_db()
    # Get and delete profile pic
    delete_pfp = connection.execute(
        "SELECT filename "
        "FROM users "
        "WHERE username = ?",
        (flask.session["username"],)
    )
    delete_pfp = delete_pfp.fetchall()
    # Delete the file using pathlib:
    # https://www.jquery-az.com/python-delete-file-directory-os-pathlib-shutil/
    obj = insta485.app.config["UPLOAD_FOLDER"] / delete_pfp[0]["filename"]
    pathlib.Path(obj).unlink()
    # Get and delete posts' filenames
    delete_post = connection.execute(
        "SELECT filename "
        "FROM posts "
        "WHERE owner = ? ",
        (flask.session["username"],)
    )
    delete_post = delete_post.fetchall()
    for post in delete_post:
        # Delete the file using pathlib:
        # https://www.jquery-az.com/python-delete-file-directory-os-pathlib-shutil/
        pathobj = insta485.app.config["UPLOAD_FOLDER"] / post["filename"]
        pathlib.Path(pathobj).unlink()

    connection.execute(
        "DELETE FROM users "
        "WHERE username = ?",
        (flask.session["username"],)
    )

    # clear users session
    flask.session.clear()


def account_create():
    """Create a new account in the system."""
    # Error check to see if any of the fields are empty
    if flask.request.form.get("username") == "":
        flask.abort(400)
    if flask.request.form.get("fullname") == "":
        flask.abort(400)
    if flask.request.form.get("email") == "":
        flask.abort(400)
    if flask.request.form.get("password") == "":
        flask.abort(400)

    # Unpack flask object for profile picture
    fileobj = flask.request.files["file"]
    filename = fileobj.filename
    if not fileobj:
        flask.abort(400)

    # To encrypt password
    algorithm = 'sha512'
    salt = uuid.uuid4().hex
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + flask.request.form['password']
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, salt, password_hash])

    # Connect to database
    connection = insta485.model.get_db()

    # Unpacked flask object couple lines above

    # Compute base name (filename without directory).
    # We use a UUID to avoid
    # clashes with existing files,
    # and ensure that the name is compatible with the
    # filesystem. For best practive,
    # we ensure uniform file extensions (e.g.
    # lowercase).
    stem = uuid.uuid4().hex
    suffix = pathlib.Path(filename).suffix.lower()
    uuid_basename = f"{stem}{suffix}"
    # Save to disk
    path = insta485.app.config["UPLOAD_FOLDER"]/uuid_basename
    fileobj.save(path)
    # check to see if a username like that already exists in db
    user_check = connection.execute(
        "SELECT username "
        "FROM users "
        "WHERE username = ? ", (flask.request.form.get("username"), )
    )
    user_check = user_check.fetchall()
    if len(user_check) != 0:
        flask.abort(409)
    # add the new user to the database
    connection.execute(
        "INSERT INTO users "
        "(username, fullname, email, filename, password) "
        "VALUES (?, ?, ?, ?, ?)",
        (flask.request.form.get("username"),
            flask.request.form.get("fullname"),
            flask.request.form.get("email"),
            uuid_basename, password_db_string, )
    )
    # Log the user in
    flask.session['username'] = flask.request.form['username']
    # Store password in cookie
    return 1


def account_login():
    """Login a new account."""
    # Username or password field is empty
    if flask.request.form.get("username") == "":
        flask.abort(400)
    if flask.request.form.get("password") == "":
        flask.abort(400)
    # Connect to database
    connection = insta485.model.get_db()
    # Grab the password thats already in there to get the salt
    password_cur = connection.execute(
        "SELECT password "
        "FROM users "
        "WHERE username = ? ", (flask.request.form['username'], )
    )
    password_cur_db = password_cur.fetchall()
    if len(password_cur_db) == 0:
        flask.abort(403)
    # Generate the encrypted password to check in database
    password_cur = password_cur_db[0]["password"].split('$')
    # Hash input password to check against
    algorithm = 'sha512'
    salt = password_cur[1]
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + flask.request.form["password"]
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, salt, password_hash])
    user_check = connection.execute(
        "SELECT username, password "
        "FROM users "
        "WHERE username = ? and password = ?",
        (flask.request.form['username'], password_db_string, )
    )
    user_check = user_check.fetchall()
    if len(user_check) != 0:
        flask.session['username'] = flask.request.form['username']
        # Don't store the password in a session, need to encrypt it
        # flask.session['password'] = flask.request.form['password']
        return
    # Abort if the username/password authentification fails
    flask.abort(403)


@insta485.app.route("/accounts/logout/", methods=["POST"])
def handle_logout():
    """Logout the user."""
    flask.session.clear()
    return flask.redirect("/accounts/login/")
