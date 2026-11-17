import sys
import socket
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QImageReader


from principal import Ui_MainWindow

BUFFER_SIZE = 1024
socket_global = None
connected = False


class ThreadSocket(QThread):

    signal_message = pyqtSignal(str)

    def __init__(self, host, port, user, password, avatar_id):
        global connected, socket_global
        super().__init__()

        socket_global.connect((host, port))
        connected = True

        msg_login = f"<login>{user}::{password}|"
        socket_global.send(bytes(msg_login, 'utf-8'))

    def run(self):
        global connected, socket_global
        buffer = ""
        try:
            while connected:
                message = socket_global.recv(BUFFER_SIZE)
                if message:
                    buffer += message.decode("utf-8")
                    while "|" in buffer:
                        msg, buffer = buffer.split("|", 1)
                        if msg.strip():
                            self.signal_message.emit(msg.strip())
                else:
                    self.signal_message.emit("<!!disconnected!!>")
                    break

        except Exception as e:
            self.signal_message.emit(f"<!!error!!>{str(e)}")
        finally:
            if socket_global:
                socket_global.close()
            connected = False

    def stop(self):
        global connected, socket_global
        connected = False
        if socket_global:
            try:
                socket_global.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                socket_global.close()
            except Exception:
                pass
            self.wait(1000)


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        self.stackedWidget.setCurrentIndex(0)
        self.setWindowTitle("Maniacos Chat - Desconectado")

        self.coneccion = None
        self.mi_id = None
        self.mi_usuario = None
        self.historial_grupos = {}

        self.btn_conectar.clicked.connect(self.conectar_servidor)
        self.btn_enviar_gen.clicked.connect(self.enviar_general)
        self.btn_enviar_priv.clicked.connect(self.enviar_privado)
        self.btn_enviar_grupo.clicked.connect(self.enviar_grupo)
        self.btn_crear_grupo.clicked.connect(self.crear_grupo)
        self.btn_enviar_can.clicked.connect(self.enviar_canal)
        self.btn_crear_canal.clicked.connect(self.crear_canal)
        self.btn_suscribir.clicked.connect(self.suscribirse_canal)
        self.combo_contactos.currentIndexChanged.connect(self.actualizar_vista_privado)
        self.combo_mis_grupos.currentIndexChanged.connect(self.actualizar_vista_grupo)
        self.combo_mis_canales.currentIndexChanged.connect(self.actualizar_vista_canal)
        self.avatares_usuarios = {}
        self.label_avatar.setScaledContents(True)

    def conectar_servidor(self):
        global socket_global
        host = self.inp_ip.text().strip()
        port = self.inp_puerto.text().strip()
        user = self.inp_usuario.text().strip()
        password = self.inp_password.text().strip()
        avatar_text = self.combo_avatar.currentText()
        avatar_id = avatar_text.replace("avatar_", "").replace(".png", "")

        if not (host and port.isnumeric() and user and password):
            QMessageBox.warning(self, "Datos faltantes", "Por favor completa todos los campos.")
            return

        if "::" in user or "::" in password or "|" in user or "|" in password:
            QMessageBox.warning(self, "Caracteres no válidos", "El usuario y la contraseña no pueden contener '::' ni '|'.")
            return

        if connected and socket_global:
            self.mi_usuario = user
            self.enviar_red(f"<login>{user}::{password}|")
            return

        try:
            if socket_global is None or getattr(socket_global, '_closed', True):
                socket_global = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            self.mi_usuario = user
            self.coneccion = ThreadSocket(host, int(port), user, password, avatar_id)
            self.coneccion.signal_message.connect(self.mensage_entrante)
            self.coneccion.start()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fallo al conectar: {e}")

    def enviar_red(self, texto):
        global connected, socket_global
        if connected and socket_global:
            socket_global.send(bytes(texto, 'utf-8'))

    def enviar_general(self):
        msg = self.inp_msg_gen.text()
        if msg:
            self.enviar_red(f"<general>1::{msg}|")
            self.lista_general.addItem(f"Tú: {msg}")
            self.inp_msg_gen.clear()

    def enviar_privado(self):
        if self.combo_contactos.count() == 0:
            QMessageBox.warning(self, "Aviso", "No hay usuarios seleccionados.")
            return
        
        dest_id = self.combo_contactos.currentData()
        seleccion = self.combo_contactos.currentText()

        msg = self.inp_msg_priv.text()
        if dest_id and msg:
            self.enviar_red(f"<privado>{dest_id}::{msg}|")
            self.lista_privada.addItem(f"Tú: {msg}")
            #self.lista_privada.addItem(f"Tú (para {seleccion}): {msg}")
            self.inp_msg_priv.clear()

    def crear_grupo(self):
        nombre_grupo = self.inp_nombre_grupo.text()
        if nombre_grupo:
            self.enviar_red(f"<crear_grupo>{nombre_grupo}|")
            self.inp_nombre_grupo.clear()

    def enviar_grupo(self):
        if self.combo_mis_grupos.count() == 0:
            QMessageBox.warning(self, "Aviso", "No tienes grupos seleccionados.")
            return

        seleccion = self.combo_mis_grupos.currentText()
        try:
            grupo_id = seleccion.split("ID: ")[1].replace(")", "").strip()
        except IndexError:
            return

        msg = self.inp_msg_grup.text()
        if msg:
            self.enviar_red(f"<grupo>{grupo_id}::{msg}|")
            texto_mostrar = f"Tú: {msg}"

            if grupo_id not in self.historial_grupos:
                self.historial_grupos[grupo_id] = []
            self.historial_grupos[grupo_id].append(texto_mostrar)

            self.lista_grupo.addItem(texto_mostrar)
            self.inp_msg_grup.clear()

    def enviar_canal(self):
        if self.combo_mis_canales.count() == 0:
            QMessageBox.warning(self, "Aviso", "No tienes canales seleccionados.")
            return

        seleccion = self.combo_mis_canales.currentText()
        try:
            canal_id = seleccion.split("ID: ")[1].replace(")", "").strip()
        except IndexError:
            return

        msg = self.inp_msg_can.text()
        if msg:
            self.enviar_red(f"<canal>{canal_id}::{msg}|")
            self.inp_msg_can.clear()

    def crear_canal(self):
        nombre_canal = self.inp_nombre_canal.text()
        if nombre_canal:
            self.enviar_red(f"<crear_canal>{nombre_canal}|")
            self.inp_nombre_canal.clear()

    def suscribirse_canal(self):
        from PyQt5.QtWidgets import QInputDialog
        canal_id, ok = QInputDialog.getText(self, "Suscribirse", "Ingresa el ID numérico del canal:")
        if ok and canal_id.strip().isnumeric():
            self.enviar_red(f"<suscribirse>{canal_id.strip()}|")
        elif ok:
            QMessageBox.warning(self, "Aviso", "El ID del canal debe ser un número.")

    def actualizar_vista_grupo(self):
        self.lista_grupo.clear()
        if self.combo_mis_grupos.count() > 0:
            seleccion = self.combo_mis_grupos.currentText()
            try:
                grupo_id = seleccion.split("ID: ")[1].replace(")", "").strip()
                if grupo_id in self.historial_grupos:
                    for mensaje in self.historial_grupos[grupo_id]:
                        self.lista_grupo.addItem(mensaje)
            except IndexError:
                pass

    def actualizar_vista_privado(self):
        self.lista_privada.clear()
        if self.combo_contactos.count() > 0:
            dest_id = self.combo_contactos.currentData()
            if not dest_id:
                return
            
            self.enviar_red(f"<pedir_historial>privado::{dest_id}|")
            
            avatar_id = self.avatares_usuarios.get(str(dest_id), "1")
            base_dir = os.path.dirname(os.path.abspath(__file__))
            carpeta = os.path.join(base_dir, "Avatar1")
            
            pixmap = QPixmap()
            nombre_avatar = f"avatar_{avatar_id}.png"
            ruta = os.path.join(carpeta,nombre_avatar)
            if os.path.exists(ruta):
                pixmap = QPixmap(ruta)   
            if not pixmap.isNull():
                self.label_avatar.setPixmap(pixmap)
            else:
                print(f"[Debug Avatar] No se encontró imagen para ID {avatar_id} en: {carpeta}")
                if os.path.exists(carpeta):
                    print("[Debug Avatar] Archivos reales en Avatar1:", os.listdir(carpeta))
                self.label_avatar.setText("Sin foto")

        else:
            self.label_avatar.clear()
                

    def actualizar_vista_canal(self):
        self.lista_canales.clear()
        if self.combo_mis_canales.count() > 0:
            seleccion = self.combo_mis_canales.currentText()
            try:
                canal_id = seleccion.split("ID: ")[1].replace(")", "").strip()
                self.enviar_red(f"<pedir_historial>canal::{canal_id}|")
            except IndexError:
                pass

    def mensage_entrante(self, mensaje):
        if mensaje.startswith("<ok_login>"):
            datos = mensaje.replace("<ok_login>", "").split("::")
            self.mi_id = datos[0]
            self.stackedWidget.setCurrentIndex(1)
            self.setWindowTitle(f"Maniacos Chat - {self.mi_usuario} (Conectado)")
            self.enviar_red("<pedir_historial>general::1|")

        elif mensaje.startswith("<ok_signup>"):
            texto = mensaje.replace("<ok_signup>", "")
            QMessageBox.information(self, "Registro Exitoso", texto)
            password = self.inp_password.text().strip()
            self.enviar_red(f"<login>{self.mi_usuario}::{password}|")

        elif mensaje.startswith("<error_signup>"):
            QMessageBox.warning(self, "Error de Registro", mensaje.replace("<error_signup>", ""))

        elif mensaje.startswith("<error>"):
            texto_error = mensaje.replace("<error>", "")
            if "incorrectos" in texto_error.lower():
                respuesta = QMessageBox.question(
                    self,
                    "Usuario no encontrado",
                    f"{texto_error}.\n\n¿Deseas registrar '{self.mi_usuario}' como un usuario nuevo?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if respuesta == QMessageBox.Yes:
                    password = self.inp_password.text().strip()
                    avatar_text = self.combo_avatar.currentText()
                    avatar_id = avatar_text.replace("avatar_", "").replace(".png", "")
                    self.enviar_red(f"<signup>{self.mi_usuario}::{password}::{avatar_id}|")
            else:
                QMessageBox.warning(self, "Error del Servidor", texto_error)

        elif mensaje.startswith("<info>"):
            QMessageBox.information(self, "Información", mensaje.replace("<info>", ""))

        elif mensaje.startswith("<!!disconnected!!>"):
            QMessageBox.warning(self, "Desconectado", "El servidor cerró la conexión.")
            self.stackedWidget.setCurrentIndex(0)
            self.setWindowTitle("Maniacos Chat - Desconectado")

        elif mensaje.startswith("<general>"):
            datos = mensaje.replace("<general>", "").split("::")
            if len(datos) >= 3:
                self.lista_general.addItem(f"{datos[1]}: {datos[2]}")

        elif mensaje.startswith("<privado>"):
            datos = mensaje.replace("<privado>", "").split("::")
            if len(datos) >= 3:
                self.lista_privada.addItem(f"{datos[1]} te susurra: {datos[2]}")

        elif mensaje.startswith("<usuarios_activos>"):
            self.combo_contactos.blockSignals(True)
            self.combo_contactos.clear()
            self.avatares_usuarios.clear()
            datos = mensaje.replace("<usuarios_activos>", "")
            if datos:
                usuarios = datos.split(",")
                for u in usuarios:
                    partes = u.split("::")
                    if len(partes)>=2:
                        u_id, u_nombre = partes[0], partes[1]
                        u_avatar = partes[2] if len(partes)>=3 else "1"
                        if str(u_id) != str(self.mi_id):
                            self.avatares_usuarios[str(u_id)] = str(u_avatar).strip()
                            self.combo_contactos.addItem(u_nombre,str(u_id))
            self.combo_contactos.blockSignals(False)
            self.actualizar_vista_privado()

        elif mensaje.startswith("<nuevo_grupo>"):
            datos = mensaje.replace("<nuevo_grupo>", "").split("::")
            if len(datos) >= 2:
                grupo_id = datos[0]
                nombre = datos[1]

                existe = False
                for i in range(self.combo_mis_grupos.count()):
                    if f"ID: {grupo_id}" in self.combo_mis_grupos.itemText(i):
                        existe = True
                        break

                if not existe:
                    self.combo_mis_grupos.addItem(f"{nombre} (ID: {grupo_id})")
                    self.enviar_red(f"<pedir_historial>grupo::{grupo_id}|")

        elif mensaje.startswith("<nuevo_canal>"):
            datos = mensaje.replace("<nuevo_canal>", "").split("::")
            if len(datos) >= 2:
                canal_id = datos[0]
                nombre = datos[1]

                existe = False
                for i in range(self.combo_mis_canales.count()):
                    if f"ID: {canal_id}" in self.combo_mis_canales.itemText(i):
                        existe = True
                        break

                if not existe:
                    self.combo_mis_canales.addItem(f"{nombre} (ID: {canal_id})")
                    self.enviar_red(f"<pedir_historial>canal::{canal_id}|")

        elif mensaje.startswith("<grupo>"):
            datos = mensaje.replace("<grupo>", "").split("::")
            if len(datos) >= 3:
                grupo_id = datos[0]
                usuario = datos[1]
                contenido = datos[2]
                texto_mostrar = f"{usuario}: {contenido}"

                if grupo_id not in self.historial_grupos:
                    self.historial_grupos[grupo_id] = []
                self.historial_grupos[grupo_id].append(texto_mostrar)

                if self.combo_mis_grupos.count() > 0 and f"ID: {grupo_id}" in self.combo_mis_grupos.currentText():
                    self.lista_grupo.addItem(texto_mostrar)

        elif mensaje.startswith("<canal>"):
            datos = mensaje.replace("<canal>", "").split("::")
            if len(datos) >= 3:
                canal_id = datos[0]
                remitente = datos[1]
                contenido = datos[2]

                if remitente == self.mi_usuario:
                    self.lista_canales.addItem(f"Tú (Canal {canal_id}): {contenido}")
                else:
                    self.lista_canales.addItem(f"{remitente} (Canal {canal_id}): {contenido}")

        elif mensaje.startswith("<historial>"):
            datos = mensaje.replace("<historial>", "").split("::")
            if len(datos) >= 4:
                tipo = datos[0]
                destino_id = datos[1]
                usuario = datos[2]
                contenido = datos[3]

                texto_mostrar = f"{usuario}: {contenido}"

                if tipo == "general":
                    self.lista_general.addItem(texto_mostrar)

                elif tipo == "privado":
                    self.lista_privada.addItem(texto_mostrar)

                elif tipo == "grupo":
                    if destino_id not in self.historial_grupos:
                        self.historial_grupos[destino_id] = []

                    if texto_mostrar not in self.historial_grupos[destino_id]:
                        self.historial_grupos[destino_id].append(texto_mostrar)

                        if self.combo_mis_grupos.count() > 0 and f"ID: {destino_id}" in self.combo_mis_grupos.currentText():
                            self.lista_grupo.addItem(texto_mostrar)
                elif tipo == "canal":
                    self.lista_canales.addItem(texto_mostrar)

    def closeEvent(self, event):
        if self.coneccion:
            self.coneccion.stop()
        event.accept()


if __name__ == "__main__":
    socket_global = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
