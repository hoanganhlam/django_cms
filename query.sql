-- CHAR_TO_INT
CREATE FUNCTION CHAR_TO_INT(character varying) RETURNS integer AS
$$
SELECT CASE
           WHEN length(btrim(regexp_replace($1, '[^0-9]', '', 'g'))) > 0
               THEN btrim(regexp_replace($1, '[^0-9]', '', 'g'))::integer
           ELSE 0
           END AS intval
$$
    LANGUAGE sql;

-- MAKE_THUMB
CREATE OR REPLACE FUNCTION MAKE_THUMB(path varchar) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT (SELECT concat('https://bubblask.sgp1.digitaloceanspaces.com/mastercms/',
                               path) AS full_size),
                (SELECT concat('https://bubblask.sgp1.digitaloceanspaces.com/mastercms/cache/247x247/',
                               path) AS thumb_247_247),
                (SELECT concat('https://bubblask.sgp1.digitaloceanspaces.com/mastercms/cache/24x24/',
                               path) AS thumb_24_24)
     ) t
$$
    LANGUAGE sql;

-- COUNT_FOLLOWING
CREATE OR REPLACE FUNCTION COUNT_FOLLOWING(uid int) RETURNS BIGINT AS
$$
SELECT COUNT(*)
FROM (
         SELECT id
         FROM activity_follow x
         WHERE x.user_id = uid
           AND (SELECT FETCH_CONTENT_TYPE('auth_user')) = x.content_type_id
     ) t
$$ LANGUAGE sql;

-- COUNT_FOLLOWED
CREATE OR REPLACE FUNCTION COUNT_FOLLOWED(ct_name varchar, oid int) RETURNS BIGINT AS
$$
SELECT COUNT(*)
FROM (
         SELECT id
         FROM activity_follow x
         WHERE x.object_id = CAST(COUNT_FOLLOWED.oid as varchar)
           AND (SELECT FETCH_CONTENT_TYPE(ct_name)) = x.content_type_id
     ) t
$$ LANGUAGE sql;

-- COUNT_COMMENT
CREATE OR REPLACE FUNCTION COUNT_COMMENT(oid int) RETURNS BIGINT AS
$$
SELECT count(*)
FROM activity_comment
WHERE activity_id = COUNT_COMMENT.oid
$$ LANGUAGE sql;

-- IS_FOLLOWING
CREATE OR REPLACE FUNCTION IS_FOLLOWING(ct_name varchar, oid int, uid int = NULL) RETURNS BOOLEAN AS
$$
DECLARE
BEGIN
    RETURN (SELECT EXISTS(SELECT id
                          FROM activity_follow x
                          WHERE x.user_id = uid
                            AND x.object_id = CAST(IS_FOLLOWING.oid as varchar)
                            AND (SELECT FETCH_CONTENT_TYPE(ct_name)) = x.content_type_id));
END;

$$ LANGUAGE PLPGSQL;

-- GFK_QUERY
CREATE OR REPLACE FUNCTION GFK_QUERY(content_type int, object_id varchar, user_id int = null) RETURNS SETOF json AS
$$
DECLARE
BEGIN
    CASE
        WHEN content_type = (SELECT FETCH_CONTENT_TYPE('auth_user'))
            THEN RETURN QUERY SELECT FETCH_USER_ID(CHAR_TO_INT(object_id)) AS data;
        WHEN content_type = (SELECT FETCH_CONTENT_TYPE('cms_post'))
            THEN RETURN QUERY SELECT FETCH_POST(CHAR_TO_INT(object_id)) AS data;
        WHEN content_type = (SELECT FETCH_CONTENT_TYPE('activity_action'))
            THEN RETURN QUERY SELECT FETCH_ACTION(CHAR_TO_INT(object_id)) AS data;
        WHEN content_type = (SELECT FETCH_CONTENT_TYPE('cms_publication'))
            THEN RETURN QUERY SELECT FETCH_PUBLICATION(CHAR_TO_INT(object_id), user_id) AS data;
        END case;
