from django.urls import path
from . import views

urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('add/', views.add_course, name='add_course'),
    path('<int:pk>/', views.course_detail, name='course_detail'),
    path('<int:pk>/edit/', views.edit_course, name='edit_course'),
    path('<int:pk>/delete/', views.delete_course, name='delete_course'),
    path('<int:course_id>/modules/', views.manage_modules, name='manage_modules'),
    path('<int:course_id>/modules/add/', views.add_module, name='add_module'),
    path('<int:course_id>/modules/<int:module_id>/edit/', views.edit_module, name='edit_module'),
    path('<int:course_id>/modules/<int:module_id>/delete/', views.delete_module, name='delete_module'),
    path('<int:course_id>/modules/reorder/', views.update_module_order, name='update_module_order'),
    path('instructor/dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    path('purchase/<int:pk>/', views.purchase_course, name='purchase_course'),
    path('payment/<int:order_id>/', views.course_payment_process, name='course_payment_process'),
    path('<int:course_id>/enroll/', views.enroll_course, name='enroll_course'),
    path('manage-content/<int:module_id>/', views.manage_content, name='manage_content'),
    path('add-content/<int:module_id>/', views.add_content, name='add_content'),
    path('edit-content/<int:module_id>/<int:content_id>/', views.edit_content, name='edit_content'),
    path('delete-content/<int:module_id>/<int:content_id>/', views.delete_content, name='delete_content'),
    path('view-content/<int:content_id>/', views.view_content, name='view_content'),
    path('content/<int:module_id>/reorder/', views.update_content_order, name='update_content_order'),
    path('my-courses/', views.my_courses, name='my_courses'),
    path('my-created-courses/', views.my_created_courses, name='my_created_courses'),
    path('stream-video/<path:path>/', views.stream_video, name='stream_video'),  # Add video streaming URL
]
