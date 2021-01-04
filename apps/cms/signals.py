from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from apps.cms.models import Post, Term, Publication
from apps.activity.models import Action, Comment
from apps.activity import verbs, action


@receiver(post_save, sender=Post)
def on_post_save(sender, instance, created, *args, **kwargs):
    if created and instance.id and str(instance.id) not in instance.slug:
        if instance.status == "POSTED" and hasattr(instance, "id"):
            if instance.options is None:
                instance.options = {}
            if instance.options.get("action_post", None) is None:
                check = Action.objects.filter(
                    verb=verbs.POST_CREATED,
                    action_object_content_type=ContentType.objects.get(model='post'),
                    action_object_object_id=str(instance.id)
                ).first()
                if check is None and instance.user is not None:
                    new_action = action.send(
                        instance.user,
                        verb=verbs.POST_CREATED,
                        action_object=instance,
                        target=instance.primary_publication if instance.primary_publication is not None else None
                    )
                    check = new_action[0][1]
                if check is not None:
                    instance.options['action_post'] = check.id
        instance.save()


@receiver(post_save, sender=Term)
def on_term_save(sender, instance, created, *args, **kwargs):
    pass


@receiver(post_save, sender=Publication)
def on_pub_save(sender, instance, created, *args, **kwargs):
    pass


@receiver(post_save, sender=Comment)
def on_comment_save(sender, instance, created, *args, **kwargs):
    pass
