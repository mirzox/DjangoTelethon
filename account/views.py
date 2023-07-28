import os.path
import logging
import asyncio
from datetime import datetime, timedelta

from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from telethon import TelegramClient, functions, types, errors

from telethon.errors.rpcerrorlist import (
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
    PasswordHashInvalidError
)
from telethon.tl.functions.messages import (
    GetDialogsRequest,
    GetScheduledMessagesRequest,
    GetScheduledHistoryRequest,
    DeleteScheduledMessagesRequest,
    GetAllStickersRequest,
    GetStickerSetRequest
)

from account.models import Group, TgUser
from utils import get_data_from_sheet
from .scheduler import get_scheduler_instance, remove_scheduled_typing, reschedule_typing


logger = logging.getLogger('django')


class Otp(LoginRequiredMixin, View):
    # http_method_names = ['GET', 'POST']
    login_url = '/admin/'

    async def get(self, request):
        name = request.GET.get('name')
        pk = request.GET.get('pk')
        obj = await TgUser.get_user(name=name)
        cache.delete(obj.name)
        if cache.get(name) is None:
            client = TelegramClient(os.path.join(settings.SESSION_DIR, f"{obj.name}.session"), obj.api_key,
                                    obj.api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                obj.is_active = False
                obj.save()
                result = await client.send_code_request(obj.phone)
                phone_hash = result.phone_code_hash
                cache.set(obj.name, phone_hash, timeout=300)
                logger.info(f"Был отправлен код для авторизации на аккаунт {obj.name}")
                return render(request, 'index.html', {"obj": obj})
            await client.disconnect()
        elif cache.get(name):

            return render(request, 'index.html', {"obj": obj})
        logger.info(f'Вход был успешно выполнен на аккаунт: {obj.name} с номеров телефона: {obj.phone}')
        obj.is_active = True
        obj.save()
        messages.success(request, f'Вход был успешно выполнен на аккаунт: {obj.name} с номеров телефона: {obj.phone}')
        return redirect('/admin/account/tguser/', request)

    async def post(self, request):
        with transaction.atomic():
            name = request.GET.get('name')
            resend = request.POST.get('resend')  # TODO: Part with resend code
            obj = await TgUser.get_user(name=name)
            client = TelegramClient(os.path.join(settings.SESSION_DIR, f"{obj.name}.session"), obj.api_key, obj.api_hash)

            await client.connect()
            # async with TelegramClient(f"{settings.SESSION_DIR}/{obj.name}", obj.api_key, obj.api_hash) as client:

            try:
                await client.sign_in(obj.phone,
                                     phone_code_hash=cache.get(name),
                                     code=request.POST.get('code', 00000))
            except PhoneCodeInvalidError as er:  # PhoneCodeExpiredError
                print(er)
                obj.is_active = False
                obj.save()
                client.disconnect()
                logger.warning(f"Был введен не верный код для аккаунта {obj.name}")
                return render(request, 'index.html', {"obj": obj, 'error': "Не верный код введите код заново!!!"})

            except SessionPasswordNeededError as er:
                print(er)
                try:
                    await client.sign_in(password=obj.password)
                    logger.info(f"Успешный вход с паролем на аккаунт {obj.name}")
                except PasswordHashInvalidError as ern:
                    obj.is_active = False
                    obj.save()
                    client.disconnect()
                    logger.error(f'Ошибка при вводе двух этапного пароля на аккаунт {obj.name} {ern}')
                    return render(request, 'index.html',
                                  {"obj": obj, 'error': "Отключите двухэтапную аунтефикацию!!! И введите код заново"})
            # except PasswordHashInvalidError:
            #     obj.is_active = False
            #     obj.save()
            #     client.disconnect()
            #     return render(request, 'index.html',
            #                   {"obj": obj, 'error': "Отключите двухэтапную аунтефикацию!!! И введите код заново"})

            aa = await client.get_me()
            client.disconnect()
            cache.expire(obj.name, timeout=1)
            obj.is_active = True
            obj.save()
            logger.info(f'Вход был успешно выполнен на аккаунт: {obj.name} с номеров телефона: {obj.phone}')
            messages.success(request, f'Вход был успешно выполнен на аккаунт: {obj.name} с номеров телефона: {obj.phone}')
            return redirect(f'/admin/account/tguser/')


async def process_group_schedule(account, data):
    warn = {
        "error": [],
        "warning": [],
        "success": []
    }


    try:
        obj = await TgUser.get_user(name=account, is_active=True)
        async with TelegramClient(f"{settings.SESSION_DIR}/{obj.name}", obj.api_key, obj.api_hash) as client:
            aa = await client.get_dialogs()
            try:
                for group_id in data['group_id']:
                    group_ = await client.get_entity(int(group_id))
                    if isinstance(group_, types.Chat):
                        group_ = types.InputPeerChat(group_.id)
                    elif isinstance(group_, types.Channel):
                        group_ = types.InputPeerChannel(group_.id, group_.access_hash)
                    msg = await client(GetScheduledHistoryRequest(peer=group_, hash=0))
                    res = await client(DeleteScheduledMessagesRequest(group_, id=[i.id for i in msg.messages]))
                    remove_scheduled_typing(
                        task_mng=get_scheduler_instance(),
                        user=obj.name,
                        group=group_id
                    )
                for row in data["reschedule"]:
                    date, t, text, gp_id = row
                    try:
                        dt = datetime.strptime(f"{date} {t}", '%Y-%m-%d %H:%M')
                        if dt < datetime.now():
                            warn['warning'].append(f"Message from {obj.name} to {gp_id} was skipped duo to time error {dt} < {datetime.now()}")
                            logger.warning(
                                f"Message from {obj.name} to {gp_id} was skipped duo to time error {dt} < {datetime.now()}"
                            )
                            continue
                        group_ = await client.get_entity(int(gp_id))
                        if isinstance(group_, types.Chat):
                            group_ = types.InputPeerChat(group_.id)
                        elif isinstance(group_, types.Channel):
                            group_ = types.InputPeerChannel(group_.id, group_.access_hash)
                        await client.send_message(
                            entity=group_,
                            message=text,
                            schedule=dt - timedelta(hours=settings.HOUR_DIFFERENCE)
                        )
                        sticker_sets = await client(GetAllStickersRequest(0))
                        sticker_set = sticker_sets.sets[0]
                        # # Get the stickers for this sticker set
                        stickers = await client(GetStickerSetRequest(
                            stickerset=types.InputStickerSetID(
                                id=sticker_set.id, access_hash=sticker_set.access_hash,
                            ), hash=0
                        ))
                        # print(stickers.documents)
                        result = await client.send_file('me', stickers.documents[2],)
                        #                        # schedule=dt - timedelta(hours=settings.HOUR_DIFFERENCE), supports_streaming=False)
                        # gif = await client.send_file('me', "https://cdn.vox-cdn.com/thumbor/yQidk0r257q3yR9mQvZEQQnNInE=/800x0/filters:no_upscale()/cdn.vox-cdn.com/uploads/chorus_asset/file/8688491/hiE5vMs.gif")
                        # print(gif)
                    except errors.PeerIdInvalidError as e:
                        group_ = await client.get_entity(types.PeerChat(int(gp_id)))
                        await client.send_message(
                            entity=group_,
                            message=text,
                            schedule=dt - timedelta(hours=settings.HOUR_DIFFERENCE)
                        )
                    reschedule_typing(
                        task_mng=get_scheduler_instance(),
                        text_len=len(text),
                        run_date=dt,
                        name=obj.name,
                        group=gp_id,
                    )
                    logger.info(
                        f'Message from: {obj.name} successfully scheduled to group {gp_id}')
                    warn['success'].append(f'Message from: {obj.name} successfully scheduled to group {gp_id}')
                return warn
            except ValueError as er:
                logger.error(f"Account {account} could not find chat_id {group_id} {er}")
                warn['error'].append(f"Account {account} could not find chat_id {group_id} {er}")
                return warn

    except ObjectDoesNotExist:
        logger.error(f"Account with name: {account} does not exist in database")
        warn['error'].append(f"Account with name: {account} does not exist in database")
        return warn


async def change_schedule(request, pk):
    start = datetime.now()
    group = await Group.get_group_by_pk(pk)
    sheet_id = group.sheet.replace('https://docs.google.com/spreadsheets/d/', '').split('/')[0]
    result = get_data_from_sheet(
        settings.GOOGLE_API_CREDENTIALS,
        sheet_id,
    )

    if 'error' not in result:
        # for account, data in result.items():
        result = await asyncio.gather(*[process_group_schedule(account=a, data=d) for a, d in result.items()])
        print(result)
        logger.info(f"Запланированные сообщения для группы {group.name} были перепланированы. {datetime.now() - start}")
        final = {
            "error": [],
            "warning": [],
            "success": []
        }
        for i in result:
            final['error'].extend(i['error'])
            final['warning'].extend(i['warning'])
            final['success'].extend(i['success'])

        if final["error"]:
            messages.error(request, '!!!   '.join(final['error']))
        if final["warning"]:
            messages.warning(request, '!!  '.join(final['warning']))
        if final['success']:
            messages.success(request, f"Остальные Запланированные сообщения для группы {group.name} были перепланированы. {datetime.now() - start}")
        return redirect(f'/admin/account/group/{pk}')
    else:
        logger.error(f"Что то пошло не так с получением данных с google sheet. Свяжитесь с администратором!!!  {result['error']}")
        messages.error(request, f"Что то пошло не так с получением данных с google sheet. Свяжитесь с администратором!!! {result['error']}")
        return redirect(f'/admin/account/group/{pk}')
