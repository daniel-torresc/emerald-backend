# Tarea: Refactorización de encryption_service.py

Necesito reubicar el archivo `encryption_service.py` que actualmente está en `src/services/`, ya que no pertenece a la misma categoría que el resto de servicios de ese directorio.

## Contexto

- Los servicios en `src/services/` representan la capa de lógica de negocio específica del proyecto
- El `encryption_service.py` es un componente utilitario genérico, sin dependencias del proyecto, y podría reutilizarse en otras aplicaciones

## Opciones que estoy considerando

1. Moverlo a `src/core/` junto con `security.py`
2. Crear un nuevo directorio para servicios utilitarios/independientes (por ejemplo, `src/utils/` o `src/common/`)

## Tarea

Investiga la mejor práctica arquitectónica para organizar este tipo de servicios genéricos y reutilizables e impleméntalo de esta forma.
