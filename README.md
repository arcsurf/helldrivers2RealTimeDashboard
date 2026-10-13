# Helldivers 2 · Real-Time Dashboard

Dashboard de escritorio en tiempo real para seguir el estado de la **Guerra Galáctica** de *Helldivers 2*, construido con **Tkinter** y **Matplotlib** sobre la [API comunitaria de Helldivers 2](https://helldivers-2.github.io/api).

## Características

- **KPIs globales**: jugadores activos, tasa de éxito de misiones, multiplicador de impacto, misiones ganadas/perdidas y bajas.
- **Bajas por facción**: Terminidos, Autómatas e Iluminados.
- **Campañas activas**: planeta, sector, facción enemiga, jugadores, porcentaje de liberación, bioma y defensas con tiempo restante.
- **Órdenes mayores** (*Major Orders*) en curso.
- **Gráficos históricos** de jugadores totales y por facción, con ventana de tiempo configurable.
- **Actualización automática** cada 30 s, 1, 2 o 5 minutos, o manual con «Actualizar ahora».
- **Historial persistente** en `history.csv` para conservar la evolución entre sesiones.
- Tema oscuro con paleta de colores apta para daltonismo.

## Requisitos

- Python 3.10 o superior
- Tkinter (incluido en la mayoría de instalaciones de Python; en Linux puede requerir el paquete `python3-tkinter` / `python3-tk`)

## Cómo ejecutarlo

Pasos para que cualquier persona pueda ejecutar el dashboard en su equipo.

### 1. Instalar Python y Tkinter

Necesitas **Python 3.10 o superior**. Compruébalo con:

```bash
python3 --version   # En Windows: python --version
```

Tkinter es la librería gráfica que usa la app. Según tu sistema:

| Sistema | Instalación |
|---|---|
| **Windows** | Instala Python desde [python.org](https://www.python.org/downloads/) dejando marcada la opción *tcl/tk and IDLE* (viene marcada por defecto). Marca también *Add python.exe to PATH*. |
| **macOS** | Instala Python desde [python.org](https://www.python.org/downloads/) (ya incluye Tkinter) o con Homebrew: `brew install python python-tk` |
| **Ubuntu / Debian** | `sudo apt install python3 python3-venv python3-tk` |
| **Fedora** | `sudo dnf install python3 python3-tkinter` |
| **Arch Linux** | `sudo pacman -S python tk` |

Para comprobar que Tkinter funciona, ejecuta `python3 -m tkinter`: debería abrirse una pequeña ventana de prueba.

### 2. Descargar el proyecto

Con Git:

```bash
git clone https://github.com/arcsurf/helldrivers2RealTimeDashboard.git
cd helldrivers2RealTimeDashboard
```

Sin Git: en la página del repositorio pulsa **Code → Download ZIP**, descomprímelo y abre una terminal dentro de la carpeta.

### 3. Crear un entorno virtual e instalar dependencias

Linux / macOS (bash o zsh):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Linux con fish:

```fish
python3 -m venv .venv
source .venv/bin/activate.fish
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Si PowerShell bloquea la activación, ejecuta antes `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Windows (CMD):

```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 4. Ejecutar la app

Con el entorno virtual activado:

```bash
python app.py
```

Se abrirá la ventana del dashboard y empezará a descargar datos de la API. Desde la barra superior puedes elegir cada cuánto se actualiza, la ventana de tiempo de los gráficos o forzar una actualización con «Actualizar ahora». Para cerrarla, cierra la ventana.

La próxima vez solo tendrás que entrar en la carpeta, activar el entorno virtual (paso 3, segunda línea) y ejecutar `python app.py`.

### 5. (Opcional) Identificarte ante la API

Por defecto la app se identifica ante la API con el nombre y la URL de este repositorio. Si vas a usarla de forma habitual o distribuirla, es recomendable indicar tus propios datos de contacto con las variables `HD2_CLIENT` y `HD2_CONTACT`:

| Shell | Comando |
|---|---|
| bash / zsh | `HD2_CLIENT=mi-dashboard HD2_CONTACT=tu@email.com python app.py` |
| fish | `env HD2_CLIENT=mi-dashboard HD2_CONTACT=tu@email.com python app.py` |
| PowerShell | `$env:HD2_CLIENT="mi-dashboard"; $env:HD2_CONTACT="tu@email.com"; python app.py` |
| CMD | `set "HD2_CLIENT=mi-dashboard" && set "HD2_CONTACT=tu@email.com" && python app.py` |

### Problemas frecuentes

- **`ModuleNotFoundError: No module named 'tkinter'`** → falta Tkinter; instálalo según el paso 1.
- **`ModuleNotFoundError: No module named 'requests'` o `'matplotlib'`** → el entorno virtual no está activado o no se instalaron las dependencias; repite el paso 3.
- **La barra superior muestra «Error: …»** → comprueba tu conexión a Internet. Si la API devuelve `429 Too Many Requests`, aumenta el intervalo de actualización.
- **`history.csv`** → se crea automáticamente junto a `app.py` para guardar el historial. Puedes borrarlo para empezar de cero.

## Estructura del proyecto

```
.
├── app.py            # Interfaz Tkinter, gráficos e historial
├── hd2_api.py        # Cliente mínimo de la API de Helldivers 2
└── requirements.txt  # Dependencias
```

## API

Los datos provienen de `https://api.helldivers2.dev`. La API pide identificar al cliente mediante las cabeceras `X-Super-Client` y `X-Super-Contact`. Por defecto se envían el nombre y la URL de este repositorio; si haces un fork o distribuyes la app, define tus propios datos con las variables de entorno `HD2_CLIENT` y `HD2_CONTACT`:

```bash
HD2_CLIENT=mi-dashboard HD2_CONTACT=tu@email.com python app.py
```

Cada actualización realiza 3 peticiones, dentro del límite de 5 peticiones cada 10 segundos.

## Ramas

- `master`: versión estable.
- `develop`: desarrollo activo.

## Aviso

Proyecto no oficial creado por fans. *Helldivers 2* es una marca de Arrowhead Game Studios y Sony Interactive Entertainment.
