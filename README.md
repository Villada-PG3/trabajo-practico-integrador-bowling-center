# Bowling Center - Sistema de Gestión

## Descripción

Sistema de gestión para un centro de bowling. El objetivo del proyecto es digitalizar y centralizar la administración de las operaciones del centro (como la gestión de pistas, turnos, clientes y demás procesos asociados), reemplazando procesos manuales por una plataforma web ordenada y mantenible.

## Tecnologías

<p align="left">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django"/>
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL"/>
  <img src="https://img.shields.io/badge/Bootstrap-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap"/>
  <img src="https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white" alt="Git"/>
  <img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"/>
</p>

- **Python** — Lenguaje principal del backend.
- **Django** — Framework web utilizado para la lógica de negocio y el manejo de datos.
- **MySQL** — Motor de base de datos relacional.
- **Bootstrap** — Framework para el diseño y estilos de la interfaz.
- **Git y GitHub** — Control de versiones y colaboración en equipo.

## Estructura principal del repositorio

```
bowling-center/
├── manage.py
│
├── config/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── bowling_center/
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── views.py
│
├── docs/
│   ├── er/
│   ├── uml/
|
├── requirements.txt
├── .gitignore
└── README.md
```

## Requisitos previos

- Python instalado (versión 3.x).
- Git instalado.

## Instalación desde cero

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/Villada-PG3/trabajo-practico-integrador-bowling-center.git
   cd trabajo-practico-integrador-bowling-center
   ```

2. **Crear y activar el entorno virtual**
   ```bash
   python -m venv .venv
   ```
   - En Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - En Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Aplicar las migraciones**
   ```bash
   python manage.py migrate
   ```

5. **Ejecutar el servidor**
   ```bash
   python manage.py runserver
   ```

## Panel para trabajadores

El panel interno está disponible desde la opción **Trabajadores** de la página principal, o directamente en `/gestion/`. Desde allí se administran los tipos de pista, las pistas, los horarios y el catálogo de comidas y bebidas; también se accede al mapa de operación, a la agenda por fecha y cliente y a la caja. En la agenda se pueden registrar llegadas y agregar consumos a las reservas. Se requiere una cuenta de personal (`is_staff`); para crear una durante el desarrollo:

```bash
python manage.py createsuperuser
```

El inicio de sesión propio del panel está en `/gestion/login/`. El admin de Django se conserva para cargar otros datos de prueba y depurar, pero no se usa como pantalla de gestión u operación del centro.

## Integrantes del equipo

- Lautaro Alladio
- Ivo Misevich
- Genaro Correa