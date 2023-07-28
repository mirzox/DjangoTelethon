import os

from django.db import models
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


class TgUser(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name='Name')
    api_key = models.BigIntegerField(verbose_name='App api_id')
    api_hash = models.CharField(max_length=150, verbose_name="App api_hash")
    phone = models.CharField(max_length=25, help_text="Phone with out +", verbose_name="Phone")
    password = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        help_text="Пароль от двухэтапной аунтефикации",
        default='517707'
    )
    is_active = models.BooleanField(default=False, editable=False, verbose_name="Активный ли аккаунт")
    timestamp = models.DateTimeField(auto_now_add=True, auto_created=True)

    class Meta:
        verbose_name = "Телеграм Аккаунт Пользователя"
        verbose_name_plural = "Телеграм Аккаунты Пользователей"

    @sync_to_async()
    def get_user(self, **kwargs):
        return TgUser.objects.get(**kwargs)

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=150, verbose_name="Название группы")
    chat_id = models.BigIntegerField(verbose_name="ID группы")
    sheet = models.URLField(
        verbose_name="Google sheet url",
        help_text="Cсылка на открытый google sheet или demonstrationalemail@gmail.com имеет доступ к этому файлу"
    )
    timestamp = models.DateTimeField(auto_now_add=True, auto_created=True)

    class Meta:
        verbose_name = "Группу"
        verbose_name_plural = "Группы"

    @sync_to_async()
    def get_group_by_pk(self, pk):
        return Group.objects.get(pk=pk)

    def __str__(self):
        return self.name


@receiver(pre_save, sender=TgUser)
def update_folder_name(sender, instance, **kwargs):
    print(instance.id)
    if instance.id is None:
        pass
    else:
        old_account = TgUser.objects.get(pk=instance.pk)
        if old_account.name.lower() != instance.name.lower():
            os.rename(f"{settings.SESSION_DIR}/{old_account.name}.session",
                      f"{settings.SESSION_DIR}/{instance.name}.session")


