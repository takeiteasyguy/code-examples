from rest_framework.versioning import NamespaceVersioning
from rest_framework.generics import GenericAPIView
from django.conf.urls import include, url


class VersioningGenericView(GenericAPIView):
    """
    Generic API class for API entry points. Covered with versioning.
    """

    versioning_class = NamespaceVersioning
    default_version = 'stable'
    stable_version = 1.0
    last_version = 1.0
    allowed_versions = [1.0]
    http_method_names = []

    def main_versioning_handler(self, request, *args, **kwargs):
        if not self.http_method_names:
            raise NotImplementedError('API View Has no any HTTP methods to accept the data')
        method = request.method.lower()
        version = request.version
        # check if version is float number set it to stable instead
        try:
            version = float(version)
        except ValueError:
            version = self.stable_version
        version = str(version).replace('.', '')
        handler = '%s_%s' % (method, version)
        # if version is implemented in view return this version
        if hasattr(self, handler):
            return getattr(self, handler)(request, *args, **kwargs)
        # else if this version not in versions at all return previously implemented version
        else:
            possible_versions = filter(lambda x: x < version, self.allowed_versions)
            possible_versions = sorted(possible_versions, reverse=True)
            for possibly_existing_version in possible_versions:
                handler = '%s_%s' % (method, possibly_existing_version)
                if hasattr(self, handler):
                    return getattr(self, handler)(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.main_versioning_handler(request, args, kwargs)

    def post(self, request, *args, **kwargs):
        return self.main_versioning_handler(request, args, kwargs)

    def put(self, request, *args, **kwargs):
        return self.main_versioning_handler(request, args, kwargs)

    def patch(self, request, *args, **kwargs):
        return self.main_versioning_handler(request, args, kwargs)

    def delete(self, request):
        return self.main_versioning_handler(request)



# USAGE EXAMPLE
class SomeApiView(VersioningGenericView):
    serializer_class = SomeSerializer
    permission_classes = (IsAuthorized,)
    http_method_names = ['post', 'delete']

    def post_10(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def post_11(self, request, *args, **kwargs):
        send_email(self.request.user)
        return self.create(request, *args, **kwargs)

    def post_12(self, request, *args, **kwargs):
        send_apns_notification(self.request.user)
        return self.create(request, *args, **kwargs)

    def delete_10(self, request, *args, **kwargs):
        try:
            Model.objects.get(user=self.request.user).delete()
        except Model.DoesNotExist:
            pass
        return JSONResponse(status=204)

"""
In case if api/1.2/some-end-point is called using POST method HTTP request is handled by post_12 method; using DELETE method - delete_10
"""

# MAIN URLS
urlpatterns = [
    url(r'^api/1.0/', include("api.urls", namespace='1.0')),
    url(r'^api/1.1/', include("api.urls", namespace='1.1')),
    url(r'^api/1.2/', include("api.urls", namespace='1.2')),
    url(r'^api/stable/', include("api.urls", namespace='stable')),
    url(r'^api/last/', include("api.urls", namespace='last')),
]

# API URLS
urlpatterns = [
    url(r'^some-end-point/$', SomeApiView.as_view(), name='ome-end-point'),
]
\ No newline at end of file