END;
$$ LANGUAGE PLPGSQL;

-- VOTE_OBJECT
CREATE OR REPLACE FUNCTION VOTE_OBJECT(user_id INT, i INT = NULL) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (SELECT (
                 SELECT EXISTS(
                                SELECT *
                                FROM activity_action_voters
                                WHERE user_id = VOTE_OBJECT.user_id
                                  AND CASE WHEN i IS NOT NULL THEN action_id = VOTE_OBJECT.i ELSE FALSE END
                            )
             ) AS is_voted,
             (
                 SELECT count(*)
                 FROM activity_action_voters
                 WHERE action_id = VOTE_OBJECT.i
             ) AS total) t
$$ LANGUAGE sql;

-- IS_IN_TERMS
CREATE OR REPLACE FUNCTION IS_IN_TERMS(post_id int, term_ids int[] = NULL) RETURNS BOOLEAN AS
$$
DECLARE
BEGIN
    RETURN (
        SELECT EXISTS(
                       SELECT x.id
                       FROM cms_post x
                                JOIN cms_post_post_terms cppt on x.id = cppt.post_id
                       WHERE x.id = IS_IN_TERMS.post_id
                         AND cppt.termtaxonomy_id = ANY (IS_IN_TERMS.term_ids)
                   ));
END;
$$ LANGUAGE PLPGSQL;

-- IS_IN_PUBS
CREATE OR REPLACE FUNCTION IS_IN_PUBS(post_id int, pub_ids int[] = NULL) RETURNS BOOLEAN AS
$$
DECLARE
BEGIN
    RETURN (
        SELECT EXISTS(
                       SELECT x.id
                       FROM cms_post x
                                JOIN cms_post_publications cpp on x.id = cpp.post_id
                       WHERE x.id = IS_IN_PUBS.post_id
                         AND (cpp.publication_id = ANY (IS_IN_PUBS.pub_ids) OR
                              x.primary_publication_id = ANY (IS_IN_PUBS.pub_ids))
                   ));
END;
$$ LANGUAGE PLPGSQL;
--

-- FETCH_CONTENT_TYPE
CREATE OR REPLACE FUNCTION FETCH_CONTENT_TYPE(name varchar) returns integer as
$$
SELECT id
FROM django_content_type
WHERE concat(app_label, '_', model) = name
$$ LANGUAGE sql;

-- FETCH_USER_BY_USERNAME
CREATE OR REPLACE FUNCTION FETCH_USER_BY_USERNAME(user_name varchar, auth_id int = NULL) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT auth_user.id,
                auth_user.username,
                auth_user.first_name,
                auth_user.last_name,
                (
                    SELECT row_to_json(t)
                    FROM (
                             SELECT *,
                                    (
                                        SELECT row_to_json(u)
                                        FROM (
                                                 SELECT *,
                                                        (SELECT MAKE_THUMB(md.path)) as sizes
                                                 FROM media_media md
                                                 WHERE md.id = dp.media_id
                                             ) u
                                    ) AS media
                             FROM authentication_profile dp
                             WHERE dp.user_id = auth_user.id
                         ) t
                ) AS profile
         FROM auth_user
         WHERE auth_user.username = user_name
         LIMIT 1
     ) t
$$ LANGUAGE sql;

-- FETCH_USER_ID
CREATE OR REPLACE FUNCTION FETCH_USER_ID(i int) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT auth_user.id,
                auth_user.username,
                auth_user.first_name,
                auth_user.last_name,
                (
                    SELECT row_to_json(t)
                    FROM (
                             SELECT *,
                                    (
                                        SELECT row_to_json(u)
                                        FROM (
                                                 SELECT *,
                                                        (SELECT MAKE_THUMB(md.path)) as sizes
                                                 FROM media_media md
                                                 WHERE md.id = dp.media_id
                                             ) u
                                    ) AS media
                             FROM authentication_profile dp
                             WHERE dp.user_id = auth_user.id
                             LIMIT 1
                         ) t
                ) AS profile
         FROM auth_user
         WHERE auth_user.id = i
     ) t
