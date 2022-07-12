import aiohttp
import asyncio
from pyuseragents import random as random_useragent
from urllib3 import disable_warnings
from loguru import logger
from sys import stderr, platform, exit
from os import system
from random import choice
from json import loads
from time import sleep
from aiohttp_proxy import ProxyConnector
from multiprocessing.dummy import Pool


headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'ru,en;q=0.9',
    'content-type': 'application/json',
    'origin': 'https://roboworld.io',
    'referer': 'https://roboworld.io/',
}


tempmail_headers = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'accept-language': 'ru,en;q=0.9',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'origin': 'https://www.smartnator.com',
    'referer': 'https://www.smartnator.com/inbox/',
    'x-requested-with': 'XMLHttpRequest'
}


class Email_Timeout(BaseException):
    pass


class NotFoundWallet(BaseException):
    pass


class NotEntrySumbitted(BaseException):
    pass


class Wrong_Response(BaseException):
    pass


class Already_Completed(BaseException):
    pass


disable_warnings()
def clear(): return system('cls' if platform == "win32" else 'clear')


logger.remove()
logger.add(stderr, format="<white>{time:HH:mm:ss}</white>"
                          " | <level>{level: <8}</level>"
                          " | <cyan>{line}</cyan>"
                          " - <white>{message}</white>")


