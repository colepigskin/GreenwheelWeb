"""REST API for posts."""
import flask
import insta485


def authenticate_user():
    """Get logname from either cookies or http auth."""
    logname = ""
    if "username" in flask.session:
        logname = flask.session["username"]
    elif flask.request.authorization is None:
        # no user logged in through cookies or HTTP auth
        flask.abort(403)
    elif 'username' in flask.request.authorization:
        logname = flask.request.authorization['username']
    else:
        flask.abort(403)
    return logname


@insta485.app.route('/api/v1/posts/<int:postid_url_slug>/')
def get_post(postid_url_slug):
    """Return post on postid.

    Example:
    {
      "created": "2017-09-28 04:33:28",
      "imgUrl": "/uploads/122a7d27ca1d7420a1072f695d9290fad4501a41.jpg",
      "owner": "awdeorio",
      "ownerImgUrl": "/uploads/e1a7c5c32973862ee15173b0259e3efdb6a391af.jpg",
      "ownerShowUrl": "/users/awdeorio/",
      "postShowUrl": "/posts/1/",
      "url": "/api/v1/posts/1/"
    }
    """
    # Connect to database
    logname = authenticate_user()
    connection = insta485.model.get_db()

    # Get post info
    post_info = connection.execute(
        "SELECT owner, filename, created "
        "FROM posts "
        "WHERE postid = ? ", (postid_url_slug, )
    )
    post_info = post_info.fetchall()

    # check if postid exists
    if len(post_info) == 0:
        flask.abort(404)

    # Get owner info
    owner_info = connection.execute(
        "SELECT filename "
        "FROM users "
        "WHERE username = ? ", (post_info[0]["owner"], )
    )
    owner_info = owner_info.fetchall()

    # Get comments info
    comments_info = connection.execute(
        "SELECT commentid, owner, text "
        "FROM comments "
        "WHERE postid = ? ", (postid_url_slug, )
    )
    comments_info = comments_info.fetchall()

    comments = []

    for comment in comments_info:
        logname_owns_this = False
        if comment["owner"] == logname:
            logname_owns_this = True
        comment_obj = {
            "commentid": comment["commentid"],
            "lognameOwnsThis": logname_owns_this,
            "owner": comment["owner"],
            "ownerShowUrl": f"/users/{comment['owner']}/",
            "text": comment["text"],
            "url": f"/api/v1/comments/{comment['commentid']}/"
        }
        comments.append(comment_obj)

    # Get likes info
    likes_info = connection.execute(
        "SELECT likeid, owner "
        "FROM likes "
        "WHERE postid = ? ", (postid_url_slug, )
    )
    likes_info = likes_info.fetchall()

    likes = {}
    logname_likes_this = False
    logname_postid = 0
    for like in likes_info:
        if like["owner"] == post_info[0]["owner"]:
            logname_likes_this = True
            logname_postid = like["likeid"]
    if logname_likes_this is True:
        likes = {
            "lognameLikesThis": logname_likes_this,
            "numLikes": len(likes_info),
            "url": f"/api/v1/likes/{logname_postid}/"
        }
    else:
        likes = {
            "lognameLikesThis": logname_likes_this,
            "numLikes": len(likes_info),
            "url": None
        }

    return flask.jsonify({
        "comments": comments,
        "comments_url": f"/api/v1/comments/?postid={postid_url_slug}",
        "created": post_info[0]["created"],
        "imgUrl": f"/uploads/{post_info[0]['filename']}",
        "likes": likes,
        "owner": post_info[0]["owner"],
        "ownerImgUrl": f"/uploads/{owner_info[0]['filename']}",
        "ownerShowUrl": f"/users/{post_info[0]['owner']}/",
        "postShowUrl": f"/posts/{postid_url_slug}/",
        "postid": postid_url_slug,
        "url": flask.request.path,
    })


@insta485.app.route('/api/v1/posts/')
def get_posts():
    """Return up to 10 newest posts."""
    logname = authenticate_user()
    # Connect to database
    connection = insta485.model.get_db()

    # pagination
    size = flask.request.args.get("size", default=10, type=int)
    page = flask.request.args.get("page", default=0, type=int)
    postid_lte = flask.request.args.get("postid_lte", type=int)

    # size and page must be non-negative
    if size < 0 or page < 0:
        flask.abort(400)

    # Get post info
    posts = None
    if postid_lte:
        posts = connection.execute(
            "SELECT owner, postid FROM posts WHERE postid <= ? "
            "ORDER BY postid DESC LIMIT ? OFFSET ?",
            (postid_lte, size, page * size,)
        )
        posts = posts.fetchall()
    else:
        posts = connection.execute(
            "SELECT owner, postid FROM posts ORDER BY postid DESC "
            "LIMIT ? OFFSET ?", (size, page * size,)
        )
        posts = posts.fetchall()
        postid_lte = posts[0]["postid"] if len(posts) > 0 else 0

    # Get following info
    following = connection.execute(
        "SELECT username1 FROM following WHERE username2 = ?", (logname,)
    )
    following = following.fetchall()
    following = [dict["username1"] for dict in following]

    results = []

    for post in posts:
        if len(results) >= size:
            break
        if post["owner"] == logname or post["owner"] in following:
            results.append({
                            "postid": post["postid"],
                            "url": f"/api/v1/posts/{post['postid']}/"
                        })

    # filter results through postid_lte
    results = [p for p in results if p["postid"] <= postid_lte]

    next_url = ""
    if len(results) >= size:
        base = "/api/v1/posts/"
        args = f"?size={size}&page={page+1}&postid_lte={postid_lte}"
        next_url = base + args

    url = flask.request.url
    for i, char in enumerate(url):
        if char + url[i + 1] == "/a":
            url = url[i:]
            break

    return flask.jsonify({
        "next": next_url,
        "results": results,
        "url": url
    })
