"""Insta485 REST API."""

from insta485.api.posts import get_post
from insta485.api.posts import get_posts
from insta485.api.services import get_services
from insta485.api.likes import post_likes
from insta485.api.likes import delete_like
from insta485.api.comments import post_comment
from insta485.api.comments import delete_comment
from insta485.api.posts import authenticate_user
