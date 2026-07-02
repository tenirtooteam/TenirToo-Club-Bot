---
type: db-schema
title: Database Entity-Relationship Model (DDL)
description: Full SQLite DDL for the Tenir-Too bot — tables, foreign keys, and indexes.
source_anchor: PL-3.1
timestamp: 2026-07-02
tags: [database, schema, sqlite, ddl]
---

# Database Entity-Relationship Model — DDL

> Moved from `PROJECT_LOGIC.md` [PL-3.1] during the two-tier documentation migration.
> Imperative constraints related to the schema ([PL-3.1.1] Transactional Integrity,
> [PL-3.2] Access Control Logic) remain in `PROJECT_LOGIC.md`.

~~~sql
CREATE TABLE IF NOT EXISTS roles (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id  INTEGER,
    role_id  INTEGER,
    topic_id INTEGER NULL,
    PRIMARY KEY (user_id, role_id, topic_id),
    FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id)  REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topic_names(topic_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS direct_topic_access (
    user_id  INTEGER,
    topic_id INTEGER,
    PRIMARY KEY (user_id, topic_id),
    FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topic_names(topic_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS groups (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS group_topics (
    group_id INTEGER,
    topic_id INTEGER,
    PRIMARY KEY (group_id, topic_id),
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS group_members (
    group_id INTEGER,
    user_id  INTEGER,
    PRIMARY KEY (group_id, user_id),
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS topic_names (
    topic_id INTEGER PRIMARY KEY,
    name     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_group_topics_topic_id ON group_topics(topic_id);
CREATE INDEX IF NOT EXISTS idx_group_members_user_id ON group_members(user_id);

CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    start_iso TEXT,
    end_iso TEXT,
    creator_id INTEGER,
    is_approved INTEGER DEFAULT 0,
    sheet_url TEXT,
    FOREIGN KEY (creator_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS event_leads (
    event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (event_id, user_id),
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS event_participants (
    event_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (event_id, user_id),
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
~~~
