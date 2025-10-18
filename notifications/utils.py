from .models import Notification


def create_notification(user, notification_type, title, message, actor=None, related_object_type=None, related_object_id=None):
    """
    Helper function to create notifications
    """
    return Notification.objects.create(
        user=user,
        actor=actor,
        notification_type=notification_type,
        title=title,
        message=message,
        related_object_type=related_object_type,
        related_object_id=related_object_id
    )


def notify_welcome(user):
    """
    Send welcome notification to new customers
    """
    return create_notification(
        user=user,
        actor=None,  # System notification
        notification_type='WELCOME',
        title='Welcome to Warranty Wallet! 👋',
        message='We\'re excited to have you here! Start by adding your receipts and managing your warranties all in one place.',
        related_object_type=None,
        related_object_id=None
    )


def notify_new_receipt(receipt, actor):
    """
    Notify customer when a new receipt is created
    """
    return create_notification(
        user=receipt.customer,
        actor=actor,
        notification_type='NEW_RECEIPT',
        title='New Receipt Received',
        message=f'You received a new receipt from {receipt.store.name} for ${receipt.total}',
        related_object_type='Receipt',
        related_object_id=receipt.id
    )


def notify_new_claim(claim, actor):
    """
    Notify retailer when a customer creates a new claim
    """
    return create_notification(
        user=claim.retailer,
        actor=actor,
        notification_type='NEW_CLAIM',
        title='New Claim Submitted',
        message=f'New claim #{claim.claim_number} submitted for {claim.product_name}',
        related_object_type='Claim',
        related_object_id=claim.id
    )


def notify_claim_status_update(claim, actor, old_status, new_status):
    """
    Notify customer when claim status is updated
    """
    return create_notification(
        user=claim.customer,
        actor=actor,
        notification_type='CLAIM_STATUS_UPDATE',
        title=f'Claim {claim.claim_number} Updated',
        message=f'Your claim has been updated from "{old_status}" to "{new_status}"',
        related_object_type='Claim',
        related_object_id=claim.id
    )


def notify_claim_note_added(claim, note, actor):
    """
    Notify customer when retailer adds a note to their claim
    """
    return create_notification(
        user=claim.customer,
        actor=actor,
        notification_type='CLAIM_NOTE_ADDED',
        title=f'New Note on Claim {claim.claim_number}',
        message=f'A new note has been added to your claim',
        related_object_type='Claim',
        related_object_id=claim.id
    )


def notify_claim_attachment_added(claim, attachment, actor):
    """
    Notify the other party when an attachment is added to a claim
    Customer adds attachment -> notify retailer
    Retailer adds attachment -> notify customer
    """
    # Determine recipient (opposite of actor)
    if actor == claim.customer:
        recipient = claim.retailer
        message = f'Customer added a new attachment to claim #{claim.claim_number}'
    else:
        recipient = claim.customer
        message = f'New attachment added to your claim #{claim.claim_number}'
    
    return create_notification(
        user=recipient,
        actor=actor,
        notification_type='CLAIM_ATTACHMENT_ADDED',
        title=f'New Attachment on Claim {claim.claim_number}',
        message=message,
        related_object_type='Claim',
        related_object_id=claim.id
    )


def notify_warranty_expiring(warranty, days_left):
    """
    Notify customer when warranty is expiring soon
    """
    return create_notification(
        user=warranty.customer,
        actor=None,  # System notification
        notification_type='WARRANTY_EXPIRING',
        title='Warranty Expiring Soon',
        message=f'Your warranty for {warranty.receipt_item.product_name} expires in {days_left} days',
        related_object_type='Warranty',
        related_object_id=warranty.id
    )


def notify_warranty_expired(warranty):
    """
    Notify customer when warranty has expired
    """
    return create_notification(
        user=warranty.customer,
        actor=None,  # System notification
        notification_type='WARRANTY_EXPIRED',
        title='Warranty Expired',
        message=f'Your warranty for {warranty.receipt_item.product_name} has expired',
        related_object_type='Warranty',
        related_object_id=warranty.id
    )

