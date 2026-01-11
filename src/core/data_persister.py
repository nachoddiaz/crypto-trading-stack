from src.database.repository import AsyncRepository
 
class DataPersister:
    def __init__(self, repository: AsyncRepository):
        self.repository = repository

    async def save_batch(self, batch_data: list):
        """
        Recibe una lista limpia de diccionarios y la guarda en DB.
        Aquí aplicas tus reglas de validación si tienes alguna.
        """
        if not batch_data:
            return

        try:
            # Golden Rule: Operation Fusion (Insertar todo de una vez)
            await self.repository.save_batch(batch_data)
            # print(f"Persistidos {len(batch_data)} registros.")
        except Exception as e:
            # Aquí podrías manejar errores de lógica (ej: duplicados)
            print(f"Error en DataPersister: {e}")
            raise e # Relanzar para que el consumidor decida si reintentar