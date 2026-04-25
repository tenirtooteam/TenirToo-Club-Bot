# Файл: database/db.py

from .connection import init_db, get_conn
from .members import (
    add_user, get_all_users, delete_user, update_user_name,
    get_user_name, user_exists, find_users_by_query, get_user_names_by_ids
)
from .groups import (
    create_group, get_all_groups, delete_group,
    get_topics_of_group, add_topic_to_group, remove_topic_from_group,
    get_groups_by_topic, get_group_name, find_groups_by_query,
    add_to_group_template, remove_from_group_template, get_group_template_members,
    get_user_group_templates, get_user_group_membership_ids, get_group_ids_by_topic
)
from .topics import (
    get_all_unique_topics, update_topic_name, get_topic_name,
    delete_topic, register_topic_if_not_exists, find_topics_by_query,
    get_topic_names_by_ids
)
from .roles import (
    get_role_id, grant_role, revoke_role, get_user_roles,
    get_moderators_of_topic, is_global_admin, is_moderator_of_topic,
    get_all_roles, get_role_name_by_id, get_global_admin_ids
)
from .permissions import (
    can_write, is_topic_restricted, get_topic_authorized_users,
    grant_direct_access, revoke_direct_access, has_direct_access,
    get_direct_access_users, grant_direct_access_bulk, revoke_all_direct_access,
    get_user_available_topics, get_direct_access_user_ids, get_topic_authorized_user_ids
)
from .events import (
    create_event, update_event_details, approve_event, set_event_sheet_url, delete_event,
    add_event_lead, add_event_participant, remove_event_participant,
    is_event_participant, get_event_details, get_active_events, get_pending_events
)

