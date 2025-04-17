from products.models import Category

categories = [
    {"name": "Electronics", "description": "Electronic devices and accessories"},
    {"name": "Books", "description": "Books and educational materials"},
    {"name": "Clothing", "description": "Fashion and apparel"},
    {"name": "Home & Living", "description": "Home decor and household items"},
    {"name": "Sports & Fitness", "description": "Sports equipment and fitness gear"},
    {"name": "Beauty & Health", "description": "Beauty products and healthcare items"}
]

for category_data in categories:
    Category.objects.get_or_create(
        name=category_data["name"],
        defaults={"description": category_data["description"]}
    )
    print(f"Added category: {category_data['name']}")
