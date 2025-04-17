from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('seller-dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller-order/<int:order_id>/', views.seller_order_detail, name='seller_order_detail'),
]
