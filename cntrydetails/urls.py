from django.urls import path
from .views import CountryList
urlpatterns = [
    path('list/all/',CountryList.as_view(),name='country_list'),
]