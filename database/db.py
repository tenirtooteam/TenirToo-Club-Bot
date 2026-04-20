# Файл: database/db.py

from .connection import init_db, get_conn
from .members import (
    add_user, get_all_users, delete_user, update_user_name,
    get_user_name, user_exists, find_users_by_query
)
from .groups import (
    create_group, get_all_groups, delete_group,
    get_topics_of_group, add_topic_to_group, remove_topic_from_group,
    get_groups_by_topic, get_user_groups, grant_group, revoke_group,
    get_group_name, get_user_available_topics
)
from .topics import (
    get_all_unique_topics, update_topic_name, get_topic_name,
    delete_topic, register_topic_if_not_exists
)
from .roles import (
    get_role_id, grant_role, revoke_role, get_user_roles,
    get_moderators_of_topic, is_global_admin, is_moderator_of_topic,
    get_all_roles, get_role_name_by_id
)
from .permissions import (
    can_write, is_topic_restricted, get_topic_authorized_users,
    grant_direct_access, revoke_direct_access, has_direct_access,
    get_direct_access_users
)

