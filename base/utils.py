from django.db.models import Max


def generate_code(sender, instance, code_field):
  if hasattr(instance, code_field):
    if not getattr(instance, code_field, None):
      # generate code by id, length = 4
      # sample: id = 12, code = 0012
      maxid = sender.objects.all().aggregate(Max('id'))
      code = ('0000' + str(maxid['id__max'] + 1))[-4:]

      try:
        instance_exist = sender.objects.get(**{code_field: code})
        # keep code field None value
      except:
        # use generate code when code does not exist
        setattr(instance, code_field, code)
        instance.save()


def set_code_to_none(instance, code_field):
  if instance._state.adding is True:
    if getattr(instance, code_field, '') == '':
      # set code to None if it has not been set
      setattr(instance, code_field, None)
  return instance