def random_file_proxy():
    with open(proxy_folder, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    proxy_str = f'{proxy_type}://' + choice(lines)

    return(proxy_str)


class App:
    def __init__(self, refcode):
        self.email = None
        self.refcode = refcode

    async def get_csrf(self, session):
        while True:
            r = await session.get('https://www.smartnator.com/inbox/')

            if not r.cookies.get('csrf_gmailnator_cookie'):
                logger.error(f'Can\'t get csrf token, response: {str(await r.text())}')
                continue

            return(r.cookies['csrf_gmailnator_cookie'].value)

    async def get_email(self, session):
        while True:
            self.csrf_token = await self.get_csrf(session)

            r = await session.post('https://www.smartnator.com/index/indexquery',
                                   data={
                                       'csrf_gmailnator_token': self.csrf_token,
                                       'action': 'GenerateEmail',
                                       'data[]': '1',
                                       'data[]': '2',
                                       'data[]': '3'
                                   })

            response_text = loads(str(await r.text()))

            if not response_text.get('email'):
                logger.error(f'Can\' get email, response: {str(await r.text())}')
                continue

            else:
                logger.success(response_text['email'] + ' | Successfully received email')

            return(response_text['email'])

    async def check_messages(self, session):
        for i in range(11):
            sleep(5)

            r = await session.post('https://www.smartnator.com/mailbox/mailboxquery',
                                   data={
                                       'csrf_gmailnator_token': self.csrf_token,
                                       'action': 'LoadMailList',
                                       'Email_address': self.email
                                   })

            for current_message in loads(str(await r.text())):
                if 'info@roboworld.io' in current_message['content']:
                    message_id = current_message['content']\
                        .split('smartnator.com/inbox/')[-1]\
                        .split('\">')[0]

                    r = await session.get(f'https://www.smartnator.com/inbox/{message_id}')
                    verify_code = str(await r.text())

                    return(verify_code.split('is  &lt;b&gt;')[-1]
                                      .split('&')[0])

            if i == 10:
                raise Email_Timeout('')

    async def get_connector(self):
        if use_proxy:
            connector = ProxyConnector.from_url(random_file_proxy())

        else:
            connector = None

        return(connector)

    async def Enter_Code(self, session, code):
        r = await session.post('https://api-staging.roboworld.io/airdrop/verification/confirm',
                               json={
                                   "email": self.email,
                                   "code": code.strip(),
                                   "referral_code": self.refcode
                               })

        if 'Email is successfully verified' not in str(await r.text()):
            raise Wrong_Response(str(await r.text()))

        token = str(await r.text())
        logger.success(f'{self.email} | The code will successfully enter')
        return(loads(token)['token'])

    async def Complete_Tasks(self, session):
        for i in range(1, 6):
            if i == 1:
                send_data = f'{self.email}action_website'
                action = 'action_website'

            elif i == 2:
                send_data = f'@{self.email}'
                action = 'action_telegram'

            elif i == 3:
                send_data = f'{self.email}action_telegram_join_global_channel'
                action = 'action_telegram_join_global_channel'

            elif i == 4:
                send_data = f'{self.email}action_telegram_join_global_community'
                action = 'action_telegram_join_global_community'

            elif i == 5:
                send_data = f'@{self.email}'
                action = 'action_twitter'

            r = await session.post('https://api-staging.roboworld.io/airdrop/record-action',
                                   json={
                                       'action_meta': send_data,
                                       'action_name': action,
                                       'email': self.email,
                                       'referral_email': None,
                                       'reward_point': 0,
                                       'wallet_address': ''
                                   })
            if r.status != 200:
                logger.error(f'{self.email} | Wrong Response: {str(await r.text())}')

            else:
                logger.success(f'{self.email} | Task completed successfully {i}/5')

    async def start_register(self, session):
        r = await session.post('https://api-staging.roboworld.io/airdrop/verification',
                               json={
                                   "email": self.email
                               })
        if 'Verification email sent' not in str(await r.text()):
            raise Wrong_Response(str(await r.text()))

        logger.success(f'{self.email} | The message was sent successfully')

    async def Create_Session(self):
        global progress

        try:
            async with aiohttp.ClientSession(
                                            headers={
                                                **headers,
                                                'user-agent': random_useragent()
                                            },
                                            connector=await self.get_connector()
            ) as session:
                async with aiohttp.ClientSession(headers={
                                                    **tempmail_headers,
                                                    'user-agent': random_useragent()
                                                }) as mail_session:
                    self.email = await self.get_email(mail_session)
                    await self.start_register(session)
                    verify_code = await self.check_messages(mail_session)
                    auth_token = await self.Enter_Code(session, verify_code)
                    session.headers['authorization'] = f'Bearer {auth_token}'
                    await self.Complete_Tasks(session)

        except Wrong_Response as error:
            logger.error(f'{self.email} | Wrong Response: {error}')
            return False

        except Email_Timeout:
            logger.error(f'{self.email} | Email Timeou')
            return False

        except Exception as error:
            logger.error(f'{self.email} | Unexpected error: {error}')
            return False

        else:
            progress += 1
            system(f'title roboworld Auto Reger // Progress: {progress}')
            return True


def wrapper(ref_code):
    for _ in range(refs_per_acc):
        while True:
            try:
                if asyncio.run(App(ref_code).Create_Session()):
                    break

            except Exception:
                pass


if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print('Telegram Channel - https://t.me/n4z4v0d\n')
    progress = 0
    system(f'title roboworld Auto Reger // Progress: {progress}')

    threads = int(input('Threads: '))
    refs_per_acc = int(input('How many referrals per account?: '))
    use_proxy = input('Use Proxies? (y/N): ').lower()

    if use_proxy == 'y':
        use_proxy = True
        proxy_type = input('Enter proxy type (http; socks4; socks5): ')
        proxy_folder = input('Drop .txt with your proxies ('
                             'user:pass@ip:port // ip:port): ')

    else:
        use_proxy = False

    ref_codes_folder = input('Drop .txt with your ref.codes: ')

    with open(ref_codes_folder, 'r', encoding='utf-8') as file:
        ref_codes = [row.strip() for row in file]

    clear()

    with Pool(processes=threads) as executor:
        executor.map(wrapper, ref_codes)

    logger.success('The work has been successfully completed')

    if platform == 'win32':
        from msvcrt import getch
        print('\nPress Any Key To Exit..')
        getch()
    else:
        print('\nPress Enter To Exit..')
        input()

    exit()
