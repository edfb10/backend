from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify, get_flashed_messages
import config
from datetime import datetime
import random


app = Flask(__name__, static_folder='static')
app.secret_key = '@secrectKEY2024'

@app.route('/')
def raiz():
    # Redirige a la página de inicio de sesión
    return redirect(url_for('login'))

# Ruta para registro de usuarios
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Obtiene los datos del formulario de registro
        nombre = request.form['nombre']
        email = request.form['email']
        rol = request.form['rol']
        password = request.form['password']
        
        # Guarda el nuevo usuario en Firestore con el campo "aceptado" como False
        config.agregar_usuario_firestore(nombre, email, rol, password)
        
        flash("Registro exitoso. Espera la aprobación del administrador.")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        # Obtiene el correo y la nueva contraseña del formulario
        email = request.form['email']
        password = request.form['password']

        # Llama a la función para actualizar la contraseña en Firebase
        success, mensaje = config.update_user_password(email, password)

        if success:
            flash(mensaje, 'success')
            return redirect(url_for('login'))
        else:
            flash(f"Error: {mensaje}", 'error')
            return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Obtiene el correo y la contraseña del formulario de inicio de sesión
        email = request.form['email']
        password = request.form['password']
        
        # Intenta iniciar sesión con las credenciales proporcionadas
        user = config.iniciar_sesion(email, password)
        
        if user:
            # Guarda información del usuario en la sesión
            session['user'] = user
            session['email'] = email
            session['user_role'] = user['rol']
            
            # Guarda el ID del profesor en la sesión si es un profesor
            if user['rol'] == 'profesor':
                session['profesor_id'] = user['id']
            
            if user['rol'] == 'admin':
                session['admin'] = True

            return redirect(url_for('dashboard'))
        else:
            flash("Correo o contraseña incorrectos, o tu cuenta aún no ha sido aceptada.")
            return redirect(url_for('login'))
    return render_template('login.html', error_message=get_flashed_messages())

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    # Verifica si hay un usuario en sesión
    if 'user' not in session:
        return redirect(url_for('login'))  # Redirige si no hay usuario en sesión

    user_id = session['user']['id']
    user_data = config.obtener_usuario_por_id(user_id)

    if request.method == 'POST':
        if 'image' in request.files:
            image = request.files['image']
            if image:
                # Sube la nueva imagen de perfil
                image_url = config.subir_imagen(user_id, image, 'profile_images')
                if image_url:
                    config.actualizar_imagen_perfil(user_id, image_url)
                    flash("Imagen de perfil actualizada.")

    # Obtener datos actualizados del usuario
    user_data = config.obtener_usuario_por_id(user_id)
    image_url = user_data.get('image_url', '')
    nombre = user_data.get('nombre', '')
    correo = user_data.get('email', '')
    rol = user_data.get('rol', '')

    # Renderiza la plantilla del perfil con los nuevos datos
    return render_template('perfil.html', nombre=nombre, image_url=image_url, correo=correo, rol=rol, random=random.random)

@app.route('/admin')
def admin():
    # Obtiene la lista de usuarios profesores y estudiantes
    usuarios_profesores = config.obtener_usuarios_por_rol('profesor')
    usuarios_estudiantes = config.obtener_usuarios_por_rol('estudiante')
    return render_template('admin.html', usuarios_profesores=usuarios_profesores, usuarios_estudiantes=usuarios_estudiantes)

@app.route('/aceptar/<usuario_id>', methods=['POST'])
def aceptar(usuario_id):
    # Acepta un usuario y envía un correo de verificación
    if config.aceptar_usuario(usuario_id):
        flash('Usuario aceptado y correo de verificación enviado.', 'success')
    else:
        flash('Error al aceptar el usuario.', 'error')
        print('Error al aceptar el usuario.')
    return redirect(url_for('admin'))

@app.route('/eliminar/<usuario_id>', methods=['POST'])
def eliminar(usuario_id):
    # Elimina un usuario
    config.eliminar_usuario(usuario_id)
    flash('Usuario eliminado correctamente.', 'success')
    return redirect(url_for('admin'))

# Ruta para el dashboard
@app.route('/dashboard')
def dashboard():
    # Verifica si hay un usuario en sesión
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

