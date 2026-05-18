"""
Módulo de Gestión Clínica - BloodConnect
Este archivo es el motor médico del sistema. Aquí se calculan las compatibilidades 
sanguíneas, se aplica la regla de usar primero la sangre más vieja (FIFO) y 
se controla el último filtro de seguridad antes de conectarle la bolsa al paciente.
"""

from enum import Enum
from typing import List, Any, Dict, Set, Optional
from operator import attrgetter
from datetime import datetime
import pandas as pd
from .gestion_almacen import EstadoHemocomponente


class NivelTriage(Enum):
    """Categorías para identificar qué tan urgente es la necesidad de sangre del paciente."""
    ROJO = 1
    AMARILLO = 2
    VERDE = 3


class TipoComponente(Enum):
    """Lista exacta de los productos sanguíneos que nuestro sistema sabe manejar."""
    GLOBULOS_ROJOS = "Globulos Rojos" 
    PLASMA = "Plasma"
    SANGRE_ENTERA = "Sangre Entera"
    PLAQUETAS = "Plaquetas"
    CRIOPRECIPITADOS = "Crioprecipitados"


class EstadoTransfusion(Enum):
    """
    Controla en qué parte del proceso va una transfusión. 
    Nos ayuda a saber si se completó con éxito o si se canceló de emergencia en el último momento.
    """
    EN_PROGRESO = "En progreso"
    COMPLETADA = "Completada"
    CANCELADA_CORRESPONDENCIA = "Cancelada por error de correspondencia"
    CANCELADA_PROTOCOLO = "Cancelada por protocolo de seguridad"
    ERROR_REGISTRO = "Error de registro"


class SolicitudMedica:
    """
    Representa la receta o petición que hace el doctor. 
    Asegura que los datos solicitados (tipo de sangre, urgencia, cantidad) 
    vengan en el formato correcto antes de buscar en el refrigerador.
    """
    
    def __init__(self, id_solicitud: int, prioridad_triage: NivelTriage, tipo_componente_requerido: str, unidades_requeridas: int, id_paciente: int):
        self.id_solicitud = id_solicitud
        self.prioridad_triage = prioridad_triage
        # Limpiamos el texto para que mayúsculas o espacios extra no arruinen la búsqueda
        self.tipo_componente_requerido = tipo_componente_requerido.strip().title()
        self.unidades_requeridas = unidades_requeridas
        self.id_paciente = id_paciente
        # Guardamos el número de urgencia para facilitar cálculos posteriores
        self.nivel_urgencia = self.prioridad_triage.value 

    def clasificar_prioridad(self) -> str:
        """
        Revisa el nivel de urgencia y genera un aviso claro para la bitácora del sistema.
        """
        if self.prioridad_triage == NivelTriage.ROJO:
            return f"Alerta de Sistema: La solicitud {self.id_solicitud} es Código Rojo. Requiere atención inmediata."
        elif self.prioridad_triage == NivelTriage.AMARILLO:
            return f"Aviso: La solicitud {self.id_solicitud} es Código Amarillo. Prioridad media."
        elif self.prioridad_triage == NivelTriage.VERDE:
            return f"Info: La solicitud {self.id_solicitud} es Código Verde. Operación de rutina."
        return "Aviso: Nivel de prioridad no definido correctamente."

    def validar_stock_emergencia(self, inventario_disponible: List[Any]) -> bool:
        """
        En caso de Código Rojo, esta función revisa rápidamente todo el inventario 
        para confirmar si tenemos suficiente sangre de 'Donante Universal' para salvar al paciente.
        """
        if self.prioridad_triage == NivelTriage.ROJO: 
            # Regla médica: El donante universal para plasma es AB, pero para glóbulos rojos es O negativo.
            if self.tipo_componente_requerido in [TipoComponente.PLASMA.value, TipoComponente.CRIOPRECIPITADOS.value]:
                sangre_univ, rh_univ = "AB", "" 
            else:
                sangre_univ, rh_univ = "O", "-" 

            # Hacemos un conteo rápido recorriendo las bolsas disponibles
            contador_universal = sum(
                1 for unidad in inventario_disponible 
                if getattr(unidad, 'tipo_sangre', '').strip().upper() == sangre_univ 
                and (rh_univ == "" or getattr(unidad, 'factor_rh', '').strip() == rh_univ)
                and getattr(unidad, 'tipo_componente').value == self.tipo_componente_requerido 
                and getattr(unidad, 'estado').value.strip().title() == "Liberada"
            )
            return contador_universal >= self.unidades_requeridas
        
        return False


