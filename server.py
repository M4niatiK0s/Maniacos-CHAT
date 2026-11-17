import socket
import threading
from BaseDatos import BaseDatos

class Cliente:
    def __init__(self):
        #Id que tiene la base de datos
        self.id = None
        self.name = ""
        self.avatar_id = 1
        self.conn = None
        self.addr = None
    

def enviar_a_usuario(usuario_id: int,paquete: str):
    #Envia paquete terminado con | al susuario si ya esta conectado, si ya no tiene conexion con el cliiente, lo quita de su listad actual
    if not paquete.endswith("|"):
        paquete += "|"
    for cliente in list_of_clients:
        if cliente.id == usuario_id:
            try:
                cliente.conn.send(paquete.encode("UTF-8"))
            except:
                remove(cliente)

def clientthread(conn, addr):
    cliente = next((c for c in list_of_clients if c.conn == conn), None)
    conn.send(f"<info>Bienvenido {addr}|".encode("utf-8"))
    buffer = ""
    
    while True:
        try:
            message = conn.recv(BUFFER_SIZE)
            if not message:
                remove(cliente)
                break
            
            
            print(f"<{addr[0]}> {message}")
            buffer += message.decode('utf-8')
            #(comandos)
            while "|" in buffer:
                msg, buffer = buffer.split("|",1)
                msg = msg.strip()
                if msg:
                    procesar_comando(cliente,msg)

            
        except Exception as e:
            print(f"Error con {addr} : {e}")
            remove(cliente)
            break


