from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views  # Import the login view
from setuptools.extern import names
from Agriskill import views  # Import your views
from Agriskill.views import user_login
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.user_login, name='login'),
    path('user_login/', views.user_login, name='user_login'),
    path('signup/skilled-professional/', views.skilled_professional_signup, name='skilled_professional_signup'),
    path('signup/landowner/', views.landowner_signup, name='landowner_signup'),
    path('role_selection/', views.role_selection, name='role_selection'),
    path('skilled_professional/', views.skilled_professional_home, name='skilled_professional'),
    path('landowner_home/', views.landowner_home, name='landowner_home'),
    path('logout/', views.custom_logout, name='logout'),
    path('matched_professionals/', views.matched_professionals, name='matched_professionals'),
    path('professional/<str:professional_name>/', views.landowner_results, name='landowner_results'),
    path('matched_landowners/', views.matched_landowners, name='matched_landowners'),
    path('skillshare/', views.skillshare_view, name='skillshare_view'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)