from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token  # ⭐ 추가
from .views import RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', obtain_auth_token, name='login'),  # ⭐ 추가
]