$$ LANGUAGE sql;

--  FETCH_POST
CREATE OR REPLACE FUNCTION FETCH_POST(i int) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT cms_post.*,
                (SELECT FETCH_MEDIA(CAST(cms_post.options ->> 'media' AS INTEGER))) AS "media",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT ct.id,
                                    ct.taxonomy,
                                    (SELECT FETCH_TERM(ct.term_id)) AS "term"
                             FROM cms_termtaxonomy ct
                                      JOIN cms_post_post_terms cppt ON ct.id = cppt.termtaxonomy_id
                             WHERE cppt.post_id = cms_post.id
                             GROUP BY ct.id
                         ) t
                )                                                                   AS "post_terms",
                (
                    SELECT VOTE_OBJECT(user_id, CAST(cms_post.options ->> 'action_post' AS INTEGER))
                )                                                                   AS "vote_object"
         FROM cms_post
         WHERE cms_post.id = i
     ) t;

$$ LANGUAGE sql;

--  FETCH_POST
CREATE OR REPLACE FUNCTION FETCH_POST(i varchar) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT cms_post.*,
                (SELECT FETCH_MEDIA(CAST(cms_post.options ->> 'media' AS INTEGER))) AS "media",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT ct.id,
                                    ct.taxonomy,
                                    (SELECT FETCH_TERM(ct.term_id)) AS "term"
                             FROM cms_termtaxonomy ct
                                      JOIN cms_post_post_terms cppt ON ct.id = cppt.termtaxonomy_id
                             WHERE cppt.post_id = cms_post.id
                             GROUP BY ct.id
                         ) t
                )                                                                   AS "post_terms",
                (
                    SELECT VOTE_OBJECT(user_id, CAST(cms_post.options ->> 'action_post' AS INTEGER))
                )                                                                   AS "vote_object"
         FROM cms_post
         WHERE cms_post.slug = i
         LIMIT 1
     ) t;

$$ LANGUAGE sql;

-- FETCH_PUBLICATION
CREATE OR REPLACE FUNCTION FETCH_PUBLICATION(i int, user_id int = null) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT pa.*,
                (
                    SELECT IS_FOLLOWING('publisher_publication', pa.id, FETCH_PUBLICATION.user_id)
                ) AS is_following,
                (
                    SELECT COUNT_FOLLOWED('publisher_publication', pa.id)
                )
         FROM cms_publication pa
         WHERE pa.id = i
     ) t;

$$ LANGUAGE sql;

-- FETCH_ACTION
CREATE OR REPLACE FUNCTION FETCH_ACTION(i int, user_id int = null) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT *,
                (SELECT GFK_QUERY(aa.actor_content_type_id, aa.actor_object_id, null)) AS actor,
                (SELECT GFK_QUERY(aa.target_content_type_id,
                                  aa.target_object_id, null))                          AS target,
                (SELECT GFK_QUERY(aa.action_object_content_type_id,
                                  aa.action_object_object_id, null))                   AS action_object,
                (SELECT COUNT_COMMENT(aa.id))                                          AS comment_count
         FROM activity_action aa
         WHERE id = i
     ) t;

$$ LANGUAGE SQL;

-- FETCH_MEDIA
CREATE OR REPLACE FUNCTION FETCH_MEDIA(i int) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT mm.id,
                (SELECT MAKE_THUMB(mm.path)) as sizes
         FROM media_media mm
         WHERE mm.id = i
         LIMIT 1
     ) t;

$$ LANGUAGE sql;

