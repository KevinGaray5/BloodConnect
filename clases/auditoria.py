"""
Módulo de Auditoría y Persistencia - BloodConnect
Este archivo es el encargado de leer y guardar toda la información del sistema. 
Maneja el registro histórico de movimientos (bitácora), la creación de gráficas 
para los reportes y protege los archivos CSV para que no se corrompan si ocurren 
cambios simultáneos.
"""

import os
import time
import json
import shutil
from enum import Enum
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import deque
from matplotlib.ticker import MaxNLocator

import pandas as pd
import matplotlib
# Usamos el backend 'Agg' para que el sistema pueda dibujar y guardar las gráficas 
# de fondo, sin necesidad de abrir ventanas emergentes que interrumpan al usuario.
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)


class NivelSeveridad(Enum):
    """
    Categorías para clasificar qué tan importante o crítico es un evento 
    que ocurre dentro del sistema.
    """
    INFO = "INFO"
    ADVERTENCIA = "ADVERTENCIA"
    CRITICO = "CRITICO"


class EntidadAfectada(Enum):
    """
    Lista de las áreas principales del proyecto. Sirve para saber exactamente 
    en qué módulo ocurrió un cambio o un error.
    """
    DONANTE = "DONANTE"
    PACIENTE = "PACIENTE"
    TRABAJADOR = "TRABAJADOR"
    HEMOCOMPONENTE = "HEMOCOMPONENTE"
    SISTEMA = "SISTEMA"


class Bitacora:
    """
    Se encarga de llevar un registro histórico (log) de todo lo que pasa. 
    Este registro está protegido: solo se pueden agregar líneas nuevas, 
    pero nunca borrar ni modificar las anteriores, cumpliendo con normas de seguridad médica.
    """
    
    def __init__(self, id_log: int, id_usuario: int, entidad_afectada: EntidadAfectada, accion_realizada: str, nivel_severidad: NivelSeveridad):
        self.id_log = id_log
        self.timestamp = datetime.now()
        self.id_usuario = id_usuario
        self.entidad_afectada = entidad_afectada
        self.accion_realizada = accion_realizada.strip()
        self.nivel_severidad = nivel_severidad

    def escribir_entrada_inmutable(self, ruta_log: str) -> bool:
        """
        Guarda el evento en el archivo de texto. Al abrirlo en modo 'append' (a), 
        nos aseguramos de que los datos antiguos no se puedan sobrescribir.
        """
        fecha_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        linea_log = f"[{fecha_str}] | LOG-{self.id_log} | SEV: {self.nivel_severidad.value} | USR: {self.id_usuario} | ENTIDAD: {self.entidad_afectada.value} | ACCION: {self.accion_realizada}\n"
        
        try:
            with open(ruta_log, "a", encoding="utf-8") as archivo:
                archivo.write(linea_log)
            return True
        except Exception as e:
            raise IOError(f"Aviso del sistema: No se pudo guardar el registro en la bitácora {self.id_log}. Detalle: {e}")

    @classmethod
    def consultar_historial_auditoria(cls, ruta_archivo: str = None, limite: int = 10) -> List[str]:
        """
        Lee las acciones más recientes registradas en el sistema. 
        Usa una estructura de cola (deque) para no cargar todo el archivo en la memoria 
        en caso de que el historial sea demasiado grande.
        """
        if ruta_archivo is None:
            ruta_archivo = os.path.join(PROJECT_ROOT, "datos", "log_auditoria.txt")
            
        try:
            with open(ruta_archivo, "r", encoding="utf-8") as archivo:
                # Extrae solo las últimas 'N' líneas de manera eficiente
                cola = deque(archivo, maxlen=limite)
                return [linea.strip() for linea in cola]
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Aviso del sistema: El archivo de auditoría en '{ruta_archivo}' no existe o no ha sido creado aún.") from e   


