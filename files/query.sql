-- ARRAY_SORT
CREATE
OR REPLACE FUNCTION ARRAY_SORT(anyarray) RETURNS anyarray AS
$$
SELECT array_agg(x order by x)
FROM unnest($1) x;
$$
LANGUAGE SQL;

-- CHAR_TO_INT
CREATE FUNCTION CHAR_TO_INT(character varying) RETURNS integer AS
    $$
SELECT CASE
           WHEN length(btrim(regexp_replace($1, '[^0-9]', '', 'g'))) > 0
               THEN btrim(regexp_replace($1, '[^0-9]', '', 'g'))::integer
           ELSE 0
END
AS intval
$$
    LANGUAGE sql;

-- MAKE_THUMB
CREATE
OR REPLACE FUNCTION MAKE_THUMB(path varchar) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT (SELECT concat('https://cdn.fournalist.com/images',
                               path) AS full_size),
                (SELECT concat('https://cdn.fournalist.com/247x247/images',
                               path) AS thumb_247_247),
                (SELECT concat('https://cdn.fournalist.com/128x128/images',
                               path) AS thumb_128_128),
                (SELECT concat('https://cdn.fournalist.com/24x24/images',
                               path) AS thumb_24_24)
     ) t $$
    LANGUAGE sql;

-- COUNT_FOLLOWING
CREATE
OR REPLACE FUNCTION COUNT_FOLLOWING(uid int) RETURNS BIGINT AS
$$
SELECT COUNT(*)
FROM (
         SELECT id
         FROM activity_follow x
         WHERE x.user_id = uid
           AND (SELECT FETCH_CONTENT_TYPE('auth_user')) = x.content_type_id
     ) t $$ LANGUAGE sql;

-- COUNT_FOLLOWED
CREATE
OR REPLACE FUNCTION COUNT_FOLLOWED(ct_name varchar, oid int) RETURNS BIGINT AS
$$
SELECT COUNT(*)
FROM (
         SELECT id
         FROM activity_follow x
         WHERE x.object_id = CAST(COUNT_FOLLOWED.oid as varchar)
           AND (SELECT FETCH_CONTENT_TYPE(ct_name)) = x.content_type_id
     ) t $$ LANGUAGE sql;

-- COUNT_COMMENT
CREATE
OR REPLACE FUNCTION COUNT_COMMENT(oid int) RETURNS BIGINT AS
$$
SELECT count(*)
FROM activity_comment
WHERE activity_id = COUNT_COMMENT.oid $$ LANGUAGE sql;

-- GFK_QUERY
CREATE
OR REPLACE FUNCTION GFK_QUERY(content_type int, object_id varchar, user_id int = null) RETURNS SETOF json AS
$$
DECLARE
BEGIN
CASE
        WHEN content_type = (SELECT FETCH_CONTENT_TYPE('auth_user'))
            THEN RETURN QUERY
SELECT FETCH_USER_ID(CHAR_TO_INT(object_id)) AS data;
WHEN content_type = (SELECT FETCH_CONTENT_TYPE('cms_post'))
            THEN RETURN QUERY
SELECT FETCH_POST(CHAR_TO_INT(object_id), FALSE, NULL, NULL) AS data;
WHEN content_type = (SELECT FETCH_CONTENT_TYPE('cms_publicationterm'))
            THEN RETURN QUERY
SELECT FETCH_TAXONOMY_BY_ID(CHAR_TO_INT(object_id)) AS data;
WHEN content_type = (SELECT FETCH_CONTENT_TYPE('activity_action'))
            THEN RETURN QUERY
SELECT FETCH_ACTION(CHAR_TO_INT(object_id)) AS data;
WHEN content_type = (SELECT FETCH_CONTENT_TYPE('cms_publication'))
            THEN RETURN QUERY
SELECT FETCH_PUBLICATION(CHAR_TO_INT(object_id), user_id) AS data;
END
CASE;
END;
$$
LANGUAGE PLPGSQL;

-- IS_FOLLOWING
CREATE
OR REPLACE FUNCTION IS_FOLLOWING(ct_name varchar, oid int, uid int = NULL) RETURNS BOOLEAN AS
$$
DECLARE
BEGIN
RETURN (SELECT EXISTS(SELECT id
                      FROM activity_follow x
                      WHERE x.user_id = uid
                        AND x.object_id = CAST(IS_FOLLOWING.oid as varchar)
                        AND (SELECT FETCH_CONTENT_TYPE(ct_name)) = x.content_type_id));
END;

$$
LANGUAGE PLPGSQL;

-- VOTE_OBJECT
CREATE
OR REPLACE FUNCTION VOTE_OBJECT(user_id INT, i INT = NULL) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (SELECT (
                 SELECT EXISTS(
                                SELECT aav.id
                                FROM activity_action_voters aav
                                WHERE aav.user_id = VOTE_OBJECT.user_id
                                  AND CASE WHEN i IS NOT NULL THEN aav.action_id = VOTE_OBJECT.i ELSE FALSE END
                            )
             ) AS is_voted,
             (
                 SELECT count(*)
                 FROM activity_action_voters
                 WHERE action_id = VOTE_OBJECT.i
             ) AS total) t $$ LANGUAGE sql;

-- IS_IN_TERMS
CREATE
OR REPLACE FUNCTION IS_IN_TERMS(post_id int, operator varchar = NULL, term_ids int[] = NULL) RETURNS BOOLEAN AS
$$
DECLARE
BEGIN
RETURN (
    SELECT EXISTS(
                   SELECT x.id
                   FROM cms_post x
                            JOIN cms_post_terms cppt on x.id = cppt.post_id
                   WHERE x.id = IS_IN_TERMS.post_id
                     AND cppt.publicationterm_id = ANY (IS_IN_TERMS.term_ids)
               ));
END;
$$
LANGUAGE PLPGSQL;

-- IS_IN_PUBS
CREATE
OR REPLACE FUNCTION IS_IN_PUBS(post_id int, pub_ids int[] = NULL) RETURNS BOOLEAN AS
$$
DECLARE
BEGIN
RETURN (
    SELECT EXISTS(
                   SELECT x.id
                   FROM cms_post x
                            LEFT JOIN cms_post_publications cpp on x.id = cpp.post_id
                   WHERE x.id = IS_IN_PUBS.post_id
                     AND (
                           cpp.publication_id = ANY (IS_IN_PUBS.pub_ids)
                           OR
                           x.primary_publication_id = ANY (IS_IN_PUBS.pub_ids))
               ));
END;
$$
LANGUAGE PLPGSQL;