class MotorCompatibilidad:
    """
    Es el 'cerebro' que sabe quién le puede donar a quién.
    Utiliza diccionarios de Python (tablas Hash) para encontrar las sangres compatibles 
    de forma instantánea (complejidad O(1)), sin importar qué tan grande sea el inventario.
    """
    
    def __init__(self):
        # Mapa de compatibilidad para glóbulos rojos y sangre entera.
        # Funciona así -> Sangre del Paciente: {Sangres que puede recibir}
        self.matriz_rojos: Dict[str, Set[str]] = {
            'O-': {'O-'},
            'O+': {'O-', 'O+'},
            'A-': {'O-', 'A-'},
            'A+': {'O-', 'O+', 'A-', 'A+'},
            'B-': {'O-', 'B-'},
            'B+': {'O-', 'O+', 'B-', 'B+'},
            'AB-': {'O-', 'A-', 'B-', 'AB-'},
            'AB+': {'O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'}
        }
        
        # Mapa de compatibilidad para el Plasma (Las reglas son distintas porque no tiene antígenos RH)
        self.matriz_plasma: Dict[str, Set[str]] = {
            'O': {'O', 'A', 'B', 'AB'},
            'A': {'A', 'AB'},
            'B': {'B', 'AB'},
            'AB': {'AB'}
        }

    def ejecutar_smart_matching(self, tipo_sangre_paciente: str, factor_rh_paciente: str, tipo_componente: TipoComponente, inventario_disponible: List[Any]) -> List[Any]:
        """
        Revisa el refrigerador y separa únicamente las bolsas que son seguras 
        para el tipo de sangre específico del paciente.
        """
        unidades_utilizables = []
        sangre_limpia = tipo_sangre_paciente.strip().upper()
        rh_limpio = factor_rh_paciente.strip()
        
        # Elegimos qué reglas aplicar dependiendo del producto solicitado
        if tipo_componente in [TipoComponente.PLASMA, TipoComponente.CRIOPRECIPITADOS]:
            matriz_activa = self.matriz_plasma
            llave_busqueda = sangre_limpia
        else:
            matriz_activa = self.matriz_rojos
            llave_busqueda = f"{sangre_limpia}{rh_limpio}"

        # Comprobamos que el tipo de sangre ingresado realmente exista en nuestras tablas
        if llave_busqueda not in matriz_activa:
            raise ValueError(f"Error Médico: El grupo sanguíneo '{llave_busqueda}' no se reconoce en nuestro protocolo.")
            
        tipos_compatibles = matriz_activa[llave_busqueda]
        
        # Recorremos el almacén buscando las bolsas que hagan 'match'
        for unidad in inventario_disponible:
            if getattr(unidad, 'tipo_componente').value != tipo_componente.value:
                continue

            estado_unidad = getattr(unidad, 'estado').value.strip().title()
            
            # Solo tomamos en cuenta las bolsas que el laboratorio ya aprobó ("Liberadas")
            if estado_unidad == "Liberada":
                tipo_u = getattr(unidad, 'tipo_sangre', '').strip().upper()
                rh_u = getattr(unidad, 'factor_rh', '').strip()
                
                sangre_bolsa = tipo_u if tipo_componente in [TipoComponente.PLASMA, TipoComponente.CRIOPRECIPITADOS] else f"{tipo_u}{rh_u}"
                
                # Búsqueda instantánea gracias al Set de Python
                if sangre_bolsa in tipos_compatibles:
                    unidades_utilizables.append(unidad)
                
        return unidades_utilizables

    def aplicar_logica_fifo(self, unidades_compatibles: List[Any]) -> List[Any]:
        """
        Ordena las bolsas compatibles usando el principio FIFO (First-In, First-Out).
        Pone de primeras las bolsas que están más próximas a caducar para evitar desperdicio de sangre.
        """
        try:
            return sorted(unidades_compatibles, key=attrgetter('fecha_caducidad'))
        except AttributeError as e:
            raise AttributeError("Error de sistema: Se intentó ordenar bolsas que no tienen registrada una fecha de caducidad.") from e


