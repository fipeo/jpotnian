import eventlet
eventlet.monkey_patch()  # Asegúrate de hacer esto antes de cualquier otro import

import psutil
import platform
from functools import wraps

from sqlalchemy import inspect
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, redirect, url_for, session, request
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send
from datetime import datetime, timedelta, timezone
import os
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# Configuración de las bases de datos separadas
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # Base de datos principal para usuarios
app.config['SQLALCHEMY_BINDS'] = {
    'programs': 'sqlite:///programs.db', # Base de datos vinculada para programas
    'chat': 'sqlite:///chat.db',
    'products' : 'sqlite:///products.db',
    'auctions' : 'sqlite:///auctions.db'
}

# Instancia de SQLAlchemy
db = SQLAlchemy(app)
socketio = SocketIO(app)


# Modelo de Usuario usando la base de datos principal
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    date_joined = db.Column(db.DateTime, default=datetime.now(timezone.utc))


# Modelo de Programa usando la base de datos vinculada 'programs'
class Program(db.Model):
    __bind_key__ = 'programs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    min_ram = db.Column(db.Float, nullable=False)
    min_processor = db.Column(db.String(100), nullable=False)
    min_disk_space = db.Column(db.Float, nullable=False)
    recommended_ram = db.Column(db.Float, nullable=True)
    recommended_processor = db.Column(db.String(100), nullable=True)
    recommended_disk_space = db.Column(db.Float, nullable=True)

def populate_db():
    programs = [
        Program(name="Program A", min_ram=2.0, min_processor="Intel i3", min_disk_space=10.0,
                recommended_ram=4.0, recommended_processor="Intel i5", recommended_disk_space=20.0),
        Program(name="Program B", min_ram=4.0, min_processor="Intel i5", min_disk_space=15.0,
                recommended_ram=8.0, recommended_processor="Intel i7", recommended_disk_space=30.0),
        Program(name="Program C", min_ram=1.0, min_processor="AMD Ryzen 3", min_disk_space=5.0,
                recommended_ram=2.0, recommended_processor="AMD Ryzen 5", recommended_disk_space=10.0),
        Program(name="Program D", min_ram=8.0, min_processor="Intel i7", min_disk_space=25.0,
                recommended_ram=16.0, recommended_processor="Intel i9", recommended_disk_space=50.0),
        Program(name="Program E", min_ram=3.0, min_processor="Intel i3", min_disk_space=8.0,
                recommended_ram=6.0, recommended_processor="Intel i5", recommended_disk_space=16.0),
        Program(name="Program F", min_ram=2.0, min_processor="Intel Pentium", min_disk_space=4.0,
                recommended_ram=4.0, recommended_processor="Intel i3", recommended_disk_space=8.0),
        Program(name="Program G", min_ram=6.0, min_processor="AMD Ryzen 5", min_disk_space=20.0,
                recommended_ram=12.0, recommended_processor="AMD Ryzen 7", recommended_disk_space=40.0),
        Program(name="Program H", min_ram=8.0, min_processor="Intel i7", min_disk_space=30.0,
                recommended_ram=16.0, recommended_processor="Intel i9", recommended_disk_space=60.0),
        Program(name="Program I", min_ram=4.0, min_processor="AMD Ryzen 3", min_disk_space=10.0,
                recommended_ram=8.0, recommended_processor="AMD Ryzen 5", recommended_disk_space=20.0),
        Program(name="Program J", min_ram=2.0, min_processor="Intel i3", min_disk_space=5.0,
                recommended_ram=4.0, recommended_processor="Intel i5", recommended_disk_space=10.0),
    ]

    db.session.bulk_save_objects(programs)
    db.session.commit()

# Población de la base de datos (solo ejecuta esto una vez)
with app.app_context():
    populate_db()


# Modelo de Mensaje usando la base de datos vinculada 'chat'
class Message(db.Model):
    __bind_key__ = 'chat'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

#Modelo de producto
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)  # Ruta a la imagen del producto
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Relacionado con el vendedor
    bid_count = db.Column(db.Integer, default=0)  # Contador de ofertas


#Modelo de boton de subasta
class Auction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    current_bid = db.Column(db.Float, nullable=False, default=0.0)
    bidder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    bidder = db.relationship('User', backref=db.backref('bids', lazy=True))
    end_time = db.Column(db.DateTime, nullable=False)