-- IS_IN_POST_RELATED
CREATE
OR REPLACE FUNCTION IS_IN_POST_RELATED(post_id int, operator varchar = NULL, post_related_id int[] = NULL) RETURNS BOOLEAN AS
$$
DECLARE
BEGIN
RETURN (
    CASE
        WHEN IS_IN_POST_RELATED.operator = 'AND'
            THEN (WITH related AS (
            SELECT cp.id
            FROM cms_post cp
                     LEFT JOIN cms_post_post_related cppr on cp.id = cppr.to_post_id AND cp.id != post_id WHERE cppr.from_post_id = post_id
                ORDER BY cp.id
    )
SELECT ARRAY(SELECT id FROM related) = ARRAY_SORT(post_related_id))
            ELSE (
                SELECT EXISTS(
                               SELECT cp.id
                               FROM cms_post cp
                                        LEFT JOIN cms_post_post_related cppr
                                                  on cp.id = cppr.to_post_id AND cp.id != post_id
                               WHERE cppr.from_post_id = post_id
                                 AND cppr.to_post_id = ANY (post_related_id)
                           )
            )
END
);
END;
$$
LANGUAGE PLPGSQL;

CREATE
OR REPLACE FUNCTION json_arr2text_arr(_js json)
    RETURNS text[]
    LANGUAGE sql
    IMMUTABLE PARALLEL SAFE AS
'SELECT ARRAY(SELECT json_array_elements_text(_js))';

-- FOLLOW_OBJECTS

CREATE
OR REPLACE FUNCTION FOLLOW_OBJECT(user_id INT, content_type_id INT, i INT = NULL) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT (
                    SELECT EXISTS(
                                   SELECT af.id
                                   FROM activity_follow af
                                   WHERE af.user_id = FOLLOW_OBJECT.user_id
                                     AND af.content_type_id = FOLLOW_OBJECT.content_type_id
                                     AND af.object_id = CAST(i AS varchar)
                               )
                ) AS is_follow,
                (
                    SELECT count(*)
                    FROM activity_follow af
                    WHERE af.content_type_id = FOLLOW_OBJECT.content_type_id
                      AND af.object_id = CAST(i AS varchar)
                ) AS total_follow) t $$ LANGUAGE sql;

CREATE
OR REPLACE FUNCTION FOLLOW_OBJECTS(user_id INT, content_type_id INT, list_id integer[]) RETURNS json AS
$$
DECLARE
var     INTEGER;
    results
jsonb = '{}';
BEGIN
    FOREACH
var IN ARRAY list_id
        LOOP
            results := jsonb_set(
                    results,
                    ARRAY [CAST(var as text)],
                    CAST((SELECT FOLLOW_OBJECT(user_id, content_type_id, var)) AS jsonb),
                    True
                );
END LOOP;
return results;
END
$$
LANGUAGE plpgsql;
--

-- FETCH_POST_RELATED
CREATE
OR REPLACE FUNCTION FETCH_POST_RELATED(post_id int,
                                              guess_post boolean = NULL,
                                              show_cms boolean = NULL) RETURNS json AS
$$
SELECT array_to_json(array_agg(row_to_json(t)))
FROM (
         SELECT cp.*,
                (SELECT FETCH_PUBLICATION(cp.primary_publication_id))      AS "primary_publication",
                (SELECT FETCH_MEDIA(CAST(cp.meta ->> 'media' AS INTEGER))) AS "media"
         FROM cms_post cp
                  LEFT JOIN cms_post_post_related cppr on cp.id = cppr.to_post_id AND cp.id != post_id
         WHERE cppr.from_post_id = FETCH_POST_RELATED.post_id
           AND cp.db_status = 1
     ) t;
$$
LANGUAGE SQL;

-- FETCH_RELATED
CREATE
OR REPLACE FUNCTION FETCH_RELATED(post_id int, publication_id int = NULL) RETURNS json AS
$$
SELECT array_to_json(array_agg(row_to_json(t)))
FROM (
         SELECT cp.*,
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT ct.id,
                                    ct.taxonomy,
                                    (SELECT FETCH_TERM(ct.term_id)) AS "term"
                             FROM cms_publicationterm ct
                                      JOIN cms_post_terms cppt ON ct.id = cppt.publicationterm_id
                             WHERE cppt.post_id = cp.id
                             GROUP BY ct.id
                         ) t
                )                                                          AS "post_terms",
                (SELECT FETCH_MEDIA(CAST(cp.meta ->> 'media' AS INTEGER))) AS "media",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT mm.id,
                                    (SELECT MAKE_THUMB(mm.path)) as sizes
                             FROM media_media mm
                                      JOIN LATERAL jsonb_array_elements_text(cp.meta -> 'medias') ids
                             ON TRUE
                             WHERE mm.id::text = ids
                         ) t
                )                                                          AS "medias"
         FROM cms_post cp
                  JOIN cms_post cpx on cpx.id = FETCH_RELATED.post_id
         WHERE cp.primary_publication_id = publication_id
           AND cp.post_type = cpx.post_type
           AND cp.show_cms = TRUE LIMIT 6
     ) t;

$$
LANGUAGE SQL;

-- FETCH_CONTENT_TYPE
CREATE
OR REPLACE FUNCTION FETCH_CONTENT_TYPE(name varchar) returns integer as
$$
SELECT id
FROM django_content_type
WHERE concat(app_label, '_', model) = name $$ LANGUAGE sql;

-- FETCH_USER_BY_USERNAME
CREATE
OR REPLACE FUNCTION FETCH_USER_BY_USERNAME(user_name varchar, auth_id int = NULL) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT auth_user.id,
                auth_user.username,
                auth_user.first_name,
                auth_user.last_name,
                auth_user.is_superuser,
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
         WHERE auth_user.username = user_name LIMIT 1
     ) t $$ LANGUAGE sql;

-- FETCH_USER_ID
CREATE
OR REPLACE FUNCTION FETCH_USER_ID(i int) RETURNS json AS
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
                             WHERE dp.user_id = auth_user.id LIMIT 1
                         ) t
                ) AS profile
         FROM auth_user
         WHERE auth_user.id = i
     ) t $$ LANGUAGE sql;

--  FETCH_POST_PARENT
CREATE
OR REPLACE FUNCTION FETCH_POST_PARENT(i int) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT cms_post.*,
                (
                    SELECT FETCH_MEDIA(CAST(cms_post.meta ->> 'media' AS INTEGER))
                ) AS "media",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT mm.id,
                                    (SELECT MAKE_THUMB(mm.path)) as sizes
                             FROM media_media mm
                                      JOIN LATERAL jsonb_array_elements_text(cms_post.meta -> 'medias') ids
                             ON TRUE
                             WHERE mm.id::text = ids
                         ) t
                ) AS "medias"
         FROM cms_post
         WHERE cms_post.id = FETCH_POST_PARENT.i) t;
$$
LANGUAGE sql;

