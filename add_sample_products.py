from products.models import Product, Category
from users.models import User
from django.core.files import File
from pathlib import Path
import os

def add_sample_products():
    # Get the seller account
    seller = User.objects.get(username='seller1')
    
    # Get the Electronics category
    electronics = Category.objects.get(name='Electronics')
    
    # Sample product data
    products = [
        {
            'name': 'Wireless Bluetooth Headphones',
            'description': 'High-quality wireless headphones with noise cancellation, 20-hour battery life, and premium sound quality. Perfect for music lovers and professionals.',
            'price': 99.99,
            'category': electronics,
            'stock': 50,
            'seller': seller
        },
        {
            'name': 'Smart Fitness Watch',
            'description': 'Track your fitness goals with this advanced smartwatch. Features include heart rate monitoring, step counting, sleep tracking, and smartphone notifications.',
            'price': 149.99,
            'category': electronics,
            'stock': 30,
            'seller': seller
        }
    ]
    
    # Create products
    for product_data in products:
        product = Product.objects.create(
            name=product_data['name'],
            description=product_data['description'],
            price=product_data['price'],
            category=product_data['category'],
            stock=product_data['stock'],
            seller=product_data['seller']
        )
        print(f"Added product: {product.name}")

if __name__ == '__main__':
    add_sample_products()
