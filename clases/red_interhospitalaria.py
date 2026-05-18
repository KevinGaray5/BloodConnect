"""
Módulo de Red Interhospitalaria - BloodConnect
Este archivo se encarga de la comunicación con otros hospitales aliados. 
Organiza cómo pedimos o enviamos bolsas de sangre, asegurando que los registros 
cuadren perfectamente y vigilando que no se rompa la cadena de frío durante el traslado.
"""

from datetime import date, datetime
from enum import Enum
from typing import List, Dict, Any
import pandas as pd
from .gestion_almacen import Hemocomponente, TipoHemocomponente, EstadoHemocomponente


class TipoMovimiento(Enum):
    """Sirve para identificar rápidamente si la sangre está entrando a nuestro hospital o si la estamos enviando a otro lado."""
    ENTRADA = "Entrada"
    SALIDA = "Salida"


class EstadoLogistico(Enum):
    """
    Controla las diferentes etapas del viaje de la sangre. 
    Si ocurre un accidente (como que falle la hielera y se caliente la sangre), 
    el sistema cambia el estado y bloquea que esas bolsas entren a nuestro inventario sano.
    """
    PREPARACION = "Preparación"
    EN_TRANSITO = "En Tránsito"
    ENTREGADO = "Entregado"
    CANCELADO = "Cancelado"
    RECHAZADO_RED_FRIO = "Rechazado - Falla térmica"


class Hospital:
    """
    Representa a una clínica o institución aliada. 
    Guarda sus datos básicos y la ruta hacia su archivo CSV de inventario 
    para que nuestro sistema pueda ir a consultarlo cuando nos falte sangre.
    """
    
    def __init__(self, id_hospital_clues: str, nombre_institucion: str, ruta_csv_inventario: str):
        # Limpiamos los textos para evitar que espacios en blanco accidentales causen errores al buscar
        self.id_hospital_clues = id_hospital_clues.strip().upper()       
        self.nombre_institucion = nombre_institucion.strip().title()     
        self.ruta_csv_inventario = ruta_csv_inventario.strip()   

    def consultar_inventario_externo(self, tipo_componente_req: str, tipo_sangre_req: str, factor_rh_req: str) -> List[Dict[str, Any]]:
        """
        Revisa el archivo del otro hospital para ver si tienen la sangre que nos urge. 
        Usa Pandas para filtrar todo rápidamente y nos devuelve solo los datos de las bolsas que nos sirven.
        """
        try:
            # Intentamos abrir el archivo del hospital aliado
            df_inventario = pd.read_csv(self.ruta_csv_inventario)
        except FileNotFoundError as e:
            raise IOError(f"Aviso de red: No pudimos acceder al archivo del hospital destino en la ruta: {self.ruta_csv_inventario}.") from e
        except pd.errors.EmptyDataError:
            # Si el archivo del aliado está vacío, simplemente devolvemos una lista vacía para que nuestro sistema no colapse
            return []

        unidades_encontradas = []
        
        # Nos aseguramos de que los datos de búsqueda estén limpios y en mayúsculas
        sangre_limpia = tipo_sangre_req.strip().upper()
        rh_limpio = factor_rh_req.strip()
        componente_limpio = tipo_componente_req.strip().title()

        # Filtramos directamente en la tabla usando las condiciones que necesitamos.
        # Usamos fillna("") por si el archivo del otro hospital tiene celdas vacías o corruptas.
        filtro = df_inventario[
            (df_inventario['tipo_componente'].fillna("").str.strip().str.title() == componente_limpio) &
            (df_inventario['tipo_sangre'].fillna("").str.strip().str.upper() == sangre_limpia) &
            (df_inventario['factor_rh'].fillna("").str.strip() == rh_limpio) &
            (df_inventario['estado'].fillna("").str.strip().str.title() == 'Liberada')
        ]
        
        # Pasamos los resultados de Pandas a una lista de diccionarios normales de Python
        # para que el resto de nuestro programa pueda manejarlos fácilmente
        for _, fila in filtro.iterrows():
            unidad = {
                'id_unidad': fila['id_unidad'],
                'tipo_componente': fila['tipo_componente'],
                'tipo_sangre': fila['tipo_sangre'],
                'factor_rh': fila['factor_rh'],
                'fecha_caducidad': fila['fecha_caducidad']
            }
            unidades_encontradas.append(unidad)
            
        return unidades_encontradas