--  FETCH_POST
CREATE
OR REPLACE FUNCTION FETCH_POST(i int, is_uid boolean,
                                      guess_post boolean = NULL,
                                      show_cms boolean = NULL,
                                      user_id int = NULL) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT cms_post.*,
                (SELECT FETCH_USER_ID(cms_post.user_id))                         AS "user",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT au.id,
                                    au.username,
                                    au.first_name,
                                    au.last_name,
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
                                                 WHERE dp.user_id = au.id LIMIT 1
                                             ) t
                                    ) AS profile
                             FROM auth_user au
                                      JOIN cms_post_collaborators c on au.id = c.user_id
                             WHERE c.post_id = cms_post.id
                         ) t
                )                                                                AS "contributors",
                (SELECT ARRAY_TO_JSON(ARRAY_AGG(ROW_TO_JSON(t)))
                 FROM (
                          SELECT au.id,
                                 au.username,
                                 au.first_name,
                                 au.last_name,
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
                                              WHERE dp.user_id = au.id LIMIT 1
                                          ) t
                                 ) AS profile
                          FROM auth_user au
                                   JOIN cms_post_collaborators cpc on au.id = cpc.user_id
                          WHERE cpc.post_id = cms_post.id
                      ) t)                                                       AS "collaborators",
                (SELECT FETCH_MEDIA(CAST(cms_post.meta ->> 'media' AS INTEGER))) AS "media",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT mm.id,
                                    mm.title,
                                    (SELECT MAKE_THUMB(mm.path)) as sizes
                             FROM media_media mm
                                      JOIN LATERAL jsonb_array_elements_text(cms_post.meta -> 'medias') ids
                             ON TRUE
                             WHERE mm.id::text = ids
                         ) t
                )                                                                AS "medias",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT ct.id,
                                    ct.taxonomy,
                                    ct.publication_id,
                                    (SELECT FETCH_TERM(ct.term_id)) AS "term"
                             FROM cms_publicationterm ct
                                      JOIN cms_post_terms cpt on ct.id = cpt.publicationterm_id
                             WHERE cpt.post_id = cms_post.id
                             GROUP BY ct.id
                         ) t
                )                                                                AS "terms",
                (
                    SELECT FETCH_POST_RELATED(cms_post.id,
                                              FETCH_POST.guess_post,
                                              FETCH_POST.show_cms)
                )                                                                AS "post_related",
                (
                    SELECT FETCH_POST_PARENT(cms_post.post_parent_id))           AS "post_parent",
                (
                    SELECT VOTE_OBJECT(FETCH_POST.user_id, CAST(cms_post.options ->> 'action_post' AS INTEGER))
                )                                                                AS "vote",
                (
                    SELECT FETCH_COMMENTS(5, 0, NULL, FETCH_POST.user_id, NULL,
                                          CAST(cms_post.options ->> 'action_post' AS INTEGER))
                )                                                                AS "comment",
                (
                    SELECT IS_FOLLOWING('cms_post', cms_post.id, FETCH_POST.user_id)
                )                                                                AS "following",
                (SELECT FETCH_PUBLICATION(cms_post.primary_publication_id))      AS "primary_publication",
                (SELECT ARRAY_TO_JSON(ARRAY_AGG(ROW_TO_JSON(t)))
                 FROM (
                          SELECT cp.*
                          FROM cms_publication cp
                                   JOIN cms_post_publications cpp on cp.id = cpp.publication_id
                          WHERE cpp.post_id = cms_post.id
                      ) t)                                                       AS "publications"
         FROM cms_post
         WHERE CASE
                   WHEN FETCH_POST.is_uid IS TRUE THEN cms_post.pid = FETCH_POST.i
                   ELSE cms_post.id = FETCH_POST.i
                   END LIMIT 1
     ) t;

$$
LANGUAGE sql;

--  FETCH_POST
CREATE
OR REPLACE FUNCTION FETCH_POST(i varchar, is_uid boolean,
                                      guess_post boolean = NULL,
                                      show_cms boolean = NULL,
                                      user_id int = NULL) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT cms_post.*,
                (SELECT FETCH_USER_ID(cms_post.user_id))                         AS "user",
                (SELECT FETCH_MEDIA(CAST(cms_post.meta ->> 'media' AS INTEGER))) AS "media",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT mm.id,
                                    (SELECT MAKE_THUMB(mm.path)) as sizes
                             FROM media_media mm
                                      JOIN LATERAL jsonb_array_elements_text(cms_post.meta -> 'medias') ids
                             ON TRUE
                             WHERE mm.id::text = ids
                         ) t
                )                                                                AS "medias",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT ct.id,
                                    ct.taxonomy,
                                    (SELECT FETCH_TERM(ct.term_id)) AS "term"
                             FROM cms_publicationterm ct
                                      JOIN cms_post_terms cpt on ct.id = cpt.publicationterm_id
                             WHERE cpt.post_id = cms_post.id
                             GROUP BY ct.id
                         ) t
                )                                                                AS "terms",
                (
                    SELECT FETCH_POST_RELATED(cms_post.id,
                                              FETCH_POST.guess_post,
                                              FETCH_POST.show_cms)
                )                                                                AS "post_related",
                (
                    SELECT FETCH_POST_PARENT(cms_post.post_parent_id))           AS "post_parent"
         FROM cms_post
         WHERE cms_post.slug = FETCH_POST.i LIMIT 1
     ) t;

$$
LANGUAGE sql;

-- FETCH_PUBLICATION
CREATE
OR REPLACE FUNCTION FETCH_PUBLICATION(i int, user_id int = null) RETURNS json AS
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

$$
LANGUAGE sql;

-- FETCH_PUBLICATION
CREATE
OR REPLACE FUNCTION FETCH_PUBLICATION(host varchar, user_id int = null) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT pa.*,
                (
                    SELECT IS_FOLLOWING('publisher_publication', pa.id, FETCH_PUBLICATION.user_id)
                ) AS is_following,
                (
                    SELECT COUNT_FOLLOWED('publisher_publication', pa.id)
                ),
                (
                    SELECT array_to_json(array_agg(row_to_json(e)))
                    FROM (
                             SELECT mm.id
                             FROM cms_publication mm
                                      JOIN cms_publicationcooperation cp ON mm.id = cp.cooperation_id
                             WHERE cp.publication_id = pa.id
                         ) e
                ) AS corps
         FROM cms_publication pa
         WHERE pa."host" = FETCH_PUBLICATION."host"
     ) t;

$$
LANGUAGE sql;

-- FETCH_ACTION
CREATE
OR REPLACE FUNCTION FETCH_ACTION(i int, user_id int = null) RETURNS json AS
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

$$
LANGUAGE SQL;

-- FETCH_MEDIA
CREATE
OR REPLACE FUNCTION FETCH_MEDIA(i int) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT mm.id,
                mm.title,
                (SELECT MAKE_THUMB(mm.path)) as sizes
         FROM media_media mm
         WHERE mm.id = i LIMIT 1
     ) t;

$$
LANGUAGE sql;