def procesar_comando(cliente: Cliente, mensaje: str):
    with BaseDatos() as db:
        
        #SIGNUP: ESTRUCTURA DEL MENSAJE: <signup>usuario::contrsenia::imagen_id
        if mensaje.startswith("<signup>"):
            usuario, passwd, imagen_id = mensaje.removeprefix("<signup>").split("::",2)
            respuesta = db.registrar_usuario(usuario,passwd,int(imagen_id))
            
            if(respuesta["ok"]):
                cliente.conn.send("<ok_signup>Usuario rgistrado correctamente|".encode("utf-8"))
            else:
                cliente.conn.send(f"<error_signup>{respuesta['mensaje']}|".encode("utf-8"))
        
        #LOGIN:ESTRUCTRURA DEL MENSAJE <login>usaurio::contrasenia
        if mensaje.startswith("<login>"):
            usuario, passwd = mensaje.removeprefix("<login>").split("::",1)
            respuesta = db.validar_login(usuario,passwd)
            
            if(respuesta["ok"]):
                cliente.id = respuesta["datos"]["id"]
                cliente.name = respuesta["datos"]["usuario"]
                cliente.avatar_id = respuesta["datos"]["imagen_local_id"]
                cliente.conn.send(f"<ok_login>{cliente.id}::{cliente.avatar_id}|".encode("utf-8"))

                usuarios_activos = []
                for c in list_of_clients:
                    if c.id is not None:
                        usuarios_activos.append(f"{c.id}::{c.name}::{c.avatar_id}")
                
                paquete_usuarios = f"<usuarios_activos>{','.join(usuarios_activos)}|"
                
                for c in list_of_clients:
                    if c.id is not None:
                        enviar_a_usuario(c.id, paquete_usuarios)
                resp_grupos = db.obtener_grupos_usuario(cliente.id)
                if resp_grupos["ok"] and resp_grupos["datos"]:
                    for fila in resp_grupos["datos"]:
                        paquete_grupo = f"<nuevo_grupo>{fila['id']}::{fila['nombre']}|"
                        cliente.conn.send(paquete_grupo.encode("utf-8"))

                resp_canales = db.obtener_canales_usuario(cliente.id)
                if resp_canales["ok"] and resp_canales["datos"]:
                    for fila in resp_canales["datos"]:
                        paquete_canal = f"<nuevo_canal>{fila['id']}::{fila['nombre']}|"
                        cliente.conn.send(paquete_canal.encode("utf-8"))
                        
            else:
                cliente.conn.send(f"<error>{respuesta['mensaje']}|".encode("utf-8"))
        
        # CREAR CANAL:ESTRUCTRURA DEL MENSAJE <crear_canal>nombre
        elif mensaje.startswith("<crear_canal>"):
            nombre_canal = mensaje.removeprefix("<crear_canal>")
            respuesta = db.crear_canal(nombre_canal, cliente.id)
            
            if respuesta["ok"]:
                canal_id = respuesta["datos"]["canal_id"]
                cliente.conn.send(f"<info>Canal '{nombre_canal}' creado con éxito. ID: {canal_id}|".encode("utf-8"))
                cliente.conn.send(f"<nuevo_canal>{canal_id}::{nombre_canal}|".encode("utf-8"))
            else:
                cliente.conn.send(f"<error>{respuesta['mensaje']}|".encode("utf-8"))

        # SUSCRIBIRSE:ESTRUCTRURA DEL MENSAJE <suscribirse>canal_id
        elif mensaje.startswith("<suscribirse>"):
            canal_id = int(mensaje.removeprefix("<suscribirse>"))
            respuesta = db.suscribirse_canal(cliente.id, canal_id)
            
            if respuesta["ok"]:
                cliente.conn.send(f"<info>Te has suscrito al canal {canal_id} exitosamente.|".encode("utf-8"))
                resp_canales = db.obtener_canales_usuario(cliente.id)
                if resp_canales["ok"] and resp_canales["datos"]:
                    for fila in resp_canales["datos"]:
                        if str(fila['id']) == str(canal_id):
                            cliente.conn.send(f"<nuevo_canal>{fila['id']}::{fila['nombre']}|".encode("utf-8"))
            else:
                cliente.conn.send(f"<error>{respuesta['mensaje']}|".encode("utf-8"))

        #CHAT GENERAL: ESTRUCTURA DEL MENSAJE <general>chat_id::contenido
        elif mensaje.startswith("<general>"):
            chat_id, contenido = mensaje.removeprefix("<general>").split("::",1)
            chat_id = int(chat_id)
            respuesta = db.enviar_mensaje_general(cliente.id,chat_id,contenido)
            
            if(respuesta["ok"]):
                salida = f"<general>{chat_id}::{cliente.name}::{contenido}|"
                for c in list_of_clients:
                    if c.id and c.id != cliente.id:
                        enviar_a_usuario(c.id, salida)
            else: 
                cliente.conn.send(f"<error>{respuesta['mensaje']}|".encode("utf-8"))
        
        #CHAT PRIVADO: ESTRCUTURA DEL MENSAJE: <privado>destino_id::contenido
        elif mensaje.startswith("<privado>"):
            destino_id, contenido = mensaje.removeprefix("<privado>").split("::",1)
            destino_id = int(destino_id)
            respuesta = db.enviar_mensaje_privado(cliente.id,destino_id,contenido)
            
            if(respuesta["ok"]):
                salida = f"<privado>{cliente.id}::{cliente.name}::{contenido}|"
                enviar_a_usuario(destino_id,salida)
                    
        #CHAT GRUPO: ESTRCUTURA DEL MENSAJE: <grupo>grupo_id::contenido
        elif mensaje.startswith("<grupo>"):
            grupo_id, contenido = mensaje.removeprefix("<grupo>").split("::",1)
            grupo_id = int(grupo_id)
            respuesta = db.enviar_mensaje_grupo(cliente.id,grupo_id,contenido)
            
            if(respuesta["ok"]):
                salida = f"<grupo>{grupo_id}::{cliente.name}::{contenido}|"
                for user_id in respuesta["datos"]["destinatarios"]:
                    if user_id != cliente.id:
                        enviar_a_usuario(user_id,salida)
                    
                
            else:
                enviar_a_usuario(cliente.id,f"<error>{respuesta['mensaje']}|")

        # CREAR GRUPO: <crear_grupo>nombre_grupo
        elif mensaje.startswith("<crear_grupo>"):
            nombre_grupo = mensaje.removeprefix("<crear_grupo>")

            respuesta = db.crear_grupo(nombre_grupo, cliente.id)
            
            if respuesta["ok"]:
                grupo_id = respuesta["datos"]["grupo_id"]
                paquete = f"<nuevo_grupo>{grupo_id}::{nombre_grupo}|"
                
                for uid in respuesta["datos"]["miembros"]:
                    enviar_a_usuario(uid, paquete)
            else:
                cliente.conn.send(f"<error>{respuesta['mensaje']}|".encode("utf-8"))

        #CHAT CANAL: ESTRCUTURA DEL MENSAJE: <canal>canal_id::contenido
        elif mensaje.startswith("<canal>"):
            canal_id, contenido = mensaje.removeprefix("<canal>").split("::",1)
            canal_id = int(canal_id)
            respuesta = db.enviar_mensaje_canal(cliente.id,canal_id,contenido)
            
            if(respuesta["ok"]):
                salida = f"<canal>{canal_id}::{cliente.name}::{contenido}|"
                for user_id in respuesta["datos"]["destinatarios"]:
                    enviar_a_usuario(user_id, salida)  
            else:
                enviar_a_usuario(cliente.id,f"<error>{respuesta['mensaje']}|")
                    
        #PEDIR HISTORIAL: ESTRUCTURA DEL MENSAJE: <pedir_historial>tipo_de_chat::destino_id
        elif mensaje.startswith("<pedir_historial>"):
            tipo, destino_id = mensaje.removeprefix("<pedir_historial>").split("::",1)
            destino_id = int(destino_id)
            respuesta = db.obtener_historial(tipo,destino_id,cliente.id)
            
            if respuesta["ok"]:
                paquetes = []
                for fila in respuesta["datos"]:
                    paquetes.append(f"<historial>{tipo}::{destino_id}::{fila['usuario']}::{fila['contenido']}|")
                cliente.conn.sendall("".join(paquetes).encode("utf-8"))
            else:
                cliente.conn.send(f"<error>{respuesta['mensaje']}|".encode("utf-8"))

