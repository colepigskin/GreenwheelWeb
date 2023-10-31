"""REST API for posts."""
import flask
import insta485
from insta485.api.posts import authenticate_user


@insta485.app.route('/api/v1/likes/', methods=['POST'])
def post_likes():
    """Create a like."""
    # get logname from either cookies or http auth
    logname = authenticate_user()

    # Connect to database
    connection = insta485.model.get_db()

    # Get like info
    likes_cur = connection.execute(
        "SELECT likeid "
        "FROM likes "
        "WHERE postid = ? AND owner = ? ",
        (flask.request.args.get('postid'), logname,)
    )
    likes_info = likes_cur.fetchall()

    # If there is no like yet, add it into the DB
    if len(likes_info) == 0:
        connection.execute(
            "INSERT INTO likes "
            "(owner, postid) "
            "VALUES (?,?) ",
            (logname, flask.request.args.get('postid'), )
        )

        # Get like info again
        likes_cur = connection.execute(
            "SELECT likeid "
            "FROM likes "
            "WHERE postid = ? AND owner = ? ",
            (flask.request.args.get('postid'), logname, )
        )
        likes_info = likes_cur.fetchall()

        like_obj = {
            "likeid": likes_info[0]["likeid"],
            "url": f"/api/v1/likes/{likes_info[0]['likeid']}/",
        }
        return flask.jsonify(like_obj), 201

    # There is already a like
    like_obj = {
        "likeid": likes_info[0]["likeid"],
        "url": f"/api/v1/likes/{likes_info[0]['likeid']}/"
    }
    return flask.jsonify(like_obj), 200


@insta485.app.route('/api/v1/likes/<int:likeid_url_slug>/', methods=['DELETE'])
def delete_like(likeid_url_slug):
    """Delete a like."""
    # get logname from either cookies or http auth
    logname = authenticate_user()

    # Connect to database
    connection = insta485.model.get_db()

    # If like_id doesn't exist
    likeid_check = connection.execute(
        "SELECT * "
        "FROM likes "
        "WHERE likeid = ? ", (likeid_url_slug, )
    )
    likeid_check = likeid_check.fetchall()

    if len(likeid_check) == 0:
        return flask.make_response('', 404)

    # If the logged in user does not own the like
    user_check = connection.execute(
        "SELECT * "
        "FROM likes "
        "WHERE likeid = ? AND owner = ? ", (likeid_url_slug, logname, )
    )
    user_check = user_check.fetchall()

    if len(user_check) == 0:
        return flask.make_response('', 403)

    # Delete the like
    connection.execute(
        "DELETE FROM likes "
        "WHERE likeid = ?", (likeid_url_slug, )
    )

    # Success
    return flask.make_response('', 204)