-- FETCH_MEDIAS
CREATE
OR REPLACE FUNCTION FETCH_MEDIAS(i int[]) RETURNS json AS
$$
SELECT array_to_json(array_agg(row_to_json(t)))
FROM (
         SELECT mm.id,
                mm.title,
                (SELECT MAKE_THUMB(mm.path)) as sizes
         FROM media_media mm
         WHERE mm.id = ANY (i)
     ) t;

$$
LANGUAGE sql;

-- FETCH_TERM
CREATE
OR REPLACE FUNCTION FETCH_TERM(i int) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT ct.*
         FROM cms_term ct
         WHERE ct.id = i LIMIT 1
     ) t;

$$
LANGUAGE SQL;

-- FETCH_TAXONOMY
CREATE
OR REPLACE FUNCTION FETCH_TAXONOMY(slug varchar, pub_id int, taxonomy varchar, user_id int = null) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT cp.*,
                (SELECT FETCH_TERM(cp.term_id))   AS "term",
                (
                    SELECT row_to_json(e)
                    FROM (
                             SELECT ct2.id,
                                    ct2.taxonomy,
                                    (SELECT FETCH_TERM(ct2.term_id)) AS "term"
                             FROM cms_publicationterm ct2
                             WHERE ct2.id = cp.parent_id
                             GROUP BY ct2.id LIMIT 1
                         ) e
                )                                 AS "parent",
                (
                    SELECT array_to_json(array_agg(row_to_json(e)))
                    FROM (
                             SELECT ct2.id,
                                    ct2.taxonomy,
                                    ct2.publication_id,
                                    (SELECT FETCH_TERM(ct2.term_id)) AS "term"
                             FROM cms_publicationterm ct2
                                      LEFT JOIN cms_publicationterm_related cpr ON ct2.id = cpr.to_publicationterm_id
                             WHERE cpr.from_publicationterm_id = cp.id
                             GROUP BY ct2.id
                         ) e
                )                                 AS "related",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT cpt.id,
                                    cpt.title
                             FROM cms_post cpt
                                      JOIN cms_post_terms cpt2 on cpt.id = cpt2.post_id
                             WHERE cpt2.publicationterm_id = cp.id
                         ) t
                )                                 AS "posts",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT csk.id,
                                    csk.title
                             FROM cms_searchkeyword csk
                                      JOIN cms_term_suggestions cts ON csk.id = cts.searchkeyword_id
                             WHERE cts.term_id = cp.term_id
                         ) t
                )                                 AS "suggestions",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT cskv.id,
                                    cskv.value,
                                    cskv.date_taken
                             FROM cms_searchkeywordvolume cskv
                                      JOIN cms_searchkeyword csk on cskv.search_keyword_id = csk.id
                             WHERE csk.slug = ct.slug
                             ORDER BY cskv.id
                         ) t
                )                                 AS "searches",
                (
                    SELECT row_to_json(t)
                    FROM (
                             SELECT csk.id,
                                    csk.title,
                                    csk.fetch_status
                             FROM cms_searchkeyword csk
                             WHERE csk.slug = ct.slug LIMIT 1
                         ) t
                )                                 AS "keyword",
                (
                    SELECT COUNT(*)
                    FROM (SELECT cppr.id FROM cms_post_terms cppr WHERE cppr.publicationterm_id = cp.id) e
                )                                 AS "total_post",
                (SELECT FETCH_MEDIA(cp.media_id)) AS "media"
         FROM cms_publicationterm cp
                  JOIN cms_term ct on cp.term_id = ct.id
         WHERE ct.slug = FETCH_TAXONOMY.slug
           AND cp.publication_id = pub_id
           AND cp.taxonomy = FETCH_TAXONOMY.taxonomy
     ) t;

$$
LANGUAGE sql;

-- FETCH_TAXONOMY_BY_ID
CREATE
OR REPLACE FUNCTION FETCH_TAXONOMY_BY_ID(id int) RETURNS json AS
$$
DECLARE
post_arr int[] = (SELECT (ARRAY(
            SELECT m.id
            FROM cms_post m
                     JOIN cms_post_terms cpt ON m.id = cpt.post_id
            WHERE FETCH_TAXONOMY_BY_ID.id = cpt.publicationterm_id
        )));
BEGIN
RETURN (SELECT row_to_json(t)
        FROM (
                 SELECT cp.*,
                        (SELECT FETCH_TERM(cp.term_id))   AS "term",
                        (SELECT FETCH_MEDIA(cp.media_id)) AS "media",
                        (SELECT ARRAY(SELECT r.id
                                          FROM (SELECT x.id,
                                                       (
                                                           SELECT COUNT(*)
                                                           FROM (SELECT y.id
                                                                 FROM cms_post_terms y
                                                                 WHERE y.publicationterm_id = x.id
                                                                   AND y.post_id = ANY (post_arr)) d
                                                       ) AS "dub_count"
                                                FROM cms_publicationterm x
                                                WHERE x.publication_id = cp.publication_id
                                                  AND x.taxonomy = cp.taxonomy
                                                ORDER BY "dub_count" DESC
                                                LIMIT 20) r))
                                                          AS "related"
                 FROM cms_publicationterm cp
                 WHERE cp.id = FETCH_TAXONOMY_BY_ID.id LIMIT 1
             ) t);
END
$$
LANGUAGE plpgsql;

