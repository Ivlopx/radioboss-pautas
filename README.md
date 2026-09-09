# radioboss-pautas

Aplicación de escritorio para convertir documentos oficiales de pauta en
entradas del **Ads Scheduler de RadioBOSS**.

La aplicación trabaja sin conexión a internet, conserva las campañas existentes,
valida los audios antes de generar y crea un respaldo del INI original.

> Herramienta independiente y no oficial. No está desarrollada ni respaldada
> por DJSoft.Net o RadioBOSS.

## Funciones principales

- Interfaz de escritorio moderna construida con PySide6.
- Flujo inicial obligatorio para seleccionar y validar el INI plantilla.
- Secciones independientes para **Tiempo Estado** y **Barra genérica nacional**.
- Lectura de documentos Excel sin requerir Microsoft Excel.
- Emparejamiento de audios mediante los prefijos RDF y RDP.
- Horas y minutos obtenidos dinámicamente del INI.
- Distribución de transmisiones de acuerdo con la carga de los bloques.
- Vista previa completa antes de generar.
- Detección de audios faltantes, claves duplicadas y notas para revisión.
- Respaldo automático, escritura segura y restauración de respaldos.
- Conservación de campañas creadas manualmente en RadioBOSS.
- Reemplazo selectivo de entradas creadas previamente por la aplicación.

## Requisitos

### Para ejecutar desde el código

- Windows 10 u 11 recomendado.
- Python 3.9 o posterior, de 64 bits.
- `PySide6` para la interfaz gráfica.
- `openpyxl` para leer los documentos Excel.

RadioBOSS no es necesario para abrir la aplicación, pero sí para utilizar el
INI generado.

### Para desarrollar

- `pytest` para ejecutar las pruebas.
- `PyInstaller` para crear el ejecutable de Windows.

## Instalación en Windows

### 1. Clonar el repositorio

```powershell
git clone git@github.com:Ivlopx/radioboss-pautas.git
cd radioboss-pautas
```

### 2. Crear y activar el entorno virtual

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell impide la activación, habilítala sólo para la sesión actual:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar las dependencias

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Ejecutar la aplicación

```powershell
python app.py
```

## Instalación en macOS o Linux para desarrollo

