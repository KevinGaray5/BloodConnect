"""
Módulo del Controlador de Autenticación - BloodConnect
Este archivo funciona como la "puerta de seguridad" del sistema. Se encarga de revisar 
las credenciales de los médicos, laboratoristas y administradores para permitirles 
el acceso, además de recordar en memoria quién está usando el programa en todo momento.
"""

from typing import Tuple, Optional, Any
from datetime import datetime

from clases.gestion_identidades import Trabajador
from clases.auditoria import GestorDatos, Bitacora, EntidadAfectada, NivelSeveridad

class CtrlAutenticacion:
    def __init__(self, gestor: GestorDatos):
        self.gestor = gestor
        # Aquí guardamos los datos de la persona que logró iniciar sesión correctamente
        self.usuario_actual: Optional[Trabajador] = None

    def _registrar_auditoria(self, entidad: EntidadAfectada, accion: str, severidad: NivelSeveridad):
        """Anota en la bitácora los inicios y cierres de sesión para tener un control de quién entra al sistema."""
        try:
            id_usuario = self.usuario_actual.id_global if self.usuario_actual else 0
            id_log = int(datetime.now().strftime("%y%m%d%H%M%S")) 
            registro = Bitacora(id_log, id_usuario, entidad, accion, severidad)
            registro.escribir_entrada_inmutable(self.gestor.ruta_log)
        except Exception as e:
            # Si el archivo de texto está ocupado o falla, avisamos por consola sin detener el programa
            print(f"Aviso del sistema: No se pudo guardar el registro de inicio/cierre de sesión. Detalle: {e}")

    def login_sistema(self, id_trabajador: Any, password_plana: str) -> Tuple[bool, str]:
        """
        Revisa que el ID y la contraseña ingresados sean correctos. 
        Si todo está en orden, le da acceso al trabajador y guarda su sesión activa.
        """
        if not id_trabajador or not password_plana:
            return False, "Por favor, ingrese su número de empleado y contraseña."

        # 1. Asegurarnos de que el usuario escribió un número en la casilla del ID
        #    Esto evita que el sistema se caiga si alguien escribe letras por error.
        try:
            id_trab_int = int(str(id_trabajador).strip())
        except ValueError:
            return False, "Error en los datos: El número de empleado debe contener solo números."

        # 2. Buscar al trabajador y verificar su identidad
        try:
            trabajador = Trabajador.cargar_desde_csv(id_trab_int, self.gestor)

            if trabajador is None:
                return False, "El número de empleado o la contraseña son incorrectos."

            # Comparamos la contraseña que escribió con la versión encriptada que guardamos en los archivos
            if trabajador.iniciar_sesion(password_plana):
                self.usuario_actual = trabajador
                self._registrar_auditoria(EntidadAfectada.TRABAJADOR, f"El usuario ingresó al sistema correctamente (Rol: {trabajador.rol}).", NivelSeveridad.INFO)
                return True, f"Bienvenido(a), {trabajador.nombre} | Rol de sistema: {trabajador.rol}"

            return False, "El número de empleado o la contraseña son incorrectos."

        except PermissionError:
            return False, "El número de empleado o la contraseña son incorrectos."
        except Exception as e:
            # Si hay un problema técnico (por ejemplo, con el desencriptado de la contraseña), mostramos este error
            return False, f"Tuvimos un problema técnico al intentar verificar su identidad: {e}"
        
    def logout_sistema(self):
        """Cierra la sesión de la persona actual por motivos de seguridad."""
        if self.usuario_actual:
            self._registrar_auditoria(EntidadAfectada.TRABAJADOR, "El usuario cerró su sesión de forma segura.", NivelSeveridad.INFO)
            self.usuario_actual.cerrar_sesion()
            # Vaciamos la variable para que el sistema le vuelva a pedir credenciales a la siguiente persona
            self.usuario_actual = None