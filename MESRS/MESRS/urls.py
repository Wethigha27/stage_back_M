from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Administration Django
    path('admin/', admin.site.urls),
    
    # API de l'application
    path('', include('myapp.urls')),
    
    # Redirection de la racine vers l'API
    path('', RedirectView.as_view(url='/api/', permanent=False)),
]

# Configuration pour servir les fichiers media et static en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Configuration du titre de l'admin
admin.site.site_header = "Administration MESRS"
admin.site.site_title = "MESRS Admin"
admin.site.index_title = "Gestion des Ressources Humaines"