class AnalizadorReportes:
    """
    Toma los datos numéricos del inventario y utiliza Matplotlib para 
    convertirlos en gráficas fáciles de leer para los reportes gerenciales.
    """
    
    def __init__(self, configuracion_graficas: Dict[str, Any]):
        self.configuracion_graficas = configuracion_graficas

    def generar_dashboard_stock(self, diccionario_stock: Dict[str, int]) -> str:
        """Verifica que haya datos y manda a generar la gráfica del inventario actual."""
        if not diccionario_stock:
            raise ValueError("Aviso: No hay datos de inventario para generar el reporte visual.")

        return self.exportar_grafica_png(diccionario_stock)
    
    def exportar_grafica_png(self, diccionario_stock: Dict[str, int], nombre_archivo: str = None) -> str:
        """
        Crea una gráfica de barras con las cantidades de sangre disponibles 
        y la guarda como una imagen PNG en la carpeta de datos.
        """
        if nombre_archivo is None:
            nombre_archivo = os.path.join(PROJECT_ROOT, "datos", "reporte_stock.png")
            
        if not diccionario_stock:
            raise ValueError("Aviso: Faltan datos para poder dibujar la gráfica.")

        grupos = list(diccionario_stock.keys())
        cantidades = list(diccionario_stock.values())
        
        plt.figure(figsize=(8, 5))
        plt.bar(grupos, cantidades, color=self.configuracion_graficas.get("color_exportacion", "darkred"))
        plt.title("Reporte Exportado - Stock de Sangre")
        
        try:
            # Asegura que el eje Y solo muestre números enteros (no podemos tener 1.5 bolsas de sangre)
            plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
            plt.savefig(nombre_archivo)
            plt.close() # Cerramos la figura para liberar memoria
            return nombre_archivo
        except Exception as e:
            raise IOError(f"Aviso del sistema: Ocurrió un error al intentar guardar la imagen en {nombre_archivo}. Detalle: {e}")
        
