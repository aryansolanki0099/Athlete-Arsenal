from users.models import User

# Create a buyer account
buyer = User.objects.create_user(
    username='buyer1',
    email='buyer1@example.com',
    password='buyer123',
    user_type='BUYER'
)
print("Buyer account created successfully!")
print("Username: buyer1")
print("Password: buyer123")
