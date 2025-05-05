from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask import Flask, render_template, redirect, url_for
import sqlalchemy
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
from data import db_session
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, TextAreaField, SubmitField, EmailField
from wtforms.validators import DataRequired
import datetime
from werkzeug.security import check_password_hash, generate_password_hash
SqlAlchemyBase = orm.declarative_base()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)


class RegisterForm(FlaskForm): # форма регистрации
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    name = StringField('Имя', validators=[DataRequired()])
    surname = StringField('Фамилия', validators=[DataRequired()])
    submit = SubmitField('Войти')


class LoginForm(FlaskForm): # форма авторизации
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class AddBookForm(FlaskForm): # форма добавления книги в базу
    name = StringField('Название', validators=[DataRequired()])
    author = StringField('Автор', validators=[DataRequired()])
    submit = SubmitField('Добавить')


@login_manager.user_loader
def load_user(user_id): # авторизация пользователя
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


class User(SqlAlchemyBase, UserMixin): # модель пользователя
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, 
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    surname = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String, 
                              index=True, unique=True, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    list_of_books = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    books = orm.relationship("Books", back_populates='user')
    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)


class Books(SqlAlchemyBase): # модель книги
    __tablename__ = 'books'

    id = sqlalchemy.Column(sqlalchemy.Integer, 
                        primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    author = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    is_available = sqlalchemy.Column(sqlalchemy.Boolean, default=True)
    reader = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"), nullable=True)
    reader_name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    user = orm.relationship('User')
    date = sqlalchemy.Column(sqlalchemy.String, nullable=True)


@app.route('/login', methods=['GET', 'POST'])
def login(): # обработчик авторизации
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect("/main_str")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register(): # обработчик регистрации
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            surname=form.surname.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


def get_book(book_id): # выдача книги пользователю
    db_sess = db_session.create_session()
    current_book = db_sess.query(Books).filter(Books.id == book_id).first()
    current_book.is_available = False
    current_book.reader = current_user.id
    current_book.reader_name = current_user.name + ' ' + current_user.surname
    delta_time = datetime.timedelta(days=14)
    date = datetime.datetime.now().date() + delta_time
    current_book.date = date.strftime("%d.%m.%Y")
    db_sess.commit()


def return_book(book_id): # возврат книги в библиотеку
    db_sess = db_session.create_session()
    current_book = db_sess.query(Books).filter(Books.id == book_id).first()
    current_book.is_available = True
    current_book.reader = None
    current_book.reader_name = None
    current_book.date = None
    db_sess.commit()


@app.route('/logout')
@login_required
def logout(): # выход из аккаунта
    logout_user()
    return redirect("/login")


@app.route('/toggle_on/<int:book_id>')
def toggle_on(book_id): # обработка выдачи книги
    get_book(int(book_id))
    session = db_session.create_session()
    books = session.query(Books).all()
    return render_template("list_of_books.html", books=books)


@app.route('/toggle_off/<int:book_id>')
def toggle_off(book_id): # обработка возврата книги
    return_book(int(book_id))
    session = db_session.create_session()
    books = session.query(Books).all()
    return render_template("list_of_books.html", books=books)


@app.route('/delete_book/<int:book_id>', methods=['GET', 'POST'])
def delete_book(book_id): # удаление книги из БД
    session = db_session.create_session()
    books = session.query(Books).filter(Books.id == book_id).first()
    if books:
        session.delete(books)
        session.commit()
    books = session.query(Books).all()
    return render_template("list_of_books.html", books=books)


@app.route('/list_of_books')
def list_of_books(): # отображение списка книг
    session = db_session.create_session()
    books = session.query(Books).all()
    return render_template("list_of_books.html", books=books)


@app.route('/main_str')
def main_str(): # отображение главного меню
    try:
        user_id = current_user.id
        if current_user.id:
            return render_template("main.html", user_id=current_user.id)
        else:
            return render_template("main.html", user_id=0)
    except Exception:
        return render_template("main.html", user_id=0)


@app.route('/add_book', methods=['GET', 'POST'])
def add_book(): # форма добавления книги
    form = AddBookForm()
    if form.validate_on_submit() and current_user.id == 2:
        db_sess = db_session.create_session()
        new_book = Books(
            name=form.name.data,
            author=form.author.data,
            is_available=True
        )
        db_sess.add(new_book)
        db_sess.commit()
        return redirect('/list_of_books')
    elif current_user.id != 2:
        return redirect('/error')
    return render_template('add_book.html', form=form)


@app.route('/error')
def error(): # окно вывода ошибки
    return render_template("error.html")


if __name__ == '__main__':
    db_session.global_init('base.db')
    app.run(port=8080, host='127.0.0.1')