# Verificar las tablas en la base de datos
with app.app_context():
    db.create_all()
    messages = Message.query.all()
    for message in messages:
        print(f"{message.username}: {message.content} a las {message.timestamp}")
    inspector = inspect(db.engine)
    # Inspecciona la tabla `message` directamente sin el esquema
    columns = inspector.get_columns('message')
    print("Columnas en la tabla 'message':")
    for column in columns:
        print(f"{column['name']} - {column['type']}")


# Resto del código para manejar rutas y lógica de la aplicación
# Función para obtener especificaciones del sistema
def get_system_specs():
    ram = round(psutil.virtual_memory().total / (1024 ** 3))
    processor = platform.processor()
    disk = round(psutil.disk_usage('/').total / (1024 ** 3))
    return ram, processor, disk




def delete_expired_messages():
    current_time = datetime.now(timezone.utc)
    expired_messages = Message.query.filter(Message.timestamp < current_time - timedelta(hours=24)).all()

    if expired_messages:
        for msg in expired_messages:
            db.session.delete(msg)
        db.session.commit()
        print(f"Se han eliminado {len(expired_messages)} mensajes caducados.")


# Ruta para la página principal
@app.route('/')
def home():
    selected_ad_images = get_random_ad_images()
    return render_template('index.html',
                           ad_image_1=url_for('static', filename=f'imagenesads/{selected_ad_images[0]}'),
                           ad_image_2=url_for('static', filename=f'imagenesads/{selected_ad_images[1]}'),
                           ad_image_3=url_for('static', filename=f'imagenesads/{selected_ad_images[2]}'))

# Ruta para la página "Acerca de"
@app.route('/about')
def about():
    selected_ad_images = get_random_ad_images()
    return render_template('about.html',
                           ad_image_1=url_for('static', filename=f'imagenesads/{selected_ad_images[0]}'),
                           ad_image_2=url_for('static', filename=f'imagenesads/{selected_ad_images[1]}'),
                           ad_image_3=url_for('static', filename=f'imagenesads/{selected_ad_images[2]}'))

# Ruta para la página "Contacto"
@app.route('/contact')
def contact():
    selected_ad_images = get_random_ad_images()
    return render_template('contact.html',
                           ad_image_1=url_for('static', filename=f'imagenesads/{selected_ad_images[0]}'),
                           ad_image_2=url_for('static', filename=f'imagenesads/{selected_ad_images[1]}'),
                           ad_image_3=url_for('static', filename=f'imagenesads/{selected_ad_images[2]}'))


# Ruta para manejar la búsqueda de programas
@app.route('/search', methods=['POST'])
def search():
    program_name = request.form['program_name']
    program = Program.query.filter(Program.name.ilike(f"%{program_name}%")).first()

    if program:
        ram, processor, disk = get_system_specs()

        meets_min_requirements = (
                ram >= program.min_ram and
                disk >= program.min_disk_space
        )

        meets_rec_requirements = (
                ram >= program.recommended_ram and
                disk >= program.recommended_disk_space
        ) if program.recommended_ram else None

        return render_template('results.html', program=program,
                               meets_min=meets_min_requirements,
                               meets_rec=meets_rec_requirements,
                               ram=ram,
                               processor=processor,
                               disk=disk)

    return redirect(url_for('add_program', program_name=program_name))

# Ruta para la página de agregar programas no encontrados
@app.route('/add_program', methods=['GET', 'POST'])
def add_program():
    if request.method == 'POST':
        name = request.form['name']
        min_ram = float(request.form['min_ram'])
        min_processor = request.form['min_processor']
        min_disk_space = float(request.form['min_disk_space'])

        new_program = Program(name=name, min_ram=min_ram, min_processor=min_processor, min_disk_space=min_disk_space)
        db.session.add(new_program)
        db.session.commit()

        return redirect(url_for('home'))

    program_name = request.args.get('program_name')
    return render_template('add_program.html', program_name=program_name)

# Ruta para manejar el formulario de contacto
@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    return "Gracias por tu mensaje. Nos pondremos en contacto contigo pronto."

# Ruta para registrarse
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_hash = generate_password_hash(password)

        new_user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

# Ruta para iniciar sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()


        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('home'))
        else:
            return render_template("user_notfound.html")

    return render_template('login.html')

# Decorador para proteger rutas que requieren login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Ejemplo de ruta protegida
@app.route('/dashboard')
@login_required
def dashboard():
    session['access_store'] = True  # Marca que el usuario tiene acceso a la tienda
    return render_template('dashboard.html')

