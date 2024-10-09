import firebase_admin
import pyrebase
from firebase_admin import credentials, auth, firestore, storage
from werkzeug.utils import secure_filename  # Agregar esta línea
import requests

#elementos de pyrebase
pyrebase_config = {
    'apiKey': "AIzaSyDbIXvBcY3eMI3gjmT6gBQzUffZBwRfs0U",
    'authDomain': "db-adultosmayores.firebaseapp.com",
    'projectId': "db-adultosmayores",
    'storageBucket': "db-adultosmayores.appspot.com",
    'messagingSenderId': "265073519756",
    'appId': "1:265073519756:web:bf73838cee30b0434f9fa9",
    'databaseURL': "",
    'measurementId': ""
}

# Inicializa Pyrebase para la autenticación
firebase = pyrebase.initialize_app(pyrebase_config)
auth_pyrebase = firebase.auth()
storag = firebase.storage()

# Inicializa Firebase Admin SDK para Firestore
cred = credentials.Certificate('src/db-adultosmayores-firebase-adminsdk-ronp2-81d9bc77c6.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': "db-adultosmayores.appspot.com"
})
db = firestore.client()

bucket = storage.bucket()

# Función para agregar usuarios a Firestore (con contraseña, pendientes de aceptación)
def agregar_usuario_firestore(nombre, email, rol, password):
    user_ref = db.collection('usuarios').add({
        'nombre': nombre,
        'email': email,
        'rol': rol,
        'password': password,  # Almacenar contraseña temporalmente
        'aceptado': False
    })
    return user_ref[1].id  # Retorna el ID del documento creado

# Función para actualizar la contraseña usando Firebase Admin SDK
def update_user_password(email, new_password):
    try:
        user_record = auth.get_user_by_email(email)
        auth.update_user(user_record.uid, password=new_password)
        return True, "Contraseña actualizada con éxito"
    except Exception as e:
        return False, str(e)

# Función para iniciar sesión (verificar si está aceptado)
def iniciar_sesion(email, password):
    try:
        # Verificar en Firebase Auth
        user = auth_pyrebase.sign_in_with_email_and_password(email, password)
        user_info = db.collection('usuarios').where('email', '==', email).get()
        
        if user_info:
            usuario = user_info[0].to_dict()
            usuario['id'] = user_info[0].id  # Asegúrate de agregar el ID al diccionario
            if usuario.get('aceptado'):  # Verifica si el usuario está aceptado
                return usuario
        
        return None  # Usuario no aceptado o no encontrado
    except Exception as e:
        print(f"Error en el inicio de sesión: {e}")
        return None  # Retorna None si hay un error

# Función para obtener un usuario por su ID
def obtener_usuario_por_id(user_id):
    user_ref = db.collection('usuarios').document(user_id).get()
    return user_ref.to_dict()  # Retorna el documento del usuario como un diccionario

# Función para subir una imagen al almacenamiento
def subir_imagen(document_id, imagen, folder):
    try:
        # Asegura el nombre del archivo
        filename = secure_filename(imagen.filename)
        
        # Define la ruta en el bucket de Firebase Storage
        blob_path = f'{folder}/{document_id}/{filename}'
        blob = storage.bucket().blob(blob_path)
        
        # Sube la imagen al storage
        blob.upload_from_file(imagen)
        
        # Establece los permisos de acceso público para el objeto
        blob.make_public()
        
        # Devuelve la URL de descarga de la imagen
        return blob.public_url
    except Exception as e:
        # Maneja cualquier error que pueda ocurrir durante la carga de la imagen
        print(f'Ocurrió un error al cargar la imagen: {str(e)}')
        return None

# Función para actualizar la imagen de perfil de un usuario
def actualizar_imagen_perfil(user_id, image_url):
    try:
        # Actualiza el campo 'image_url' del usuario en Firestore
        db.collection('usuarios').document(user_id).update({
            'image_url': image_url
        })
    except Exception as e:
        print(f'Error actualizando la imagen de perfil: {str(e)}')

# Función para obtener usuarios por rol
def obtener_usuarios_por_rol(rol):
    usuarios = []
    usuarios_ref = db.collection('usuarios').where('rol', '==', rol).get()
    for usuario in usuarios_ref:
        data = usuario.to_dict()
        usuarios.append({
            'id': usuario.id,
            'nombre': data.get('nombre'),
            'email': data.get('email'),
            'rol': data.get('rol'),
            'aceptado': data.get('aceptado', False)
        })
    return usuarios  # Retorna una lista de usuarios filtrados por rol

