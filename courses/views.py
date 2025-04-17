from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.files.storage import default_storage
from django.db.models import Count
from django.conf import settings
from wsgiref.util import FileWrapper
import json
import os
import re
from .models import Course, Module, Content, Enrollment, CourseOrder
from products.models import Order
from decimal import Decimal
from .forms import CourseForm, ModuleForm, ContentForm

# Add range regex pattern for video streaming
range_re = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.I)

def course_list(request):
    search_query = request.GET.get('search')
    courses = Course.objects.all()
    
    if search_query:
        courses = courses.filter(title__icontains=search_query)
    
    if request.user.is_authenticated:
        purchased_courses = CourseOrder.objects.filter(
            user=request.user,
            status='COMPLETED',
            payment_status=True
        ).values_list('course_id', flat=True)
    else:
        purchased_courses = []
    
    return render(request, 'courses/course_list.html', {
        'courses': courses,
        'purchased_courses': purchased_courses
    })

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    has_access = False
    pending_order = None
    
    if request.user.is_authenticated:
        # Check if user has purchased and paid for the course
        completed_order = CourseOrder.objects.filter(
            user=request.user,
            course=course,
            status='COMPLETED',
            payment_status=True
        ).first()
        
        # Allow instructor to access their own course
        has_access = completed_order is not None or request.user == course.instructor
        
        # Check for pending orders only if user doesn't have access
        if not has_access:
            pending_order = CourseOrder.objects.filter(
                user=request.user,
                course=course,
                status='PENDING'
            ).first()
            
            # If there's a pending order with COD payment, complete it
            if pending_order and pending_order.payment_method == 'COD':
                pending_order.status = 'COMPLETED'
                pending_order.payment_status = True
                pending_order.save()
                has_access = True
                pending_order = None
                messages.success(request, f'Successfully enrolled in {course.title}!')
        
        # If user has access, prefetch all content
        if has_access:
            course.modules.prefetch_related('contents').all()
    
    context = {
        'course': course,
        'has_access': has_access,
        'pending_order': pending_order
    }
    
    return render(request, 'courses/course_detail.html', context)

