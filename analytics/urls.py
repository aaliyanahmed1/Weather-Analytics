from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    path('presentation/', views.presentation_view, name='presentation'),
    path('api/charts/', views.dashboard_chart_data, name='chart_data'),
    
    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='analytics/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    # Weather Records CRUD
    path('records/', views.record_list_view, name='record_list'),
    path('records/add/', views.record_create_view, name='record_add'),
    path('records/<int:pk>/edit/', views.record_update_view, name='record_edit'),
    path('records/<int:pk>/delete/', views.record_delete_view, name='record_delete'),
    
    # Upload & Exports
    path('upload/', views.upload_csv_view, name='upload_csv'),
    path('export/csv/', views.export_csv_view, name='export_csv'),
    path('export/pdf/', views.export_pdf_view, name='export_pdf'),
]
