# Deploy-Ngnix-NetdroidDale permisos de ejecución:



chmod +x deploy_django.py

3. Ejecútalo con sudo:



sudo ./deploy_django.py

4. Responde a las preguntas:

Nombre del proyecto → infohub_diario_flask o mi_django_app

Dominio → tu dominio o IP pública

Ruta del proyecto → donde tengas el código (/var/www/mi_django_app)

Ruta venv → por ejemplo /var/www/mi_django_app/venv

Módulo WSGI → normalmente mi_django_app.wsgi:application




Después de eso, ya deberías tener:

/etc/systemd/system/mi_django_app.service

/etc/nginx/sites-available/mi_django_app

/etc/nginx/sites-enabled/mi_django_app (symlink)

Servicio de Gunicorn corriendo y Nginx recargado.
