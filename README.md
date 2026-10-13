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

## Instalación

```bash
git clone https://github.com/arcsurf/helldrivers2RealTimeDashboard.git
cd helldrivers2RealTimeDashboard
python -m venv .venv
source .venv/bin/activate   # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

```bash
python app.py
```

## Estructura del proyecto

```
.
├── app.py            # Interfaz Tkinter, gráficos e historial
├── hd2_api.py        # Cliente mínimo de la API de Helldivers 2
└── requirements.txt  # Dependencias
```

## API

Los datos provienen de `https://api.helldivers2.dev`. La API pide identificar al cliente mediante las cabeceras `X-Super-Client` y `X-Super-Contact` (definidas en `hd2_api.py`); si publicas o distribuyes la app, cámbialas por tus propios datos de contacto. Cada actualización realiza 3 peticiones, dentro del límite de 5 peticiones cada 10 segundos.

## Ramas

- `master`: versión estable.
- `develop`: desarrollo activo.

## Aviso

Proyecto no oficial creado por fans. *Helldivers 2* es una marca de Arrowhead Game Studios y Sony Interactive Entertainment.