-- FETCH_TERM
CREATE OR REPLACE FUNCTION FETCH_TERM(i int) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT ct.*
         FROM cms_term ct
         WHERE ct.id = i
         LIMIT 1
     ) t;

$$ LANGUAGE SQL;

--

-- FETCH_ACTIVITIES
CREATE OR REPLACE FUNCTION FETCH_ACTIVITIES(page_size int = NULL,
                                            os int = NULL,
                                            search varchar = NULL,
                                            order_by varchar = NULL,
                                            verb varchar = NULL,
                                            is_activity boolean = NULL,
                                            is_notify boolean = NULL,
                                            term_ids integer[] = NULL,
                                            target_content int = NULL,
                                            target_id varchar = NULL,
                                            user_id int = null) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT *,
                                    (SELECT GFK_QUERY(aa.actor_content_type_id, aa.actor_object_id, null)) AS actor,
                                    (SELECT GFK_QUERY(aa.target_content_type_id,
                                                      aa.target_object_id, null))                          AS target,
                                    (SELECT GFK_QUERY(aa.action_object_content_type_id,
                                                      aa.action_object_object_id,
                                                      null))                                               AS action_object,
                                    (SELECT VOTE_OBJECT(user_id, aa.id))                                   AS vote,
                                    (SELECT COUNT_COMMENT(aa.id))                                          AS comment_count
                             FROM activity_action aa
                             WHERE ((
                                            (aa.target_content_type_id = target_content
                                                AND aa.target_object_id = target_id) OR
                                            (target_id IS NULL AND target_content IS NULL)
                                        )
                                 OR (
                                            (aa.actor_content_type_id = target_content
                                                AND aa.actor_object_id = target_id) OR
                                            (target_id IS NULL AND target_content IS NULL)
                                        )
                                 OR (
                                            (aa.action_object_content_type_id = target_content
                                                AND aa.action_object_object_id = target_id) OR
                                            (target_id IS NULL AND target_content IS NULL)
                                        ))
                               AND CASE
                                       WHEN FETCH_ACTIVITIES.verb IS NOT NULL THEN aa.verb = FETCH_ACTIVITIES.verb
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_ACTIVITIES.is_activity IS NOT NULL
                                           THEN aa.is_activity = FETCH_ACTIVITIES.is_activity
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_ACTIVITIES.is_notify IS NOT NULL
                                           THEN aa.is_notify = FETCH_ACTIVITIES.is_notify
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_ACTIVITIES.term_ids IS NOT NULL
                                           THEN (SELECT IS_IN_TERMS(aa.id, FETCH_ACTIVITIES.term_ids))
                                       ELSE TRUE
                                 END
                             ORDER BY aa.id DESC
                             LIMIT page_size
                             OFFSET
                             os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT aa.id
                             FROM activity_action aa
                             WHERE ((
                                            (aa.target_content_type_id = target_content
                                                AND aa.target_object_id = target_id) OR
                                            (target_id IS NULL AND target_content IS NULL)
                                        )
                                 OR (
                                            (aa.actor_content_type_id = target_content
                                                AND aa.actor_object_id = target_id) OR
                                            (target_id IS NULL AND target_content IS NULL)
                                        )
                                 OR (
                                            (aa.action_object_content_type_id = target_content
                                                AND aa.action_object_object_id = target_id) OR
                                            (target_id IS NULL AND target_content IS NULL)
                                        ))
                               AND CASE
                                       WHEN FETCH_ACTIVITIES.verb IS NOT NULL THEN aa.verb = FETCH_ACTIVITIES.verb
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_ACTIVITIES.is_activity IS NOT NULL
                                           THEN aa.is_activity = FETCH_ACTIVITIES.is_activity
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_ACTIVITIES.is_notify IS NOT NULL
                                           THEN aa.is_notify = FETCH_ACTIVITIES.is_notify
                                       ELSE TRUE
                                 END
                               AND CASE
                                       WHEN FETCH_ACTIVITIES.term_ids IS NOT NULL
                                           THEN (SELECT IS_IN_TERMS(aa.id, FETCH_ACTIVITIES.term_ids))
                                       ELSE TRUE
                                 END
                         ) t
                ) AS count
     ) e
