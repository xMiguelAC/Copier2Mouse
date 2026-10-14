# Copier2Mouse

Aplicación de escritorio para Windows que permite pegar textos predefinidos usando botones adicionales del mouse. Es útil para respuestas frecuentes, comandos, plantillas, mensajes repetitivos o cualquier texto que quieras insertar rápidamente desde otra aplicación.

## Función principal

La aplicación permanece activa en segundo plano y escucha los botones del mouse que hayas configurado. Cuando pulsas un botón asignado, copia el texto correspondiente al portapapeles y ejecuta `Ctrl+V` en la aplicación que está activa.

Incluye:

- Interfaz gráfica para crear, editar, activar y eliminar textos.
- Asignación de textos a los botones laterales X1 y X2 del mouse.
- Posibilidad de usar también el botón central, izquierdo o derecho.
- Activación y pausa de la escucha global del mouse.
- Guardado automático de la configuración.
- Opción para restaurar el contenido anterior del portapapeles después de pegar.
- Ejecutable de Windows que no requiere abrir la terminal.

## Instalación rápida con el ejecutable

1. Descarga o clona este repositorio.
2. Entra en la carpeta `dist`.
3. Ejecuta `MouseTextPaster.exe` con doble clic.
4. Si Windows muestra una advertencia de seguridad, revisa que el archivo provenga de este repositorio antes de permitir su ejecución.

La configuración se crea automáticamente junto al ejecutable en el archivo `mouse_text_paster_config.json`. Ese archivo es local y está excluido del repositorio para no publicar textos personales.

## Uso

1. Abre `MouseTextPaster.exe`.
2. Pulsa **Nuevo**.
3. Escribe un nombre descriptivo, por ejemplo `Saludo`.
4. Escribe el texto que quieres pegar.
5. Selecciona un botón del mouse, preferiblemente **X1** o **X2**.
6. Guarda la asignación y deja la escucha activa.
7. Coloca el cursor en cualquier campo de texto de otra aplicación.
8. Pulsa el botón asignado para pegar el texto.

Puedes editar o eliminar asignaciones desde la ventana principal. La escucha también puede pausarse desde el menú **Escucha** o mediante el botón correspondiente.

### Restaurar el portapapeles

Activa **Restaurar el portapapeles después de pegar** si quieres que la aplicación vuelva a colocar el contenido que tenía el portapapeles antes de utilizar un texto rápido.

## Ejecución desde Python

Requiere Python 3.9 o posterior:

```powershell
pip install -r requirements.txt
python mouse_text_paster.py
```

## Generar el `.exe`

En Windows, abre PowerShell dentro de esta carpeta y ejecuta:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_exe.ps1
```

El ejecutable se generará en `dist\MouseTextPaster.exe`. El script utiliza una carpeta local para PyInstaller y no necesita modificar la instalación global de Python.

## Nota sobre permisos de Windows

Si la aplicación donde quieres pegar texto se está ejecutando como administrador y Copier2Mouse no, Windows puede impedir la entrada simulada. En ese caso, ejecuta ambos programas con el mismo nivel de permisos.

## Licencia

Este proyecto se publica bajo la licencia MIT. Consulta el archivo `LICENSE`.
