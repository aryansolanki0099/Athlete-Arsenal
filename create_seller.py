from users.models import User

# Create a seller account
seller = User.objects.create_user(
    username='seller1',
    email='seller1@example.com',
    password='seller123',
    user_type='SELLER'
)
print("Seller account created successfully!")
print("Username: seller1")
print("Password: seller123")
