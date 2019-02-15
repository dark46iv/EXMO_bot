import urllib
import requests
import time
import datetime
import json
import chardet  # библиотека определения кодировки файла
import hmac, hashlib  # эти модули нужны для генерации подписи API
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import threading


class MyThread(threading.Thread):
    """Класс для запуска отдельных потоков GUI и подключения к api"""

    def __init__(self, func, counter):
        threading.Thread.__init__(self)
        self.threadID = counter
        self.counter = counter
        self.func = func

    def run(self):
        print("Запуск " + self.name)
        self.func()
        print("Выход " + self.name)


class GuiBot(tk.Tk):
    """Графический интерфейс"""

    def __init__(self):
        self.running = False
        tk.Tk.__init__(self)
        self.title('EXMO bot v0.0.4')
        self.frame = ttk.Frame(self)
        self.info_box = ScrolledText(self, width=80, height=21)  # Основное окно с информацией
        self.pair_info = tk.Text(self, width=40, height=10)  # Информация о парах
        self.open_orders = tk.Text(self, width=40, height=10)  # Открытые ордера
        self.other_info = tk.Label(self, width=80, height=2)  # Остальная информация под основным окном
        self.start_button = ttk.Button(self, text='Старт', command=self.start_working)
        self.stop_button = ttk.Button(self, text='Стоп', command=self.stop_working)
        self.exit_button = ttk.Button(self, text='Выход', command=self.exit_app)
        self.pressing_count = 0

    def initialization(self):
        """Распологаем виджеты"""

        self.frame.grid(column=0, row=0)
        self.info_box.grid(column=0, row=0, columnspan=3, rowspan=2, padx=5, pady=5)
        self.pair_info.grid(column=3, row=0, padx=5, pady=5, sticky='n')
        self.open_orders.grid(column=3, row=1, padx=5, pady=5, sticky='s')
        self.other_info.grid(column=0, row=2, columnspan=3)
        self.start_button.grid(column=1, row=3, pady=5, padx=5, sticky='w,e')
        self.stop_button.grid(column=2, row=3, pady=5, padx=5, sticky='w,e')
        self.exit_button.grid(column=3, row=3, pady=5, padx=5, sticky='w,e')

    def print_into_gui(self, text):
        """Отображение текста в GUI"""

        self.info_box.configure(state=tk.NORMAL)
        self.info_box.insert('end', datetime.datetime.today().strftime('[%H-%M-%S]') + ' ' + text + '\n')
        self.info_box.see('end')
        self.info_box.configure(state=tk.DISABLED)

    def logger(self, input_text):
        """Запись логов в файл"""

        with open(f'{datetime.datetime.today().strftime("%d-%m-%Y")}-log.txt', 'a') as file:
            file.write(f'{datetime.datetime.today().strftime("[%H-%M-%S]")} {input_text}\n')

    def start_working(self):
        """Команда для кнопки Старт
        Смотрим количество нажатий, чтобы не запускать кучу циклов и потоков
        Запускаются 2 потока - ГУИ и метода с логикой торговли и тд"""

        try:
            self.pressing_count += 1
            if self.pressing_count <= 1:
                self.running = True
                self.print_into_gui('Старт')
                bot.import_options()
                thread1 = MyThread(bot.main_flow, '1')
                thread2 = MyThread(bot.Bot.update, '1')
                while self.running:
                    thread1.run()
                    thread2.run()
        except requests.exceptions.ProxyError:
            self.pressing_count = 0

    def stop_working(self):
        """Команда для кнопки Стоп
        Сбрасываем счетчик нажатий для кнопки Старт и отменяем последний ордер"""

        self.pressing_count = 0
        self.running = False
        self.print_into_gui('Стоп. Отмена ордера.')

        try:
            bot.call_api(
                'order_cancel',
                order_id=bot.order_id,
            )
        except Exception:
            pass

    def exit_app(self):
        """Кнопка выход"""

        self.logger('Выход')
        self.destroy()