RadioBOSS se utiliza normalmente en Windows, pero la interfaz y las pruebas
pueden ejecutarse en otros sistemas:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python app.py
```

## Uso de la aplicación

### Paso 1: seleccionar el INI plantilla

Selecciona el archivo actual del Ads Scheduler. La aplicación valida su
estructura y muestra las horas de `SHours` y los minutos de `SMinutes`.

Las secciones de trabajo permanecen deshabilitadas hasta que el INI sea válido.

### Paso 2: elegir una sección

#### Tiempo Estado

1. Selecciona el Excel de Tiempo Estado.
2. Selecciona la carpeta `Material Radio`.
3. Presiona **Analizar y previsualizar**.

La aplicación:

- Lee la fecha, clave RDF y franja horaria de cada fila.
- Busca un archivo cuyo nombre comience con la clave RDF correspondiente.
- Reutiliza los bloques que tengan al menos un anuncio activo y vigente.
- Si hay varios bloques activos, selecciona el menos cargado.
- Si una hora no tiene bloques activos, usa el primer minuto habilitado por el
  INI.
- Aplica sustituciones de claves indicadas explícitamente en las notas del Excel.
- Presenta las demás notas como advertencias para revisión manual.

Las entradas de esta sección se identifican internamente con `AUTO_TE_`.

#### Barra genérica nacional

1. Selecciona el Excel de Barra genérica nacional.
2. Selecciona la carpeta `Material Radio`.
3. Elige el tipo de estación:
   - Programas de 5 minutos: requiere `Horario 1` y `Horario 2`.
   - Programas de 10 minutos: requiere un solo horario.
4. Selecciona los horarios y presiona **Analizar y previsualizar**.

La aplicación:

- Detecta automáticamente el periodo y las columnas de lunes a lunes.
- Busca los audios mediante el prefijo RDP.
- Muestra solamente horas habilitadas por el INI.
- Para cada fecha y hora compara todos los minutos de `SMinutes`, incluidos los
  bloques vacíos.
- Coloca el programa en el bloque con menos anuncios.
- En caso de empate, respeta el orden de minutos del INI.

Las entradas de esta sección se identifican internamente con `AUTO_BGN_`.

### Paso 3: revisar la vista previa

La tabla presenta la fecha, hora, bloque final, clave, audio encontrado, origen
del bloque y fila del Excel. La generación se bloquea si falta un audio o si una
clave coincide con varios archivos.

### Paso 4: generar el INI

1. Cierra RadioBOSS y Ads Scheduler.
2. Mantén seleccionada la opción **Crear respaldo antes de reemplazar el INI**.
3. Presiona **Generar INI**.
4. Selecciona como destino el INI utilizado por RadioBOSS.

Si RadioBOSS está abierto, la aplicación muestra una advertencia para evitar que
sobrescriba el archivo nuevo con una versión anterior.

## Respaldos y restauración

Antes de reemplazar el INI se crea una copia con un nombre similar a:

```text
adscheduler_respaldo_AAAAMMDD_HHMMSS.ini
```

El archivo nuevo se valida y se escribe de forma atómica. Si la generación
falla, el INI original permanece intacto.

El botón **Restaurar respaldo** permite recuperar una copia anterior. Antes de
restaurarla, también se conserva una copia preventiva del archivo reemplazado.

## Convención para los audios

El nombre de cada audio debe comenzar con la clave indicada en el Excel:

```text
RDF2532026 descripcion del spot.mp3
RDP1322026 nombre del programa.mp3
```

Se admiten archivos MP3, WAV, OGG, FLAC, M4A, AAC y WMA. La búsqueda incluye
subcarpetas. Los archivos sin prefijo RDF o RDP se omiten y se informan en la
pantalla de validación.

## Crear el ejecutable de Windows

Desde PowerShell, en la raíz del repositorio:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

El resultado queda en:

```text
dist\GeneradorPautaRadio\GeneradorPautaRadio.exe
```

El equipo que utilice el ejecutable no necesita tener Python ni Microsoft Excel
instalados.

## Ejecutar las pruebas

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Las pruebas cubren ambos tipos de Excel, emparejamiento de claves, distribución
de bloques, validación de horas, generación del INI, convivencia de las secciones
y respaldos.

## Estructura del proyecto

```text
radioboss-pautas/
├── app.py
├── radioboss_pautas/
│   ├── core/
│   │   ├── ini.py
│   │   ├── models.py
│   │   └── planner.py
│   ├── tiempo_estado/
│   │   ├── excel.py
│   │   └── distribution.py
│   ├── barra_generica/
│   │   ├── excel.py
│   │   └── distribution.py
│   └── service.py
├── tests/
├── requirements.txt
├── requirements-dev.txt
└── build_windows.ps1
```

- `core`: modelos, INI y motor compartido de asignación.
- `tiempo_estado`: lectura y reglas exclusivas de Tiempo Estado.
- `barra_generica`: lectura y reglas exclusivas de Barra genérica nacional.
- `service.py`: coordinación del análisis, generación y respaldos.
- `app.py`: interfaz gráfica.

## Recomendaciones operativas

- Conserva activada la creación de respaldos.
- Cierra RadioBOSS antes de reemplazar el INI.
- Revisa todas las advertencias del documento antes de generar.
- Prueba una nueva versión primero sobre una copia del INI.
- Después de cargar el archivo en RadioBOSS, revisa los bloques y genera las
  playlists y eventos correspondientes.
- No subas al repositorio pautas oficiales, audios ni archivos INI reales.

## Solución de problemas

### El INI no habilita las secciones

Comprueba que seleccionaste el archivo de configuración del Ads Scheduler y no
una playlist o un archivo de eventos.

### Aparece un audio faltante

Confirma que el archivo comienza exactamente con la clave RDF o RDP del Excel.

### Aparece una clave duplicada

Existe más de un audio con el mismo prefijo. Retira las versiones que no deban
utilizarse o cambia sus nombres antes de volver a analizar.

### Un horario no aparece en Barra genérica

La hora no está habilitada en `SHours`. Actívala en Ads Scheduler, guarda el INI
y vuelve a seleccionarlo.

### PowerShell no permite ejecutar la compilación

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

## Datos privados

El repositorio excluye intencionalmente Excel, PDF, audios, archivos INI reales,
respaldos y entornos virtuales. La aplicación procesa los archivos localmente.

