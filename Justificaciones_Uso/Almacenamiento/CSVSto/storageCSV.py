import os
import csv

class StorageCSV:
    def __init__(self, filename='bench_data.csv'):
        self.filename = filename
        if os.path.exists(self.filename): os.remove(self.filename)

    def write(self, data_list):
        # CSV escribe rápido texto plano
        file_exists = os.path.isfile(self.filename)
        with open(self.filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data_list[0].keys())
            if not file_exists: writer.writeheader()
            writer.writerows(data_list)
    
    def get_size(self):
        return os.path.getsize(self.filename) / (1024 * 1024)