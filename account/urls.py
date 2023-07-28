from django.urls import path, include

from .views import Otp, change_schedule

urlpatterns = [
    path('otp/', Otp.as_view()),
    path('group/<int:pk>/', change_schedule, name='custom_action'),
]