-- FETCH_TERM_WITH_TAX
CREATE
OR REPLACE FUNCTION FETCH_TERM_WITH_TAX(slug varchar, publication int) RETURNS json AS
$$
SELECT row_to_json(t)
FROM (
         SELECT ct.*,
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT cpt.id,
                                    cpt.description,
                                    cpt.taxonomy,
                                    cpt.options,
                                    (SELECT FETCH_MEDIA(cpt.media_id)) AS "media",
                                    (
                                        SELECT row_to_json(e)
                                        FROM (
                                                 SELECT cpt2.id,
                                                        cpt2.taxonomy,
                                                        (SELECT FETCH_TERM(cpt2.term_id)) as "term"
                                                 FROM cms_publicationterm cpt2
                                                 WHERE cpt2.id = cpt.parent_id LIMIT 1
                                             ) e
                                    )                                  as "parent",
                                    (SELECT array_to_json(array_agg(row_to_json(e)))
                                     FROM (
                                              SELECT ct2.id,
                                                     ct2.taxonomy,
                                                     ct2.publication_id,
                                                     (SELECT FETCH_TERM(ct2.term_id)) AS "term"
                                              FROM cms_publicationterm ct2
                                                       LEFT JOIN cms_publicationterm_related cpr ON ct2.id = cpr.to_publicationterm_id
                                              WHERE cpr.from_publicationterm_id = cpt.id
                                              GROUP BY ct2.id
                                          ) e
                                    )                                  AS "related"
                             FROM cms_publicationterm cpt
                             WHERE cpt.publication_id = FETCH_TERM_WITH_TAX.publication
                               and cpt.term_id = ct.id
                         ) t
                ) AS "instances",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT cpt.id,
                                    cpt.title
                             FROM cms_post cpt
                                      JOIN cms_post_terms ccpt on cpt.id = ccpt.post_id
                                      JOIN cms_publicationterm cp on ccpt.publicationterm_id = cp.id
                             WHERE cpt.primary_publication_id = FETCH_TERM_WITH_TAX.publication
                               AND cp.term_id = ct.id
                         ) t
                ) AS "posts",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT csk.id,
                                    csk.title
                             FROM cms_searchkeyword csk
                                      JOIN cms_term_suggestions cts ON csk.id = cts.searchkeyword_id
                             WHERE cts.term_id = ct.id
                         ) t
                ) AS "suggestions",
                (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT cts.id,
                                    cts.value,
                                    cts.date_taken
                             FROM cms_searchkeywordvolume cts
                                      JOIN cms_searchkeyword cs on cts.search_keyword_id = cs.id
                             WHERE cs.slug = ct.slug
                             ORDER BY cts.id
                         ) t
                ) AS "searches",
                (
                    SELECT row_to_json(t)
                    FROM (
                             SELECT cts.id,
                                    cts.title,
                                    cts.fetch_status
                             FROM cms_searchkeyword cts
                             WHERE cts.slug = ct.slug LIMIT 1
                         ) t
                ) AS "keyword"
         FROM cms_term ct
         WHERE ct.slug = FETCH_TERM_WITH_TAX.slug LIMIT 1
     ) t;

$$
LANGUAGE SQL;
--

-- FETCH_TERMS
CREATE
OR REPLACE FUNCTION FETCH_TERMS(page_size int = NULL,
                                       os int = NULL,
                                       search varchar = NULL,
                                       order_by varchar = NULL) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT aa.*
                             FROM cms_term aa
                             WHERE CASE
                                       WHEN FETCH_TERMS.search IS NOT NULL THEN
                                           LOWER(aa.title) LIKE LOWER(CONCAT('%', FETCH_TERMS.search, '%'))
                                       ELSE TRUE END
                             ORDER BY aa.id DESC LIMIT page_size
                             OFFSET os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT aa.id
                             FROM cms_term aa
                             WHERE CASE
                                       WHEN FETCH_TERMS.search IS NOT NULL THEN
                                           LOWER(aa.title) LIKE LOWER(CONCAT('%', FETCH_TERMS.search, '%'))
                                       ELSE TRUE END
                         ) t
                ) AS count
     ) e $$ LANGUAGE SQL;

-- FETCH_TERMS_WITH_SEARCH
CREATE
OR REPLACE FUNCTION FETCH_TERMS_WITH_SEARCH(page_size int = NULL,
                                                   os int = NULL,
                                                   search varchar = NULL,
                                                   order_by varchar = NULL,
                                                   taxonomy varchar = NULL,
                                                   publication int = NULL) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT aa.*,
                                    (
                                        SELECT COUNT(*)
                                        FROM (
                                                 SELECT cpt.id
                                                 FROM cms_post cpt
                                                          JOIN cms_post_terms ccpt on cpt.id = ccpt.post_id
                                                          JOIN cms_publicationterm cp on ccpt.publicationterm_id = cp.id
                                                 WHERE cpt.primary_publication_id = FETCH_TERMS_WITH_SEARCH.publication
                                                   AND cp.term_id = aa.id
                                             ) t
                                    ) AS "count_post",
                                    (
                                        SELECT row_to_json(t)
                                        FROM (
                                                 SELECT cts.id,
                                                        cts.value,
                                                        cts.date_taken
                                                 FROM cms_searchkeywordvolume cts
                                                          JOIN cms_searchkeyword cs on cts.search_keyword_id = cs.id
                                                 WHERE cs.slug = aa.slug
                                                 ORDER BY cts.date_taken LIMIT 1
                                             ) t
                                    ) AS "search",
                                    (
                                        SELECT row_to_json(t)
                                        FROM (
                                                 SELECT cts.id,
                                                        cts.title,
                                                        cts.fetch_status
                                                 FROM cms_searchkeyword cts
                                                 WHERE cts.slug = aa.slug LIMIT 1
                                             ) t
                                    ) AS "keyword"
                             FROM cms_term aa
                                      JOIN cms_publicationterm cpt on aa.id = cpt.term_id
                             WHERE CASE
                                       WHEN FETCH_TERMS_WITH_SEARCH.search IS NOT NULL THEN
                                               LOWER(aa.title) LIKE
                                               LOWER(CONCAT('%', FETCH_TERMS_WITH_SEARCH.search, '%'))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TERMS_WITH_SEARCH.taxonomy IS NOT NULL THEN
                                           cpt.taxonomy = FETCH_TERMS_WITH_SEARCH.taxonomy
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TERMS_WITH_SEARCH.publication IS NOT NULL THEN
                                           cpt.publication_id = FETCH_TERMS_WITH_SEARCH.publication
                                       ELSE FALSE END
                             GROUP BY aa.id
                             ORDER BY aa.id LIMIT page_size
                             OFFSET os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT aa.id
                             FROM cms_term aa
                                      JOIN cms_publicationterm cpt on aa.id = cpt.term_id
                             WHERE CASE
                                       WHEN FETCH_TERMS_WITH_SEARCH.search IS NOT NULL THEN
                                               LOWER(aa.title) LIKE
                                               LOWER(CONCAT('%', FETCH_TERMS_WITH_SEARCH.search, '%'))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TERMS_WITH_SEARCH.taxonomy IS NOT NULL THEN
                                           cpt.taxonomy = FETCH_TERMS_WITH_SEARCH.taxonomy
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_TERMS_WITH_SEARCH.publication IS NOT NULL THEN
                                           cpt.publication_id = FETCH_TERMS_WITH_SEARCH.publication
                                       ELSE FALSE END
                             GROUP BY aa.id
                         ) t
                ) AS count
     ) e $$ LANGUAGE SQL;

-- FETCH_ACTIVITIES
CREATE
OR REPLACE FUNCTION FETCH_ACTIVITIES(page_size int = NULL,
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
                             ORDER BY aa.id DESC LIMIT page_size
                             OFFSET os
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
     ) e $$ LANGUAGE sql;