$$ LANGUAGE sql;

-- FETCH_POSTS
CREATE OR REPLACE FUNCTION FETCH_POSTS(page_size int = NULL,
                                       os int = NULL,
                                       search varchar = NULL,
                                       order_by varchar = NULL,
                                       user_id int = null,
                                       post_type varchar = NULL,
                                       taxonomies integer[] = NULL,
                                       publications integer[] = NULL) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT aa.*,
                                    (SELECT FETCH_MEDIA(CAST(aa.options ->> 'media' AS INTEGER))) AS "media",
                                    (
                                        SELECT array_to_json(array_agg(row_to_json(t)))
                                        FROM (
                                                 SELECT ct.id,
                                                        ct.taxonomy,
                                                        (SELECT FETCH_TERM(ct.term_id)) AS "term"
                                                 FROM cms_termtaxonomy ct
                                                          JOIN cms_post_post_terms cppt ON ct.id = cppt.termtaxonomy_id
                                                 WHERE cppt.post_id = aa.id
                                                 GROUP BY ct.id
                                             ) t
                                    )                                                             AS "post_terms",
                                    (
                                        SELECT VOTE_OBJECT(user_id, CAST(aa.options ->> 'action_post' AS INTEGER))
                                    )                                                             AS "vote_object"
                             FROM cms_post aa
                             WHERE aa.db_status = 1
                               AND aa.status = 'POSTED'
                               AND CASE
                                       WHEN FETCH_POSTS.post_type IS NOT NULL THEN aa.post_type = FETCH_POSTS.post_type
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.search IS NOT NULL THEN
                                           LOWER(aa.title) LIKE LOWER(CONCAT('%', FETCH_POSTS.search, '%'))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.taxonomies IS NOT NULL THEN
                                               (SELECT IS_IN_TERMS(aa.id, FETCH_POSTS.taxonomies))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.publications IS NOT NULL THEN
                                               (SELECT IS_IN_PUBS(aa.id, FETCH_POSTS.publications))
                                       ELSE TRUE END
                             ORDER BY aa.id DESC
                             LIMIT page_size
                             OFFSET
                             os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT aa.id
                             FROM cms_post aa
                             WHERE aa.db_status = 1
                               AND aa.status = 'POSTED'
                               AND CASE
                                       WHEN FETCH_POSTS.post_type IS NOT NULL THEN aa.post_type = FETCH_POSTS.post_type
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.search IS NOT NULL THEN
                                           LOWER(aa.title) LIKE LOWER(CONCAT('%', FETCH_POSTS.search, '%'))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.taxonomies IS NOT NULL THEN
                                               (SELECT IS_IN_TERMS(aa.id, FETCH_POSTS.taxonomies))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.publications IS NOT NULL THEN
                                               (SELECT IS_IN_PUBS(aa.id, FETCH_POSTS.publications))
                                       ELSE TRUE END
                         ) t
                ) AS count
     ) e
$$ LANGUAGE SQL;

