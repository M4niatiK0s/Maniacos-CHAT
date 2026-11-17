# Maniacos Chat - Práctica 1 (Sistemas Distribuidos)

Sistema de mensajería instantánea basado en arquitectura **Cliente-Servidor** desarrollado en Python utilizando sockets TCP puros (`AF_INET`, `SOCK_STREAM`), interfaz gráfica multiplataforma en **PyQt5** y persistencia de datos en **Microsoft SQL Server**.

El servidor sin interfaz gráfica ya se encuentra desplegado y en ejecución continua en el servidor remoto asignado al equipo (`3.149.102.2`, puerto `3025`), por lo que únicamente es necesario clonar este repositorio y ejecutar el cliente gráfico desde **Windows**, **GNU/Linux** o **macOS**.

---

## Estructura del Repositorio

- `cliente_gui.py`: Aplicación principal del cliente con interfaz gráfica en PyQt5, gestión de hilos de red (`QThread`) y manejo de sesiones.
- `principal.py` / `principal.ui`: Definición visual de ventanas, pestañas y widgets generada con Qt Designer.
- `server.py`: Servidor TCP concurrente multihilo que gestiona conexiones activas, autenticación y enrutamiento de mensajes.
- `BaseDatos.py`: Capa de acceso a datos con consultas parametrizadas hacia Microsoft SQL Server.
- `avatares/`: Recursos gráficos (`avatar_1.png` a `avatar_8.png`) disponibles para seleccionar foto de perfil al registrarse.
- `requirements.txt`: Archivo de dependencias necesarias para ejecutar el proyecto.
- `LICENSE`: Licencia de código abierto del proyecto.

---

## Requisitos Previos por Sistema Operativo

Dado que **Git** y **Python 3 (versión 3.9 o superior)** no vienen preinstalados en todos los sistemas operativos, sigue los pasos correspondientes a tu sistema antes de clonar el proyecto:

