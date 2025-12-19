import os
from pymongo import MongoClient
import pymongo

class StorageMongo:
    def __init__(self, uri):
        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            self.db = self.client['finance_bench']
            self.col = self.db['ticks']
            # Verificar conexión
            self.client.server_info()
            self.col.drop() # Limpieza inicial
        except Exception as e:
            print(f"Error MongoDB: {e}")
            self.col = None

    def write(self, data_list):
        if self.col is not None:
             try:
                 self.col.insert_many(data_list)
             except Exception:
                 pass

    def get_size(self):
        if self.col is None: return 0
        try:
            return self.db.command("dbstats")['dataSize'] / (1024 * 1024)
        except:
             return 0