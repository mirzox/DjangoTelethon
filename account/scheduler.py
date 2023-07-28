import logging
from datetime import datetime, timedelta
import asyncio
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from telethon import TelegramClient, events, types, errors
from telethon.tl.functions.messages import SetTypingRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from django.core.exceptions import ObjectDoesNotExist

import logging
from datetime import datetime, timedelta
import asyncio
import urllib.parse


from .models import Group, TgUser

from utils import get_data_from_sheet


password = os.environ.get('DB_PASS')  # Replace this with your actual password
encoded_password = urllib.parse.quote(password, safe='')


jobstore = {
        'default': SQLAlchemyJobStore(url=f"postgresql+psycopg2://{os.environ.get('DB_USER')}:{encoded_password}@{os.environ.get('DB_HOST')}:{os.environ.get('DB_PORT')}/{os.environ.get('DB_NAME')}")
    }

logger = logging.getLogger('scheduler')

scheduler_ = AsyncIOScheduler({'apscheduler.timezone': 'Asia/Tashkent'}, jobstores=jobstore, logger=logger)


async def schedule_typing(user: str, group: str, repeat_time: int):
    obj = await TgUser.get_user(name=user, is_active=True)
    async with TelegramClient(f"{settings.SESSION_DIR}/{obj.name}", obj.api_key, obj.api_hash) as client:
        # try:
        dialogs = await client.get_dialogs()
        group_ = await client.get_entity(int(group))
        # print(group_)
        # except errors.ChatIdInvalidError as er:
        #     print(er)
        if isinstance(group_, types.Chat):
            group_ = types.InputPeerChat(group_.id)
        elif isinstance(group_, types.Channel):
            group_ = types.InputPeerChannel(group_.id, group_.access_hash)

        async with client.action(group_, 'typing'):
            await asyncio.sleep(repeat_time*5)
        await client.action(group_, 'cancel')
        # for i in range(repeat_time):
        #     res = await client.action(group, 'typing')
        #     # result = await client(SetTypingRequest(
        #     #     peer=group_,
        #     #     action=types.SendMessageTypingAction()
        #     # ))
        #     print(res)
        #     await asyncio.sleep(5)
        logger.info(f"Typing Task successfully executed!!! {user}:{group_}")


def remove_scheduled_typing(task_mng: AsyncIOScheduler, user: str, group: str):
    all_jobs = task_mng.get_jobs()
    for job in all_jobs:
        if f"{user}_{group}" in job.id:
            task_mng.remove_job(job_id=job.id)
            logger.info(f"Task with id = {job.id} removed")


def count_repeat(text_len):
    if text_len <= 20:
        return 1
    if 20 < text_len < 200:
        return text_len//20
    return 10


def reschedule_typing(task_mng: AsyncIOScheduler, text_len, run_date, name, group):
    repeat_time = count_repeat(text_len)
    run_date = run_date - timedelta(seconds=(repeat_time * 5 + settings.TYPING_DELAY))
    task_mng.add_job(
        schedule_typing,
        'date',
        run_date=run_date,
        kwargs={"user": name, "group": group, "repeat_time": repeat_time},
        id=f"{name}_{group}_{datetime.now().timestamp()}"
    )
    logger.info(f"")


async def process_group_schedule(task_mng: AsyncIOScheduler, account: str, data):
    try:
        obj = await TgUser.get_user(name=account, is_active=True)
        async with TelegramClient(f"{settings.SESSION_DIR}/{obj.name}", obj.api_key, obj.api_hash) as client:
            try:
                for row in data["reschedule"]:
                    date, t, text, gp_id = row
                    run_date = datetime.strptime(f"{date} {t}", '%Y-%m-%d %H:%M')
                    if run_date < datetime.now():
                        logger.warning(f"Message from {obj.name} to {gp_id} was scipped duo to time error {run_date} < {datetime.now()}")
                        continue
                    try:
                        # dt = datetime.strptime(f"{date} {t}", '%Y-%m-%d %H:%M')
                        # group_ = await client.get_entity(int(gp_id))
                        group_ = await client.get_entity(int(gp_id))
                        if isinstance(group_, types.Chat):
                            group_ = types.InputPeerChat(group_.id)
                        elif isinstance(group_, types.Channel):
                            group_ = types.InputPeerChannel(group_.id, group_.access_hash)

                        await client.send_message(
                            entity=group_,
                            message=text,
                            schedule=run_date - timedelta(hours=settings.HOUR_DIFFERENCE)
                        )
                    except (errors.PeerIdInvalidError, errors.ChatIdInvalidError) as e:
                        group_ = await client.get_entity(types.PeerChat(int(gp_id)))
                        await client.send_message(
                            entity=group_,
                            message=text,
                            schedule=run_date - timedelta(hours=settings.HOUR_DIFFERENCE)
                        )
                    logger.info(f'Message from: {obj.name} successfully scheduled to group {gp_id}')
                    repeat_time = count_repeat(len(text))
                    run_date = run_date - timedelta(seconds=(repeat_time * 5 + settings.TYPING_DELAY))

                    task_mng.add_job(
                        schedule_typing,
                        'date',
                        run_date=run_date,
                        kwargs={"user": obj.name, "group": gp_id, "repeat_time": repeat_time},
                        id=f"{obj.name}_{gp_id}_{datetime.now().timestamp()}"
                    )
                    # reschedule_typing(
                    #     task_mng=task_mng,
                    #     text_len=len(text),
                    #     run_date=run_date,
                    #     name=obj.name,
                    #     group=gp_id
                    # )
                a = [i.id for i in task_mng.get_jobs()]
                print(a)
            except ValueError as er:
                logger.error(f"account {account} could not find chat_id {gp_id} {er}")

    except ObjectDoesNotExist:
        logger.error(f"account with name: {account} does not exist in database")


async def schedule_message():
    start = datetime.now()
    async for group in Group.objects.all():
        sheet_id = group.sheet.replace('https://docs.google.com/spreadsheets/d/', '').split('/')[0]
        result = get_data_from_sheet(
            settings.GOOGLE_API_CREDENTIALS,
            sheet_id,
        )
        if 'error' not in result:
            await asyncio.gather(*[process_group_schedule(task_mng=get_scheduler_instance(), account=a, data=d) for a, d in result.items()])
        else:
            logger.error(f"Что то пошло не так с получением данных с google sheet. {result['error']}")
    logger.info(datetime.now() - start)
    for task in get_scheduler_instance().get_jobs():
        logger.info(f"Added tasks {task.id}")


def check():
    print("schedeuler works")


try:
    run_date = '2023-07-24 00:21:00'
    scheduler_.add_job(schedule_message, 'cron', hour=0, minute=10, id='daily_schedule_message', replace_existing=True)
    scheduler_.start()
except Exception as e:
    print(f"Error starting scheduler: {e}")


def get_scheduler_instance():
    return scheduler_