@app.route('/adultos_mayores', methods=['GET', 'POST'])
def adultos_mayores():
    if request.method == 'POST':
        # Agrega un nuevo adulto mayor
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        imagen = request.files['imagen']
        config.agregar_adulto_mayor(nombre, descripcion, imagen)
        flash('Adulto mayor agregado exitosamente')
        return redirect(url_for('adultos_mayores'))

    # Obtiene la lista de adultos mayores
    adultos = config.obtener_adultos()
    
    return render_template('adultos_mayores.html', adultos=adultos)

@app.route('/eliminar_adulto/<adulto_id>', methods=['GET'])
def eliminar_adulto(adulto_id):
    # Elimina un adulto mayor
    config.eliminar_adulto(adulto_id)
    flash('Adulto mayor eliminado exitosamente')
    return redirect(url_for('adultos_mayores'))

@app.route('/editar_adulto', methods=['POST'])
def editar_adulto():
    # Edita la información de un adulto mayor
    adulto_id = request.form['adulto_id']
    nombre = request.form['nombre']
    descripcion = request.form['descripcion']
    imagen = request.files.get('imagen')  # Imagen es opcional

    # Actualiza los datos del adulto mayor
    config.editar_adulto_mayor(adulto_id, nombre, descripcion, imagen)
    flash('Adulto mayor actualizado exitosamente')
    return redirect(url_for('adultos_mayores'))

@app.route('/plantas', methods=['GET', 'POST'])
def plantas():
    # Obtiene la lista de adultos mayores
    adultos = config.obtener_adultos()
    modo = request.form.get('modo', 'ver_plantas')
    seleccionado_id = request.form.get('adulto_id')

    if request.method == 'POST':
        if modo == 'registro' and seleccionado_id:
            # Agrega una nueva etapa de planta
            nombre_planta = request.form.get('nombre_planta')
            descripcion_etapa = request.form.get('descripcion_etapa')
            imagen_etapa = request.files.get('imagen_etapa')
            fecha_registro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            config.agregar_etapa_planta(seleccionado_id, nombre_planta, descripcion_etapa, imagen_etapa, fecha_registro)
            flash('Etapa de planta agregada exitosamente')
            return redirect(url_for('plantas'))

    # Organiza las etapas de planta por adulto
    plantas = {
        adulto['id']: {
            'adulto': adulto,
            'etapas': sorted(config.obtener_etapas_por_adulto(adulto['id']), key=lambda p: p['fecha_registro'])
        }
        for adulto in adultos
    }

    adulto = None
    etapas_ordenadas = []
    if modo in ['registro', 'editar'] and seleccionado_id:
        adulto = config.obtener_adulto_por_id(seleccionado_id)
        etapas_ordenadas = sorted(config.obtener_etapas_por_adulto(seleccionado_id), key=lambda p: p['fecha_registro'])

    return render_template('plantas.html', adultos=adultos, plantas=plantas, adulto=adulto, etapas=etapas_ordenadas, modo=modo)

@app.route('/eliminar-etapa/<adulto_id>/<etapa_id>', methods=['POST'])  # Asegúrate de incluir adulto_id en la ruta
def eliminar_etapa(adulto_id, etapa_id):
    # Elimina una etapa de planta
    config.eliminar_etapa_planta(adulto_id, etapa_id)
    flash('Etapa de planta eliminada exitosamente')
    return redirect(url_for('plantas'))

@app.route('/editar-etapa/<adulto_id>/<etapa_id>', methods=['POST'])
def editar_etapa(adulto_id, etapa_id):
    # Edita la información de una etapa de planta
    nombre_planta = request.form.get('nombre_planta')
    descripcion_etapa = request.form.get('descripcion_etapa')
    imagen_etapa = request.files.get('imagen_etapa')

    # Actualiza los datos de la etapa de planta
    config.editar_etapa_planta(adulto_id, etapa_id, nombre_planta, descripcion_etapa, imagen_etapa)
    flash('Etapa de planta editada exitosamente')
    return redirect(url_for('plantas'))