class ConnectApi:
    """Интерфейс соединения с api Exmo"""

    def __init__(self):

        self.proxy = None
        self.API_KEY = ''  # ключ берется с биржи
        self.API_SECRET = b''  # секрет там же
        self.API_URL = 'https://api.exmo.me'
        self.API_VERSION = 'v1'

        # Тонкая настройка
        self.CURRENCY_1 = 'USDT'  # Торгуемая валюта
        self.CURRENCY_2 = 'USD'  # В какой валюте торговать
        self.CURRENT_PAIR = f'{self.CURRENCY_1}_{self.CURRENCY_2}'
        self.balances = {self.CURRENCY_1: 'Обновляется', self.CURRENCY_2: 'Обновляется'}
        self.CURRENCY_1_MIN_QUANTITY = 1  # минимальная сумма ставки - берется из https://api.exmo.com/v1/pair_settings/
        self.ORDER_LIFE_TIME = 1  # через сколько минут отменять неисполненный ордер на покупку CURRENCY_1
        self.STOCK_FEE = 0.002  # Комиссия, которую берет биржа (0.002 = 0.2%)
        self.AVG_PRICE_PERIOD = 60  # За какой период брать среднюю цену (мин) УЖЕ НЕ АКТУАЛЬНО
        self.CAN_SPEND = 5  # Сколько тратить CURRENCY_2 каждый раз при покупке CURRENCY_1
        self.PROFIT_MARKUP = 0.001  # Какой навар нужен с каждой сделки? (0.001 = 0.1%)
        self.DEBUG = True  # True - выводить отладочную информацию, False - писать как можно меньше
        self.STOCK_TIME_OFFSET = 0  # Если расходится время биржи с текущим

        # базовые настройки
        self.API_URL = 'https://api.exmo.me'
        self.API_VERSION = 'v1'
        self.payload = {'nonce': int(round(time.time() * 1000))}
        self.proxies = {}
        self.Bot = GuiBot()
        self.import_options()
        self.Bot.other_info.configure(
            text=f'Пара: {self.CURRENT_PAIR}     Навар: {self.PROFIT_MARKUP*100}%    Можно тратить {self.CURRENCY_2}: {self.CAN_SPEND}')
        self.Bot.pair_info.insert(1.0, 'Нет информации')
        self.Bot.open_orders.insert(1.0, 'Нет информации')
        self.Bot.info_box.configure(state=tk.DISABLED)
        self.Bot.pair_info.configure(state=tk.DISABLED)
        self.Bot.open_orders.configure(state=tk.DISABLED)

    def import_options(self):
        """Импортируем опции из файла config.cfg.
        Если файла нет, то остаются дефолтные настройки"""

        try:
            with open('config.cfg', 'rb', ) as file:
                encode = chardet.detect(file.read())['encoding']
            with open('config.cfg', 'r', encoding=encode) as file:
                config = json.loads(file.read())
                self.CURRENCY_1 = config['Валюта1']
                self.CURRENCY_2 = config['Валюта2']
                self.balances = {self.CURRENCY_1: 'Обновляется', self.CURRENCY_2: 'Обновляется'}
                self.STOCK_FEE = float(config['Комиссия биржи *100%'])
                self.CAN_SPEND = float(config['На сколько Валюты2 можно закупиться'])
                self.PROFIT_MARKUP = float(config['Навар *100%'])
                self.CURRENT_PAIR = f'{self.CURRENCY_1}_{self.CURRENCY_2}'
                self.CURRENCY_1_MIN_QUANTITY = self.find_min_quantity()
                if config['Ключ API открытый'] != '':
                    self.API_KEY = config['Ключ API открытый']
                    self.API_SECRET = bytes(config['Ключ API закрытый'], encoding="utf_8")
        except FileNotFoundError:
            pass
        except requests.exceptions.ProxyError:
            self.Bot.print_into_gui('Нет соединения с прокси-сервером')

    def find_min_quantity(self):
        """Запрашиваем минимальное количество валюты для ордера"""

        quantity = requests.get(f'{self.API_URL}/{self.API_VERSION}/pair_settings/').json()[self.CURRENT_PAIR][
            'min_quantity']
        return float(quantity)

    def sha512_sign(self):
        """Шифруем подпись для запроса POST к api Exmo"""

        H = hmac.new(key=self.API_SECRET, digestmod=hashlib.sha512)
        H.update(self.payload.encode('utf-8'))
        return H.hexdigest()

    def call_api(self, api_method, **kwargs):
        """Основной метод соединения с api Exmo"""

        # Составляем словарь {ключ:значение} для отправки на биржу
        # пока что в нём {'nonce':123172368123}
        self.payload = {'nonce': int(round(time.time() * 1000))}

        # Если в ф-цию переданы параметры в формате ключ:значение
        if kwargs:
            # добавляем каждый параметр в словарь payload
            # Получится {'nonce':123172368123, 'param1':'val1', 'param2':'val2'}
            self.payload.update(kwargs)

        # Переводим словарь payload в строку, в формат для отправки через GET/POST и т.п.
        self.payload = urllib.parse.urlencode(self.payload)

        # Формируем заголовки request для отправки запроса на биржу.
        # Передается публичный ключ API и подпись, полученная с помощью hmac
        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Key": self.API_KEY,
                   "Sign": self.sha512_sign()}
        # Создаем подключение к бирже
        # В заголовке запроса уходят headers, в теле - payload
        response = requests.post(f'{self.API_URL}/{self.API_VERSION}/{api_method}',
                                 headers=headers,
                                 data=self.payload
                                 )
        # Получаем ответ с биржи и читаем его в переменную response
        try:
            # Полученный ответ переводим в строку UTF, и пытаемся преобразовать из текста в объект Python
            obj = response.json()

            # Смотрим, есть ли в полученном объекте ключ "error"
            if 'error' in obj and obj['error']:
                # Если есть, выдать ошибку, код дальше выполняться не будет
                raise ScriptError(obj['error'])
            # Вернуть полученный объект как результат работы ф-ции
            return obj
        except ValueError:
            # Если не удалось перевести полученный ответ (вернулся не JSON)
            raise ScriptError('Ошибка анализа возвращаемых данных, получена строка')

    def last_bids(self):
        """Запрашиваем последнюю информацию о торгуемых парах и отображаем в GUI"""

        lastbids = requests.get(f'{self.API_URL}/{self.API_VERSION}/order_book/', params={'pair': self.CURRENT_PAIR})
        bids_info = lastbids.json()[self.CURRENT_PAIR]
        my_balances = self.call_api('user_info')['balances']
        self.ask_top = bids_info['ask_top']
        self.bid_top = bids_info['bid_top']
        self.Bot.pair_info.configure(state=tk.NORMAL)
        self.Bot.pair_info.delete(1.0, 'end')
        self.Bot.pair_info.insert(1.0, f'Пара: {self.CURRENT_PAIR}\n')
        self.Bot.pair_info.insert(2.0, f'Курс покупки: {self.bid_top}\n')
        self.Bot.pair_info.insert(3.0, f'Курс продажи: {self.ask_top}\n')
        self.Bot.pair_info.insert(4.0, f'Количество {self.CURRENCY_1} не в ордерах: {my_balances[self.CURRENCY_1]}\n')
        self.Bot.pair_info.insert(5.0, f'Количество {self.CURRENCY_2} не в ордерах: {my_balances[self.CURRENCY_2]}')
        self.Bot.open_orders.configure(state=tk.DISABLED)

    def last_buy_price(self):
        """Выдаст цену за которую купили CURRENCY1 в последний раз"""

        last_buy_price = self.call_api(
            'order_create'
        )
        for i in last_buy_price.json()[self.CURRENT_PAIR]:
            if i['type'] == 'buy':
                buy_price = i['price']
                break
        return buy_price

    def main_flow(self):
        """Основной метод логики торговли"""

        self.last_bids()
        try:
            # Получаем список активных ордеров
            try:
                opened_orders = self.call_api('user_open_orders')[self.CURRENT_PAIR]
                self.Bot.open_orders.configure(state=tk.NORMAL)
                self.Bot.open_orders.delete(1.0, 'end')
                self.Bot.open_orders.insert(1.0,
                                            f'Создан: {time.ctime(int(opened_orders[0]["created"]))}\n[{opened_orders[0]["type"]}] {opened_orders[0]["quantity"]} {self.CURRENCY_1} за {opened_orders[0]["price"]}')
                self.Bot.open_orders.configure(state=tk.DISABLED)
            except KeyError:
                if self.DEBUG:
                    print('Открытых ордеров нет')
                    self.Bot.print_into_gui('Открытых ордеров нет')
                    self.Bot.open_orders.configure(state=tk.NORMAL)
                    self.Bot.open_orders.delete(1.0, 'end')
                    self.Bot.open_orders.insert(1.0, 'Открытых ордеров нет')
                    self.Bot.open_orders.configure(state=tk.DISABLED)
                opened_orders = []

            sell_orders = []
            # Есть ли неисполненные ордера на продажу CURRENCY_1?
            for order in opened_orders:
                if order['type'] == 'sell':
                    # Есть неисполненные ордера на продажу CURRENCY_1, выход
                    raise ScriptQuitCondition(
                        'Выход, ждем пока не исполнятся/закроются все ордера на продажу (один ордер может быть разбит биржей на несколько и исполняться частями)')
                else:
                    # Запоминаем ордера на покупку CURRENCY_1
                    sell_orders.append(order)

            # Проверяем, есть ли открытые ордера на покупку CURRENCY_1
            if sell_orders:  # открытые ордера есть
                for order in sell_orders:
                    # Проверяем, есть ли частично исполненные
                    if self.DEBUG:
                        print('Проверяем, что происходит с отложенным ордером', order['order_id'])
                        self.Bot.print_into_gui(f'Проверяем, что происходит с отложенным ордером {order["order_id"]}')
                    try:
                        order_history = self.call_api('order_trades', order_id=order['order_id'])
                        # хуй знает зачем надо бы разобраться как нибудь

                        # по ордеру уже есть частичное выполнение, выход
                        raise ScriptQuitCondition(
                            'Выход, продолжаем надеяться докупить валюту по тому курсу, по которому уже купили часть')
                    except ScriptError as e:
                        if 'Error 50304' in str(e):
                            if self.DEBUG:
                                print('Частично исполненных ордеров нет')
                                self.Bot.print_into_gui('Частично исполненных ордеров нет')

                            time_passed = time.time() + self.STOCK_TIME_OFFSET * 60 * 60 - int(order['created'])

                            if time_passed > self.ORDER_LIFE_TIME * 60:
                                # Ордер уже давно висит, никому не нужен, отменяем
                                self.call_api('order_cancel', order_id=order['order_id'])
                                self.Bot.logger(f'Отмена ордера {order["order_id"]}\n')
                                raise ScriptQuitCondition(
                                    'Отменяем ордер за ' + str(
                                        self.ORDER_LIFE_TIME) + ' минут не удалось купить ' + str(
                                        self.CURRENCY_1))
                            else:
                                raise ScriptQuitCondition(
                                    'Выход, продолжаем надеяться купить валюту по указанному ранее курсу, со времени создания ордера прошло %s секунд' % str(
                                        time_passed))
                        else:
                            raise ScriptQuitCondition(str(e))

            else:  # Открытых ордеров нет
                balances = self.call_api('user_info')['balances']
                if float(balances[
                             self.CURRENCY_1]) >= self.CURRENCY_1_MIN_QUANTITY:  # Есть ли в наличии CURRENCY_1, которую можно продать?

                    """
                        Высчитываем курс для продажи.
                        Нам надо продать всю валюту, которую купили, на сумму, за которую купили + немного навара и минус комиссия биржи
                        При этом важный момент, что валюты у нас меньше, чем купили - бирже ушла комиссия
                        0.00134345 1.5045
                    """
                    wanna_get = self.CAN_SPEND + self.CAN_SPEND * (
                            self.STOCK_FEE + self.PROFIT_MARKUP)  # сколько хотим получить за наше кол-во
                    buy_price = self.last_buy_price()
                    wanna_get1 = (buy_price + buy_price * (self.STOCK_FEE + self.PROFIT_MARKUP)) * float(
                        balances[self.CURRENCY_1])
                    oprimal_price = buy_price + buy_price * (self.STOCK_FEE + self.PROFIT_MARKUP)
                    print('sell', balances[self.CURRENCY_1], oprimal_price, balances[self.CURRENCY_1] * oprimal_price)
                    self.Bot.print_into_gui(
                        f'Продажа {balances[self.CURRENCY_1]} за {oprimal_price}: {balances[self.CURRENCY_1]*oprimal_price}')
                    debug_info = f'[ПРОДАЖА]\n Цена продажи({oprimal_price}) = цена последной покупки({buy_price} + {buy_price} * (комиссия биржи({self.STOCK_FEE}) + навар({self.PROFIT_MARKUP}))\n' \
                                 f'Продаем всю котлету которая имеется({balances[self.CURRENCY_1]})'
                    self.Bot.logger(debug_info + '\n')
                    new_order = self.call_api(
                        'order_create',
                        pair=self.CURRENT_PAIR,
                        quantity=balances[self.CURRENCY_1],
                        price=oprimal_price,
                        type='sell'
                    )
                    self.order_id = new_order['order_id']
                    if self.DEBUG:
                        print('Создан ордер на продажу', self.CURRENCY_1, new_order['order_id'])
                        self.Bot.print_into_gui(f'Создан ордер на продажу {self.CURRENCY_1} {new_order["order_id"]}')
                        self.Bot.logger(f'Создан ордер на продажу {self.CURRENCY_1} {new_order["order_id"]}\n')
                else:
                    # CURRENCY_1 нет, надо докупить
                    # Достаточно ли денег на балансе в валюте CURRENCY_2 (Баланс >= CAN_SPEND)
                    if float(balances[self.CURRENCY_2]) >= self.CAN_SPEND:
                        # Узнать среднюю цену за AVG_PRICE_PERIOD, по которой продают CURRENCY_1
                        """
                         Exmo не предоставляет такого метода в API, но предоставляет другие, к которым можно попробовать привязаться.
                         У них есть метод required_total, который позволяет подсчитать курс, но,
                             во-первых, похоже он берет текущую рыночную цену (а мне нужна в динамике), а
                             во-вторых алгоритм расчета скрыт и может измениться в любой момент.
                         Сейчас я вижу два пути - либо смотреть текущие открытые ордера, либо последние совершенные сделки.
                         Оба варианта мне не слишком нравятся, но завершенные сделки покажут реальные цены по которым продавали/покупали,
                         а открытые ордера покажут цены, по которым только собираются продать/купить - т.е. завышенные и заниженные.
                         Так что берем информацию из завершенных сделок.
                         
                         УЖЕ НЕ АКТУАЛЬНО. В НОВОЙ ВЕРСИИ БЕРЕМ СРЕДНЮЮ ЦЕНУ ПО ПОСЛЕДНИМ 15 СДЕЛКАМ
                        """
                        deals = self.call_api('trades', pair=self.CURRENT_PAIR)
                        prices = []
                        for deal in deals[self.CURRENT_PAIR]:
                            time_passed = time.time() + self.STOCK_TIME_OFFSET * 60 * 60 - int(deal['date'])
                            if time_passed < self.AVG_PRICE_PERIOD * 60:
                                prices.append(float(deal['price']))
                        good_prices = []
                        trades = deals[self.CURRENT_PAIR][:15]
                        for trade in trades:
                            good_prices.append(float(trade['price']))
                        try:
                            avg_price = sum(prices) / len(prices)
                            avg_price1 = sum(good_prices) / 15
                            """
                                Посчитать, сколько валюты CURRENCY_1 можно купить.
                                На сумму CAN_SPEND за минусом STOCK_FEE, и с учетом PROFIT_MARKUP
                                ( = ниже средней цены рынка, с учетом комиссии и желаемого профита)
                            """
                            # купить больше, потому что биржа потом заберет кусок
                            my_need_price = avg_price1 - avg_price1 * (self.STOCK_FEE + self.PROFIT_MARKUP)
                            my_amount = self.CAN_SPEND / my_need_price

                            print('buy', my_amount, my_need_price)
                            self.Bot.print_into_gui(
                                f'Покупка {float("{0:.7f}".format(my_amount))} {self.CURRENCY_1} за {my_need_price}')
                            debug_info = f'[ПОКУПКА] \n{my_need_price}(Цена) = ср. цена {avg_price1} - ср. цена {avg_price1} * ( коммиссия {self.STOCK_FEE} + профит {self.PROFIT_MARKUP})\n' \
                                         f'{my_amount}(Кол-во)  = {self.CAN_SPEND}(Котлета на которую можно закупиться) / {my_need_price}'
                            self.Bot.logger(debug_info + '\n')

                            # Допускается ли покупка такого кол-ва валюты (т.е. не нарушается минимальная сумма сделки)
                            if my_amount >= self.CURRENCY_1_MIN_QUANTITY:
                                new_order = self.call_api(
                                    'order_create',
                                    pair=self.CURRENT_PAIR,
                                    quantity=my_amount,
                                    price=my_need_price,
                                    type='buy'
                                )
                                self.order_id = new_order['order_id']
                                if self.DEBUG:
                                    print('Создан ордер на покупку', new_order['order_id'])
                                    self.Bot.print_into_gui(f'Создан ордер на покупку {new_order["order_id"]}')
                                    self.Bot.logger(f'Создан ордер на покупку {new_order["order_id"]}\n')

                            else:  # мы можем купить слишком мало на нашу сумму
                                print(f'{my_amount} >= {self.CURRENCY_1_MIN_QUANTITY}')
                                print(f'my_amount = {self.CAN_SPEND} / {my_need_price}')
                                print(
                                    f'my_need_price = {avg_price1} - {avg_price1} * ({self.STOCK_FEE} + {self.PROFIT_MARKUP})')
                                raise ScriptQuitCondition('Выход, не хватает денег на создание ордера')
                        except ZeroDivisionError:
                            print('Не удается вычислить среднюю цену. проверьте есть ли продажи за указанное время',
                                  prices)
                            self.Bot.print_into_gui(
                                'Не удается вычислить среднюю цену. Проверьте есть ли продажи за указанное время')
                    else:
                        raise ScriptQuitCondition('Выход, не хватает денег')
        except ScriptError as e:
            print(e)

        except ScriptQuitCondition as e:
            if self.DEBUG:
                print(e)
            pass
        except Exception as e:
            print("!!!!", e)
            self.Bot.logger('!!!!!' + e + '\n')


# Свой класс исключений
class ScriptError(Exception):
    def __init__(self, value):
        self.msg = value

    def __str__(self):
        return self.msg


class ScriptQuitCondition(Exception):
    def __init__(self, value):
        self.msg = value

    def __str__(self):
        bot.Bot.print_into_gui(self.msg)
        return self.msg


if __name__ == '__main__':
    bot = ConnectApi()
    bot.Bot.initialization()
    bot.Bot.mainloop()