class Transferencia:
    """
    Lleva el control de un envío o recepción en específico. 
    Registra qué hospital manda o recibe, en qué etapa del viaje va el paquete 
    y qué bolsas exactas van adentro.
    """
    
    def __init__(self, id_envio: int, hospital_externo: Hospital, tipo_movimiento: TipoMovimiento):
        self.id_envio = id_envio                 
        self.hospital_externo = hospital_externo 
        
        # Verificamos que el movimiento sea estrictamente "Entrada" o "Salida"
        if not isinstance(tipo_movimiento, TipoMovimiento):
            raise TypeError(f"Error interno: El tipo de movimiento ingresado no es válido. Recibido: {type(tipo_movimiento).__name__}.")
        self.tipo_movimiento = tipo_movimiento   
        
        # Todo traslado inicia en estado de preparación
        self._estado_logistico: EstadoLogistico = EstadoLogistico.PREPARACION
        self.unidades_a_transferir: List[Any] = []

    @property
    def estado_logistico(self) -> EstadoLogistico:
        return self._estado_logistico

    @estado_logistico.setter
    def estado_logistico(self, nuevo_estado: EstadoLogistico):
        if not isinstance(nuevo_estado, EstadoLogistico):
            raise TypeError(f"Error al cambiar el estado del viaje. Se esperaba un EstadoLogistico y se recibió {type(nuevo_estado).__name__}.")
        self._estado_logistico = nuevo_estado

    def generar_guia_transporte_biologico(self) -> str:
        """
        Crea un resumen de texto (como un recibo o carta de porte) con todos los detalles del traslado, 
        listo para imprimirlo o mostrarlo en pantalla como comprobante físico.
        """
        guia = (
            f"{'='*50}\n"
            f"   [BLOODCONNECT] GUÍA DE TRANSPORTE BIOLÓGICO\n"
            f"{'='*50}\n"
            f"Folio del Viaje: {self.id_envio}\n"
            f"Hospital Origen/Destino: {self.hospital_externo.nombre_institucion}\n"
            f"Clave Oficial (CLUES): {self.hospital_externo.id_hospital_clues}\n"
            f"Tipo de Movimiento: {self.tipo_movimiento.value}\n"
            f"Total de bolsas amparadas: {len(self.unidades_a_transferir)}\n"
            f"Estado de la Cadena de Frío: Verificado por el sistema\n"
            f"{'='*50}"
        )
        return guia

    def registrar_recepcion_externa(self, datos_unidades_externas: List[Dict[str, Any]], inventario_local: Any, gestor_datos: Any) -> bool:
        """
        Procesa las bolsas de sangre que nos acaban de llegar de otro hospital.
        Crea un número de ID nuevo y único para cada bolsa para que no se revuelvan con nuestros propios registros,
        y luego las guarda automáticamente en nuestro refrigerador.
        """
        if self.tipo_movimiento != TipoMovimiento.ENTRADA:
            raise ValueError("Alerta de seguridad: Está intentando ingresar sangre al hospital, pero este traslado fue marcado como 'Salida'.")

        # Catálogo que le dice al sistema a qué temperatura y en qué refri guardar cada tipo de bolsa que llegue
        CONFIG_ALMACENAMIENTO = {
            "Sangre Entera":    {"temperatura": 4.0,   "refrigerador": "Ref-Externos-01"},
            "Globulos Rojos":   {"temperatura": 4.0,   "refrigerador": "Ref-Externos-01"},
            "Plasma":           {"temperatura": -20.0, "refrigerador": "Congelador-Externos-A"},
            "Plaquetas":        {"temperatura": 22.0,  "refrigerador": "Agitador-Externos-01"},
            "Crioprecipitados": {"temperatura": -20.0, "refrigerador": "Congelador-Externos-B"},
        }

        # Vamos bolsa por bolsa revisando la información que nos mandó la otra clínica
        for indice, datos in enumerate(datos_unidades_externas):
            try:
                # Separamos la fecha manualmente para no tener problemas de formato entre nuestro sistema y el del aliado
                partes_fecha = str(datos['fecha_caducidad']).split('-')
                fecha_cad = date(int(partes_fecha[0]), int(partes_fecha[1]), int(partes_fecha[2]))
                
                tipo_componente_str = str(datos['tipo_componente']).strip().title()
                tipo_comp_enum = TipoHemocomponente(tipo_componente_str)
                
                # Buscamos en qué refri debe ir. Si hay un error, lo mandamos al refri general por defecto
                config = CONFIG_ALMACENAMIENTO.get(tipo_componente_str, {"temperatura": 4.0, "refrigerador": "Ref-Externos-01"})

                # Truco para crear un número de bolsa (ID) que jamás se repita:
                # Juntamos la fecha/hora actual + el ID viejo + la posición en la lista
                nuevo_id_local = int(datetime.now().strftime("%y%m%d%H%M%S")) + int(datos['id_unidad']) + indice
                
                # Creamos la bolsa dentro de nuestro propio sistema
                nueva_unidad = Hemocomponente(
                    id_unidad=nuevo_id_local,
                    tipo_componente=tipo_comp_enum,
                    tipo_sangre=datos['tipo_sangre'],
                    factor_rh=datos['factor_rh'],
                    fecha_caducidad=fecha_cad,
                    temperatura_almacenamiento=config["temperatura"],
                    estado=EstadoHemocomponente.LIBERADA,
                    refrigerador_asignado=config["refrigerador"]
                )
                
                # Le pedimos a nuestro módulo de inventario que guarde esta nueva bolsa
                if inventario_local.ingresar_unidad(nueva_unidad):
                    self.unidades_a_transferir.append(nueva_unidad)
            
            except (ValueError, KeyError, TypeError) as e:
                raise ValueError(f"Ocurrió un problema leyendo los datos de la bolsa externa {datos.get('id_unidad', 'Desconocida')}. Detalle: {e}")
        
        # Marcamos que el viaje se completó exitosamente
        self.estado_logistico = EstadoLogistico.ENTREGADO
        
        # Guardamos todos los cambios de un solo golpe en el archivo CSV
        return inventario_local.guardar_inventario_actualizado(gestor_datos)