# Función para aceptar un usuario
def aceptar_usuario(user_id):
    user_ref = db.collection('usuarios').document(user_id)
    user_data = user_ref.get().to_dict()

    if user_data and not user_data['aceptado']:
        try:
            # Crear el usuario en Firebase Authentication si no existe
            auth.create_user(
                uid=user_id,
                email=user_data['email'],
                password=user_data['password']
            )

            # Iniciar sesión con Pyrebase para enviar el correo de verificación
            user = auth_pyrebase.sign_in_with_email_and_password(user_data['email'], user_data['password'])
            auth_pyrebase.send_email_verification(user['idToken'])

            # Actualizar el estado del usuario en Firestore
            user_ref.update({
                'aceptado': True,
                'password': firestore.DELETE_FIELD  # Eliminar la contraseña por seguridad
            })

            return True  # Retorna True si el usuario fue aceptado
        except Exception as e:
            print(f"Error al aceptar el usuario: {e}")
            return False  # Retorna False si ocurre un error
    return False  # Retorna False si el usuario ya está aceptado

# Función para eliminar un usuario
def eliminar_usuario(user_id):
    try:
        # Obtener los datos del usuario antes de eliminarlo
        user_ref = db.collection('usuarios').document(user_id)
        user_data = user_ref.get().to_dict()

        if user_data:
            try:
                # Intentar eliminar el usuario de Firebase Authentication
                auth.delete_user(user_id)
            except auth.UserNotFoundError:
                # Si el usuario no existe en Authentication, continuar
                print(f"Usuario con ID {user_id} no encontrado en Firebase Authentication.")

            # Eliminar el usuario de Firestore
            user_ref.delete()
            return True  # Retorna True si el usuario fue eliminado correctamente
    except Exception as e:
        print(f"Error al eliminar el usuario: {e}")
        return False  # Retorna False si ocurre un error

# Función para agregar un adulto mayor
def agregar_adulto_mayor(nombre, descripcion, imagen):
    ref = db.collection('adultos_mayores').document()
    image_url_adulto = subir_imagen(ref.id, imagen, 'adultos')
    ref.set({
        'nombre': nombre,
        'descripcion': descripcion,
        'imagen': image_url_adulto
    })  # Almacena un nuevo adulto mayor en Firestore

# Función para obtener todos los adultos mayores
def obtener_adultos():
    adultos = []
    for doc in db.collection('adultos_mayores').stream():
        data = doc.to_dict()
        data['id'] = doc.id
        adultos.append(data)  # Agrega cada adulto mayor a la lista
    return adultos  # Retorna la lista de adultos mayores

# Función para eliminar un adulto mayor
def eliminar_adulto(id):
    db.collection('adultos_mayores').document(id).delete()  # Elimina un adulto mayor por su ID

# Función para editar un adulto mayor
def editar_adulto_mayor(adulto_id, nombre, descripcion, imagen=None):
    ref = db.collection('adultos_mayores').document(adulto_id)
    
    # Actualizar los campos necesarios
    actualizacion = {
        'nombre': nombre,
        'descripcion': descripcion,
    }

    if imagen:  # Si hay una nueva imagen, la subimos y actualizamos la URL
        image_url_adulto = subir_imagen(adulto_id, imagen, 'adultos')
        actualizacion['imagen'] = image_url_adulto

    ref.update(actualizacion)  # Actualiza el documento del adulto mayor en Firestore

# Función para agregar una etapa de planta
def agregar_etapa_planta(adulto_id, nombre_planta, descripcion_etapa, imagen_etapa, fecha_registro):
    ref = db.collection('adultos_mayores').document(adulto_id).collection('plantas').document()
    image_url_etapa = subir_imagen(ref.id, imagen_etapa, 'plantas')
    ref.set({
        'nombre_planta': nombre_planta,
        'descripcion_etapa': descripcion_etapa,
        'imagen': image_url_etapa,
        'fecha_registro': fecha_registro
    })  # Almacena una nueva etapa de planta

# Función para obtener etapas de plantas por adulto
def obtener_etapas_por_adulto(adulto_id):
    etapas = []
    for doc in db.collection('adultos_mayores').document(adulto_id).collection('plantas').stream():
        etapa = doc.to_dict()
        etapa['id'] = doc.id
        etapas.append(etapa)  # Agrega cada etapa a la lista
    return etapas  # Retorna la lista de etapas

