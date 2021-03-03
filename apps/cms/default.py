def publication_options():
    return {
        "taxonomies": [
            {
                "label": 'keyword',
                "title": 'Keyword',
                "description": None
            },
            {
                "label": 'category',
                "title": 'Category',
                "description": None
            },
            {
                "label": 'tag',
                "title": 'Tag',
                "description": None
            }
        ],
        "post_types": [
            {
                "label": 'article',
                "title": 'Article',
                "description": None
            },
            {
                "label": 'post',
                "title": 'Post',
                "description": None
            }
        ],
        "post_fields": []
    }


def theme_options():
    return {
        "header": {},
        "layout": {},
        "menu": {},
        "css": {},
        "widget": {},
        "homepage": {}
    }


def publication_cooperation_options():
    return {
        "mapping": [
            {"left": {"taxonomy": "tag"}, "right": {"post_type": "post"}},
            {"left": {"post_type": "post"}, "right": {"post_type": "post"}},
        ],
    }
