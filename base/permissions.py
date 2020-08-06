from rest_framework import permissions

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


class CorePermission(permissions.BasePermission):
    pass


class IsSuperUserOrReadOnly(CorePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            if request.user and request.user.is_authenticated:
                if request.user.is_superuser:
                    return True

        return False


class IsSuperUserCanDeleteOrReadOnly(CorePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff:
                return True
            else:
                if request.method == "DELETE":
                    return False
                else:
                    return True
        else:
            if request.method in permissions.SAFE_METHODS:
                return True
        return False


# has permissions decorator
# use before view function
# example:
#
# @has_permissions('ADD_DEPARTMENT', 'EDIT_DEPARTMENT')
# def get(self, request, *args, **kwargs)
#
def has_permissions(*decorator_args):
    def decorator(function):
        def wrapper(self, request, *args, **kwargs):
            # get permissions from decorator arguments
            function_permissions = set(decorator_args)
            # check user authenticated
            if request.user and request.user.is_authenticated:
                user_permissions = request.user.permission_codes
            else:
                user_permissions = set()
            # compare functions permissions and user permissions
            if len(function_permissions - user_permissions) > 0:
                # raise exception if user does not have enough permissions
                self.permission_denied(request, message=None)

            # continue to perform request
            return function(self, request, *args, **kwargs)

        return wrapper

    return decorator


class IsAuthenticatedStaffOrReadOnly(CorePermission):
    """
    The request is authenticated as a user, or is a read-only request.
    """

    def has_permission(self, request, view):
        return (
                request.method in SAFE_METHODS or
                request.user and
                request.user.is_authenticated or
                request.user.is_staff
        )