# Función para obtener un adulto mayor por su ID
def obtener_adulto_por_id(id):
    doc = db.collection('adultos_mayores').document(id).get()
    if doc.exists:
        return doc.to_dict()  # Retorna el documento del adulto mayor como un diccionario
    return None  # Retorna None si el adulto mayor no existe

# Función para eliminar una etapa de planta
def eliminar_etapa_planta(adulto_id, etapa_id):
    db.collection('adultos_mayores').document(adulto_id).collection('plantas').document(etapa_id).delete()  # Elimina una etapa de planta

# Función para editar una etapa de planta
def editar_etapa_planta(adulto_id, etapa_id, nombre_planta, descripcion_etapa, imagen_etapa):
    # Creamos un diccionario con los datos de la etapa
    data = {
        'nombre_planta': nombre_planta,
        'descripcion_etapa': descripcion_etapa
    }

    # Si hay una nueva imagen, la subimos y actualizamos la URL
    if imagen_etapa:  
        image_url = subir_imagen(etapa_id, imagen_etapa, 'plantas')
        data['imagen'] = image_url  # Añadimos la URL de la nueva imagen

    # Actualiza la etapa en Firestore
    db.collection('adultos_mayores').document(adulto_id).collection('plantas').document(etapa_id).update(data)

# Función para crear una nueva actividad
def crear_actividad(profesor_id, nombre, objetivo, materiales, instrucciones, archivo):
    print(f"Profesor ID: {profesor_id}")  # Mostramos el ID del profesor en consola

    # Referencia a la colección de actividades del profesor
    profesor_ref = db.collection('usuarios').document(profesor_id).collection('actividades')

    # Creamos un diccionario con los datos de la actividad
    actividad_data = {
        'nombre': nombre,
        'objetivo': objetivo,
        'materiales': materiales,
        'instrucciones': instrucciones,
        'archivo': None  # Inicializamos el campo archivo como None
    }

    # Si hay un archivo PDF, lo subimos y actualizamos la URL
    if archivo and archivo.filename.endswith('.pdf'):
        blob = bucket.blob(f'actividades/{profesor_id}/{archivo.filename}')  # Referencia al blob
        blob.upload_from_file(archivo)  # Subimos el archivo al Storage
        blob.make_public()  # Hacemos el archivo público
        actividad_data['archivo'] = blob.public_url  # Guardamos la URL pública del archivo

    # Agregamos la actividad a la colección del profesor
    profesor_ref.add(actividad_data)  # No es necesario obtener el ID si solo lo agregas

# Función para obtener las actividades de un profesor por su ID
def obtener_actividades_por_profesor_id(profesor_id):
    actividades = []  # Inicializamos una lista para las actividades
    for doc in db.collection('usuarios').document(profesor_id).collection('actividades').stream():
        actividad = doc.to_dict()  # Convertimos el documento a un diccionario
        actividad['id'] = doc.id  # Asegúrate de agregar el ID
        actividades.append(actividad)  # Añadimos la actividad a la lista
    return actividades  # Retornamos la lista de actividades

# Función para eliminar una actividad por su ID
def eliminar_actividad(profesor_id, actividad_id):
    # Eliminamos la actividad especificada de Firestore
    db.collection('usuarios').document(profesor_id).collection('actividades').document(actividad_id).delete()

# Función para editar una actividad existente
def editar_actividad(profesor_id, actividad_id, nombre, objetivo, materiales, instrucciones, archivo=None):
    # Creamos un diccionario con los nuevos datos de la actividad
    data_act = {
        'nombre': nombre,
        'objetivo': objetivo,
        'materiales': materiales,
        'instrucciones': instrucciones
    }
    
    # Si se sube un nuevo archivo, actualizarlo en el Storage
    if archivo and archivo.filename.endswith('.pdf'):
        blob = bucket.blob(f'actividades/{profesor_id}/{archivo.filename}')  # Referencia al blob
        blob.upload_from_file(archivo)  # Subimos el nuevo archivo al Storage
        blob.make_public()  # Hacemos el archivo público
        data_act['archivo'] = blob.public_url  # Añadir la nueva URL del archivo a los datos

    # Actualiza los datos de la actividad en Firestore
    db.collection('usuarios').document(profesor_id).collection('actividades').document(actividad_id).update(data_act)