-- FETCH_FETCH_TERM_TAXONOMIES
CREATE OR REPLACE FUNCTION FETCH_TERM_TAXONOMIES(page_size int = NULL,
                                                 os int = NULL,
                                                 search varchar = NULL,
                                                 order_by varchar = NULL,
                                                 user_id int = null,
                                                 taxonomy varchar = NULL,
                                                 taxonomies integer[] = NULL,
                                                 publications integer[] = NULL) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT ct.*,
                                    (SELECT FETCH_TERM(ct.term_id)) AS "term"
                             FROM cms_termtaxonomy ct
                                      JOIN cms_publication_publication_terms cppt on ct.id = cppt.termtaxonomy_id
                                      JOIN cms_term ctm on ct.term_id = ctm.id
                             WHERE ct.db_status = 1
                               AND CASE
                                       WHEN FETCH_TERM_TAXONOMIES.publications IS NOT NULL THEN
                                           cppt.publication_id = ANY (FETCH_TERM_TAXONOMIES.publications)
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TERM_TAXONOMIES.taxonomy IS NOT NULL THEN
                                           ct.taxonomy = FETCH_TERM_TAXONOMIES.taxonomy
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TERM_TAXONOMIES.taxonomies IS NOT NULL THEN
                                           ct.id = ANY (FETCH_TERM_TAXONOMIES.taxonomies)
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TERM_TAXONOMIES.search IS NOT NULL THEN
                                               LOWER(ctm.title) LIKE
                                               LOWER(CONCAT('%', FETCH_TERM_TAXONOMIES.search, '%'))
                                       ELSE TRUE END
                             GROUP BY ct.id
                             ORDER BY ct.id DESC
                             LIMIT page_size
                             OFFSET
                             os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT ct.id
                             FROM cms_termtaxonomy ct
                                      JOIN cms_publication_publication_terms cppt on ct.id = cppt.termtaxonomy_id
                                      JOIN cms_term ctm on ct.term_id = ctm.id
                             WHERE ct.db_status = 1
                               AND CASE
                                       WHEN FETCH_TERM_TAXONOMIES.publications IS NOT NULL THEN
                                           cppt.publication_id = ANY (FETCH_TERM_TAXONOMIES.publications)
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TERM_TAXONOMIES.taxonomy IS NOT NULL THEN
                                           ct.taxonomy = FETCH_TERM_TAXONOMIES.taxonomy
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TERM_TAXONOMIES.taxonomies IS NOT NULL THEN
                                           ct.id = ANY (FETCH_TERM_TAXONOMIES.taxonomies)
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TERM_TAXONOMIES.search IS NOT NULL THEN
                                               LOWER(ctm.title) LIKE
                                               LOWER(CONCAT('%', FETCH_TERM_TAXONOMIES.search, '%'))
                                       ELSE TRUE END
                         ) t
                ) AS count
     ) e
$$ LANGUAGE SQL;

-- FETCH_COMMENTS
CREATE OR REPLACE FUNCTION FETCH_COMMENTS(page_size int = NULL,
                                          os int = NULL,
                                          order_by varchar = NULL,
                                          user_id int = NULL,
                                          parent_id int = NULL,
                                          action_id int = NULL) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT ac.*
                             FROM activity_comment ac
                             WHERE ac.db_status = 1
                               AND CASE
                                       WHEN FETCH_COMMENTS.action_id is NOT NULL THEN
                                           ac.activity_id = action_id
                                       ELSE FALSE END
                               AND CASE
                                       WHEN FETCH_COMMENTS.parent_id IS NOT NULL THEN
                                           ac.parent_comment_id = FETCH_COMMENTS.parent_id
                                       ELSE TRUE END
                             GROUP BY ac.id
                             ORDER BY ac.id DESC
                             LIMIT page_size
                             OFFSET
                             os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT ac.id
                             FROM activity_comment ac
                             WHERE ac.db_status = 1
                               AND CASE
                                       WHEN FETCH_COMMENTS.action_id is NOT NULL THEN
                                           ac.activity_id = action_id
                                       ELSE FALSE END
                               AND CASE
                                       WHEN FETCH_COMMENTS.parent_id IS NOT NULL THEN
                                           ac.parent_comment_id = FETCH_COMMENTS.parent_id
                                       ELSE TRUE END
                         ) t
                ) AS count
     ) e
$$ LANGUAGE SQL;

ALTER SEQUENCE cms_post_id_seq RESTART WITH 1904;
SELECT FETCH_POST('nuxt-basic-auth-module');
