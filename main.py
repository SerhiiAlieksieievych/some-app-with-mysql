import tkinter as tk
import re
import os
from dotenv import load_dotenv
import pymysql.cursors

class App():
    def __init__(self):
        self.win = tk.Tk()
        self.user = User()
        self.connector = Connector()
        self.sites_handler = SitesHandler(self)
        self.windows = {"start_window": StartWindow(self),
                        "sign_in_window": SignInWindow(self),
                        "sign_on_window": SignOnWindow(self),
                        "my_sites_window": MySitesWindow(self)
                        }

    def validate_username(self):
        """Дозволяє лише літери, цифри та _, від 3 до 20 символів."""
        return bool(re.fullmatch(r'^[a-zA-Z0-9_]{3,20}$', self.user.username.get()))

    def validate_password(self):
        """Пароль має бути довжиною від 8 до 20 символів, містити хоча б одну літеру та одну цифру."""
        return bool(re.fullmatch(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@#$%^&+=!]{8,20}$', self.user.password.get()))

    def validate_email(self):
        """Проста перевірка коректного формату email."""
        return bool(re.fullmatch(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', self.user.email.get()))

    def start_app(self):
        self.connector.create_table("users", f"""
                    CREATE TABLE users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(255) UNIQUE,
                        password VARCHAR(255),
                        email VARCHAR(255) UNIQUE
                    )
                """)
        self.connector.create_table("sites", f"""
                    CREATE TABLE sites (
                        id INT AUTO_INCREMENT,
                        site VARCHAR(255),
                        entrance_type VARCHAR(255),
                        user_id INT, PRIMARY KEY (id),
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        login VARCHAR(255),
                        password VARCHAR(255)
                    )
                """)
        def center_window(root, width=400, height=300):
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width - width) // 2
            y = (screen_height - height) // 2
            root.geometry(f"{width}x{height}+{x}+{y}")

        center_window(self.win)
        self.win.title('Якийсь там застосунок')
        self.win.resizable(height=False, width=False)
        self.windows['start_window'].show()
        self.win.mainloop()

    def _go_back(self):
        self.user.reset_all()
        self.windows['start_window'].show()

    def clear_window(self):
        for widget in self.win.winfo_children():
            widget.destroy()

    def _show_warning_message(self, text, callback):
        label = tk.Label(self.win, text=text, font=("Arial", 14), wraplength=260, justify="left")
        label.pack(pady=20)
        btn = tk.Button(self.win, text="Спробувати ще раз", command=callback)
        btn.pack(pady=20)

    def _show_success_message(self, text):
        label = tk.Label(self.win, text=text, font=("Arial", 14),  wraplength=260, justify="left")
        label.pack(pady=20)
        btn = tk.Button(self.win, text="Закінчити це все", command=self.win.destroy)
        btn.pack(pady=20)

    def sign_in(self):
        if not self.validate_username():
            self.clear_window()
            self._show_warning_message("Ім'я має містити лише латинські літери, цифри та знак підкреслення, та має бути довжиною від 3 до 20 символів.", self.windows['sign_in_window'].show)
            self.user.reset_all()
        elif not self.user.check_for_existence_username(self.connector,self.user.username.get()):
            self.clear_window()
            self._show_warning_message(
                "Користувач з таким логіном не зареєстрований.",
                self.windows['sign_in_window'].show)
            self.user.reset_all()
        elif self.user.login(self.connector, self.user.username.get(), self.user.password.get()):
            self.clear_window()
            self.user.reset_all()
            self.windows["my_sites_window"].show()
        else:
            self.clear_window()
            self._show_warning_message("Невірний пароль!", self.windows['sign_in_window'].show)
            self.user.reset_password()

    def sign_on(self):
        if not self.validate_username():
            self.clear_window()
            self._show_warning_message(
                "Ім'я має містити лише латинські літери, цифри та знак підкреслення, та має бути довжиною від 3 до 20 символів.",
                self.windows['sign_on_window'].show)
            self.user.reset_all()
        elif not self.validate_email():
            self.clear_window()
            self._show_warning_message(
                "Введіть коректну пошту.",
                self.windows['sign_on_window'].show)
            self.user.reset_email()
            self.user.reset_password()
            self.user.reset_repeated_password()
        elif not self.validate_password():
            self.clear_window()
            self._show_warning_message(
                "Пароль має бути довжиною від 8 до 20 символів, містити хоча б одну латинську літеру та одну цифру.",
                self.windows['sign_on_window'].show)
            self.user.reset_password()
            self.user.reset_repeated_password()
        elif self.user.password.get() != self.user.repeated_password.get():
            self.clear_window()
            self._show_warning_message(
                "Пароль має збігатися в обох полях.",
                self.windows['sign_on_window'].show)
            self.user.reset_password()
            self.user.reset_repeated_password()
        elif self.user.check_for_existence_username(self.connector, self.user.username.get()):
            self.clear_window()
            self._show_warning_message("Користувач з таким ім'ям вже зареєстрований!", self.windows['sign_on_window'].show)
            self.user.reset_all()
        elif self.user.check_has_duplication_email(self.connector, self.user.email.get()):
            self.clear_window()
            self._show_warning_message("Користувач з такою поштою вже зареєстрований!",self.windows['sign_on_window'].show)
            self.user.reset_email()
            self.user.reset_password()
            self.user.reset_repeated_password()
        else:
            self.user.register(self.connector)
            self.sign_in()

    def sign_out(self):
        self.user.clear_user_id()
        self.windows['start_window'].show()

class Connector():
    def __init__(self):
        load_dotenv()  # Завантажує змінні з .env

        self.host = os.getenv("DB_HOST")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME")
        self.charset = os.getenv("DB_CHARSET", "utf8mb4")

    def create_connection(self):
        return pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            charset=self.charset,
            cursorclass=pymysql.cursors.DictCursor
        )

    def table_exists(self, table_name):
        with self.create_connection().cursor() as c:
            c.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            """, (self.database, table_name))
            return c.fetchone() is not None  # Повертає True, якщо таблиця існує

    def create_table(self, table_name:str, command:str):
        connection = self.create_connection()
        """Створює таблицю у MySQL, якщо вона не існує."""
        with connection.cursor() as c:
            # Якщо таблиця не існує, створюємо її
            if not self.table_exists(table_name):
                c.execute(command)
                # Збереження змін
                connection.commit()
class User():
    def __init__(self):
        self.user_id = None
        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.repeated_password = tk.StringVar()
        self.email = tk.StringVar()

    def set_user_id(self, connector):
        connection = connector.create_connection()
        with connection.cursor() as c:
            c.execute("""SELECT id FROM users WHERE username = %s;""", self.username.get())
            self.user_id = c.fetchone()['id']

    def get_user_id(self):
        return self.user_id

    def clear_user_id(self):
        self.user_id = None

    def reset_username(self):
        self.username.set("")

    def reset_password(self):
        self.password.set("")

    def reset_repeated_password(self):
        self.repeated_password.set("")

    def reset_email(self):
        self.email.set("")

    def reset_all(self):
        self.reset_username()
        self.reset_password()
        self.reset_repeated_password()
        self.reset_email()

    def check_for_existence_username(self, connector, username: str) -> bool:
        connection = connector.create_connection()
        with connection.cursor() as c:
            # Перевіряємо, чи існує такий username
            c.execute("SELECT EXISTS(SELECT 1 FROM users WHERE username = %s) AS user_exists", (username,))
            return c.fetchone()["user_exists"]  # Повертає 1 або 0

    def check_has_duplication_email(self, connector, email: str) -> bool:
        connection = connector.create_connection()
        with connection.cursor() as c:
            # Перевіряємо, чи існує такий email
            c.execute("SELECT EXISTS(SELECT 1 FROM users WHERE email = %s) AS email_exists", (email,))
            return c.fetchone()["email_exists"]  # Повертає 1 або 0

    def register(self, connector):
        connection = connector.create_connection()
        """Зберігає дані про користувача у базу даних MySQL."""
        with connection.cursor() as c:
            # Вставка нового користувача в таблицю 'users'
            c.execute("""
                INSERT INTO users (username, password, email) 
                VALUES (%s, %s, %s)
            """, (self.username.get(), self.password.get(), self.email.get()))
            # Збереження змін
            connection.commit()

    def login(self,connector, username: str, password_input: str) -> bool:
        connection = connector.create_connection()
        """ Перевіряє, чи існує користувач з вказаним username та password у базі даних MySQL. Повертає True, якщо такий користувач існує, і False в іншому випадку. """
        with connection.cursor() as c:
            # Перевіряємо наявність користувача з відповідними username та password
            c.execute("""
                SELECT EXISTS(SELECT 1 FROM users WHERE username = %s AND password = %s)
             AS user_exists""", (username, password_input))
            if c.fetchone()["user_exists"]:
                c.close()
                self.set_user_id(connector)
                return True
            else: return False

class SitesHandler():
    def __init__(self, app: App):
        self.app = app
        self.win = app.win
        self.connector = app.connector
        self.user= app.user
        self.selected_kind_of_entrance = tk.StringVar()
        self.site = tk.StringVar()
        self.login = tk.StringVar()
        self.password = tk.StringVar()
        self.selected_kind_of_entrance.set("password")

    def clear_all(self):
        self.selected_kind_of_entrance.set('')
        self.site.set('')
        self.login.set('')
        self.password.set('')
        self.selected_kind_of_entrance.set("password")

    def _show_warning_message(self, text):
        self.app.clear_window()
        label = tk.Label(self.win, text=text, font=("Arial", 14), wraplength=260, justify="left")
        label.pack(pady=20)
        btn = tk.Button(self.win, text="Спробувати ще раз", command=self.app.windows['my_sites_window'].show)
        btn.pack(pady=20)

    def add_site(self):
        connection = self.connector.create_connection()
        if self.validator(self.site.get(), self.selected_kind_of_entrance.get(), self.login.get(), self.password.get()):
            with connection.cursor() as c:
                try:
                    query = """
                            INSERT INTO sites (site, entrance_type, user_id, login, password)
                            VALUES (%s, %s, %s, %s, %s)
                        """
                    values = (self.site.get(), self.selected_kind_of_entrance.get(), self.user.get_user_id(), self.login.get(), self.password.get())#self.user.user_id
                    c.execute(query, values)
                    connection.commit()
                    self.clear_all()
                    self.app.windows['my_sites_window'].show()
                    return True
                except self.connector.Error as err:
                    self._show_warning_message(err)
                    return False

    def validator(self, site, entrance_type ,login, password):
        site_pattern = r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(site_pattern, site):
            self._show_warning_message("Введіть адекватний URL")
            return False
        if entrance_type == 'password':
            if login.strip() == '':
                self._show_warning_message("Введіть логін")
                return False
            if password.strip() == '':
                self._show_warning_message("Введіть пароль")
                return False
            with self.connector.create_connection().cursor() as c:
                user_id = self.user.user_id

                query = "SELECT COUNT(*) FROM sites WHERE user_id = %s AND site = %s AND login = %s"
                c.execute(query, (user_id, site, login))
                result = c.fetchone()
                count = result['COUNT(*)']
                if count:
                    self._show_warning_message("Сайт з таким логіном вже доданий в базу даних")
                    return False
                else:
                    return True
        else:
            with self.connector.create_connection().cursor() as c:
                user_id = self.user.user_id

                query = "SELECT COUNT(*) FROM sites WHERE user_id = %s AND site = %s AND entrance_type = %s"
                c.execute(query, (user_id, site, entrance_type))
                (count,) = c.fetchone()
                if count:
                    return False
                else:
                    return True

    def get_sites(self, user_id):
        connection = self.connector.create_connection()
        try:
            with connection.cursor() as c:
                query = "SELECT * FROM sites WHERE user_id = %s"
                c.execute(query, (user_id,))
                result = c.fetchall()
                return result
        except  pymysql.MySQLError as err:
            self._show_warning_message(err)
            return None

class Window():
    def __init__(self, app:App, previous_window = None):
        self.app = app
        self.previous_window = previous_window

    def set_fullscreen(self):
        app = self.app
        screen_width = app.win.winfo_screenwidth()
        screen_height = app.win.winfo_screenheight()
        app.win.geometry(f"{screen_width}x{screen_height}+0+0")
        app.win.attributes('-fullscreen', True)
        app.win.bind("<Escape>", lambda e: app.win.attributes("-fullscreen", False))

    def set_small_window(self, width=400, height=300):
        app = self.app
        app.win.attributes("-fullscreen", False)
        screen_width = app.win.winfo_screenwidth()
        screen_height = app.win.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        app.win.geometry(f"{width}x{height}+{x}+{y}")


class StartWindow(Window):
    def show(self):
        self.set_small_window()

        app = self.app
        btn_font = ("Arial", 14, "bold")
        app.clear_window()
        suggestion = tk.Label(app.win, text="Оберіть потрібну дію:", font=("Arial", 18, 'bold'), pady=10)
        sign_in_btn = tk.Button(app.win, text="Увійти", command=app.windows['sign_in_window'].show, pady=10, width=15,
                                font=btn_font)
        sign_on_btn = tk.Button(app.win, text="Зареєструватись", command=app.windows['sign_on_window'].show, pady=10, width=15,
                                font=btn_font)
        close_btn = tk.Button(app.win, text="Закрити", command=app.win.destroy, pady=10, width=15, font=btn_font)
        suggestion.pack()
        sign_in_btn.place(relx=0.5, rely=0.3, anchor="center")
        sign_on_btn.place(relx=0.5, rely=0.55, anchor="center")
        close_btn.place(relx=0.5, rely=0.8, anchor="center")

class SignInWindow(Window):
    def show(self):
        self.set_small_window()

        app = self.app
        user = app.user
        app.clear_window()
        label = tk.Label(app.win, text="Введіть Ваше ім'я і пароль!", font=("Arial", 14))
        label.pack(pady=20)

        frame = tk.Frame(app.win, bd=2, relief="ridge")
        btns_frame = tk.Frame(app.win)
        label = tk.Label(frame, text='Username:', bd=10)
        label.grid(row=0, column=0)
        username_field = tk.Entry(frame, textvariable=user.username, bg='white', highlightthickness=1)
        username_field.insert(0, "")
        username_field.grid(row=0, column=1)

        label = tk.Label(frame, text='Password:', bd=10)
        label.grid(row=1, column=0)
        password_field = tk.Entry(frame, textvariable=user.password, bg='white', highlightthickness=1, show="*")
        password_field.insert(0, "")
        password_field.grid(row=1, column=1)

        frame.pack(pady=10)
        btns_frame.pack(pady=10)

        back_btn = tk.Button(btns_frame, text="Назад", command=self.app.windows['start_window'].show)
        btn = tk.Button(btns_frame, text="Увійти", command=self.app.sign_in)
        btn.grid(row=0, column=0, padx=10)
        back_btn.grid(row=0, column=1, padx=10)

class SignOnWindow(Window):
    def show(self):
        self.set_small_window()

        app = self.app
        user = app.user
        app.clear_window()
        label = tk.Label(app.win, text="Введіть Ваші дані!", font=("Arial", 14))
        label.pack(pady=20)

        frame = tk.Frame(app.win, bd=2, relief="ridge")  # рельєф межі фрейму
        btns_frame = tk.Frame(app.win)

        label = tk.Label(frame, text='Username:', bd=10)
        label.grid(row=0, column=0)
        username_field = tk.Entry(frame, textvariable=user.username, bg='white', highlightthickness=1)
        username_field.insert(0, "")
        username_field.grid(row=0, column=1)

        label = tk.Label(frame, text='Email:', bd=10)
        label.grid(row=1, column=0)
        email_field = tk.Entry(frame, textvariable=user.email, bg='white', highlightthickness=1)
        email_field.insert(0, "")
        email_field.grid(row=1, column=1)

        label = tk.Label(frame, text='Password:', bd=10)
        label.grid(row=2, column=0)
        password_field = tk.Entry(frame, textvariable=user.password, bg='white', highlightthickness=1, show="*")
        password_field.insert(0, "")
        password_field.grid(row=2, column=1)

        label = tk.Label(frame, text='Repeat password:', bd=10)
        label.grid(row=3, column=0)
        password_field = tk.Entry(frame, textvariable=user.repeated_password, bg='white', highlightthickness=1,
                                  show="*")
        password_field.insert(0, "")
        password_field.grid(row=3, column=1)

        frame.pack(pady=10)
        btns_frame.pack(pady=10)

        back_btn = tk.Button(btns_frame, text="Назад", command=self.app.windows['start_window'].show)
        btn = tk.Button(btns_frame, text="Зареєструватися", command=self.app.sign_on)
        btn.grid(row=0, column=0, padx=10)
        back_btn.grid(row=0, column=1, padx=10)

class MySitesWindow(Window):
    def parser(self, pframe: tk.Frame, sites: list[dict]):
        for count, site in enumerate(sites, start=1):
            self._string_generator(pframe, site, count)

    def _string_generator(self, frame: tk.Frame, site: dict, string_number: int):
        gusset = f", Login: {site['login']}, Password: {site['password']}" if site['entrance_type'] == 'password' else "."
        label = tk.Label(frame, text=f"Site: {site['site']}, Kind of entrance: {site['entrance_type']}{gusset}", anchor="w")
        label.grid(row=string_number, column=0, sticky="w", padx=5, pady=2)

    def _toggle_inputs(self, radio_var, handled_fields: tuple):
        choice = radio_var.get()
        if choice == "password":
            for f in handled_fields:
                f.config(state='normal')
        else:
            for f in handled_fields:
                f.config(state='disabled')

    def show(self):

        app = self.app
        sites_handler = app.sites_handler
        app.clear_window()
        self.set_fullscreen()

        # Основний контейнер
        main_container = tk.Frame(app.win)
        main_container.pack(fill="both", expand=True, padx=50, pady=30)

        # Заголовок
        title = tk.Label(main_container, text="Сайти на яких ви зареєстровані", font=("Arial", 18, "bold"))
        title.pack(pady=(0, 20))

        # Список сайтів
        sites_frame = tk.Frame(main_container, bd=2, relief="groove", padx=10, pady=10)
        sites_frame.pack(fill="x", padx=10, pady=10)
        self.parser(sites_frame, sites_handler.get_sites(app.user.user_id))

        # Форма додавання
        add_frame = tk.LabelFrame(main_container, text="Додати новий сайт", padx=10, pady=10, font=("Arial", 12))
        add_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(add_frame, text='Сайт:').grid(row=0, column=0, sticky="e", pady=5)
        sitename_field = tk.Entry(add_frame, textvariable=sites_handler.site, bg='white', width=40)
        sitename_field.grid(row=0, column=1, pady=5)

        tk.Label(add_frame, text='Логін:').grid(row=1, column=0, sticky="e", pady=5)
        login_field = tk.Entry(add_frame, textvariable=sites_handler.login, bg='white', width=40)
        login_field.grid(row=1, column=1, pady=5)

        tk.Label(add_frame, text='Пароль:').grid(row=2, column=0, sticky="e", pady=5)
        password_field = tk.Entry(add_frame, textvariable=sites_handler.password, bg='white', show="*", width=40)
        password_field.grid(row=2, column=1, pady=5)

        tk.Label(add_frame, text='Тип входу:').grid(row=3, column=0, sticky="ne", pady=5)
        radio_frame = tk.Frame(add_frame)
        radio_frame.grid(row=3, column=1, sticky="w", pady=5)

        radios = [
            ("Логін-пароль", "password"),
            ("Гугл", "google"),
            ("Фейс.. Мета", "meta"),
            ("Гітхаб", "github"),
            ("Яблуко", "apple")
        ]

        for i, (text, value) in enumerate(radios):
            tk.Radiobutton(radio_frame, text=text, variable=sites_handler.selected_kind_of_entrance, command=lambda: self._toggle_inputs(sites_handler.selected_kind_of_entrance,(login_field,password_field)), value=value).grid(row=i, column=0, sticky="w")

        # Кнопки
        btns_add_frame = tk.Frame(main_container)
        btns_add_frame.pack(pady=20)

        tk.Button(btns_add_frame, text="Додати", command=sites_handler.add_site, width=15).grid(row=0, column=0, padx=20)
        tk.Button(btns_add_frame, text="Вийти", command=self.app.sign_out, width=15).grid(row=0, column=1, padx=20)


import pymysql

some_app = App()
some_app.start_app()