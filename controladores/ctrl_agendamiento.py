"""
Módulo del Controlador de Agendamiento - BloodConnect
Este archivo se encarga de organizar la agenda del laboratorio. Su función principal 
es evitar que se saturen los sillones de extracción (control de aforo) y asegurar 
que los donantes cumplen con sus tiempos de recuperación antes de confirmarles un turno.
"""

from typing import Tuple, List, Dict, Optional, Any
from datetime import datetime, date
import pandas as pd

# Importaciones de modelos de dominio
from clases.gestion_agendamiento import Cita, EstadoCita
from clases.gestion_identidades import Donante, Trabajador
from clases.auditoria import GestorDatos, Bitacora, EntidadAfectada, NivelSeveridad

class CtrlAgendamiento:
    def __init__(self, gestor: GestorDatos):
        self.gestor = gestor
        # Almacena la sesión de quien está usando el sistema para saber quién agenda o cancela
        self.usuario_actual: Optional[Trabajador] = None

    def _registrar_auditoria(self, entidad: EntidadAfectada, accion: str, severidad: NivelSeveridad):
        """Anota los movimientos importantes de la agenda en el archivo de texto para tener un historial seguro."""
        try:
            id_usuario = self.usuario_actual.id_global if self.usuario_actual else 0
            id_log = int(datetime.now().strftime("%y%m%d%H%M%S")) 
            
            registro = Bitacora(id_log, id_usuario, entidad, accion, severidad)
            registro.escribir_entrada_inmutable(self.gestor.ruta_log)
        except Exception as e:
            # Mensaje en consola si falla el registro silencioso
            print(f"Aviso del sistema: No se pudo guardar el registro de agenda en la bitácora. Detalle: {e}")

    def _validar_fecha(self, fecha_str: str) -> bool:
        """Verifica que la fecha introducida tenga exactamente el formato Año-Mes-Día (YYYY-MM-DD)."""
        try:
            datetime.strptime(fecha_str.strip(), "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def obtener_horarios_disponibles(self, fecha: str) -> Tuple[bool, List[str]]:
        """
        Revisa cuántas citas ya están programadas en un día específico y 
        devuelve únicamente los horarios donde todavía hay camillas libres.
        """
        if not fecha or not fecha.strip():
            return False, []
            
        if not self._validar_fecha(fecha):
            return False, ["Formato de fecha inválido. Use YYYY-MM-DD."]

        # Catálogo de los horarios de atención del laboratorio
        bloques_estandar = ["08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00"]
        fecha_limpia = fecha.strip()
        horarios_disponibles = []

        try:
            df_citas = self.gestor.leer_persistencias("citas")
            
            # Si el archivo está vacío o no existe, todos los horarios están libres
            if df_citas is None or df_citas.empty or 'fecha' not in df_citas.columns:
                return True, bloques_estandar

            # Filtramos solo las citas activas de ese día
            citas_del_dia = df_citas[
                (df_citas['fecha'].astype(str).str.strip() == fecha_limpia) &
                (df_citas['estado'].astype(str).str.strip().str.title() == EstadoCita.PROGRAMADA.value)
            ]

            # Contamos cuántas personas hay agendadas por cada hora
            conteo_ocupacion = citas_del_dia['hora'].astype(str).str.strip().value_counts().to_dict()
            limite_camillas = 3
            
            # Construimos la lista de horarios que aún tienen lugar
            for bloque in bloques_estandar:
                camillas_ocupadas = conteo_ocupacion.get(bloque, 0)
                if camillas_ocupadas < limite_camillas:
                    horarios_disponibles.append(bloque)

            return True, horarios_disponibles

        except Exception as e:
            self._registrar_auditoria(EntidadAfectada.SISTEMA, f"Problema al calcular los espacios libres para el {fecha_limpia}: {e}", NivelSeveridad.ADVERTENCIA)
            return False, []

    def agendar_cita_donante(self, id_donante: Any, fecha: str, hora: str) -> Tuple[bool, str]:
        """
        Función principal para separar un lugar. 
        Revisa la salud del donante y el espacio físico antes de guardar la cita.
        """
        if not id_donante or not fecha or not hora:
            return False, "Datos incompletos: Se requiere el donante, la fecha y la hora."

        if not self._validar_fecha(fecha):
            return False, "El formato de la fecha es incorrecto. Debe ser YYYY-MM-DD."

        try:
            id_d_int = int(id_donante)
            fecha_limpia = fecha.strip()
            hora_limpia = hora.strip()
        except (ValueError, TypeError):
            return False, "Error: El identificador del donante debe ser un número."

        try:
            donante = Donante.cargar_desde_csv(id_d_int, self.gestor)
            if not donante:
                return False, f"No encontramos a ningún donante registrado con el número {id_d_int}."
            
            # --- Reglas del negocio antes de agendar ---
            # 1. ¿El donante ya descansó sus 56 días desde su última donación?
            Cita.validar_elegibilidad_donante(donante)
            # 2. ¿Hay camillas libres en ese horario?
            Cita.validar_disponibilidad_horario(self.gestor, fecha_limpia, hora_limpia, limite_camillas=3)
            # ------------------------------------------

            # Si pasa las pruebas, creamos y guardamos la cita
            id_nueva_cita = int(datetime.now().strftime("%y%m%d%H%M%S"))
            nueva_cita = Cita(
                id_cita=id_nueva_cita,
                id_donante=id_d_int,
                fecha=fecha_limpia,
                hora=hora_limpia,
                estado=EstadoCita.PROGRAMADA
            )

            nueva_cita.registrar_cita(self.gestor)

            self._registrar_auditoria(EntidadAfectada.DONANTE, f"Se agendó un turno (Folio: {id_nueva_cita}) para el {fecha_limpia} a las {hora_limpia}.", NivelSeveridad.INFO)
            return True, f"¡Cita programada con éxito!\nFolio: {id_nueva_cita}\nDonante: {donante.nombre}\nFecha y hora: {fecha_limpia} a las {hora_limpia} hrs."

        except ValueError as ve:
            return False, f"No se pudo agendar: {ve}"
        except IOError as ioe:
            return False, f"Problema técnico al guardar la cita en el archivo: {ioe}"
        except Exception as e:
            return False, f"Ocurrió un error inesperado al procesar la cita: {e}"

    def sincronizar_cita_inteligente_controller(self, id_donante: Any, fecha_hoy: str, nuevo_estado_str: str):
        """
        Busca si el donante tiene una cita programada para hoy y actualiza su estado automáticamente 
        (por ejemplo, cuando llega al laboratorio y comienza su proceso).
        """
        try:
            df_citas = self.gestor.leer_persistencias("citas")
            if df_citas is not None and not df_citas.empty:
                fecha_limpia = fecha_hoy.strip()
                df_citas['id_donante_limpio'] = pd.to_numeric(df_citas['id_donante'], errors='coerce').fillna(0).astype(int).astype(str)
                id_buscar = str(int(float(id_donante))) 
                
                filtro = df_citas[
                    (df_citas['id_donante_limpio'] == id_buscar) &
                    (df_citas['fecha'].astype(str).str.strip() == fecha_limpia) &
                    (df_citas['estado'].astype(str).str.strip().str.title() == "Programada")
                ]
                
                # Si encontramos su cita activa del día, la actualizamos
                if not filtro.empty:
                    id_cita = int(filtro.iloc[0]['id_cita'])
                    self.actualizar_estado_cita(id_cita, nuevo_estado_str)
        except Exception as e:
            print(f"Aviso del sistema: Hubo un problema al intentar sincronizar el estado de la cita: {e}")
        
    def obtener_id_donante_por_cita(self, id_cita: Any) -> Optional[int]:
        """A partir del número de folio de la cita, averigua a qué donante le pertenece."""
        try:
            df_citas = self.gestor.leer_persistencias("citas")
            if df_citas is not None and not df_citas.empty and 'id_cita' in df_citas.columns:
                mascara = df_citas['id_cita'].astype(str) == str(id_cita).strip()
                if mascara.any():
                    return int(df_citas.loc[mascara, 'id_donante'].iloc[0])
        except Exception as e:
            print(f"Aviso del sistema: Error al buscar los datos del donante usando el folio de la cita: {e}")
        return None        

    def actualizar_estado_cita(self, id_cita: Any, nuevo_estado_str: str) -> Tuple[bool, str]:
        """
        Cambia la situación de una cita. Se usa para marcarla como 'Completada' cuando terminan, 
        o como 'Cancelada'/'Ausente' si la persona no se presentó.
        """
        if not self.usuario_actual:
            return False, "Permiso denegado: Inicie sesión para modificar citas."

        try:
            id_c_int = int(id_cita)
            estado_enum = EstadoCita(nuevo_estado_str.strip().title())
        except ValueError:
            return False, f"Aviso: El estado '{nuevo_estado_str}' no es válido o el folio tiene un error."

        try:
            df_citas = self.gestor.leer_persistencias("citas")
            if df_citas is None or df_citas.empty or 'id_cita' not in df_citas.columns:
                return False, "No hay registro de citas en el sistema."

            mascara = df_citas['id_cita'] == id_c_int
            if not mascara.any():
                return False, f"No existe ninguna cita con el número de folio {id_c_int}."

            df_citas.loc[mascara, 'estado'] = estado_enum.value
            self.gestor.guardar_cambios_atomicos("citas", df_citas)

            self._registrar_auditoria(EntidadAfectada.DONANTE, f"La cita {id_c_int} ahora aparece como: {estado_enum.value}", NivelSeveridad.INFO)
            return True, f"Cita actualizada. Nuevo estado: {estado_enum.value}."

        except Exception as e:
            return False, f"Ocurrió un error al guardar los cambios en la agenda: {e}"

    def obtener_agenda_del_dia(self, fecha: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Prepara y ordena todas las citas de un día específico para poder mostrarlas 
        claramente en la tabla de la interfaz visual.
        """
        if not fecha or not fecha.strip():
            fecha_busqueda = date.today().strftime("%Y-%m-%d")
        else:
            fecha_busqueda = fecha.strip()

        agenda_estructurada = []

        try:
            df_citas = self.gestor.leer_persistencias("citas")
            if df_citas is None or df_citas.empty or 'fecha' not in df_citas.columns:
                return []

            # Filtramos solo lo que corresponde al día solicitado
            citas_dia = df_citas[df_citas['fecha'].astype(str).str.strip() == fecha_busqueda]
            if citas_dia.empty:
                return []

            # Buscamos los nombres de los donantes para no mostrar solo sus IDs numéricos
            df_donantes = self.gestor.leer_persistencias("donantes")
            mapa_identidades = {}
            if df_donantes is not None and not df_donantes.empty and 'id_global' in df_donantes.columns:
                mapa_identidades = dict(zip(df_donantes['id_global'].dropna().astype(int), df_donantes['nombre'].dropna().astype(str)))

            # Ordenamos cronológicamente de la mañana a la tarde
            citas_ordenadas = citas_dia.sort_values(by='hora')

            for _, fila in citas_ordenadas.iterrows():
                id_donante = int(fila['id_donante'])
                nombre_real = mapa_identidades.get(id_donante, f"Donante Desconocido (ID: {id_donante})")

                # Empaquetamos la información lista para la tabla
                agenda_estructurada.append({
                    "Folio": int(fila['id_cita']),
                    "Donante": nombre_real,
                    "Hora": str(fila['hora']).strip(),
                    "Estado": str(fila['estado']).strip().title()
                })

            return agenda_estructurada

        except Exception as e:
            self._registrar_auditoria(EntidadAfectada.SISTEMA, f"Hubo un problema armando la lista de citas para el día {fecha_busqueda}: {e}", NivelSeveridad.ADVERTENCIA)
            return []