@login_required
def add_course(request):
    if not request.user.is_instructor:
        messages.error(request, 'Only instructors can add courses')
        return redirect('course_list')
        
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            messages.success(request, 'Course created successfully! Now you can add modules and content.')
            return redirect('manage_modules', course_id=course.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseForm()
        
    return render(request, 'courses/add_course.html', {'form': form})

@login_required
def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    
    if request.user != course.instructor:
        messages.error(request, 'You can only edit your own courses')
        return redirect('course_detail', pk=pk)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully!')
            return redirect('course_detail', pk=course.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CourseForm(instance=course)
    
    return render(request, 'courses/edit_course.html', {
        'course': course,
        'form': form
    })

@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    
    # Check if user has already purchased and paid for the course
    if CourseOrder.objects.filter(
        user=request.user,
        course=course,
        status='COMPLETED',
        payment_status=True
    ).exists():
        messages.warning(request, 'You have already purchased this course')
        return redirect('course_detail', pk=course_id)
    
    # Create order for direct purchase
    order = Order.objects.create(
        user=request.user,
        status='PENDING',
        payment_method=request.POST.get('payment_method', 'CARD'),
        payment_status=False,
        shipping_address=request.user.address or '',
        phone=request.user.phone or '',
        email=request.user.email,
        subtotal=course.price,
        shipping_cost=0,  # Digital product, no shipping
        total=course.price
    )
    
    # Create course order
    CourseOrder.objects.create(
        user=request.user,
        course=course,
        order=order
    )
    
    messages.success(request, f'Please complete the payment for {course.title}')
    return redirect('payment_process', order_id=order.id)

@login_required
def manage_modules(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    
    if request.user != course.instructor:
        messages.error(request, 'You can only manage modules for your own courses')
        return redirect('course_detail', pk=course_id)
    
    modules = course.modules.order_by('order').prefetch_related('contents')
    
    return render(request, 'courses/manage_modules.html', {
        'course': course,
        'modules': modules
    })

@login_required
def add_module(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    
    if request.user != course.instructor:
        messages.error(request, 'You can only add modules to your own courses')
        return redirect('course_detail', pk=course_id)
    
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.order = course.modules.count() + 1
            module.save()
            messages.success(request, 'Module added successfully! Now you can add content to it.')
            return redirect('manage_modules', course_id=course_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ModuleForm()
    
    return render(request, 'courses/add_module.html', {
        'course': course,
        'form': form
    })

@login_required
def edit_module(request, course_id, module_id):
    course = get_object_or_404(Course, pk=course_id)
    module = get_object_or_404(Module, pk=module_id, course=course)
    
    if request.user != course.instructor:
        messages.error(request, 'You can only edit modules in your own courses')
        return redirect('course_detail', pk=course_id)
    
    if request.method == 'POST':
        form = ModuleForm(request.POST, instance=module)
        if form.is_valid():
            form.save()
            messages.success(request, 'Module updated successfully!')
            return redirect('manage_modules', course_id=course_id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ModuleForm(instance=module)
    
    return render(request, 'courses/edit_module.html', {
        'course': course,
        'module': module,
        'form': form
    })

@login_required
def delete_module(request, course_id, module_id):
    course = get_object_or_404(Course, pk=course_id)
    module = get_object_or_404(Module, pk=module_id, course=course)
    
    if request.user != course.instructor:
        messages.error(request, 'You can only delete modules from your own courses')
        return redirect('course_detail', pk=course_id)
    
    if request.method == 'POST':
        # Delete all content files associated with this module
        for content in module.contents.all():
            if content.file:
                default_storage.delete(content.file.path)
                
        module.delete()
        messages.success(request, 'Module deleted successfully')
        
    return redirect('manage_modules', course_id=course_id)

@login_required
def manage_content(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    
    if request.user != module.course.instructor:
        messages.error(request, 'You can only manage content in your own courses')
        return redirect('course_detail', pk=module.course.id)
    
    contents = module.contents.order_by('order').all()
    return render(request, 'courses/manage_content.html', {
        'module': module,
        'contents': contents
    })

@login_required
def add_content(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    
    if request.user != module.course.instructor:
        messages.error(request, 'You can only add content to your own courses')
        return redirect('course_detail', pk=module.course.id)
    
    if request.method == 'POST':
        form = ContentForm(request.POST, request.FILES)
        if form.is_valid():
            content = form.save(commit=False)
            content.module = module
            content.order = module.contents.count() + 1
            content.save()
            messages.success(request, 'Content added successfully!')
            return redirect('manage_content', module_id=module.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContentForm()
    
    return render(request, 'courses/add_content.html', {
        'module': module,
        'form': form
    })

@login_required
def edit_content(request, module_id, content_id):
    module = get_object_or_404(Module, pk=module_id)
    content = get_object_or_404(Content, pk=content_id, module=module)
    
    if request.user != module.course.instructor:
        messages.error(request, 'You can only edit content in your own courses')
        return redirect('course_detail', pk=module.course.id)
    
    if request.method == 'POST':
        form = ContentForm(request.POST, request.FILES, instance=content)
        if form.is_valid():
            form.save()
            messages.success(request, 'Content updated successfully!')
            return redirect('manage_content', module_id=module.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContentForm(instance=content)
    
    return render(request, 'courses/edit_content.html', {
        'module': module,
        'content': content,
        'form': form
    })

@login_required
def delete_content(request, module_id, content_id):
    module = get_object_or_404(Module, pk=module_id)
    content = get_object_or_404(Content, pk=content_id, module=module)
    
    if request.user != module.course.instructor:
        messages.error(request, 'You can only delete content from your own courses')
        return redirect('course_detail', pk=module.course.id)
    
    if request.method == 'POST':
        # Delete content files
        if content.content_type == 'VIDEO' and content.video:
            default_storage.delete(content.video.path)
        
        content.delete()
        messages.success(request, 'Content deleted successfully')
        
    return redirect('manage_content', module_id=module.id)

@login_required
@require_POST
def update_content_order(request, module_id):
    module = get_object_or_404(Module, pk=module_id)
    
    if request.user != module.course.instructor:
        return HttpResponseForbidden('You can only reorder content in your own courses')
    
    try:
        order_data = json.loads(request.body)
        with transaction.atomic():
            for item in order_data:
                content = get_object_or_404(Content, id=item['id'], module=module)
                content.order = item['order']
                content.save()
        return JsonResponse({'status': 'success'})
    except (ValueError, KeyError):
        return JsonResponse({'status': 'error', 'message': 'Invalid data format'}, status=400)
    except Content.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Content not found'}, status=404)

@login_required
def view_content(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    course = content.module.course
    
    # Check if user has purchased and completed payment for the course
    has_access = CourseOrder.objects.filter(
        user=request.user,
        course=course,
        status='COMPLETED',
        payment_status=True
    ).exists() or request.user == course.instructor
    
    if not has_access:
        messages.error(request, 'You need to purchase this course to access its content.')
        return redirect('course_detail', pk=course.id)
    
    # Get previous and next content
    module_contents = list(content.module.contents.order_by('id'))
    current_index = module_contents.index(content)
    
    prev_content = module_contents[current_index - 1] if current_index > 0 else None
    next_content = module_contents[current_index + 1] if current_index < len(module_contents) - 1 else None
    
    return render(request, 'courses/view_content.html', {
        'content': content,
        'prev_content': prev_content,
        'next_content': next_content,
        'course': course
    })

@login_required
def purchase_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    
    # Check if user has already purchased and completed the course
    existing_order = CourseOrder.objects.filter(
        user=request.user,
        course=course,
        status='COMPLETED',
        payment_status=True
    ).first()
    
    if existing_order:
        messages.warning(request, 'You have already purchased this course.')
        return redirect('course_detail', pk=pk)
    
    # Check if there's a pending order
    pending_order = CourseOrder.objects.filter(
        user=request.user,
        course=course,
        status='PENDING'
    ).first()
    
    if pending_order:
        if pending_order.payment_method in ['CARD', 'UPI']:
            return redirect('course_payment_process', order_id=pending_order.id)
        else:
            # Delete the pending order and create a new one
            pending_order.delete()
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'CARD')
        
        try:
            with transaction.atomic():
                # Create course order
                order = CourseOrder.objects.create(
                    user=request.user,
                    course=course,
                    status='PENDING',
                    payment_method=payment_method,
                    amount=course.price
                )
                
                if payment_method == 'COD':
                    order.status = 'COMPLETED'
                    order.payment_status = True
                    order.save()
                    messages.success(request, f'Successfully enrolled in {course.title}!')
                    return redirect('course_detail', pk=pk)
                else:
                    return redirect('course_payment_process', order_id=order.id)
                    
        except Exception as e:
            messages.error(request, 'An error occurred while processing your purchase. Please try again.')
            return redirect('course_detail', pk=pk)
    
    return render(request, 'courses/purchase_course.html', {'course': course})

@login_required
def course_payment_process(request, order_id):
    order = get_object_or_404(CourseOrder, id=order_id, user=request.user)
    
    # If order is already completed, redirect to course
    if order.status == 'COMPLETED' and order.payment_status:
        messages.info(request, 'This order has already been completed.')
        return redirect('course_detail', pk=order.course.id)
    
    # If order is not pending, redirect to course detail
    if order.status != 'PENDING':
        messages.warning(request, 'This order cannot be processed.')
        return redirect('course_detail', pk=order.course.id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # For now, simulate payment success for Card/UPI
                if order.payment_method in ['CARD', 'UPI']:
                    order.status = 'COMPLETED'
                    order.payment_status = True
                    order.save()
                    
                    messages.success(request, f'Successfully enrolled in {order.course.title}!')
                    return redirect('course_detail', pk=order.course.id)
                else:
                    messages.error(request, 'Invalid payment method.')
                    return redirect('course_detail', pk=order.course.id)
        except Exception as e:
            messages.error(request, 'An error occurred while processing your payment. Please try again.')
            return redirect('course_detail', pk=order.course.id)
    
    context = {
        'order': order,
        'show_payment_form': order.payment_method in ['CARD', 'UPI']
    }
    
    return render(request, 'courses/payment_process.html', context)

@login_required
@require_POST
def update_module_order(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    
    if request.user != course.instructor:
        return HttpResponseForbidden('You can only reorder modules in your own courses')
    
    try:
        order_data = json.loads(request.body)
        with transaction.atomic():
            for item in order_data:
                module = get_object_or_404(Module, id=item['id'], course=course)
                module.order = item['order']
                module.save()
        return JsonResponse({'status': 'success'})
    except (ValueError, KeyError):
        return JsonResponse({'status': 'error', 'message': 'Invalid data format'}, status=400)
    except Module.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Module not found'}, status=404)

@login_required
def my_courses(request):
    enrolled_courses = Course.objects.filter(
        courseorder__user=request.user,
        courseorder__status='COMPLETED',
        courseorder__payment_status=True
    ).distinct()
    
    return render(request, 'courses/my_courses.html', {
        'courses': enrolled_courses,
        'title': 'My Enrolled Courses'
    })

@login_required
def my_created_courses(request):
    created_courses = Course.objects.filter(instructor=request.user)
    
    return render(request, 'courses/my_courses.html', {
        'courses': created_courses,
        'title': 'My Created Courses'
    })

@login_required
def instructor_dashboard(request):
    if not request.user.is_instructor:
        messages.error(request, 'Only instructors can access the dashboard')
        return redirect('course_list')
    
    # Get total number of students enrolled in instructor's courses
    total_students = Enrollment.objects.filter(
        course__instructor=request.user
    ).values('user').distinct().count()
    
    # Get courses with enrollment counts
    courses = Course.objects.filter(instructor=request.user).annotate(
        student_count=Count('enrollment')
    )
    
    context = {
        'courses': courses,
        'total_students': total_students,
    }
    
    return render(request, 'courses/instructor_dashboard.html', context)

@login_required
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    
    if request.user != course.instructor:
        messages.error(request, 'You can only delete your own courses')
        return redirect('course_detail', pk=pk)
    
    if request.method == 'POST':
        # Delete course thumbnail if it exists
        if course.thumbnail:
            default_storage.delete(course.thumbnail.path)
        
        # Delete course
        course.delete()
        messages.success(request, 'Course deleted successfully')
        return redirect('instructor_dashboard')
    
    return redirect('course_detail', pk=pk)

def stream_video(request, path):
    """Stream video content in chunks to support seeking and prevent buffering."""
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_match = range_re.match(range_header)
    video_path = os.path.join(settings.MEDIA_ROOT, 'course_videos', path)
    
    # Ensure the file exists and is accessible
    if not os.path.exists(video_path):
        return HttpResponseForbidden("Video not found")
    
    size = os.path.getsize(video_path)
    content_type = 'video/mp4'  # Default to MP4, adjust if needed
    
    if range_match:
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = int(last_byte) if last_byte else size - 1
        if last_byte >= size:
            last_byte = size - 1
        length = last_byte - first_byte + 1
        
        resp = StreamingHttpResponse(
            FileWrapper(open(video_path, 'rb')),
            status=206,
            content_type=content_type
        )
        resp['Content-Length'] = str(length)
        resp['Content-Range'] = f'bytes {first_byte}-{last_byte}/{size}'
    else:
        # Return the entire file if no range is provided
        resp = StreamingHttpResponse(
            FileWrapper(open(video_path, 'rb')),
            content_type=content_type
        )
        resp['Content-Length'] = str(size)
    
    resp['Accept-Ranges'] = 'bytes'
    return resp
