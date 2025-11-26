#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Asistente de despliegue Django (Linux)
--------------------------------------
Este script crea automáticamente:

1. Un servicio systemd para Gunicorn.
2. Una configuración de Nginx que apunta a Gunicorn (por socket Unix).
3. Directorios para static y media (si no existen).
4. Habilita el sitio en Nginx y recarga servicios.

IMPORTANTE:
- Debes ejecutarlo como root:  sudo python3 deploy_django.py
- Debes tener Nginx instalado y Gunicorn dentro del entorno virtual.
"""

import os
import subprocess
import textwrap

NGINX_AVAILABLE = "/etc/nginx/sites-available"
NGINX_ENABLED = "/etc/nginx/sites-enabled"
SYSTEMD_DIR = "/etc/systemd/system"


def run(cmd: str) -> None:
    """Ejecuta un comando en shell y muestra lo que hace."""
    print(f"\n-> Ejecutando comando: {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def write_file(path: str, content: str) -> None:
    """Crea o sobrescribe un archivo con el contenido dado."""
    print(f"\n-> Creando archivo: {path}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("   ✔ Archivo creado correctamente.")


def input_with_help(prompt: str, help_text: str, default: str | None = None) -> str:
    """
    Muestra una explicación previa (help_text) y luego pide el dato.
    Si el usuario no escribe nada, retorna el default (si existe).
    """
    print("\n" + "-" * 60)
    print(help_text)
    if default is not None:
        value = input(f"{prompt} [{default}]: ").strip()
        return value or default
    value = input(f"{prompt}: ").strip()
    return value


def main() -> None:
    print("============================================")
    print("  Asistente de despliegue Django (Linux)")
    print("  Stack: Nginx (puerto público) + Gunicorn + systemd")
    print("============================================\n")

    # 1) Nombre del proyecto
    project_name = input_with_help(
        "1) Nombre corto del proyecto (sin espacios)",
        "Este nombre se usará para:\n"
        "- El servicio de systemd (ej: infohub.service)\n"
        "- El archivo de Nginx (ej: /etc/nginx/sites-available/infohub)\n"
        "Usa algo simple, en minúsculas, sin espacios. Ejemplo: infohub, panel_ipsi, apidjango.",
    )
    if not project_name:
        raise SystemExit("⚠ Debes indicar un nombre de proyecto. Abortando.")

    # 2) Dominio o IP
    domain = input_with_help(
        "2) Dominio o IP público de la app",
        "Escribe el dominio (ej: infohubdiario.com) o la IP pública del servidor.\n"
        "Si aún no tienes dominio, puedes dejarlo vacío y se usará '_', que acepta cualquier host.",
        default="_",
    )

    # 3) Puerto PÚBLICO donde saldrá la app a Internet
    listen_port_raw = input_with_help(
        "3) Puerto PÚBLICO donde Nginx escuchará la app",
        "Este es el puerto por donde los usuarios entrarán a tu app desde Internet.\n"
        "Ejemplos:\n"
        "- 80   → http://TU_IP/          (típico para HTTP, puede estar ocupado)\n"
        "- 8080 → http://TU_IP:8080/     (útil si ya tienes algo en el 80)\n"
        "- 8000 → http://TU_IP:8000/     (otra opción común de pruebas).\n"
        "IMPORTANTE: si ya tienes otra página en el puerto 80, elige 8080, 8000, etc.",
        default="80",
    )
    if not listen_port_raw.isdigit():
        print("⚠ El puerto no es un número válido. Usando 80 por defecto.")
        listen_port = 80
    else:
        listen_port = int(listen_port_raw)

    # 4) Ruta raíz del proyecto
    default_root = f"/var/www/{project_name}"
    project_root = input_with_help(
        "4) Ruta raíz del proyecto",
        "Ruta donde está tu proyecto Django (el manage.py suele estar aquí).\n"
        f"Ejemplo típico: {default_root}",
        default=default_root,
    )

    # 5) Entorno virtual
    default_venv = os.path.join(project_root, "venv")
    venv_path = input_with_help(
        "5) Ruta del entorno virtual (venv)",
        "Ruta al entorno virtual de Python que contiene Django y Gunicorn.\n"
        f"Si creaste el venv dentro del proyecto, normalmente será: {default_venv}",
        default=default_venv,
    )

    # 6) Usuario y grupo de Linux
    linux_user = input_with_help(
        "6) Usuario Linux para ejecutar Gunicorn",
        "Usuario del sistema bajo el cual correrá el proceso de Gunicorn.\n"
        "En servidores de producción suele usarse 'www-data' o 'ubuntu' dependiendo de tu setup.",
        default="www-data",
    )
    linux_group = input_with_help(
        "7) Grupo Linux para ejecutar Gunicorn",
        "Grupo del sistema para el proceso de Gunicorn.\n"
        "Normalmente coincide con el usuario, por ejemplo 'www-data'.",
        default="www-data",
    )

    # 7) Módulo WSGI
    default_wsgi = f"{project_name}.wsgi:application"
    wsgi_module = input_with_help(
        "8) Módulo WSGI de Django",
        "Este es el módulo WSGI de tu proyecto Django.\n"
        "Suele tener la forma: nombre_proyecto.wsgi:application\n"
        f"Ejemplo: {default_wsgi}",
        default=default_wsgi,
    )

    # 8) Rutas de static y media
    static_root = input_with_help(
        "9) Ruta de STATIC_ROOT (para Nginx)",
        "Directorio donde se guardan los archivos estáticos recolectados con collectstatic.\n"
        "Debe coincidir con la variable STATIC_ROOT de tu settings.py.",
        default=f"{project_root}/static/",
    )
    media_root = input_with_help(
        "10) Ruta de MEDIA_ROOT (para Nginx)",
        "Directorio donde se guardan los archivos subidos por los usuarios.\n"
        "Debe coincidir con MEDIA_ROOT en tu settings.py, si lo usas.",
        default=f"{project_root}/media/",
    )

    # 9) Ruta a binario de Gunicorn
    gunicorn_bin = os.path.join(venv_path, "bin", "gunicorn")

    # 10) Socket Unix para Gunicorn (interno, NO público)
    socket_path = f"/run/gunicorn-{project_name}.sock"

    # Resumen
    print("\n============================================")
    print("RESUMEN DE CONFIGURACIÓN")
    print("============================================")
    print(f"  Proyecto              : {project_name}")
    print(f"  Dominio/IP            : {domain}")
    print(f"  PUERTO PÚBLICO (Nginx): {listen_port}")
    print(f"  Root proyecto         : {project_root}")
    print(f"  Venv                  : {venv_path}")
    print(f"  Gunicorn bin          : {gunicorn_bin}")
    print(f"  WSGI module           : {wsgi_module}")
    print(f"  Socket Gunicorn       : {socket_path}")
    print(f"  STATIC_ROOT           : {static_root}")
    print(f"  MEDIA_ROOT            : {media_root}")
    print("============================================")
    print("\nNOTA CLAVE:")
    print("- El PUERTO PÚBLICO es donde los usuarios acceden desde Internet (Nginx).")
    print("- Gunicorn NO se expone a Internet; se comunica con Nginx por un socket Unix interno.\n")

    cont = input("¿Continuar y generar archivos de configuración? [s/N]: ").strip().lower()
    if cont != "s":
        raise SystemExit("Abortado por el usuario.")

    # ================================
    # 1. Crear directorios básicos
    # ================================
    for d in [project_root, static_root, media_root]:
        if not os.path.exists(d):
            print(f"-> Creando directorio: {d}")
            os.makedirs(d, exist_ok=True)

    # ================================
    # 2. Archivo systemd para Gunicorn
    # ================================
    service_path = os.path.join(SYSTEMD_DIR, f"{project_name}.service")

    service_content = textwrap.dedent(f"""
        [Unit]
        Description=Gunicorn service for {project_name}
        After=network.target

        [Service]
        User={linux_user}
        Group={linux_group}
        WorkingDirectory={project_root}
        Environment="PATH={venv_path}/bin"
        ExecStart={gunicorn_bin} \\
            --workers 3 \\
            --bind unix:{socket_path} \\
            {wsgi_module}

        Restart=always
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
    """).strip() + "\n"

    write_file(service_path, service_content)

    # ================================
    # 3. Archivo de configuración Nginx
    # ================================
    nginx_conf_path = os.path.join(NGINX_AVAILABLE, project_name)

    nginx_content = textwrap.dedent(f"""
        server {{
            # PUERTO PÚBLICO: aquí escucha Nginx hacia Internet
            listen {listen_port};
            server_name {domain};

            # Archivos estáticos
            location /static/ {{
                alias {static_root};
            }}

            # Archivos multimedia
            location /media/ {{
                alias {media_root};
            }}

            # Tráfico hacia Django (Gunicorn, interno, por socket)
            location / {{
                include proxy_params;
                proxy_pass http://unix:{socket_path};
                proxy_read_timeout 300;
            }}
        }}
    """).strip() + "\n"

    write_file(nginx_conf_path, nginx_content)

    # ================================
    # 4. Enlazar Nginx site-enabled
    # ================================
    nginx_link = os.path.join(NGINX_ENABLED, project_name)
    if os.path.islink(nginx_link) or os.path.exists(nginx_link):
        print(f"\n-> El link {nginx_link} ya existe, no se modifica.")
    else:
        run(f"ln -s {nginx_conf_path} {nginx_link}")

    # ================================
    # 5. Recargar systemd y arrancar servicio
    # ================================
    run("systemctl daemon-reload")
    run(f"systemctl enable {project_name}.service")
    run(f"systemctl restart {project_name}.service")

    # ================================
    # 6. Probar configuración de Nginx y recargar
    # ================================
    run("nginx -t")
    run("systemctl reload nginx")

    print("\n============================================")
    print("  Despliegue básico completado ✅")
    print("  Revisa el estado de Gunicorn con:")
    print(f"    systemctl status {project_name}.service")
    print("\n  Logs de Nginx (si algo falla):")
    print("    journalctl -xeu nginx")
    print("\n  Para probar la app en el navegador, usa:")
    if domain == "_":
        print(f"    http://TU_IP:{listen_port}/")
    else:
        if listen_port == 80:
            print(f"    http://{domain}/")
        else:
            print(f"    http://{domain}:{listen_port}/")
    print("============================================")


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("⚠ Este script debe ejecutarse como root (sudo).")
        raise SystemExit(1)
    main()
