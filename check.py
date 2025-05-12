import pandas as pd
import pprint

def read_random_samples_from_parquet(filepath, num_samples=10):
    """
    Читает указанное количество случайных строк из Parquet файла.

    Args:
        filepath (str): Путь к .parquet файлу.
        num_samples (int): Количество случайных строк для извлечения.

    Returns:
        list: Список словарей со случайными строками или пустой список при ошибке.
    """
    try:
        # Читаем Parquet файл в pandas DataFrame
        df = pd.read_parquet(filepath)

        if df.empty:
            print(f"Файл Parquet '{filepath}' пуст.")
            return []

        if len(df) < num_samples:
            print(f"В файле меньше строк ({len(df)}), чем запрошено ({num_samples}). Будут выведены все строки.")
            sample_df = df
        else:
            # Извлекаем случайные строки
            sample_df = df.sample(n=num_samples, random_state=42) # random_state для воспроизводимости
        
        # Преобразуем сэмплированный DataFrame в список словарей
        sample_data = sample_df.to_dict(orient='records')
        return sample_data

    except FileNotFoundError:
        print(f"Ошибка: Файл не найден по пути: {filepath}")
        return []
    except Exception as e:
        print(f"Ошибка при чтении Parquet файла: {e}")
        return []

# --- Основное выполнение ---
if __name__ == "__main__":
    parquet_file_path = "all_stm_products.parquet"
    number_of_random_rows = 10

    random_product_samples = read_random_samples_from_parquet(parquet_file_path, num_samples=number_of_random_rows)

    if random_product_samples:
        print(f"\n--- {number_of_random_rows} случайных записей из '{parquet_file_path}' ---")
        pprint.pprint(random_product_samples)
        
        print(f"\nВсего извлечено случайных записей: {len(random_product_samples)}")
    else:
        print(f"\nНе удалось извлечь случайные данные из Parquet файла: {parquet_file_path}")