class GestorDatos:
    """
    Es el coordinador principal de los archivos. Se encarga de leer y escribir en los CSV, 
    crear copias de seguridad y asegurarse de que dos procesos no arruinen un archivo 
    si intentan guardar información exactamente al mismo tiempo.
    """
    
    def __init__(self, ruta_config: str = None):
        if ruta_config is None:
            ruta_config = os.path.join(PROJECT_ROOT, "config.json")
        
        self.config = self._cargar_configuracion(ruta_config)
        
        # Convierte las rutas relativas en rutas absolutas para que funcione en cualquier computadora
        self.rutas_archivos_csv = {
            clave: os.path.join(PROJECT_ROOT, valor) 
            for clave, valor in self.config["archivos"].items()
        }
        
        self.ruta_log = os.path.join(PROJECT_ROOT, self.config["archivos"]["log_auditoria"])
        self.ruta_respaldos = os.path.join(PROJECT_ROOT, self.config["directorios"]["respaldos"])

    def es_id_global_unico(self, id_propuesto: int) -> bool:
        """
        Revisa las bases de datos de personas (Donantes, Pacientes, Trabajadores) 
        para asegurarse de que un número de ID no se le asigne a dos personas distintas.
        """
        archivos_identidades = [
            ("donantes", "id_global"),
            ("pacientes", "id_global"),
            ("trabajadores", "id_global")
        ]
        
        for clave_archivo, columna in archivos_identidades:
            df = self.leer_persistencias(clave_archivo)
            if df is not None and not df.empty and columna in df.columns:
                if id_propuesto in df[columna].values:
                    return False
                
        return True

    def _cargar_configuracion(self, ruta: str) -> dict:
        """
        Lee el archivo de configuración JSON. Si alguien lo borró por accidente, 
        el sistema lo vuelve a crear con las rutas por defecto para evitar que el programa colapse.
        """
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Recreación automática del entorno base
            config_seguridad = {
                "directorios": {
                    "datos": "datos",
                    "respaldos": "datos/respaldos"
                },
                "archivos": {
                    "donantes": "datos/donantes.csv",
                    "pacientes": "datos/pacientes.csv",
                    "trabajadores": "datos/trabajadores.csv",
                    "extracciones": "datos/extracciones.csv",
                    "inventario": "datos/inventario.csv",
                    "transfusiones": "datos/transfusiones.csv",
                    "citas": "datos/citas.csv", 
                    "log_auditoria": "datos/log_auditoria.txt"
                }
            }
            try:
                os.makedirs(os.path.dirname(ruta), exist_ok=True)
                with open(ruta, 'w', encoding='utf-8') as f:
                    json.dump(config_seguridad, f, indent=4)
            except Exception:
                pass  
                
            return config_seguridad
        
    def verificar_integridad_archivos(self) -> bool:
        """
        Se ejecuta al abrir el programa. Verifica que todas las carpetas necesarias existan; 
        si no, las crea, e inicializa el archivo de la bitácora si es la primera vez que se usa.
        """
        for dir_ruta_relativa in self.config["directorios"].values():
            ruta_completa = os.path.join(PROJECT_ROOT, dir_ruta_relativa)
            os.makedirs(ruta_completa, exist_ok=True)
        
        if not os.path.exists(self.ruta_log):
            try:
                with open(self.ruta_log, 'w', encoding='utf-8') as f:
                    f.write(f"--- [BLOODCONNECT INIT] INICIO DE BITÁCORA DEL SISTEMA | FECHA: {datetime.now()} ---\n")
            except Exception as e:
                raise IOError(f"Error crítico al intentar crear el archivo de auditoría. {e}")

        return True

    def leer_persistencias(self, clave_archivo: str) -> Optional[pd.DataFrame]:
        """Carga la información de los archivos CSV a la memoria del programa usando Pandas."""
        ruta = self.rutas_archivos_csv.get(clave_archivo)
        if not ruta:
            return None

        try:
            return pd.read_csv(ruta)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            # Si el archivo no existe o está en blanco, devolvemos una tabla vacía para no causar errores
            return pd.DataFrame()

    def guardar_cambios_atomicos(self, clave_archivo: str, dataframe_actualizado: pd.DataFrame) -> bool:
        """
        Guarda los datos de forma segura. Usa un archivo ".lock" como semáforo para que 
        solo un proceso pueda escribir a la vez. Además, guarda primero en un archivo temporal 
        y luego lo reemplaza, así si se va la luz a mitad del proceso, el archivo original no se daña.
        """
        ruta = self.rutas_archivos_csv.get(clave_archivo)
        if not ruta:
            raise ValueError(f"Error: El archivo '{clave_archivo}' no está registrado en la configuración.")

        ruta_lock = f"{ruta}.lock"
        intentos = 0
        max_intentos = 5

        # Esperamos si alguien más está guardando en este mismo instante
        while os.path.exists(ruta_lock):
            try:
                tiempo_actual = time.time()
                tiempo_lock = os.path.getmtime(ruta_lock)
                
                # Si el candado se quedó atorado por más de 5 segundos, lo borramos a la fuerza
                if tiempo_actual - tiempo_lock > 5.0:
                    os.remove(ruta_lock)
                    break 
            except FileNotFoundError:
                break

            if intentos >= max_intentos:
                raise IOError(f"Aviso: El archivo {ruta} está bloqueado por otra operación. Intente de nuevo.")
            time.sleep(0.5) 
            intentos += 1

        try:
            # Ponemos nuestro propio candado
            with open(ruta_lock, 'w') as f:
                f.write("locked")

            # Escribimos los datos en un archivo temporal (.tmp)
            ruta_temporal = f"{ruta}.tmp"
            dataframe_actualizado.to_csv(ruta_temporal, index=False)
            # Reemplazamos el archivo viejo de un solo golpe (Operación Atómica)
            os.replace(ruta_temporal, ruta)
            return True

        except Exception as e:
            # Si algo falla, borramos el archivo temporal para no dejar basura
            if 'ruta_temporal' in locals() and os.path.exists(ruta_temporal):
                os.remove(ruta_temporal)
            raise IOError(f"Error grave al intentar guardar los cambios en los archivos. Detalle: {e}")
        finally:
            # Siempre quitamos el candado al terminar, pase lo que pase
            if os.path.exists(ruta_lock):
                os.remove(ruta_lock)

    def respaldar_datos(self) -> List[str]:
        """
        Copia todos los archivos de datos actuales y los guarda en la carpeta de respaldos 
        agregándoles la fecha y hora en el nombre para mantener un archivo histórico.
        """
        if not os.path.exists(self.ruta_respaldos):
            os.makedirs(self.ruta_respaldos, exist_ok=True)
            
        fecha_hoy = datetime.now().strftime("%Y%m%d_%H%M")
        archivos_respaldados = []
        
        for _, ruta_origen in self.rutas_archivos_csv.items():
            if os.path.exists(ruta_origen) and not ruta_origen.endswith('.txt'):
                nombre_archivo = os.path.basename(ruta_origen)
                ruta_destino = os.path.join(self.ruta_respaldos, f"{fecha_hoy}_{nombre_archivo}")
                try:
                    # Hacemos una copia exacta del archivo
                    shutil.copy2(ruta_origen, ruta_destino)
                    archivos_respaldados.append(ruta_destino)
                except IOError:
                    continue
                     
        return archivos_respaldados
    
    def existe_id_en_archivo(self, clave_archivo: str, columna_id: str, valor_id: int) -> bool:
        """
        Verifica rápidamente si un número de identificación ya está registrado en un archivo específico 
        (útil para verificar que un paciente o una unidad existan antes de hacer algún proceso).
        """
        df = self.leer_persistencias(clave_archivo)
        
        if df is None or df.empty or columna_id not in df.columns:
            return False
            
        return valor_id in df[columna_id].values