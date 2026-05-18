"""
Módulo Orquestador Principal - BloodConnect
Este archivo es el "director de orquesta" de todo el sistema. En lugar de que la 
interfaz gráfica tenga que hablar con cada controlador por separado, le pide todo a 
este archivo, y este se encarga de repartir el trabajo al ayudante correspondiente.
Esto mantiene el código limpio, ordenado y fácil de conectar con las pantallas.
"""

import os
from typing import Tuple, List, Dict, Optional, Any

# Importación de la base de datos y almacén central
from clases.auditoria import GestorDatos
from clases.gestion_almacen import Inventario

from .ctrl_autenticacion import CtrlAutenticacion
from .ctrl_identidades import CtrlIdentidades
from .ctrl_agendamiento import CtrlAgendamiento
from .ctrl_almacen import CtrlAlmacen
from .ctrl_clinico import CtrlClinico
from .ctrl_auditoria import CtrlAuditoria

class SistemaBloodConnect:
    """
    Clase principal del sistema (Patrón de Diseño Facade / Fachada).
    Funciona como una ventanilla única de atención para la interfaz visual.
    """

    def __init__(self):
        # 1. Arrancamos el motor de la base de datos y verificamos que los archivos existan
        self.gestor = GestorDatos() 
        self.gestor.verificar_integridad_archivos()
        
        # 2. Preparamos el refrigerador virtual (inventario en memoria)
        self.inventario = Inventario(umbral_critico_seguridad=10)
        self.inventario.cargar_inventario_inicial(self.gestor)

        # 3. Instanciamos a todos los "ayudantes" (sub-controladores especializados)
        self.ctrl_autenticacion = CtrlAutenticacion(self.gestor)
        self.ctrl_identidades = CtrlIdentidades(self.gestor)
        self.ctrl_agendamiento = CtrlAgendamiento(self.gestor)
        
        self.ctrl_almacen = CtrlAlmacen(self.gestor)
        self.ctrl_almacen.inventario = self.inventario # Le entregamos el control del inventario
        
        self.ctrl_clinico = CtrlClinico(self.gestor, self.inventario)
        self.ctrl_auditoria = CtrlAuditoria(self.gestor, self.inventario)

    @property
    def usuario_actual(self):
        """Nos dice rápidamente quién es la persona que está usando el sistema en este momento."""
        return self.ctrl_autenticacion.usuario_actual

    def _sincronizar_sesion(self):
        """
        Como tenemos varios sub-controladores trabajando en equipo, esta función se asegura 
        de avisarles a todos quién acaba de iniciar (o cerrar) sesión. Así, si alguien 
        hace un cambio, el sistema sabe exactamente a nombre de quién registrarlo.
        """
        usuario = self.ctrl_autenticacion.usuario_actual
        self.ctrl_identidades.usuario_actual = usuario
        self.ctrl_agendamiento.usuario_actual = usuario
        self.ctrl_almacen.usuario_actual = usuario
        self.ctrl_clinico.usuario_actual = usuario
        self.ctrl_auditoria.usuario_actual = usuario

    # =========================================================================
    # MÓDULO DE AUTENTICACIÓN (PUERTA DE ENTRADA)
    # =========================================================================
    def login_sistema(self, id_trabajador: Any, password_plana: str) -> Tuple[bool, str]:
        """Pasa los datos a la puerta de seguridad. Si el acceso es correcto, sincroniza la sesión."""
        exito, msj = self.ctrl_autenticacion.login_sistema(id_trabajador, password_plana)
        if exito: self._sincronizar_sesion() 
        return exito, msj
        
    def logout_sistema(self):
        """Cierra la sesión y le avisa a todos los módulos que el usuario se fue."""
        self.ctrl_autenticacion.logout_sistema()
        self._sincronizar_sesion() 

    # =========================================================================
    # MÓDULO DE IDENTIDADES Y CENSO MÉDICO
    # =========================================================================
    def registrar_nuevo_trabajador_ui(self, datos: dict) -> Tuple[bool, str, int]:
        return self.ctrl_identidades.registrar_nuevo_trabajador_ui(datos)

    def obtener_lista_trabajadores(self) -> List[dict]:
        return self.ctrl_identidades.obtener_lista_trabajadores()

    def registrar_nuevo_donante_ui(self, datos: dict) -> Tuple[bool, str, int]:
        return self.ctrl_identidades.registrar_nuevo_donante_ui(datos)

    def evaluar_pretriaje_donante(self, id_donante: Any, respuestas: dict, signos: dict) -> Tuple[bool, str]:
        return self.ctrl_identidades.evaluar_pretriaje_donante(id_donante, respuestas, signos)

    def registrar_nuevo_paciente(self, datos: dict) -> Tuple[bool, str]:
        # La interfaz gráfica solo espera saber si hubo éxito y el mensaje, por eso omitimos el ID autogenerado aquí
        exito, msj, _id_generado = self.ctrl_identidades.registrar_nuevo_paciente_ui(datos)
        return exito, msj

    def obtener_resumen_paciente(self, id_paciente: Any) -> Optional[str]:
        return self.ctrl_identidades.obtener_resumen_paciente(id_paciente)

    def obtener_donante_especifico(self, id_donante: Any):
        return self.ctrl_identidades.obtener_donante_especifico(id_donante)

    def obtener_lista_donantes(self) -> List[Dict[str, Any]]:
        return self.ctrl_identidades.obtener_lista_donantes()

    def obtener_lista_pacientes(self) -> List[Dict[str, Any]]:
        return self.ctrl_identidades.obtener_lista_pacientes()
    
    def dar_alta_paciente(self, id_paciente: Any, motivo: str = "Alta Médica") -> Tuple[bool, str]:
        return self.ctrl_identidades.dar_alta_paciente(id_paciente, motivo)

    # =========================================================================
    # MÓDULO DE AGENDAMIENTO (CONTROL DE CITAS Y CAMILLAS)
    # =========================================================================
    def obtener_horarios_disponibles(self, fecha: str) -> Tuple[bool, List[str]]:
        return self.ctrl_agendamiento.obtener_horarios_disponibles(fecha)

    def agendar_cita_donante(self, id_donante: Any, fecha: str, hora: str) -> Tuple[bool, str]:
        return self.ctrl_agendamiento.agendar_cita_donante(id_donante, fecha, hora)

    def actualizar_estado_cita(self, id_cita: Any, estado_str: str) -> Tuple[bool, str]:
        return self.ctrl_agendamiento.actualizar_estado_cita(id_cita, estado_str)

    def obtener_agenda_del_dia(self, fecha: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.ctrl_agendamiento.obtener_agenda_del_dia(fecha)
        
    def obtener_id_donante_por_cita(self, id_cita: Any) -> Optional[int]:
        return self.ctrl_agendamiento.obtener_id_donante_por_cita(id_cita)

    def sincronizar_cita_inteligente_controller(self, id_donante: Any, fecha_hoy: str, nuevo_estado_str: str):
        self.ctrl_agendamiento.sincronizar_cita_inteligente_controller(id_donante, fecha_hoy, nuevo_estado_str)

    # =========================================================================
    # MÓDULO DE ALMACÉN (EXTRACCIONES, FRACCIONAMIENTO Y PRUEBAS)
    # =========================================================================
    def procesar_donacion_exitosa_ui(self, id_donante_str: Any, volumen_str: Any) -> Tuple[bool, str, int]:
        return self.ctrl_almacen.procesar_donacion_exitosa_ui(id_donante_str, volumen_str)

    def registrar_estabilidad_post_donacion(self, id_extraccion: Any, complicaciones: list) -> Tuple[bool, str]:
        return self.ctrl_almacen.registrar_estabilidad_post_donacion(id_extraccion, complicaciones)

    def procesar_fraccionamiento(self, id_unidad: Any) -> Tuple[bool, str]:
        return self.ctrl_almacen.procesar_fraccionamiento(id_unidad)

    def procesar_extraccion_crioprecipitado(self, id_unidad: Any) -> Tuple[bool, str]:
        return self.ctrl_almacen.procesar_extraccion_crioprecipitado(id_unidad)

    def procesar_liberacion_unidad(self, id_unidad: Any, resultados: dict, password: str) -> Tuple[bool, str]:
        return self.ctrl_almacen.procesar_liberacion_unidad(id_unidad, resultados, password)

    def verificar_alertas_stock(self) -> str:
        return self.ctrl_almacen.verificar_alertas_stock()

    def obtener_unidades_cuarentena(self) -> List[Dict[str, Any]]:
        return self.ctrl_almacen.obtener_unidades_cuarentena()

    def obtener_inventario_general(self) -> List[Dict[str, Any]]:
        return self.ctrl_almacen.obtener_inventario_general()

    def obtener_historial_extracciones_tabla(self) -> List[Dict[str, Any]]:
        return self.ctrl_almacen.obtener_historial_extracciones_tabla()

    # =========================================================================
    # MÓDULO CLÍNICO Y RED INTERHOSPITALARIA (TRANSFUSIONES Y TRASLADOS)
    # =========================================================================
    def procesar_transfusion_rutina(self, id_paciente: Any, tipo_req: str, factor_req: str, unidades: int = 1, tipo_comp: Any = "Globulos Rojos", prioridad: Any = "Verde") -> Tuple[bool, str]:
        # Nos aseguramos de que no lleguen valores nulos desde la pantalla antes de enviarlos a procesar
        comp_seguro = tipo_comp if tipo_comp is not None else "Globulos Rojos"
        prio_segura = prioridad if prioridad is not None else "Verde"
        return self.ctrl_clinico.procesar_transfusion_rutina(id_paciente, tipo_req, factor_req, unidades, comp_seguro, prio_segura)

    def procesar_emergencia_primaria(self, id_paciente_str: str, unidades: int) -> Tuple[bool, str, str]:
        return self.ctrl_clinico.procesar_emergencia_primaria(id_paciente_str, unidades)

    def procesar_emergencia_fallback(self, id_paciente_str: str, grupo: str, rh: str, unidades: int) -> Tuple[bool, str, str]:
        return self.ctrl_clinico.procesar_emergencia_fallback(id_paciente_str, grupo, rh, unidades)

    def procesar_baja_retrospectiva(self, ids_str: str, password_firma: str) -> Tuple[bool, str]:
        return self.ctrl_clinico.procesar_baja_retrospectiva(ids_str, password_firma)

    def registrar_reaccion_adversa_transfusion(self, id_transfusion: Any, id_donante: Any, notas: str) -> Tuple[bool, str]:
        return self.ctrl_clinico.registrar_reaccion_adversa_transfusion(id_transfusion, id_donante, notas)

    def procesar_devolucion_quirofano(self, id_unidad: Any, cadena_frio: bool, password: str) -> Tuple[bool, str]:
        return self.ctrl_clinico.procesar_devolucion_quirofano(id_unidad, cadena_frio, password)

    def buscar_stock_en_red(self, id_clues: str, nombre_hosp: str, ruta_csv: str, tipo_comp: str, tipo_sangre: str, factor: str) -> Tuple[bool, Any]:
        return self.ctrl_clinico.buscar_stock_en_red(id_clues, nombre_hosp, ruta_csv, tipo_comp, tipo_sangre, factor)

    def procesar_ingreso_externo(self, id_envio: int, id_clues: str, nombre_hosp: str, ruta_csv: str, unidades: list) -> Tuple[bool, str]:
        return self.ctrl_clinico.procesar_ingreso_externo(id_envio, id_clues, nombre_hosp, ruta_csv, unidades)

    def procesar_envio_externo(self, id_envio: int, id_clues: str, nombre_hosp: str, ruta_csv: str, ids_unidades: list) -> Tuple[bool, str]:
        return self.ctrl_clinico.procesar_envio_externo(id_envio, id_clues, nombre_hosp, ruta_csv, ids_unidades)

    def obtener_historial_transfusiones_tabla(self) -> List[Dict[str, Any]]:
        return self.ctrl_clinico.obtener_historial_transfusiones_tabla()
        
    def obtener_donante_origen_por_unidad(self, id_unidad: Any) -> str:
        return self.ctrl_clinico.obtener_donante_origen_por_unidad(id_unidad)

    # =========================================================================
    # MÓDULO DE AUDITORÍA (HISTORIALES, GRÁFICAS Y RESPALDOS)
    # =========================================================================
    def rastrear_trazabilidad_bolsa(self, id_unidad: Any) -> Tuple[bool, Any]:
        return self.ctrl_auditoria.rastrear_trazabilidad_bolsa(id_unidad)

    def ejecutar_respaldo_seguridad(self) -> Tuple[bool, str]:
        return self.ctrl_auditoria.ejecutar_respaldo_seguridad()

    def obtener_historial_auditoria(self, limite: int = 20) -> Tuple[bool, Any]:
        return self.ctrl_auditoria.obtener_historial_auditoria(limite)

    def visualizar_estado_actual(self) -> Optional[str]:
        return self.ctrl_auditoria.visualizar_estado_actual()

    def exportar_etiqueta_fisica_mock(self, id_unidad: Any) -> Tuple[bool, str]:
        return self.ctrl_auditoria.exportar_etiqueta_fisica_mock(id_unidad)