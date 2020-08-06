from sorl.thumbnail.base import ThumbnailBackend
from sorl.thumbnail.conf import settings

EXTENSIONS = {
    'JPEG': 'jpg',
    'PNG': 'png',
    'GIF': 'gif',
    'WEBP': 'webp',
}


class CThumbnailBackend(ThumbnailBackend):
    def _get_thumbnail_filename(self, source, geometry_string, options):
        path = '%s/%s' % (geometry_string, source.__str__())
        return '%s%s' % (settings.THUMBNAIL_PREFIX, path)