def setName(connection, name:str):
    for client in list_of_clients:
        if client.conn == connection:
            client.name = name
            break

def getName(connection) -> str:
    for client in list_of_clients:
        if client.conn == connection:
            return client.name
    return ""

def broadcast(message, connection):
    for client in list_of_clients:
        if client.conn != connection:
            try:
                client.conn.send(bytes(message, 'utf-8'))
            except:
                client.conn.close()
                remove(client)

def remove(connection):
    if connection in list_of_clients:
        list_of_clients.remove(connection)


if __name__ == "__main__":
    #host = socket.gethostname()  # Esta función nos da el nombre de la máquina
    #host = "0.0.0.0"
    #port = 80
    host = "0.0.0.0"
    port = 3025
    BUFFER_SIZE = 1024  # Usamos un número pequeño para tener una respuesta rápida
    # Creamos un socket TCP
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(100)  # Escuchamos hasta 100 clientes
    list_of_clients = []  # Lista de clientes conectados
    print(f"Escuchando conexiones en: {(host, port)}")
    try:
        while True:
            conn, addr = server.accept()
            nuevo_cliente = Cliente()
            nuevo_cliente.conn = conn
            nuevo_cliente.addr = addr
            #list_of_clients.append(conn)  # Agregamos a la lista de clientes
            list_of_clients.append(nuevo_cliente)  # Agregamos a la lista de clientes
            print(f"Cliente conectado: {addr}")
            # Creamos y ejecutamos el hilo para atender al cliente
            threading.Thread(target=clientthread, args=(conn, addr)).start()
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        conn.close()
        server.close()   
    print("Conexión terminada.")


