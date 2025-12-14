from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('deals/', views.deal_list, name='deal_list'),
    path('search/', views.search_tracked_products, name='search_tracked_products'),
    path('add/', views.add_product, name='add_product'),
    path('update/', views.update_prices, name='update_prices'),
    path('delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('api/search_alternatives/<int:product_id>/', views.search_alternatives, name='search_alternatives'),
    path('api/search/', views.api_search_products, name='api_search_products'),
    path('history/<int:product_id>/', views.get_price_history, name='get_price_history'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('login/', auth_views.LoginView.as_view(template_name='tracker/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='dashboard'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('profile/', views.profile, name='profile'),
]
