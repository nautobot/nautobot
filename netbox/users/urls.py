from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^profile/$', views.profile, name='profile'),
    url(r'^profile/password/$', views.change_password, name='change_password'),
    url(r'^profile/user-key/$', views.userkey, name='userkey'),
    url(r'^profile/user-key/edit/$', views.userkey_edit, name='userkey_edit'),
]
