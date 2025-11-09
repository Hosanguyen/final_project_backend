# backend/media_views.py
import os
from urllib.parse import unquote
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils.http import http_date
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
import mimetypes

@require_GET
def media_proxy(request):
    """
    Proxy an endpoint that serves files from MEDIA_ROOT safely.
    Expects a query param `path` containing the path returned by your API,
    e.g. /media/files/uploads/Test_1-_Database_XZ7VlJ0.pdf
    """
    raw_path = request.GET.get('path')
    if not raw_path:
        raise Http404("Missing 'path' parameter")

    # URL-decode
    raw_path = unquote(raw_path)

    # Basic sanity: ensure path starts with /media/ or media url
    # You can also accept paths without leading slash; normalize
    if raw_path.startswith(settings.MEDIA_URL):
        rel_path = raw_path[len(settings.MEDIA_URL):]
    elif raw_path.startswith('/' + settings.MEDIA_URL.lstrip('/')):
        # in case media_url begins with slash
        rel_path = raw_path[len(settings.MEDIA_URL):]
    elif raw_path.startswith('/media/'):
        rel_path = raw_path.lstrip('/')
        # remove the 'media/' prefix to get path relative to MEDIA_ROOT
        if rel_path.startswith('media/'):
            rel_path = rel_path[len('media/'):]
    else:
        # Reject any path not under /media/ to avoid exposing other FS parts
        return HttpResponseForbidden("Invalid media path")

    # Prevent path traversal
    # Join with MEDIA_ROOT and resolve real path
    file_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    file_path = os.path.realpath(file_path)
    media_root_real = os.path.realpath(str(settings.MEDIA_ROOT))

    if not file_path.startswith(media_root_real + os.sep) and file_path != media_root_real:
        # path is outside MEDIA_ROOT
        return HttpResponseForbidden("Forbidden")

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise Http404("File not found")

    # Determine content-type
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = 'application/octet-stream'

    # Create FileResponse (streaming)
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)

    # Inline so browsers try to render (PDF in iframe, video in video tag if supported)
    filename = os.path.basename(file_path)
    response['Content-Disposition'] = f'inline; filename="{filename}"'

    # Optional: add last-modified and content-length for better client behaviour
    statobj = os.stat(file_path)
    response['Content-Length'] = str(statobj.st_size)
    response['Last-Modified'] = http_date(statobj.st_mtime)

    # Important headers to allow cross-origin embedding on dev:
    # Allow your frontend origin (or use '*' for dev)
    response['Access-Control-Allow-Origin'] = '*'  # dev only; use specific origin in prod
    response['Access-Control-Expose-Headers'] = 'Content-Disposition, Content-Length, Last-Modified'
    # Allow embedding in iframe
    response['X-Frame-Options'] = 'ALLOWALL'
    # Remove/refine referrer policy if the browser blocks; set to no-referrer-when-downgrade
    response['Referrer-Policy'] = 'no-referrer-when-downgrade'
    # Optionally add:
    response['Cross-Origin-Resource-Policy'] = 'cross-origin'
    response['Cross-Origin-Opener-Policy'] = 'unsafe-none'
    response['Cross-Origin-Embedder-Policy'] = 'unsafe-none'

    return response
