import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sdp.settings')
django.setup()

from courses.models import CourseOrder
from django.utils import timezone
from datetime import timedelta

def fix_course_orders():
    # Complete COD orders
    cod_orders = CourseOrder.objects.filter(
        status='PENDING',
        payment_method='COD'
    )
    
    for order in cod_orders:
        order.status = 'COMPLETED'
        order.payment_status = True
        order.save()
        print(f"Completed COD order {order.id} for course {order.course.title}")
    
    # Cancel stale orders (older than 24 hours)
    stale_orders = CourseOrder.objects.filter(
        status='PENDING',
        created_at__lt=timezone.now() - timedelta(hours=24)
    )
    
    for order in stale_orders:
        order.status = 'CANCELLED'
        order.save()
        print(f"Cancelled stale order {order.id} for course {order.course.title}")

if __name__ == '__main__':
    fix_course_orders()
