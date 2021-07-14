POST_DETAIL = [
    "id",
    "to",
    "title",
    "content",
    "slug",
    "description",
    "post_type",
    "created",
    "comment",
    "media",
    "medias",
    "meta",
    {
        "user": [
            "username",
            "first_name",
            "last_name",
            {
                "profile": [
                    {
                        "media": ["sizes", "id"]
                    }
                ]
            }
        ]
    },
    {
        "terms": [
            "taxonomy",
            {
                "term": ["title", "slug"]
            }
        ]
    },
    "collaborators",
    {
        "related": [
            "id",
            "title",
            "slug",
            "description",
            "user",
            "media",
            "post_type"
        ]
    }
]
POST_LIST = [
    "id",
    "to",
    "title",
    "slug",
    "post_type",
    "description",
    "user",
    "media",
]
TERM_DETAIL = [
    "id",
    "to",
    "description",
    "media",
    "taxonomy",
    {
        "term": [
            "title",
            "slug"
        ]
    },
    "meta"
]
TERM_LIST = [
    "id",
    "to",
    "description",
    "media",
    "taxonomy",
    {
        "term": [
            "title",
            "slug"
        ]
    },
    "meta"
]
USER_DETAIL = [
    "id",
    "to",
    "username",
    "first_name",
    "last_name",
    {
        "profile": ["media", "full_name"]
    },
]
