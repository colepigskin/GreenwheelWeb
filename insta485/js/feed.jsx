import React, { useEffect, useState } from "react";
import InfiniteScroll from "react-infinite-scroll-component";
import PropTypes from "prop-types";
import Post from "./post";

export default function Feed({ url }) {
  // Display the feed of posts and get more when user reaches
  // the end of the current feed

  const [posts, setPosts] = useState([]);
  const [nextUrl, setNextUrl] = useState("");

  useEffect(() => {
    // Declare a boolean flag that we can use to cancel the API request.
    let ignoreStaleRequest = false;

    fetch(url, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        if (!ignoreStaleRequest) {
          setPosts((p) => [...p, ...data.results]);
          setNextUrl(data.next);
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

  const postArray = posts.map((post) => (
    <Post key={post.postid} url={post.url} />
  ));

  function handleUpdate() {
    fetch(nextUrl, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw Error(response.statusText);
        return response.json();
      })
      .then((data) => {
        setPosts([...posts, ...data.results]);
        setNextUrl(data.next);
      })
      .catch((error) => console.log(error));
  }

  return (
    <InfiniteScroll
      dataLength={postArray.length} // This is important field to render the next data
      next={() => handleUpdate()}
      hasMore={nextUrl !== ""}
      loader={<h4>Loading...</h4>}
    >
      {postArray}
    </InfiniteScroll>
  );
}

Feed.propTypes = {
  url: PropTypes.string.isRequired,
};