-- FETCH_POSTS
CREATE
OR REPLACE FUNCTION FETCH_POSTS(page_size int = NULL,
                                       os int = NULL,
                                       search varchar = NULL,
                                       order_by varchar = NULL,
                                       user_id int = NULL,
                                       post_type varchar = NULL,
                                       status varchar = NULL,
                                       guess_post boolean = NULL,
                                       show_cms boolean = NULL,
                                       taxonomies_operator varchar = NULL,
                                       taxonomies integer[] = NULL,
                                       publications integer[] = NULL,
                                       post_related_operator varchar = NULL,
                                       post_related integer[] = NULL,
                                       meta jsonb = NULL) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT aa.*,
                                    (SELECT FETCH_USER_ID(aa.user_id))                         AS "user",
                                    (SELECT FETCH_MEDIA(CAST(aa.meta ->> 'media' AS INTEGER))) AS "media",
                                    (
                                        SELECT array_to_json(array_agg(row_to_json(t)))
                                        FROM (
                                                 SELECT mm.id,
                                                        (SELECT MAKE_THUMB(mm.path)) as sizes
                                                 FROM media_media mm
                                                          JOIN LATERAL jsonb_array_elements_text(aa.meta -> 'medias') ids
                                                 ON TRUE
                                                 WHERE mm.id::text = ids
                                             ) t
                                    )                                                          AS "medias",
                                    (
                                        SELECT array_to_json(array_agg(row_to_json(t)))
                                        FROM (
                                                 SELECT ct.id,
                                                        ct.taxonomy,
                                                        (SELECT FETCH_TERM(ct.term_id)) AS "term"
                                                 FROM cms_publicationterm ct
                                                          JOIN cms_post_terms cpt on ct.id = cpt.publicationterm_id
                                                 WHERE cpt.post_id = aa.id
                                                 GROUP BY ct.id
                                             ) t
                                    )                                                          AS "terms",
                                    (
                                        SELECT FETCH_POST_RELATED(aa.id, NULL, TRUE)
                                    )                                                          AS "post_related",
                                    (
                                        SELECT FETCH_POST_PARENT(aa.post_parent_id))           AS "post_parent",
                                    (
                                        SELECT VOTE_OBJECT(FETCH_POSTS.user_id,
                                                           CAST(aa.options ->> 'action_post' AS INTEGER))
                                    )                                                          AS "vote",
                                    (
                                        SELECT FETCH_COMMENTS(5, 0, NULL, FETCH_POSTS.user_id, NULL,
                                                              CAST(aa.options ->> 'action_post' AS INTEGER))
                                    )                                                          AS "comment",
                                    (
                                        SELECT IS_FOLLOWING('', CAST(aa.options ->> 'action_post' AS INTEGER),
                                                            FETCH_POSTS.user_id)
                                    )                                                          AS "following"
                             FROM cms_post aa
                             WHERE aa.db_status = 1
                               AND CASE
                                       WHEN FETCH_POSTS.post_type IS NOT NULL THEN aa.post_type = FETCH_POSTS.post_type
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.status IS NOT NULL THEN aa.status = FETCH_POSTS.status
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.guess_post IS NOT NULL
                                           THEN aa.is_guess_post = FETCH_POSTS.guess_post
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.show_cms IS NOT NULL THEN aa.show_cms = FETCH_POSTS.show_cms
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.search IS NOT NULL THEN
                                           LOWER(aa.title) LIKE LOWER(CONCAT('%', FETCH_POSTS.search, '%'))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.taxonomies IS NOT NULL THEN
                                           (SELECT IS_IN_TERMS(aa.id, taxonomies_operator, FETCH_POSTS.taxonomies))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.post_related IS NOT NULL THEN
                                           (SELECT IS_IN_POST_RELATED(aa.id, FETCH_POSTS.post_related_operator,
                                                                      FETCH_POSTS.post_related))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.publications IS NOT NULL THEN
                                               (SELECT IS_IN_PUBS(aa.id, FETCH_POSTS.publications))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.meta IS NOT NULL THEN
                                           aa.meta::jsonb @> FETCH_POSTS.meta
                                       ELSE TRUE END
                             ORDER BY aa.id DESC LIMIT page_size
                             OFFSET os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT aa.id
                             FROM cms_post aa
                             WHERE aa.db_status = 1
                               AND CASE
                                       WHEN FETCH_POSTS.post_type IS NOT NULL THEN aa.post_type = FETCH_POSTS.post_type
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.status IS NOT NULL THEN aa.status = FETCH_POSTS.status
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.guess_post IS NOT NULL
                                           THEN aa.is_guess_post = FETCH_POSTS.guess_post
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.show_cms IS NOT NULL THEN aa.show_cms = FETCH_POSTS.show_cms
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
                                       WHEN FETCH_POSTS.post_related IS NOT NULL THEN
                                           (SELECT IS_IN_POST_RELATED(aa.id, FETCH_POSTS.post_related_operator,
                                                                      FETCH_POSTS.post_related))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.publications IS NOT NULL THEN
                                               (SELECT IS_IN_PUBS(aa.id, FETCH_POSTS.publications))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS.meta IS NOT NULL THEN
                                           aa.meta::jsonb @> FETCH_POSTS.meta
                                       ELSE TRUE END
                         ) t
                ) AS count
     ) e $$ LANGUAGE SQL;

