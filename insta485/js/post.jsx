import React, { useState, useEffect } from "react";
import moment from "moment";
import PropTypes from "prop-types";
import Likes from "./likes";
// import { post } from "cypress/types/jquery";

// The parameter of this function is an object with a string called url inside it.
// url is a prop for the Post component.
export default function Post({ url }) {
  /* Display image and post owner of a single post */

  const [imgUrl, setImgUrl] = useState("");
  const [owner, setOwner] = useState("");
  const [ownerImgUrl, setOwnerImg] = useState("");
  const [likes, setLikes] = useState({});
  const [postComments, setComments] = useState([]);
  const [postid, setPostid] = useState(0);
  const [commentText, setCommentText] = useState("");
  const [postTime, setPostTime] = useState("");

  useEffect(() => {
    // Declare a boolean flag that we can use to cancel the API request.
    let ignoreStaleRequest = false;

    // Call REST API to get the post's information
    fetch(url, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        // If ignoreStaleRequest was set to true, we want to ignore the results of the
        // the request. Otherwise, update the state to trigger a new render.
        if (!ignoreStaleRequest) {
          setImgUrl(data.imgUrl);
          setOwner(data.owner);
          setOwnerImg(data.ownerImgUrl);
          setLikes(data.likes);
          setComments(data.comments);
          setPostid(data.postid);
          setPostTime(moment.utc(data.created).fromNow());
        }
      })
      .catch((error) => console.log(error));

    return () => {
      // This is a cleanup function that runs whenever the Post component
      // unmounts or re-renders. If a Post is about to unmount or re-render, we
      // should avoid updating state.
      ignoreStaleRequest = true;
    };
  }, [url]);

  // Handle new comment input
  function handleCommentSubmit(event) {
    event.preventDefault();
    const target = `/api/v1/comments/?postid=${postid}`;
    fetch(target, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      method: "POST",
      body: JSON.stringify({ text: commentText }),
    })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((response) => {
        const newComment = {
          commentid: response.commentid,
          lognameOwnsThis: response.lognameOwnsThis,
          owner: response.owner,
          ownerShowUrl: response.ownerShowUrl,
          text: response.text,
          url: response.url,
        };
        setComments([...postComments, newComment]);
      });
    setCommentText("");
  }

  function handleCommentChange(event) {
    event.preventDefault();
    setCommentText(event.target.value);
  }

  // Handle how to delete comment
  function handleDeleteComment(comment) {
    const updatedComments = postComments.filter(
      (commentObj) => commentObj.commentid !== comment.commentid
    );
    fetch(comment.url, { method: "DELETE" }).then(setComments(updatedComments));
  }

  function handleDoubleClick() {
    if (!likes.lognameLikesThis) {
      // Add a like to the DB
      fetch(`/api/v1/likes/?postid=${postid}`, { method: "POST" })
        .then((response) => {
          if (!response.ok) throw Error(response.statusText);
          return response.json();
        })
        .then((response) => {
          setLikes({
            lognameLikesThis: !likes.lognameLikesThis,
            numLikes: likes.numLikes + 1,
            url: response.url,
          });
        });
    }
  }

  const ownerUrl = `/users/${owner}/`;
  const postUrl = `/posts/${postid}/`;

  // Render post image and post owner
  return (
    <div className="post">
      <div className="post-header">
        <img src={ownerImgUrl} alt="owner_image" height="60" width="60" />
        <a href={ownerUrl} className="post-header-user">
          <b>{owner}</b>
        </a>
        <a href={postUrl} className="post-header-timestamp">
          {postTime}
        </a>
      </div>
      <img
        src={imgUrl}
        className="post-image"
        onDoubleClick={handleDoubleClick}
        alt="post_image"
      />
      {Object.keys(likes).length > 0 ? (
        <Likes likes={likes} setLikes={setLikes} postid={postid} />
      ) : (
        <p>Loading likes...</p>
      )}
      {/* Comments section */}
      {postComments.map((comment) =>
        comment.lognameOwnsThis ? (
          <div key={comment.commentid}>
            <span className="comment-text">
              <a href={`/users/${comment.owner}/`}>
                <b>{comment.owner}</b>
              </a>{" "}
              {comment.text}
              <button
                className="delete-comment-button"
                type="button"
                onClick={() => handleDeleteComment(comment)}
              >
                Delete comment
              </button>
            </span>
          </div>
        ) : (
          <div key={comment.commentid}>
            <span className="comment-text">
              <a href={`/users/${comment.owner}/`}>
                <b>{comment.owner}</b>
              </a>{" "}
              {comment.text}
            </span>
          </div>
        )
      )}

      <form className="comment-form" onSubmit={handleCommentSubmit}>
        <input
          type="text"
          value={commentText}
          onChange={handleCommentChange}
          disabled={postid === 0}
        />
      </form>
    </div>
  );
}

Post.propTypes = {
  url: PropTypes.string.isRequired,
};
