from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from decimal import Decimal
from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .forms import ProductForm, OrderForm
from courses.models import CourseOrder

def product_list(request):
    # Get all products
    products = Product.objects.all()
    
    # Get all categories for the sidebar
    categories = Category.objects.all().order_by('name')
    selected_category = None
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)
        products = products.filter(category=selected_category)
    
    # Filter by price range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'min_price': min_price,
        'max_price': max_price,
        'search_query': search_query,
    }
    
    return render(request, 'products/product_list.html', context)

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    related_products = Product.objects.filter(category=product.category).exclude(pk=pk)[:4]
    
    context = {
        'product': product,
        'related_products': related_products,
    }
    
    return render(request, 'products/product_detail.html', context)

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            messages.error(request, 'Quantity must be at least 1.')
            return redirect('product_detail', pk=product_id)
            
        if quantity > product.stock:
            messages.error(request, f'Sorry, only {product.stock} units available.')
            return redirect('product_detail', pk=product_id)
            
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            if cart_item.quantity > product.stock:
                messages.error(request, f'Sorry, only {product.stock} units available.')
                return redirect('product_detail', pk=product_id)
            cart_item.save()
        
        messages.success(request, f'{product.name} added to cart.')
        
    except ValueError:
        messages.error(request, 'Invalid quantity specified.')
        return redirect('product_detail', pk=product_id)
        
    return redirect('view_cart')

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('view_cart')

@login_required
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Cart updated successfully.')
        else:
            cart_item.delete()
            messages.success(request, 'Item removed from cart.')
    except ValueError:
        messages.error(request, 'Invalid quantity specified.')
    return redirect('view_cart')

@login_required
def view_cart(request):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.cartitem_set.all()
    except Cart.DoesNotExist:
        cart = None
        cart_items = []
    
    subtotal = sum(item.get_cost() for item in cart_items) if cart_items else 0
    shipping_cost = Decimal('50.00')
    total = subtotal + shipping_cost

    
    return render(request, 'products/cart.html', {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total
    })

@login_required
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related('product')
        
        if not cart_items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('view_cart')
            
        # Validate stock availability before proceeding
        for item in cart_items:
            if item.quantity > item.product.stock:
                messages.error(request, f'Sorry, only {item.product.stock} units of {item.product.name} are available.')
                return redirect('view_cart')
            
    except Cart.DoesNotExist:
        messages.error(request, 'Your cart is empty.')
        return redirect('view_cart')
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Calculate totals
                    subtotal = sum(item.get_cost() for item in cart_items)
                    shipping_cost = Decimal('50.00')  # Fixed shipping cost
                    total = subtotal + shipping_cost
                    
                    # Create order
                    order = form.save(commit=False)
                    order.user = request.user
                    order.subtotal = subtotal
                    order.shipping_cost = shipping_cost
                    order.total = total
                    order.save()
                    
                    # Create order items and update stock
                    for cart_item in cart_items:
                        OrderItem.objects.create(
                            order=order,
                            product=cart_item.product,
                            quantity=cart_item.quantity,
                            price=cart_item.product.price
                        )
                        
                        # Update product stock
                        product = cart_item.product
                        product.stock -= cart_item.quantity
                        product.save()
                    
                    # Clear cart
                    cart.delete()
                    
                    messages.success(request, 'Order placed successfully!')
                    return redirect('payment_process', order_id=order.id)
                    
            except Exception as e:
                messages.error(request, 'An error occurred while processing your order. Please try again.')
                return redirect('view_cart')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial_data = {
            'email': request.user.email,
            'phone': request.user.phone,
            'shipping_address': request.user.address,
        }
        form = OrderForm(initial=initial_data)
    
    subtotal = sum(item.get_cost() for item in cart_items)
    shipping_cost = Decimal('50.00')  # Fixed shipping cost
    total = subtotal + shipping_cost
    
    return render(request, 'products/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'total': total
    })

@login_required
def payment_process(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        if order.payment_method == 'COD':
            order.payment_status = True
            order.status = 'PROCESSING'
            order.save()
            messages.success(request, 'Order placed successfully! Your order will be delivered soon.')
            return redirect('order_detail', order_id=order.id)
        elif order.payment_method in ['CARD', 'UPI']:
            # For now, just simulate payment success
            order.payment_status = True
            order.status = 'PROCESSING'
            order.save()
            messages.success(request, 'Payment successful! Thank you for your purchase.')
            return redirect('order_detail', order_id=order.id)
    
    context = {
        'order': order,
        'show_payment_form': order.payment_method in ['CARD', 'UPI']
    }
    return render(request, 'products/payment_process.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'products/order_detail.html', {'order': order})

@login_required
def my_orders(request):
    # Get both product orders and course orders
    product_orders = Order.objects.filter(user=request.user).order_by('-created_at')
    course_orders = CourseOrder.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'product_orders': product_orders,
        'course_orders': course_orders
    }
    return render(request, 'products/my_orders.html', context)

@login_required
def add_product(request):
    if not request.user.is_seller:
        messages.error(request, 'Only sellers can add products.')
        return redirect('profile')
        
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            messages.success(request, 'Product added successfully!')
            return redirect('profile')
    else:
        form = ProductForm()
    
    # Get all categories for the form
    categories = Category.objects.all().order_by('name')
    
    return render(request, 'products/add_product.html', {
        'form': form,
        'categories': categories,
        'title': 'Add Product'
    })
