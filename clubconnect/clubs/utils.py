import qrcode
from io import BytesIO
from django.core.files import File
from .models import Notification


def generate_qr_code_for_event(event, request=None):
    from django.conf import settings
    import os
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    checkin_path = event.get_qr_code_url()
    
    if request:
        absolute_url = request.build_absolute_uri(checkin_path)
    else:
        replit_domain = os.environ.get('REPLIT_DEV_DOMAIN', '')
        if replit_domain:
            absolute_url = f"https://{replit_domain}{checkin_path}"
        else:
            absolute_url = f"http://localhost:5000{checkin_path}"
    
    qr.add_data(absolute_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    filename = f'qr_event_{event.id}.png'
    event.qr_code.save(filename, File(buffer), save=True)
    buffer.close()


def create_notification(users, notification_type, title, message, link=''):
    notifications = []
    for user in users:
        notification = Notification(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link
        )
        notifications.append(notification)
    Notification.objects.bulk_create(notifications)


def notify_club_members(club, notification_type, title, message, link=''):
    from clubs.models import Membership
    members = Membership.objects.filter(club=club, status='approved').select_related('user')
    users = [m.user for m in members]
    create_notification(users, notification_type, title, message, link)
