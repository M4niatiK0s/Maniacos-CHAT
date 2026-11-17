import hashlib
import hmac
import os
import secrets
from datetime import datetime

import mssql_python
from dotenv import load_dotenv

#Exito
def _ok(datos=None):
    return{"ok":True, "datos":datos}

#Error y su respuesta
def _error(codigo,mensaje, detalle=None):
    return{"ok":False,"error":codigo, "mensaje":mensaje, "detalle":detalle}

#Maneja los errores de SQL
def _error_excepcion(excepcion):
    texto = str(excepcion).upper()
    if "UNIQUE" in texto or "2627" in texto:
        return _error("usuario_existe", "Ese nombre de usuario ya existe", str(excepcion))
    if "FOREIGN KEY" in texto:
        return _error("imagen_invalida", "La imagen elegida no existe", str(excepcion))
    return _error("error_bd", "Error en la base de datos", str(excepcion))

def _obtener_fecha_sql() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

load_dotenv()

LONGITUD_MAX_USUARIO = 100

class BaseDatos:

    def __init__(self,servidor=None,base=None,usuario=None,password=None):
        
        self.servidor = servidor or os.environ.get("DB_SERVER","localhost")
        self.base = base or os.environ.get("DB_NAME", "maniacos")
        self.usuario = usuario or os.environ.get("DB_USER","maniacos")
        self.password = password or os.environ.get("DB_PWD")
        self._conn = None
        
    
    """Metodo para conectarnos a la Base de datos de SQL Server usando la biblioteca mssql_python"""    
    def conectar(self):
        if self._conn is None:
            self._conn = mssql_python.connect(
                server=self.servidor,
                database=self.base,
                uid=self.usuario,
                pwd=self.password,
                encrypt="yes",
                trust_server_certificate="yes",
            )
        return self
    #Liberamos los recursos de manera segura 
    def cerrar_conexion(self):
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None
    
#Cuando se inicia comienza la conexion
    def __enter__(self):
        return self.conectar()
    
