import os
import pandas as pd

class StorageParquet:
    def __init__(self, filename='bench_data.parquet'):
        self.filename = filename
        if os.path.exists(self.filename): os.remove(self.filename)

    def write(self, data_list):
        # Parquet requiere DataFrames y Append
        df = pd.DataFrame(data_list)
        if not os.path.exists(self.filename):
            df.to_parquet(self.filename, engine='fastparquet', index=False)
        else:
            df.to_parquet(self.filename, engine='fastparquet', append=True, index=False)

    def get_size(self):
        return os.path.getsize(self.filename) / (1024 * 1024)
