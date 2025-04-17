from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login
from .models import User
from products.models import Product, Order, OrderItem  # Import Order and OrderItem from products app
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.core.exceptions import PermissionDenied
import json

# Create your views here.

def home(request):
    products = Product.objects.all().order_by('-id')[:8]  # Get latest 8 products
    return render(request, 'users/home.html', {
        'products': products
    })

def register(request):
    if request.method == 'POST':
        user_type = request.POST.get('user_type')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return redirect('register')
            
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return redirect('register')
            
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type=user_type
        )
        login(request, user)
        messages.success(request, f'Account created for {username}!')
        return redirect('home')
        
    return render(request, 'users/register.html')

@login_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.phone = request.POST.get('phone')
        user.address = request.POST.get('address')
        
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
            
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
        
    return render(request, 'users/profile.html')

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'users/my_orders.html', {'orders': orders})

@login_required
def seller_dashboard(request):
    if not request.user.is_seller:
        raise PermissionDenied("Only sellers can access this page")
    
    # Get all orders containing products sold by this seller
    seller_orders = OrderItem.objects.filter(
        product__seller=request.user
    ).select_related('order', 'product').order_by('-order__created_at')
    
    # Get monthly sales data for the graph
    monthly_sales = OrderItem.objects.filter(
        product__seller=request.user
    ).annotate(
        month=TruncMonth('order__created_at')
    ).values(
        'month', 'product__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales=Sum('price')
    ).order_by('month', 'product__name')
    
    # Format data for the chart
    chart_data = {}
    for sale in monthly_sales:
        month_str = sale['month'].strftime('%B %Y')
        if month_str not in chart_data:
            chart_data[month_str] = []
        
        chart_data[month_str].append({
            'product': sale['product__name'],
            'quantity': sale['total_quantity'],
            'sales': float(sale['total_sales'])
        })
    
    return render(request, 'users/seller_dashboard.html', {
        'seller_orders': seller_orders,
        'chart_data': json.dumps(chart_data)
    })

@login_required
def seller_order_detail(request, order_id):
    if not request.user.is_seller:
        raise PermissionDenied("Only sellers can access this page")
    
    # Get the order items for this seller in this order
    order_items = OrderItem.objects.filter(
        order_id=order_id,
        product__seller=request.user
    ).select_related('order', 'product', 'order__user')
    
    if not order_items.exists():
        raise PermissionDenied("No items from this order belong to you")
    
    order = order_items[0].order
    
    return render(request, 'users/seller_order_detail.html', {
        'order': order,
        'order_items': order_items,
        'total_amount': sum(item.get_cost() for item in order_items)
    })
