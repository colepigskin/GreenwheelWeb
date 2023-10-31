import React from "react";
import PropTypes from "prop-types";

function handleLikeClick(likes, setLikes, postid) {
  if (likes.lognameLikesThis) {
    // Delete the like from the DB
    fetch(likes.url, { method: "DELETE" })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
      })
      .then(() => {
        setLikes({
          lognameLikesThis: !likes.lognameLikesThis,
          numLikes: likes.numLikes - 1,
          url: "",
        });
      })
      .catch((error) => console.log(error));
  } else {
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
      })
      .catch((error) => console.log(error));
  }
}

export default function Likes({ likes, setLikes, postid }) {
  return (
    <div>
      {likes.numLikes === 1 ? (
        <p>{likes.numLikes} like</p>
      ) : (
        <p>{likes.numLikes} likes</p>
      )}
      <button
        className="like-unlike-button"
        type="button"
        onClick={() => handleLikeClick(likes, setLikes, postid)}
      >
        {likes.lognameLikesThis ? "Unlike" : "Like"}
      </button>
    </div>
  );
}

Likes.propTypes = {
  likes: PropTypes.shape({
    lognameLikesThis: PropTypes.bool.isRequired,
    numLikes: PropTypes.number.isRequired,
    url: PropTypes.string,
  }).isRequired,
  setLikes: PropTypes.func.isRequired,
  postid: PropTypes.number.isRequired,
};
