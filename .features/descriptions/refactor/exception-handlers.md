## Refactor exception handlers to a separate module

Move all exception handler functions currently defined in `main.py` to a dedicated `src/core/handlers.py` file. After the refactor, `main.py` should only contain simple registration calls for each handler (similar to how middleware is currently organized with `app.add_middleware(...)`). Ensure all existing exception handling behavior remains unchanged.