@app.route('/linea_tiempo', methods=['GET'])
def linea_tiempo():
    # Obtener todos los adultos mayores desde la base de datos
    adultos = config.obtener_adultos()

    # Crear una lista para almacenar las líneas del tiempo de cada adulto mayor
    lineas_tiempo = []

    for adulto in adultos:
        # Obtener las plantas asociadas a este adulto mayor específico
        plantas = config.obtener_etapas_por_adulto(adulto['id'])

        # Ordenar las plantas por fecha de registro
        plantas_ordenadas = sorted(plantas, key=lambda p: p['fecha_registro'])

        # Añadir la información del adulto mayor y sus plantas ordenadas a la línea del tiempo
        lineas_tiempo.append({
            'adulto': {
                'nombre': adulto['nombre'],
                'descripcion': adulto['descripcion'],
                'imagen': adulto['imagen']
            },
            'plantas': plantas_ordenadas  # Lista de plantas con sus imágenes, descripciones y fechas
        })

    # Renderizar la plantilla con las líneas del tiempo obtenidas
    return render_template('linea_tiempo.html', lineas_tiempo=lineas_tiempo)

@app.route('/adulto_mayor/<adulto_id>/plantas', methods=['GET'])
def obtener_plantas_adulto(adulto_id):
    # Obtener las plantas asociadas al adulto mayor especificado
    plantas = config.obtener_etapas_por_adulto(adulto_id)
    # Retornar las plantas en formato JSON
    return jsonify({'plantas': plantas})

@app.route('/actividades', methods=['GET', 'POST'])
def actividades():
    # Obtener el ID del profesor desde la sesión actual
    profesor_id = session.get('profesor_id')

    if request.method == 'POST':
        # Crear una nueva actividad a partir de los datos del formulario
        nombre = request.form['nombre']
        objetivo = request.form['objetivo']
        materiales = request.form['materiales']
        instrucciones = request.form['instrucciones']
        archivo = request.files.get('archivo')

        # Crear la actividad utilizando la función del config
        config.crear_actividad(profesor_id, nombre, objetivo, materiales, instrucciones, archivo)

        # Mostrar un mensaje de éxito y redirigir a la misma página
        flash('Actividad creada exitosamente!')
        return redirect(url_for('actividades'))

    # Obtener la lista de profesores desde la base de datos
    profesores = config.obtener_usuarios_por_rol('profesor')

    # Obtener actividades asociadas a cada profesor
    actividades_por_profesor = {}
    for profesor in profesores:
        actividades_por_profesor[profesor['id']] = config.obtener_actividades_por_profesor_id(profesor['id'])

    # Renderizar la plantilla de actividades con los datos obtenidos
    return render_template('actividades.html', profesores=profesores, actividades_por_profesor=actividades_por_profesor)

@app.route('/eliminar_actividad/<profesor_id>/<actividad_id>', methods=['POST'])
def eliminar_actividad(profesor_id, actividad_id):
    try:
        # Intentar eliminar la actividad especificada
        config.eliminar_actividad(profesor_id, actividad_id)
        # Redirigir a la página de actividades después de eliminar
        return redirect(url_for('actividades'))
    except Exception as e:
        print(f"Error al eliminar la actividad: {e}")
        # Retornar un mensaje de error si no se pudo eliminar
        return jsonify({'error': 'No se pudo eliminar la actividad.'}), 500

@app.route('/editar_actividad/<profesor_id>/<actividad_id>', methods=['POST'])
def editar_actividad(profesor_id, actividad_id):
    # Obtener los datos del formulario para editar la actividad
    nombre = request.form['nombre']
    objetivo = request.form['objetivo']
    materiales = request.form['materiales']
    instrucciones = request.form['instrucciones']
    archivo = request.files.get('archivo')  # Captura el archivo subido, si existe

    try:
        # Intentar editar la actividad con los nuevos datos
        config.editar_actividad(profesor_id, actividad_id, nombre, objetivo, materiales, instrucciones, archivo)
        flash('Actividad actualizada exitosamente!')
        return redirect(url_for('actividades'))
    except Exception as e:
        print(f"Error al editar la actividad: {e}")
        # Retornar un mensaje de error si no se pudo editar
        return jsonify({'error': 'No se pudo editar la actividad.'}), 500

@app.errorhandler(404)
def page_not_found(e):
    # Manejar el error 404 (página no encontrada)
    return "Página no encontrada", 404

@app.route('/cerrar_sesion')
def cerrar_sesion():
    # Limpiar la sesión del usuario actual
    session.clear()
    
    # Limpiar la caché del navegador y redirigir al login
    response = redirect(url_for('login'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    flash('Sesión cerrada exitosamente.', 'success')
    return response

if __name__ == '__main__':
    # Ejecutar la aplicación Flask en modo debug
    app.run(debug=True, port=6660)