### 1. Windows
1. **Instalar Git:**
   - Descarga el instalador desde [git-scm.com/downloads](https://git-scm.com/downloads), ejecútalo y avanza con **Next** hasta finalizar (o abre PowerShell y ejecuta `winget install --id Git.Git -e --source winget`).
2. **Instalar Python 3:**
   - Descarga el instalador oficial desde [python.org/downloads](https://www.python.org/downloads/).
   - Al abrir el instalador, **marca obligatoriamente la casilla "Add Python to PATH"** en la parte inferior antes de hacer clic en **Install Now**.

### 2. GNU/Linux (Ubuntu, Debian, Parrot OS y derivados)
1. **Instalar Git, Python 3, pip y soporte de entornos virtuales:**
   Abre una terminal y ejecuta:
   ```bash
   sudo apt update
   sudo apt install -y git python3 python3-pip python3-venv
   ```

### 3. macOS
1. **Instalar Git:**
   - Abre la aplicación **Terminal** (`Cmd + Espacio`, escribe `Terminal` y presiona `Enter`) y ejecuta `git --version`. Si no está instalado, macOS mostrará una ventana para instalar las *Command Line Tools*; haz clic en **Instalar**.
2. **Instalar Python 3:**
   - Descarga el instalador para macOS desde [python.org/downloads](https://www.python.org/downloads/) o instálalo mediante Homebrew ejecutando:
     ```bash
     brew install python
     ```

---

## Instalación y Ejecución del Cliente

### En Windows (CMD o PowerShell)

1. Presiona la tecla **Windows**, escribe `cmd` (o `PowerShell`) y abre la consola.
2. Ubícate en la carpeta donde deseas descargar el proyecto (por ejemplo, el Escritorio):
   ```powershell
   cd Desktop
   ```
3. Clona el repositorio y entra a la carpeta del proyecto:
   ```powershell
   git clone [https://github.com/M4niatiK0s/Maniacos-CHAT.git](https://github.com/M4niatiK0s/Maniacos-CHAT.git)
   cd Maniacos-CHAT
   ```
4. Crea y activa un entorno virtual de Python:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   ```
   *(Nota: Si utilizas PowerShell y aparece un error de políticas de ejecución al activar el entorno, ejecuta `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` y vuelve a correr `venv\Scripts\activate`).*
5. Actualiza `pip` e instala las dependencias:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
6. Inicia la aplicación cliente:
   ```powershell
   python cliente_gui.py
   ```

---

### En GNU/Linux

1. Abre una terminal y ubícate en tu directorio personal:
   ```bash
   cd ~
   ```
2. Clona el repositorio y entra a la carpeta del proyecto:
   ```bash
   git clone [https://github.com/M4niatiK0s/Maniacos-CHAT.git](https://github.com/M4niatiK0s/Maniacos-CHAT.git)
   cd Maniacos-CHAT
   ```
3. Crea y activa el entorno virtual:
   ```bash
   python3 -m venv venv
   source ./venv/bin/activate
   ```
4. Actualiza `pip` e instala las dependencias:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Inicia la aplicación cliente:
   ```bash
   python3 cliente_gui.py
   ```

---

### En macOS

1. Abre la aplicación **Terminal** y ubícate en tu directorio personal:
   ```bash
   cd ~
   ```
2. Clona el repositorio y entra a la carpeta del proyecto:
   ```bash
   git clone [https://github.com/M4niatiK0s/Maniacos-CHAT.git](https://github.com/M4niatiK0s/Maniacos-CHAT.git)
   cd Maniacos-CHAT
   ```
3. Crea y activa el entorno virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
4. Actualiza `pip` e instala las dependencias:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Inicia la aplicación cliente:
   ```bash
   python3 cliente_gui.py
   ```

---

## Guía de Conexión y Uso de la Aplicación

1. **Pantalla de Inicio de Sesión / Registro:**
   Al abrirse la ventana de `cliente_gui.py`, ingresa los siguientes parámetros:
   - **Dirección IP:** `3.149.102.2`
   - **Puerto:** `3025`
   - **Usuario:** Tu nombre de usuario (evita usar los caracteres `::` o `|`, ya que son los delimitadores del protocolo de red).
   - **Contraseña:** Tu contraseña.
   - **Avatar:** Selecciona una imagen de perfil del menú desplegable (`avatar_1.png` a `avatar_8.png`).

2. **Conexión y Registro Automático:**
   - Haz clic en el botón **Conectar**.
   - Si el usuario ya existe en la base de datos, ingresarás directamente a la sala principal.
   - Si el usuario aún no está registrado, el cliente mostrará una ventana emergente preguntando si deseas registrarlo como cuenta nueva con la foto de perfil seleccionada; haz clic en **Yes** para crear la cuenta e iniciar sesión automáticamente.

3. **Secciones del Chat:**
   - **General:** Sala pública global donde todos los usuarios conectados pueden enviar y leer mensajes en tiempo real, mostrando el nombre del remitente y el historial previo.
   - **Privado:** Permite seleccionar a cualquier usuario conectado en ese momento desde el menú desplegable superior para mantener una conversación directa uno a uno.
   - **Grupos:** Permite crear nuevas salas grupales asignándoles un nombre y enviar mensajes visibles únicamente dentro de ese grupo.
   - **Canales:** Permite crear un canal de difusión propio (donde únicamente el creador puede publicar mensajes) o suscribirse a un canal existente ingresando su ID numérico para visualizar sus publicaciones en modo de solo lectura.

---

## Notas Técnicas del Servidor (Referencia)

El componente servidor (`server.py` + `BaseDatos.py`) se ejecuta de forma independiente en el servidor Linux remoto del curso bajo la cuenta del equipo (`maniaco`) escuchando en `0.0.0.0:3025` mediante:

```bash
nohup python3 server.py > server.log 2>&1 &
```

La configuración de conexión a SQL Server se gestiona en el servidor mediante variables de entorno en un archivo privado `.env` (excluido del repositorio público por seguridad).