-- FETCH_POSTS_X
CREATE
OR REPLACE FUNCTION FETCH_POSTS_X(page_size int = NULL,
                                         os int = NULL,
                                         search varchar = NULL,
                                         order_by varchar = NULL,
                                         user_id int = NULL,
                                         post_type varchar = NULL,
                                         status varchar = NULL,
                                         guess_post boolean = NULL,
                                         show_cms boolean = NULL,
                                         taxonomies_operator varchar = NULL,
                                         taxonomies integer[] = NULL,
                                         publications integer[] = NULL,
                                         post_related_operator varchar = NULL,
                                         post_related integer[] = NULL,
                                         related integer = NULL,
                                         meta jsonb = NULL) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT aa.*,
                                    (SELECT FETCH_USER_ID(aa.user_id))                         AS "user",
                                    (SELECT FETCH_MEDIA(CAST(aa.meta ->> 'media' AS INTEGER))) AS "media",
                                    (
                                        SELECT array_to_json(array_agg(row_to_json(t)))
                                        FROM (
                                                 SELECT mm.id,
                                                        (SELECT MAKE_THUMB(mm.path)) as sizes
                                                 FROM media_media mm
                                                          JOIN LATERAL jsonb_array_elements_text(aa.meta -> 'medias') ids
                                                 ON TRUE
                                                 WHERE mm.id::text = ids
                                             ) t
                                    )                                                          AS "medias",
                                    (
                                        SELECT array_to_json(array_agg(row_to_json(t)))
                                        FROM (
                                                 SELECT ct.id,
                                                        ct.taxonomy,
                                                        (SELECT FETCH_TERM(ct.term_id)) AS "term"
                                                 FROM cms_publicationterm ct
                                                          JOIN cms_post_terms cpt on ct.id = cpt.publicationterm_id
                                                 WHERE cpt.post_id = aa.id
                                                 GROUP BY ct.id
                                             ) t
                                    )                                                          AS "terms",
                                    (
                                        SELECT FETCH_POST_RELATED(aa.id, NULL, TRUE)
                                    )                                                          AS "post_related",
                                    (
                                        SELECT FETCH_POST_PARENT(aa.post_parent_id))           AS "post_parent",
                                    (
                                        SELECT VOTE_OBJECT(FETCH_POSTS_X.user_id,
                                                           CAST(aa.options ->> 'action_post' AS INTEGER))
                                    )                                                          AS "vote",
                                    (
                                        SELECT FETCH_COMMENTS(5, 0, NULL, FETCH_POSTS_X.user_id, NULL,
                                                              CAST(aa.options ->> 'action_post' AS INTEGER))
                                    )                                                          AS "comment",
                                    (
                                        SELECT IS_FOLLOWING('cms_post', CAST(aa.id AS INTEGER),
                                                            FETCH_POSTS_X.user_id)
                                    )                                                          AS "following"
                             FROM cms_post aa
                                      LEFT JOIN cms_post cpx on cpx.id = FETCH_POSTS_X.related
                             WHERE aa.db_status = 1
                               AND CASE
                                       WHEN FETCH_POSTS_X.post_type IS NOT NULL
                                           THEN aa.post_type = FETCH_POSTS_X.post_type
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.status IS NOT NULL THEN aa.status = FETCH_POSTS_X.status
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.guess_post IS NOT NULL
                                           THEN aa.is_guess_post = FETCH_POSTS_X.guess_post
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.show_cms IS NOT NULL THEN aa.show_cms = FETCH_POSTS_X.show_cms
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.search IS NOT NULL THEN
                                               LOWER(aa.title) LIKE LOWER(CONCAT('%', FETCH_POSTS_X.search, '%'))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.taxonomies IS NOT NULL THEN
                                           (SELECT IS_IN_TERMS(aa.id, taxonomies_operator, FETCH_POSTS_X.taxonomies))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.post_related IS NOT NULL THEN
                                           (SELECT IS_IN_POST_RELATED(aa.id, FETCH_POSTS_X.post_related_operator,
                                                                      FETCH_POSTS_X.post_related))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.publications IS NOT NULL THEN
                                               (SELECT IS_IN_PUBS(aa.id, FETCH_POSTS_X.publications))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.meta IS NOT NULL THEN
                                           aa.meta::jsonb @> FETCH_POSTS_X.meta
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.related IS NOT NULL THEN
                                               cpx.primary_publication_id = aa.primary_publication_id
                                               AND cpx.post_type = cpx.post_type
                                               AND cpx.show_cms = TRUE
                                               AND cpx.id != aa.id
                                       ELSE TRUE END
                             ORDER BY aa.id DESC LIMIT page_size
                             OFFSET os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT aa.id
                             FROM cms_post aa
                                      LEFT JOIN cms_post cpx on cpx.id = FETCH_POSTS_X.related
                             WHERE aa.db_status = 1
                               AND CASE
                                       WHEN FETCH_POSTS_X.post_type IS NOT NULL
                                           THEN aa.post_type = FETCH_POSTS_X.post_type
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.status IS NOT NULL THEN aa.status = FETCH_POSTS_X.status
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.guess_post IS NOT NULL
                                           THEN aa.is_guess_post = FETCH_POSTS_X.guess_post
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.show_cms IS NOT NULL THEN aa.show_cms = FETCH_POSTS_X.show_cms
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.search IS NOT NULL THEN
                                               LOWER(aa.title) LIKE LOWER(CONCAT('%', FETCH_POSTS_X.search, '%'))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.taxonomies IS NOT NULL THEN
                                           (SELECT IS_IN_TERMS(aa.id, taxonomies_operator, FETCH_POSTS_X.taxonomies))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.post_related IS NOT NULL THEN
                                           (SELECT IS_IN_POST_RELATED(aa.id, FETCH_POSTS_X.post_related_operator,
                                                                      FETCH_POSTS_X.post_related))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.publications IS NOT NULL THEN
                                               (SELECT IS_IN_PUBS(aa.id, FETCH_POSTS_X.publications))
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.meta IS NOT NULL THEN
                                           aa.meta::jsonb @> FETCH_POSTS_X.meta
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_POSTS_X.related IS NOT NULL THEN
                                               cpx.primary_publication_id = aa.primary_publication_id
                                               AND cpx.post_type = cpx.post_type
                                               AND cpx.show_cms = TRUE
                                               AND cpx.id != aa.id
                                       ELSE TRUE END
                         ) t
                ) AS count
     ) e $$ LANGUAGE SQL;

-- FETCH_FETCH_TERM_TAXONOMIES
CREATE
OR REPLACE FUNCTION FETCH_TERM_TAXONOMIES(page_size int = NULL,
                                                 os int = NULL,
                                                 search varchar = NULL,
                                                 order_by varchar = NULL,
                                                 user_id int = null,
                                                 taxonomy varchar = NULL,
                                                 taxonomies integer[] = NULL,
                                                 publication integer = NULL) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT ct.*,
                                    (SELECT FETCH_TERM(ct.term_id)) AS "term",
                                    (
                                        SELECT COUNT(*)
                                        FROM (
                                                 SELECT cppr.id
                                                 FROM cms_post_terms cppr
                                                 WHERE cppr.publicationterm_id = ct.id
                                             ) e
                                    )                               AS "total_post"

                             FROM cms_publicationterm ct
                                      JOIN cms_term term on ct.term_id = term.id
                             WHERE ct.db_status = 1
                               AND CASE
                                       WHEN FETCH_TERM_TAXONOMIES.publication IS NOT NULL THEN
                                           ct.publication_id = FETCH_TERM_TAXONOMIES.publication
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
                                               LOWER(term.title) LIKE
                                               LOWER(CONCAT('%', FETCH_TERM_TAXONOMIES.search, '%'))
                                       ELSE TRUE END
                             GROUP BY ct.id
                             ORDER BY ct.id DESC LIMIT page_size
                             OFFSET os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT ct.id
                             FROM cms_publicationterm ct
                                      JOIN cms_term term on ct.term_id = term.id
                             WHERE ct.db_status = 1
                               AND CASE
                                       WHEN FETCH_TERM_TAXONOMIES.publication IS NOT NULL THEN
                                           ct.publication_id = FETCH_TERM_TAXONOMIES.publication
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
                                               LOWER(term.title) LIKE
                                               LOWER(CONCAT('%', FETCH_TERM_TAXONOMIES.search, '%'))
                                       ELSE TRUE END
                         ) t
                ) AS count
     ) e $$ LANGUAGE SQL;

-- FETCH_COMMENTS
CREATE
OR REPLACE FUNCTION FETCH_COMMENTS(page_size int = NULL,
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
                             SELECT ac.*,
                                    (SELECT FETCH_USER_ID(ac.user_id)) as "user"
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
                             ORDER BY ac.id DESC LIMIT page_size
                             OFFSET os
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
     ) e $$ LANGUAGE SQL;