#Cuando se cierra se desconecta
    def __exit__(self,exc_type, exc_val, exc_tb):
        self.cerrar_conexion()
        return False
    
    """Metodo para ejecutar cualquier query en la base de datos, tenemos una variable, 
    la cual nos duvuelve una fila, una abala completa o solo informacion de que se afecto"""
    def _ejecutar_query(self,sql:str,parametros=(),devolver=None):
        """Primero checamos la conexion a la base de datos, si no pues nos conectamos"""
        if self._conn is None:
            self.conectar()
            
        cursor = self._conn.cursor()
        
        try:
            """if: Aqui es para cuando hagamos consultas o peticiones que lleven parametros, como inserciones o registros de usuarios"""
            """else: En este es cuando nuestras consultas o peticiones no lleven parametros, cuando carguemos un chat o saber quien se conecto"""
            if parametros:
                cursor.execute(sql,parametros)
            
            else:
                cursor.execute(sql)
            
            if devolver == "una":
                columnas = [c[0] for c in cursor.description]
                fila = cursor.fetchone()
                resultado = dict(zip(columnas,fila)) if fila else None
            elif devolver == "toda":
                columnas = [c[0] for c in cursor.description]
                resultado = [dict(zip(columnas,f)) for f in cursor.fetchall()]
            else:
                resultado = cursor.rowcount
            
            """Funcion que se ejecuta para asegurar que los cambios son permamentes en la base de datos"""
            self._conn.commit()
            return resultado
        
        except Exception:
            """Esta funcion es por si algo falla y ya no se ejecuta todo el query. manda a llamr el error de sql con el raise"""
            self._conn.rollback()
            raise
        
        finally:
            """Cierra la conexion"""
            cursor.close()
            

    #Registrar un usuario
    def registrar_usuario(self,usuario:str,passwrd:str,imagen_id = 1):
        usuario = (usuario or "").strip()


        #Realizamos validaciones en python antes de pasar a la db 
        if not usuario or (len(usuario) > LONGITUD_MAX_USUARIO):
            return _error("datos_invalidos",f"El nombre del usuario debe tener entre 1 y {LONGITUD_MAX_USUARIO} caracteres")
        if not passwrd:
            raise _error("datos_invalidos","No se puede tener una contraseña vacia")
        
        try:
            query = "INSERT INTO maniacosdb.usuarios (usuario, contrasena, imagen_local_id, fecha_registro) VALUES (?, ?, ?, ?)"
            fecha = _obtener_fecha_sql()
            insercion = self._ejecutar_query(query,(usuario,passwrd,imagen_id,fecha))
            if not insercion:
                return _error("error_insercion", "No se logro la insercion del usuario")
            return _ok(insercion)
        except Exception as e:
            return _error_excepcion(e)
    
    #Checar login
    def validar_login(self,usuario:str,passwd:str):
        try:
            query = "SELECT id, usuario, contrasena, imagen_local_id FROM maniacosdb.usuarios WHERE usuario = ?"
            resultado = self._ejecutar_query(query,(usuario,),devolver="una")
        except Exception as e:
            return _error_excepcion(e)
        
        if resultado is None or (resultado["contrasena"] != passwd):
            return _error("credenciales_no_validas",f"Contraseña y/o usuario incorrectos")
        del resultado["contrasena"]

        #Inscribe a la tabla de grupos los usuarios que se registren despues de los que crearon los grupos
        try:
            usuario_id = resultado["id"]
            query_sync = """
                INSERT INTO maniacosdb.miembros_grupo (grupo_id, usuario_id, rol)
                SELECT id, ?, 'miembro'
                FROM maniacosdb.grupos
                WHERE id NOT IN (SELECT grupo_id FROM maniacosdb.miembros_grupo WHERE usuario_id = ?)
            """
            self._ejecutar_query(query_sync, (usuario_id, usuario_id))
        except Exception:
            pass 
            
        return _ok(resultado)
    
    #Chat general
    def enviar_mensaje_general(self,usuario_id: int, chat_general_id:int, contenido:str):
        """Insertar en la tabla de mensajes"""
        try:
            fecha = _obtener_fecha_sql()
            query = "INSERT INTO maniacosdb.mensajes (usuario_id,contenido,fecha_envio,chat_general_id) VALUES (?,?,?,?)"
            self._ejecutar_query(query,(usuario_id,contenido,fecha,chat_general_id))
            return _ok({"chat_general_id":chat_general_id})
        except Exception as e:
            return _error_excepcion(e)
        
    #Mensaje Privado
    def enviar_mensaje_privado(self,remitente_id: int, destinatario_id: int, contenido: str):
        try:
            #Vemos si hay algun chat privado para dos usuarios diferentes
            query_buscar_conversacion = """SELECT id FROM maniacosdb.chats_privados 
                    WHERE (usuario_1_id = ? AND usuario_2_id = ?)
                    OR (usuario_1_id = ? AND usuario_2_id = ?)"""
                    
            chat = self._ejecutar_query(query_buscar_conversacion,(remitente_id,destinatario_id,destinatario_id,remitente_id),devolver="una")
            
            fecha = _obtener_fecha_sql()
            if chat:
                chat_privado_id = chat["id"]
            else:
                #Creamos uno si no hay alguno en la db
                query_nuevo_chat = """INSERT INTO maniacosdb.chats_privados (usuario_1_id, usuario_2_id, fecha_creacion)
                OUTPUT Inserted.id
                VALUES (?,?,?)"""
                
                nuevo = self._ejecutar_query(query_nuevo_chat,(remitente_id,destinatario_id,fecha),devolver="una")
                #Linea cambiada
                chat_privado_id = nuevo["id"]
                
            query = "INSERT INTO maniacosdb.mensajes (usuario_id,contenido,fecha_envio,chat_privado_id) VALUES (?,?,?,?)"
            
            self._ejecutar_query(query,(remitente_id,contenido,fecha,chat_privado_id))
            return _ok({"chat_privado_id":chat_privado_id, "destinatario_id":destinatario_id})
        except Exception as e:
            return _error_excepcion(e)
    
    #Grupos, se verifica qeu sea del grupo, una vez verificado, se obtienen los usuarios del grupo
    def enviar_mensaje_grupo(self,usuario_id: int, grupo_id: int, contenido: str):
        try:
            query_buscar_usuario = "SELECT 1 AS ok FROM maniacosdb.miembros_grupo WHERE grupo_id = ? AND usuario_id = ?"
            es_miembro = self._ejecutar_query(query_buscar_usuario,(grupo_id,usuario_id),devolver="una")
            
            if not es_miembro:
                return _error("sin_permiso","No perteneces al grupo")
            
            fecha = _obtener_fecha_sql()
            query_mensaje = "INSERT INTO maniacosdb.mensajes (usuario_id, contenido, fecha_envio, grupo_id) VALUES (?,?,?,?)"
            self._ejecutar_query(query_mensaje,(usuario_id,contenido,fecha,grupo_id))
            
            query_obtener_usuarios_grupo = "SELECT usuario_id FROM maniacosdb.miembros_grupo WHERE grupo_id = ? "
            resultado = self._ejecutar_query(query_obtener_usuarios_grupo,(grupo_id),devolver="toda")
            
            usuarios_grupo = [res["usuario_id"] for res in resultado]
            return _ok({"grupo_id":grupo_id, "destinatarios":usuarios_grupo})
        
        except Exception as e:
            return _error_excepcion(e)
        
    #Canales, se valida el dueño del canal y los usuarios activos del grupo
    def enviar_mensaje_canal(self, usuario_id: int, canal_id: int, contenido: str):
        try:
            query_buscar_canal = "SELECT creado_por FROM maniacosdb.canales WHERE id = ?"
            canal = self._ejecutar_query(query_buscar_canal,(canal_id),devolver="una")
            
            if not canal:
                return _error("no_existe","Canal no existente") 
            
            if canal["creado_por"] != usuario_id:
                return _error("solo_dueño","Solo el dueño del canal puede escribr en el")
            
            fecha = _obtener_fecha_sql()
            query_publicacion = "INSERT INTO maniacosdb.mensajes (usuario_id, contenido, fecha_envio, canal_id) VALUES (?,?,?,?)" 
            self._ejecutar_query(query_publicacion,(usuario_id,contenido,fecha,canal_id))
            
            query_obtener_suscriptores = "SELECT usuario_id FROM maniacosdb.suscripciones_canal WHERE canal_id = ? "
            resultado = self._ejecutar_query(query_obtener_suscriptores,(canal_id),devolver="toda")
                        
            suscriptores = [res["usuario_id"] for res in resultado]
            return _ok({"canal_id":canal_id, "destinatarios":suscriptores})
            
        except Exception as e:
            return _error_excepcion(e)

    # Crear un grupo y agregar a los miembros
    def crear_grupo(self, nombre: str, creador_id: int):
        try:
            fecha = _obtener_fecha_sql()

            query_grupo = """INSERT INTO maniacosdb.grupos (nombre, creado_por, fecha_creacion)
                             OUTPUT Inserted.id
                             VALUES (?, ?, ?)"""
            nuevo_grupo = self._ejecutar_query(query_grupo, (nombre, creador_id, fecha), devolver="una")
            grupo_id = nuevo_grupo["id"]

            query_todos = "SELECT id FROM maniacosdb.usuarios"
            todos_los_usuarios = self._ejecutar_query(query_todos, devolver="toda")

            query_miembro = "INSERT INTO maniacosdb.miembros_grupo (grupo_id, usuario_id, rol) VALUES (?, ?, ?)"
            
            miembros_ids = []
            for fila in todos_los_usuarios:
                uid = fila["id"]
                miembros_ids.append(uid)
                rol = 'admin' if uid == creador_id else 'miembro'
                self._ejecutar_query(query_miembro, (grupo_id, uid, rol))
                    
            return _ok({"grupo_id": grupo_id, "nombre": nombre, "miembros": miembros_ids})
        except Exception as e:
            return _error_excepcion(e)

    # Crear un nuevo canal
    def crear_canal(self, nombre: str, creador_id: int):
        try:
            fecha = _obtener_fecha_sql()
            # 1. Crear el canal
            query_canal = """INSERT INTO maniacosdb.canales (nombre, creado_por, fecha_creacion)
                             OUTPUT Inserted.id
                             VALUES (?, ?, ?)"""
            nuevo_canal = self._ejecutar_query(query_canal, (nombre, creador_id, fecha), devolver="una")
            canal_id = nuevo_canal["id"]
            
            # 2. Suscribir automáticamente al creador
            query_sub = "INSERT INTO maniacosdb.suscripciones_canal (canal_id, usuario_id) VALUES (?, ?)"
            self._ejecutar_query(query_sub, (canal_id, creador_id))
            
            return _ok({"canal_id": canal_id, "nombre": nombre})
        except Exception as e:
            return _error_excepcion(e)

    # Suscribirse a un canal para leerlo
    def suscribirse_canal(self, usuario_id: int, canal_id: int):
        try:
            query = "INSERT INTO maniacosdb.suscripciones_canal (canal_id, usuario_id) VALUES (?, ?)"
            self._ejecutar_query(query, (canal_id, usuario_id))
            return _ok({"canal_id": canal_id})
        except Exception as e:
            return _error_excepcion(e)

    # Obtener los grupos a los que pertenece un usuario
    def obtener_grupos_usuario(self, usuario_id: int):
        try:
            query = """SELECT T1.id, T1.nombre 
                       FROM maniacosdb.grupos T1
                       INNER JOIN maniacosdb.miembros_grupo T2 ON T1.id = T2.grupo_id
                       WHERE T2.usuario_id = ?"""
            resultado = self._ejecutar_query(query, (usuario_id,), devolver="toda")
            return _ok(resultado)
        except Exception as e:
            return _error_excepcion(e)

    # Obtener los canales de un usuario
    def obtener_canales_usuario(self, usuario_id: int):
        try:
            query = """SELECT T1.id, T1.nombre 
                       FROM maniacosdb.canales T1
                       INNER JOIN maniacosdb.suscripciones_canal T2 ON T1.id = T2.canal_id
                       WHERE T2.usuario_id = ?"""
            resultado = self._ejecutar_query(query, (usuario_id,), devolver="toda")
            return _ok(resultado)
        except Exception as e:
            return _error_excepcion(e)
        
    #Obetener la conversacion o lo qeu habia en el canal
    def obtener_historial(self, tipo_de_chat: str, destino_id: int, mi_usuario_id: int = None):
        try:
            if tipo_de_chat == "general":
                query = """SELECT T1.usuario, T2.contenido
                            FROM maniacosdb.mensajes T2
                            INNER JOIN maniacosdb.usuarios T1 ON T2.usuario_id = T1.id
                            WHERE T2.chat_general_id = ?
                            ORDER BY T2.id ASC"""
                respuesta = self._ejecutar_query(query, (destino_id,), devolver="toda")
            
            elif tipo_de_chat == "grupo":
                query = """SELECT T1.usuario, T2.contenido
                            FROM maniacosdb.mensajes T2
                            INNER JOIN maniacosdb.usuarios T1 ON T2.usuario_id = T1.id
                            WHERE T2.grupo_id = ?
                            ORDER BY T2.id ASC"""
                respuesta = self._ejecutar_query(query, (destino_id,), devolver="toda")
                
            elif tipo_de_chat == "canal":
                query = """SELECT T1.usuario, T2.contenido
                            FROM maniacosdb.mensajes T2
                            INNER JOIN maniacosdb.usuarios T1 ON T2.usuario_id = T1.id
                            WHERE T2.canal_id = ?
                            ORDER BY T2.id ASC"""
                respuesta = self._ejecutar_query(query, (destino_id,), devolver="toda")

            elif tipo_de_chat == "privado":
                query = """SELECT T1.usuario, T2.contenido
                            FROM maniacosdb.mensajes T2
                            INNER JOIN maniacosdb.usuarios T1 ON T2.usuario_id = T1.id
                            INNER JOIN maniacosdb.chats_privados T3 ON T2.chat_privado_id = T3.id
                            WHERE (T3.usuario_1_id = ? AND T3.usuario_2_id = ?) OR (T3.usuario_1_id = ? AND T3.usuario_2_id = ?)
                            ORDER BY T2.id ASC"""
                respuesta = self._ejecutar_query(query, (mi_usuario_id, destino_id, destino_id, mi_usuario_id), devolver="toda")
            
            else: 
                return _error("tipo_invalido","No existe ese tipo de chat")
            
            return _ok(respuesta)

        except Exception as e:
            return _error_excepcion(e)