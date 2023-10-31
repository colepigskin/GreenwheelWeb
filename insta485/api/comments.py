"""REST API for posts."""
import flask
import insta485
from insta485.api.posts import authenticate_user


@insta485.app.route('/api/v1/comments/', methods=['POST'])
def post_comment():
    """Create a comment."""
    # get logname from either cookies or http auth
    logname = authenticate_user()

    # Connect to database
    connection = insta485.model.get_db()

    # Put the new comment into the database
    connection.execute(
            "INSERT INTO comments "
            "(owner, postid, text) "
            "VALUES (?,?,?) ",
            (logname, flask.request.args.get('postid'),
             flask.request.get_json()['text'], )
        )

    # Get the last row
    last_row_id = connection.execute("SELECT last_insert_rowid() ")

    # Get all info from the new entry
    temp = connection.execute(
            "SELECT * "
            "FROM comments "
            "WHERE rowid = ? ",
            (last_row_id.lastrowid, )
        )
    new_comment = temp.fetchall()

    logname_owns_this = False
    if new_comment[0]["owner"] == logname:
        logname_owns_this = True

    context = {
        "commentid": new_comment[0]["commentid"],
        "lognameOwnsThis": logname_owns_this,
        "owner": new_comment[0]["owner"],
        "ownerShowUrl": f"/users/{new_comment[0]['owner']}/",
        "text": flask.request.get_json()['text'],
        "url": f"/api/v1/comments/{new_comment[0]['commentid']}/"
    }

    return flask.jsonify(context), 201


@insta485.app.route('/api/v1/comments/<int:commentid_url_slug>/',
                    methods=['DELETE'])
def delete_comment(commentid_url_slug):
    """Delete a comment."""
    logname = authenticate_user()

    # Connect to database
    connection = insta485.model.get_db()

    # Check if comment with comment id exists
    temp = connection.execute(
            "SELECT * "
            "FROM comments "
            "WHERE commentid = ? ",
            (commentid_url_slug, )
        )
    comment_check = temp.fetchall()

    # Check if comment with comment id exists
    if len(comment_check) == 0:
        return flask.make_response('', 404)

    # Check if user owns the comment
    if comment_check[0]["owner"] != logname:
        return flask.make_response('', 403)

    # Delete the comment from the DB
    connection.execute(
            "DELETE FROM comments "
            "WHERE commentid = ? ",
            (commentid_url_slug, )
        )

    # Success
    return flask.make_response('', 204)
