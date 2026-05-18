"""
Módulo de Gestión de Agendamiento - BloodConnect
Este archivo se encarga de administrar los turnos del laboratorio. Su propósito principal 
es evitar que se agenden más donantes de los que podemos atender (controlando las camillas disponibles) 
y asegurarse de que los donantes cumplan con las reglas médicas antes de confirmarles una cita.
"""

from enum import Enum
from datetime import datetime
from typing import Any
import pandas as pd


class EstadoCita(Enum):
    """
    Define los estados exactos por los que puede pasar una cita. 
    Esto nos ayuda a llevar un control estricto en el sistema y evita que se guarden 
    estados inválidos o inventados accidentalmente.
    """
    PROGRAMADA = "Programada"
    COMPLETADA = "Completada"
    CANCELADA = "Cancelada"
    AUSENTE = "Ausente"


class Cita:
    """
    Representa un espacio reservado en el laboratorio.
    Antes de permitir que la cita se guarde, esta clase realiza validaciones 
    para comprobar que haya espacio físico y que el donante esté sano.
    """
    
    def __init__(self, id_cita: int, id_donante: int, fecha: str, hora: str, estado: EstadoCita):
        self.id_cita = id_cita
        self.id_donante = id_donante
        self.fecha = fecha.strip()
        self.hora = hora.strip()
        
        # Validación de seguridad para que el estado pertenezca obligatoriamente a nuestras opciones válidas
        if not isinstance(estado, EstadoCita):
            raise TypeError("Error de Integridad: El estado de la cita debe ser estrictamente uno de los permitidos en EstadoCita.")
        self.estado = estado

    @staticmethod
    def validar_disponibilidad_horario(gestor_datos: Any, fecha: str, hora: str, limite_camillas: int = 3) -> bool:
        """
        Revisa cuántas camillas están ocupadas en una fecha y hora específicas. 
        Si ya llegamos al límite de capacidad, detiene el proceso para evitar saturar el laboratorio.
        
        Parámetros:
            gestor_datos: Conexión a nuestros archivos de datos.
            fecha: Día que el donante quiere agendar.
            hora: Bloque de tiempo solicitado.
            limite_camillas: Cantidad de sillones de extracción físicos en el lugar.
            
        Retorna:
            bool: True si hay espacio libre.
        """
        # Leemos todas las citas guardadas
        df_citas = gestor_datos.leer_persistencias("citas")
        
        # Si el archivo todavía no existe o está vacío, significa que el horario está completamente libre
        if df_citas is None or df_citas.empty:
            return True
            
        # Revisamos que el archivo tenga la estructura correcta para no causar un error al buscar
        if not all(columna in df_citas.columns for columna in ['fecha', 'hora', 'estado']):
            return True

        # Limpiamos los textos para evitar que espacios en blanco nos den resultados engañosos
        fecha_limpia = fecha.strip()
        hora_limpia = hora.strip()

        # Filtramos rápido usando Pandas para ver cuántas citas están "Programadas" en esa misma hora y día
        ocupacion_actual = df_citas[
            (df_citas['fecha'].astype(str).str.strip() == fecha_limpia) &
            (df_citas['hora'].astype(str).str.strip() == hora_limpia) &
            (df_citas['estado'].astype(str).str.strip().str.title() == EstadoCita.PROGRAMADA.value)
        ]
        
        # Si la cantidad de citas encontradas es igual o mayor a nuestras camillas, rechazamos la solicitud
        if len(ocupacion_actual) >= limite_camillas:
            raise ValueError(f"Agenda llena: Se agotó el límite máximo ({limite_camillas} camillas) para el horario de las {hora_limpia}.")
            
        return True

    @staticmethod
    def validar_elegibilidad_donante(donante: Any) -> bool:
        """
        Paso de seguridad previo a agendar. Confirma que el donante haya cumplido 
        sus 56 días de recuperación obligatoria para proteger su salud.
        """
        if not donante:
            raise ValueError("Error del sistema: No se encontró el expediente del donante para verificar su estado de salud.")
        
        # Utilizamos la validación médica que ya existe dentro del perfil del donante
        try:
            donante.verificar_intervalo()
        except ValueError as ve:
            raise ValueError(f"No se puede agendar la cita por protocolo médico: {ve}")
            
        return True

    def registrar_cita(self, gestor_datos: Any) -> bool:
        """
        Guarda la cita en nuestro archivo de datos. 
        Si la cita ya existía, actualiza su información; si es nueva, la agrega a la lista. 
        También prepara el archivo si es la primera vez que se usa el sistema.
        """
        df_citas = gestor_datos.leer_persistencias("citas")
        
        # Preparamos la información de la cita en formato de diccionario para Pandas
        nuevo_registro = {
            'id_cita': self.id_cita,
            'id_donante': self.id_donante,
            'fecha': self.fecha,
            'hora': self.hora,
            'estado': self.estado.value
        }
        
        # Caso 1: El archivo de citas ya existe y tiene datos
        if df_citas is not None and not df_citas.empty and 'id_cita' in df_citas.columns:
            
            # Revisamos si este número de cita ya estaba registrado
            if self.id_cita in df_citas['id_cita'].values:
                # Actualizamos la fila que corresponde a esta cita específica
                mascara = df_citas['id_cita'] == self.id_cita
                df_citas.loc[mascara, 'id_donante'] = self.id_donante
                df_citas.loc[mascara, 'fecha'] = self.fecha
                df_citas.loc[mascara, 'hora'] = self.hora
                df_citas.loc[mascara, 'estado'] = self.estado.value
            else:
                # Como no existe, la añadimos al final del archivo
                df_nuevo = pd.DataFrame([nuevo_registro])
                df_citas = pd.concat([df_citas, df_nuevo], ignore_index=True)
                
        else:
            # Caso 2: Es la primera cita que se agenda en el sistema, creamos el formato desde cero
            df_citas = pd.DataFrame([nuevo_registro])
            
        # Le pedimos al gestor que guarde todos los cambios de forma segura en el CSV
        return gestor_datos.guardar_cambios_atomicos("citas", df_citas)