-- FETCH_ORDER_ITEMS
CREATE
OR REPLACE FUNCTION PUBLIC.FETCH_ORDER_ITEMS(page_size int = NULL,
                                                    os int = NULL,
                                                    order_by varchar = NULL,
                                                    order_id int = NULL,
                                                    shopping_profile int = NULL,
                                                    product_id int = NULL) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT co.*,
                                    (SELECT FETCH_POST(co.product_id, NULL, NULL, NULL)) AS "product"
                             FROM commerce_orderitem co
                             WHERE co.db_status = 1
                               AND co.shopping_profile_id = FETCH_ORDER_ITEMS.shopping_profile
                               AND CASE
                                       WHEN FETCH_ORDER_ITEMS.order_id IS NULL THEN co.order_id IS NULL
                                       ELSE co.order_id = FETCH_ORDER_ITEMS.order_id END
                             GROUP BY co.id
                             ORDER BY co.id DESC LIMIT page_size
                             OFFSET os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT co.id
                             FROM commerce_orderitem co
                             WHERE co.db_status = 1
                               AND CASE
                                       WHEN FETCH_ORDER_ITEMS.order_id IS NULL THEN co.order_id IS NULL
                                       ELSE co.order_id = FETCH_ORDER_ITEMS.order_id END
                             GROUP BY co.id
                         ) t
                ) AS count
     ) e $$ LANGUAGE SQL;

-- FETCH_RELATED_POST
CREATE
OR REPLACE FUNCTION FETCH_RELATED_POST(id int, post_type varchar = NULL, lm int = 6) RETURNS JSON AS
$$
WITH post AS (SELECT cp.post_type, cp.primary_publication_id FROM cms_post cp WHERE cp.id = FETCH_RELATED_POST.id)
SELECT array_to_json(array_agg(row_to_json(t)))
FROM (
         SELECT a.id,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT cpt.id
                             FROM cms_publicationterm cpt
                                      JOIN cms_post_terms c on cpt.id = c.publicationterm_id
                                      JOIN cms_post_terms c2 on cpt.id = c2.publicationterm_id
                             WHERE c.post_id = a.id
                               AND c2.post_id = FETCH_RELATED_POST.id
                         ) e
                ) as "count"
         FROM cms_post a
         WHERE CASE
                   WHEN FETCH_RELATED_POST.post_type IS NOT NULL THEN a.post_type = FETCH_RELATED_POST.post_type
                   ELSE a.post_type = (SELECT FETCH_RELATED_POST.post_type FROM post) END
           AND a.primary_publication_id = (SELECT primary_publication_id FROM post)
           AND a.id != FETCH_RELATED_POST.id
         GROUP BY a.id
         ORDER BY count DESC
             LIMIT FETCH_RELATED_POST.lm
     ) t $$ LANGUAGE SQL;

-- FETCH_CONTRIBUTIONS
CREATE
OR REPLACE FUNCTION FETCH_CONTRIBUTIONS(
    page_size int = NULL,
    os int = NULL,
    order_by varchar = NULL,
    target_content_type int = NULL,
    target_object_id int = NULL,
    contributor int = NULL,
    field varchar = NULL
) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT aa.*
                             FROM cms_contribute aa
                             WHERE FETCH_CONTRIBUTIONS.target_content_type = aa.target_content_type_id
                               AND FETCH_CONTRIBUTIONS.target_object_id = CAST(aa.target_object_id as int)
                               AND CASE
                                       WHEN FETCH_CONTRIBUTIONS.contributor IS NOT NULL
                                           THEN FETCH_CONTRIBUTIONS.contributor = aa.user_id
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_CONTRIBUTIONS.field IS NOT NULL
                                           THEN FETCH_CONTRIBUTIONS.field = aa.field
                                       ELSE TRUE END
                             ORDER BY aa.id DESC LIMIT page_size
                             OFFSET os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT aa.id
                             FROM cms_contribute aa
                             WHERE FETCH_CONTRIBUTIONS.target_content_type = aa.target_content_type_id
                               AND FETCH_CONTRIBUTIONS.target_object_id = CAST(aa.target_object_id as int)
                               AND CASE
                                       WHEN FETCH_CONTRIBUTIONS.contributor IS NOT NULL
                                           THEN FETCH_CONTRIBUTIONS.contributor = aa.user_id
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_CONTRIBUTIONS.field IS NOT NULL
                                           THEN FETCH_CONTRIBUTIONS.field = aa.field
                                       ELSE TRUE END
                         ) t
                ) AS count
     ) e $$ LANGUAGE SQL;

-- FETCH_LIST_FOLLOWING
CREATE
OR REPLACE FUNCTION FETCH_LIST_FOLLOWING(
    page_size int = NULL,
    os int = NULL,
    user_id int = NULL,
    content_type int = NULL,
    object_ids int[] = NULL
) RETURNS JSON AS
$$
SELECT row_to_json(e)
FROM (
         SELECT (
                    SELECT array_to_json(array_agg(row_to_json(t)))
                    FROM (
                             SELECT *,
                                    (
                                        SELECT GFK_QUERY(
                                                       aa.content_type_id,
                                                       aa.object_id,
                                                       null
                                                   )
                                    ) AS instance
                             FROM activity_follow aa
                             WHERE FETCH_LIST_FOLLOWING.user_id = aa.user_id
                               AND CASE
                                       WHEN FETCH_LIST_FOLLOWING.content_type IS NOT NULL THEN
                                           FETCH_LIST_FOLLOWING.content_type = aa.content_type_id
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_LIST_FOLLOWING.object_ids IS NOT NULL THEN
                                           aa.content_type_id = ANY (FETCH_LIST_FOLLOWING.object_ids)
                                       ELSE TRUE END
                             ORDER BY aa.id DESC LIMIT page_size
                             OFFSET os
                         ) t
                ) AS results,
                (
                    SELECT COUNT(*)
                    FROM (
                             SELECT aa.id
                             FROM activity_follow aa
                             WHERE FETCH_LIST_FOLLOWING.user_id = aa.user_id
                               AND CASE
                                       WHEN FETCH_LIST_FOLLOWING.content_type IS NOT NULL THEN
                                           FETCH_LIST_FOLLOWING.content_type = aa.content_type_id
                                       ELSE TRUE END
                               AND CASE
                                       WHEN FETCH_LIST_FOLLOWING.object_ids IS NOT NULL THEN
                                           aa.content_type_id = ANY (FETCH_LIST_FOLLOWING.object_ids)
                                       ELSE TRUE END
                         ) t
                ) AS count
     ) e $$ LANGUAGE sql;

SELECT FETCH_POST(76452, FALSE, NULL, NULL, NULL);
SELECT FOLLOW_OBJECTS(1, 22, '{11256,11259,11255}');
SELECT FETCH_TAXONOMY_BY_ID(1);