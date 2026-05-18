"""
Módulo del Controlador de Identidades - BloodConnect
Este archivo es el administrador del "censo" del hospital. Se encarga de dar de alta, 
modificar y organizar a todas las personas que interactúan con el sistema: 
los empleados (médicos/laboratoristas), los donantes de sangre y los pacientes internados.
"""

from typing import Tuple, List, Dict, Optional, Any
from datetime import datetime

# Importaciones de modelos de dominio
from clases.gestion_identidades import Donante, Trabajador, Paciente
from clases.auditoria import GestorDatos, Bitacora, EntidadAfectada, NivelSeveridad

class CtrlIdentidades:
    def __init__(self, gestor: GestorDatos):
        self.gestor = gestor
        # Guardamos quién inició sesión para registrar qué empleado hizo cada cambio en los expedientes
        self.usuario_actual: Optional[Trabajador] = None 

    def _registrar_auditoria(self, entidad: EntidadAfectada, accion: str, severidad: NivelSeveridad):
        """Anota silenciosamente en el historial cada vez que registramos o modificamos a una persona."""
        try:
            id_usuario = self.usuario_actual.id_global if self.usuario_actual else 0
            id_log = int(datetime.now().strftime("%y%m%d%H%M%S")) 
            
            registro = Bitacora(id_log, id_usuario, entidad, accion, severidad)
            registro.escribir_entrada_inmutable(self.gestor.ruta_log)
        except Exception as e:
            # Aviso en consola por si el archivo de historial está ocupado
            print(f"Aviso del sistema: No se pudo guardar el registro de la persona en la bitácora. Detalle: {e}")

    def _validar_formato_fecha(self, fecha_str: str) -> bool:
        """Se asegura de que todas las fechas de nacimiento se guarden con el mismo formato (Año-Mes-Día)."""
        try:
            datetime.strptime(fecha_str.strip(), "%Y-%m-%d")
            return True
        except ValueError:
            return False

    # --- GESTIÓN DE TRABAJADORES ---

    def registrar_nuevo_trabajador_ui(self, datos_trabajador: dict) -> Tuple[bool, str, int]:
        """
        Recibe los datos desde la pantalla para dar de alta a un nuevo empleado. 
        Le asigna un número de matrícula único automáticamente para evitar duplicados.
        """
        fecha_nac = datos_trabajador.get('fecha_nacimiento', '').strip()
        if not self._validar_formato_fecha(fecha_nac):
            return False, "Por favor, escriba la fecha de nacimiento en el formato YYYY-MM-DD.", 0

        # Creamos un número de identificación único basado en la fecha y hora actuales
        id_autogenerado = int(datetime.now().strftime("%y%m%d%H%M%S"))
        
        # Si por alguna casualidad extrema el ID ya existe, le sumamos 1 hasta encontrar uno libre
        while not self.gestor.es_id_global_unico(id_autogenerado):
            id_autogenerado += 1

        try:
            # Si no le asignaron contraseña en la pantalla, le ponemos una por defecto
            password_plana = datos_trabajador.pop('password_plana', 'BloodConnect2026')
            
            datos_limpios = {
                'id_global': id_autogenerado,
                'nombre': str(datos_trabajador.get('nombre', '')),
                'fecha_nacimiento': fecha_nac,
                'genero': str(datos_trabajador.get('genero', '')),
                'tipo_sangre': "N/A", # No es obligatorio saber el tipo de sangre de un trabajador
                'factor_rh': "",
                'cedula_profesional': str(datos_trabajador.get('cedula_profesional', '')),
                'rol': str(datos_trabajador.get('rol', 'Laboratorista')),
                'password_plana': password_plana
            }

            nuevo_trabajador = Trabajador(**datos_limpios)
            nuevo_trabajador.registrar_trabajador(self.gestor)
            
            self._registrar_auditoria(
                EntidadAfectada.TRABAJADOR,
                f"Nuevo empleado registrado: {nuevo_trabajador.nombre} ({nuevo_trabajador.rol}). Matrícula: {id_autogenerado}",
                NivelSeveridad.INFO
            )
            return True, f"¡Listo! El trabajador {nuevo_trabajador.nombre} fue registrado correctamente.", id_autogenerado

        except ValueError as ve:
            return False, f"Tuvimos un problema con los datos ingresados: {ve}", 0
        except Exception as e:
            return False, f"Ocurrió un error inesperado al guardar al empleado: {e}", 0

    def obtener_lista_trabajadores(self) -> List[dict]:
        """Prepara la lista de todos los empleados del hospital, pero oculta sus contraseñas por seguridad."""
        try:
            return Trabajador.obtener_todos_los_trabajadores(self.gestor)
        except Exception as e:
            self._registrar_auditoria(EntidadAfectada.SISTEMA, f"Problema al intentar leer la lista de trabajadores: {e}", NivelSeveridad.ADVERTENCIA)
            return []

    # --- GESTIÓN DE DONANTES ---

    def registrar_nuevo_donante_ui(self, datos_donante: dict) -> Tuple[bool, str, int]:
        """
        Abre el expediente de una persona que viene a donar sangre. 
        Revisa que sus datos básicos estén correctos antes de pasar a la revisión médica.
        """
        fecha_nac = datos_donante.get('fecha_nacimiento', '').strip()
        if not self._validar_formato_fecha(fecha_nac):
            return False, "La fecha de nacimiento es incorrecta. Use el formato YYYY-MM-DD.", 0

        # Generamos su número de expediente único
        id_autogenerado = int(datetime.now().strftime("%y%m%d%H%M%S"))
        while not self.gestor.es_id_global_unico(id_autogenerado):
            id_autogenerado += 1

        try:
            datos_donante['id_global'] = id_autogenerado
            
            # Si es un donante nuevo desde la pantalla, indicamos que nunca ha donado antes
            if 'ultima_donacion' not in datos_donante:
                datos_donante['ultima_donacion'] = None
            
            # Verificamos que el peso y la hemoglobina sean números válidos
            try:
                datos_donante['peso_kg'] = float(datos_donante.get('peso_kg', 0))
                datos_donante['hemoglobina'] = float(datos_donante.get('hemoglobina', 0))
            except ValueError:
                return False, "Aviso: El peso y la hemoglobina deben ingresarse solo con números.", 0

            estado_elegibilidad_externo = datos_donante.pop('estado_elegibilidad', None)
            nuevo_donante = Donante(**datos_donante)

            if estado_elegibilidad_externo is True:
                nuevo_donante.estado_elegibilidad = True

            nuevo_donante.registrar_donante(self.gestor)
            return True, f"¡Expediente creado! {nuevo_donante.nombre} ha sido registrado exitosamente.", id_autogenerado

        except Exception as e:
            return False, f"Tuvimos un problema al intentar guardar el expediente del donante: {e}", 0

    def evaluar_pretriaje_donante(self, id_donante: Any, respuestas_cuestionario: dict, signos_vitales: dict) -> Tuple[bool, str]:
        """
        Procesa el cuestionario médico y los signos vitales del donante (presión, frecuencia cardíaca).
        Decide si la persona está lo suficientemente sana para donar sangre hoy.
        """
        try:
            id_d_int = int(id_donante)
            donante = Donante.cargar_desde_csv(id_d_int, self.gestor)
            if not donante:
                return False, f"No encontramos el expediente del donante número {id_d_int}."

            # Enviamos los datos a la clase Donante para que aplique las reglas de salud oficiales
            donante.validar_cuestionario_pretriaje(
                respuestas_cuestionario, 
                ta_sistolica=int(signos_vitales.get('ta_sistolica', 120)), 
                ta_diastolica=int(signos_vitales.get('ta_diastolica', 80)), 
                frec_cardiaca=int(signos_vitales.get('frec_cardiaca', 75))
            )

            donante.registrar_donante(self.gestor)
            self._registrar_auditoria(EntidadAfectada.DONANTE, f"El donante {donante.nombre} aprobó su revisión médica.", NivelSeveridad.INFO)
            return True, f"Aprobado: {donante.nombre} cumple con todos los requisitos para donar."

        except ValueError as ve:
            return False, f"Rechazado por motivos de salud: {ve}"
        except Exception as e:
            return False, f"Ocurrió un error técnico durante la revisión médica: {e}"

    def obtener_donante_especifico(self, id_donante: Any) -> Optional[Donante]:
        """Busca y devuelve toda la información de un donante usando su número de expediente."""
        try:
            return Donante.cargar_desde_csv(int(id_donante), self.gestor)
        except:
            return None

    def obtener_lista_donantes(self) -> List[Dict[str, Any]]:
        """Acomoda la información de todos los donantes para mostrarla limpia en la tabla de la pantalla."""
        try:
            todos = Donante.obtener_todos_los_donantes(self.gestor)
            return [
                {
                    "ID": d.get('id_global'),
                    "Nombre": d.get('nombre'),
                    "Tipo": f"{d.get('tipo_sangre','')}{d.get('factor_rh','')}",
                    "Última Donación": d.get('ultima_donacion') or "Nunca",
                    "Elegible": "Sí" if str(d.get('estado_elegibilidad')).lower() in ('true', '1', 'si') else "No"
                } for d in todos
            ]
        except: return []

    # --- GESTIÓN DE PACIENTES ---

    def registrar_nuevo_paciente_ui(self, datos_paciente: dict) -> Tuple[bool, str, int]:
        """
        Da de alta a un paciente en el hospital. 
        Revisa sus fechas y le asigna un folio interno, respetando su número de expediente clínico.
        """
        fecha_nac = datos_paciente.get('fecha_nacimiento', '').strip()
        if not self._validar_formato_fecha(fecha_nac):
            return False, "La fecha de nacimiento no tiene el formato correcto (YYYY-MM-DD).", 0

        # Le damos un número global para que el sistema lo identifique internamente
        id_autogenerado = int(datetime.now().strftime("%y%m%d%H%M%S"))
        while not self.gestor.es_id_global_unico(id_autogenerado):
            id_autogenerado += 1

        try:
            datos_paciente['id_global'] = id_autogenerado
            
            # Si en la pantalla no llenaron algunos datos secundarios, les ponemos valores por defecto
            if 'genero' not in datos_paciente:
                datos_paciente['genero'] = "NO ESPECIFICADO"
            if 'area_internamiento' not in datos_paciente:
                datos_paciente['area_internamiento'] = "General"
            
            id_clinico = int(datos_paciente.get('id_paciente', 0))
            
            # Verificamos que no haya otro paciente usando ese mismo número de cuarto o expediente
            if self.gestor.existe_id_en_archivo("pacientes", "id_paciente", id_clinico):
                return False, f"Atención: El expediente clínico {id_clinico} ya está registrado a nombre de otro paciente.", 0

            nuevo_paciente = Paciente(**datos_paciente)
            nuevo_paciente.registrar_paciente(self.gestor)
            return True, f"Paciente registrado: {nuevo_paciente.nombre} ha sido ingresado con el expediente {id_clinico}.", id_autogenerado
        except ValueError as ve:
            return False, f"Revisar datos: {ve}", 0
        except Exception as e:
            return False, f"Problema técnico al guardar al paciente: {e}", 0

    def obtener_resumen_paciente(self, id_paciente: Any) -> Optional[str]:
        """Genera un pequeño texto con la situación médica del paciente, listo para imprimir o leer rápido."""
        try:
            paciente = Paciente.cargar_desde_csv(int(id_paciente), self.gestor)
            return paciente.obtener_resumen_clinico() if paciente else None
        except: return None

    def dar_alta_paciente(self, id_paciente: Any, motivo: str = "Alta Médica") -> Tuple[bool, str]:
        """
        Registra que un paciente ya se fue del hospital (o falleció). 
        No borra su historial, solo lo quita de la lista de personas "internadas".
        """
        try:
            # Nos aseguramos de convertir correctamente el ID, incluso si viene con decimales desde Pandas
            id_p_int = int(float(str(id_paciente).strip()))
            
            paciente = Paciente.cargar_desde_csv(id_p_int, self.gestor)
            if not paciente:
                return False, f"No pudimos encontrar el expediente número {id_p_int}."

            # Cambiamos su "área" al motivo de salida para que ya no aparezca en las búsquedas normales
            paciente.area_internamiento = motivo
            paciente.registrar_paciente(self.gestor)

            self._registrar_auditoria(
                EntidadAfectada.PACIENTE,
                f"El paciente {paciente.nombre} (Expediente: {id_p_int}) salió del hospital. Motivo: {motivo}.",
                NivelSeveridad.INFO
            )
            return True, f"Proceso finalizado. Se ha registrado la salida de {paciente.nombre}."
        except Exception as e:
            return False, f"Ocurrió un error al intentar dar de alta al paciente: {e}"

    def obtener_lista_pacientes(self) -> List[Dict[str, Any]]:
        """
        Prepara la lista de pacientes para la pantalla, pero filtra a los que ya se fueron 
        para mostrar únicamente a los que siguen internados.
        """
        try:
            todos = Paciente.obtener_todos_los_pacientes(self.gestor)
            return [
                {
                    "Expediente": p.get('id_paciente'),
                    "Nombre": p.get('nombre'),
                    "Tipo": f"{p.get('tipo_sangre','')}{p.get('factor_rh','')}",
                    "Área": p.get('area_internamiento'),
                    "Prioridad": p.get('prioridad_clinica')
                } for p in todos if str(p.get('area_internamiento')).strip().title() not in ["Alta Médica", "Defunción"]
            ]
        except: return []