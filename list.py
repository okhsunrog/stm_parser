import pandas as pd

def print_all_part_numbers_from_parquet(parquet_filepath):
    """
    Читает Parquet файл и выводит список всех уникальных part_number.
    """
    try:
        df = pd.read_parquet(parquet_filepath)
        print(f"Прочитано {len(df)} записей из '{parquet_filepath}'.")

        if 'part_number' not in df.columns:
            print("Ошибка: Столбец 'part_number' не найден в Parquet файле.")
            return

        # Получаем уникальные part_number и сортируем их для удобства
        unique_part_numbers = sorted(df['part_number'].unique())
        
        print(f"\n--- Уникальные Part Numbers ({len(unique_part_numbers)}): ---")
        for pn in unique_part_numbers:
            print(pn)

    except FileNotFoundError:
        print(f"Ошибка: Файл не найден по пути: {parquet_filepath}")
    except Exception as e:
        print(f"Ошибка при чтении или обработке Parquet файла: {e}")

if __name__ == "__main__":
    parquet_file = "all_stm_products.parquet"
    print_all_part_numbers_from_parquet(parquet_file)