@app.route('/store')
@login_required
def store():
    page = request.args.get('page', 1, type=int)  # Obtén el número de página de la URL, por defecto es 1
    products = Product.query.paginate(page=page, per_page=3)  # Muestra 3 productos por página
    return render_template('store.html', products=products)

@app.route('/my_products', methods=['GET', 'POST'])
@login_required
def my_products():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        image_url = request.form['image_url']
        price = float(request.form['price'])
        new_product = Product(name=name, description=description, image_url=image_url, price=price, seller_id=session['user_id'])
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('my_products'))

    products = Product.query.filter_by(seller_id=session['user_id']).all()
    return render_template('my_products.html', products=products)

@app.route('/bid/<int:product_id>', methods=['POST'])
@login_required
def bid(product_id):
    product = Product.query.get_or_404(product_id)
    product.price += 1  # Incrementa el precio en 1
    product.bid_count += 1  # Incrementa el número de ofertas

    db.session.commit()  # Guarda los cambios en la base de datos

    return redirect(url_for('store'))  # Redirige de vuelta a la tienda

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))


def get_random_ad_images():
    ad_images_directory = os.path.join(app.static_folder, 'imagenesads')
    ad_images = [f for f in os.listdir(ad_images_directory) if os.path.isfile(os.path.join(ad_images_directory, f))]

    selected_images = random.sample(ad_images, 3)  # Selecciona 3 imágenes aleatoriamente
    print(f"Imágenes seleccionadas: {selected_images}")  # Línea de depuración

    return selected_images


@app.route('/user_notfound')
def user_notfound():
    return render_template('user_notfound.html')

@socketio.on('message')
def handle_message(msg):
    username = session.get('username')
    if username:
        current_time = datetime.now(timezone.utc)  # Marca de tiempo actual
        print(f"Recibiendo mensaje: {msg} de {username}")

        # Guarda el mensaje con la marca de tiempo actual
        new_message = Message(username=username, content=msg, timestamp=current_time)
        db.session.add(new_message)

        try:
            db.session.commit()
            print(f"Mensaje guardado correctamente: {new_message.username} - {new_message.content}")
        except Exception as e:
            db.session.rollback()
            print(f"Error al guardar el mensaje: {str(e)}")

        # Envía el mensaje a todos los clientes conectados
        send({'username': username, 'message': msg, 'timestamp': current_time.strftime('%H:%M:%S')}, broadcast=True)

@app.route('/chat')
@login_required
def chat():
    current_time = datetime.now(timezone.utc)  # Hora actual con zona horaria UTC
    messages = Message.query.filter(Message.timestamp >= current_time - timedelta(hours=24)).order_by(Message.timestamp.asc()).all()

    # Depuración para mostrar si se recuperan mensajes
    if messages:
        print(f"Se han recuperado {len(messages)} mensajes.")
        for message in messages:
            print(f"{message.username}: {message.content} a las {message.timestamp}")
    else:
        print("No se han recuperado mensajes.")

    return render_template('chat.html', messages=messages)

@socketio.on('message')
def handle_message(msg):
    username = session.get('username')
    if username:
        current_time = datetime.now(timezone.utc)  # Marca de tiempo actual
        print(f"Recibiendo mensaje: {msg} de {username}")

        # Guarda el mensaje con la marca de tiempo actual
        new_message = Message(username=username, content=msg, timestamp=current_time)
        db.session.add(new_message)

        try:
            db.session.commit()
            print(f"Mensaje guardado correctamente: {new_message.username} - {new_message.content}")
        except Exception as e:
            db.session.rollback()
            print(f"Error al guardar el mensaje: {str(e)}")

        # Envía el mensaje a todos los clientes conectados
        send({'username': username, 'message': msg, 'timestamp': current_time.strftime('%H:%M:%S')}, broadcast=True)

@app.route('/profile')
@login_required
def profile():
    selected_ad_images = get_random_ad_images()
    return render_template('profile.html',
                           ad_image_1=url_for('static', filename=f'imagenesads/{selected_ad_images[0]}'),
                           ad_image_2=url_for('static', filename=f'imagenesads/{selected_ad_images[1]}'),
                           ad_image_3=url_for('static', filename=f'imagenesads/{selected_ad_images[2]}'))


# Iniciar la aplicación Flask
if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)



