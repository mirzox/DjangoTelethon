from django.contrib import admin
from django.shortcuts import redirect
from django.db import transaction


from .models import TgUser, Group


class TgUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'api_key', 'api_hash', 'is_active')
    list_filter = ('is_active', )
    search_fields = ('name', 'api_key', 'api_hash')

    # @transaction.atomic()
    def response_add(self, request, obj, post_url_continue=None):
        return redirect(f'/otp?name={obj.name}&pk={obj.pk}', request)

    def response_change(self, request, obj):
        return redirect(f'/otp?name={obj.name}&pk={obj.pk}', request)


class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'chat_id', 'sheet')
    search_fields = ('name', 'chat_id')
    list_editable = ('sheet', )

    change_form_template = 'custom_group_button.html'


admin.site.register(TgUser, TgUserAdmin)
admin.site.register(Group, GroupAdmin)
