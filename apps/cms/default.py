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
        "layout": {},
        "menu": {},
        "css": {},
        "widget": {},
        "homepage": {}
    }
