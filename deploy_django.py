#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import textwrap

NGINX_AVAILABLE = "/etc/nginx/sites-available"
NGINX_ENABLED = "/etc/nginx/sites-enabled"
SYSTEMD_DIR = "/etc/systemd/system"


def run(cmd):
    print(f"\n-> Ejecutando: {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def write_file(path, content):
    print(f"\n-> Creando archivo: {path}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("   OK.")


def main():
    print("============================================")
    print("  Asistente de despliegue Django (Linux)")
    print("  Nginx + Gunicorn + systemd")
    print("============================================\n")

    project_name = input("Nombre corto del proyecto (sin espacios, ej: infohub): ").strip()
    if not project_name:
        raise SystemExit("⚠ Debes indicar un nombre de proyecto.")

    domain = input("Dominio o IP (ej: infohubdiario.com o 123.123.123.123): ").strip() or "_"

    default_root = f"/var/www/{project_name}"
    project_root = input(f"Ruta raíz del proyecto [{default_root}]: ").strip() or default_root

    default_venv = os.path.join(project_root, "venv")
    venv_path = input(f"Ruta del entorno virtual [{default_venv}]: ").strip() or default_venv

    linux_user = input("Usuario Linux para ejecutar Gunicorn [www-data]: ").strip() or "www-data"
    linux_group = input("Grupo Linux [www-data]: ").strip() or "www-data"

    default_wsgi = f"{project_name}.wsgi:application"
    wsgi_module = input(f"Módulo WSGI de Django [{default_wsgi}]: ").strip() or default_wsgi

    # Puedes usar socket o puerto; aquí uso socket Unix
    socket_path = f"/run/gunicorn-{project_name}.sock"

    static_root = input(f"Ruta de STATIC_ROOT (para Nginx) [{project_root}/static/]: ").strip() or f"{project_root}/static/"
    media_root = input(f"Ruta de MEDIA_ROOT (para Nginx) [{project_root}/media/]: ").strip() or f"{project_root}/media/"

    gunicorn_bin = os.path.join(venv_path, "bin", "gunicorn")

    print("\nResumen de configuración:")
    print(f"  Proyecto      : {project_name}")
    print(f"  Dominio/IP    : {domain}")
    print(f"  Root proyecto : {project_root}")
    print(f"  Venv          : {venv_path}")
    print(f"  Gunicorn bin  : {gunicorn_bin}")
    print(f"  WSGI module   : {wsgi_module}")
    print(f"  Socket        : {socket_path}")
    print(f"  STATIC_ROOT   : {static_root}")
    print(f"  MEDIA_ROOT    : {media_root}")
    cont = input("\n¿Continuar y generar archivos? [s/N]: ").strip().lower()
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
            listen 80;
            server_name {domain};

            # Static files
            location /static/ {{
                alias {static_root};
            }}

            # Media files
            location /media/ {{
                alias {media_root};
            }}

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
        print(f"\n-> El link {nginx_link} ya existe, no se toca.")
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
    print("  Despliegue básico completado.")
    print("  Revisa el estado de Gunicorn con:")
    print(f"    systemctl status {project_name}.service")
    print("  Revisa Nginx con:")
    print("    journalctl -xeu nginx")
    print("============================================")


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("⚠ Este script debe ejecutarse como root (sudo).")
        raise SystemExit(1)
    main()
