import sys
import logging

# Configuración del sistema de trazabilidad (Logging)
logging.basicConfig(
    filename='logs/bloodconnect_errores.log',
    level=logging.ERROR,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def main():
    """Punto de entrada principal para el arranque del sistema BloodConnect."""
    try:
        # IMPORTACIÓN ACTUALIZADA A LA NUEVA ARQUITECTURA MODULAR
        from gui_vistas.login import VentanaLogin
        
        # Ahora el sistema arranca desde la pantalla de bloqueo modular
        app = VentanaLogin()
        app.mainloop()

    except ImportError as ie:
        mensaje = f"Dependencia faltante: CustomTkinter o módulo de la interfaz no encontrado. Detalles: {ie}"
        logging.error(mensaje)
        print("\n[ERROR] El sistema no pudo iniciar. Revisa 'logs/bloodconnect_errores.log' para más detalles.")
        sys.exit(1)
        
    except Exception as e:
        mensaje = f"Caída inesperada del sistema durante la ejecución: {e}"
        logging.error(mensaje, exc_info=True)
        print("\n[ERROR FATAL] La aplicación se cerró. Revisa 'logs/bloodconnect_errores.log'.")
        sys.exit(1)

if __name__ == "__main__":
    main()