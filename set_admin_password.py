from django.contrib.auth import get_user_model
User = get_user_model()
admin_user = User.objects.get(username='admin')
admin_user.is_superuser = True
admin_user.is_staff = True
admin_user.save()
admin = User.objects.get(username='admin')
admin.set_password('admin123')
admin.save()
print("Admin password has been set to: admin123")