class Transfusion:
    """
    Representa el evento final a pie de cama. 
    Guarda los datos exactos de qué bolsa se le conectó a qué paciente y quién fue el médico responsable.
    """
    
    def __init__(self, id_transfusion: int, id_unidad: int, id_paciente: int, id_personal_medico: int, reacciones_adversas: Optional[str], timestamp_inicio: datetime):
        self.id_transfusion = id_transfusion
        self.id_unidad = id_unidad
        self.id_paciente = id_paciente
        self.id_personal_medico = id_personal_medico
        
        # Aseguramos que el reporte de reacciones quede limpio y en un formato estándar
        if reacciones_adversas and reacciones_adversas.strip():
            self.reacciones_adversas = reacciones_adversas.strip().capitalize()
        else:
            self.reacciones_adversas = "Ninguna"
            
        self.timestamp_inicio = timestamp_inicio
        # Al crearse, la transfusión arranca en progreso
        self._estado_transfusion: EstadoTransfusion = EstadoTransfusion.EN_PROGRESO

    @property
    def estado_transfusion(self) -> EstadoTransfusion:
        return self._estado_transfusion

    @estado_transfusion.setter
    def estado_transfusion(self, nuevo_estado: EstadoTransfusion):
        if not isinstance(nuevo_estado, EstadoTransfusion):
            raise TypeError(f"Error interno: El estado de transfusión no es válido. Recibido: '{type(nuevo_estado).__name__}'.")
        self._estado_transfusion = nuevo_estado
        
    def registrar_transfusion(self, gestor_datos: Any) -> bool:
        """
        Guarda el historial de la transfusión verificando antes que 
        el paciente y la bolsa de sangre de verdad existan en los registros.
        """
        # Filtros de seguridad cruzada con otros archivos
        if not gestor_datos.existe_id_en_archivo("pacientes", "id_paciente", self.id_paciente):
            raise ValueError(f"Error de Integridad: El paciente con ID {self.id_paciente} no está registrado en el hospital.")

        if not gestor_datos.existe_id_en_archivo("inventario", "id_unidad", self.id_unidad):
            raise ValueError(f"Error de Integridad: La bolsa de sangre {self.id_unidad} no se encuentra en el inventario.")

        df_transfusiones = gestor_datos.leer_persistencias("transfusiones")

        if df_transfusiones is None:
            raise IOError(f"Aviso del sistema: No pudimos acceder al archivo de transfusiones para guardar la operación {self.id_transfusion}.")

        fecha_str = self.timestamp_inicio.strftime("%Y-%m-%d %H:%M:%S") if isinstance(self.timestamp_inicio, datetime) else str(self.timestamp_inicio)

        # Preparamos los datos
        nuevo_registro = {
            'id_transfusion': self.id_transfusion,
            'id_unidad': self.id_unidad,
            'id_paciente': self.id_paciente,
            'id_personal_medico': self.id_personal_medico,
            'reacciones_adversas': self.reacciones_adversas,
            'timestamp_inicio': fecha_str,
            'estado_transfusion': self.estado_transfusion.value 
        }
        
        # Los agregamos al final de la tabla y guardamos
        df_nuevo = pd.DataFrame([nuevo_registro])
        df_transfusiones = pd.concat([df_transfusiones, df_nuevo], ignore_index=True)
        gestor_datos.guardar_cambios_atomicos("transfusiones", df_transfusiones)
        
        return True

    def registrar_evento_vena_a_vena(self, paciente_objetivo: Any, unidad_fisica: Any) -> bool:
        """
        El filtro más crítico. Justo antes de abrir la llave de la sangre, comprueba 
        que la bolsa que el enfermero tiene en la mano sea exactamente la misma 
        que el sistema autorizó para ese paciente.
        """
        id_unidad_fisica = getattr(unidad_fisica, 'id_unidad', None)
        id_paciente_objetivo = getattr(paciente_objetivo, 'id_paciente', None)
        
        # Verificamos que sea la bolsa correcta
        if self.id_unidad != id_unidad_fisica:
            self.estado_transfusion = EstadoTransfusion.CANCELADA_CORRESPONDENCIA
            return False

        # Verificamos que sea el paciente correcto
        if self.id_paciente == id_paciente_objetivo:
            try:
                # Si todo coincide, actualizamos el expediente del paciente y tachamos la bolsa del inventario
                if paciente_objetivo.actualizar_historial_transfusional(self.id_unidad):
                    self.estado_transfusion = EstadoTransfusion.COMPLETADA
                    unidad_fisica.estado = EstadoHemocomponente.TRANSFUNDIDA 
                    return True
            except ValueError:
                self.estado_transfusion = EstadoTransfusion.ERROR_REGISTRO
                return False
        else:
            self.estado_transfusion = EstadoTransfusion.CANCELADA_PROTOCOLO
            return False

    def bloquear_donante_por_reaccion(self, donante_origen: Any) -> bool:
        """
        Si el paciente presentó fiebre o alergias al recibir la sangre, 
        esta función bloquea de inmediato al donante para que no vuelva a dar sangre 
        hasta que sea evaluado por un médico.
        """
        if self.reacciones_adversas != "Ninguna":
            donante_origen.estado_elegibilidad = False
            return True
            
        return False