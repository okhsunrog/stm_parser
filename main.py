import pandas as pd
import pprint
import glob # Для поиска файлов по шаблону

def parse_csv_product_list(filepath):
    """
    Парсит данные о продуктах из CSV файла с учетом специфической структуры заголовков.
    """
    try:
        df = pd.read_csv(filepath, header=0, skiprows=[1])
        df = df.fillna('') # Заменяем NaN на пустые строки для консистентности

        # Начальная очистка имен столбцов (snake_case, удаление спецсимволов)
        cleaned_column_names = {}
        for original_col_name in df.columns:
            new_name = str(original_col_name).strip().lower()
            new_name = new_name.replace(' ', '_').replace('-', '_')
            new_name = new_name.replace('(', '').replace(')', '').replace('/', '_').replace('.', '_') # . -> _
            new_name = new_name.replace('@', 'at') # Заменяем @
            new_name = new_name.replace('µ', 'u')  # Заменяем µ на u
            new_name = new_name.replace('°', 'deg') # Заменяем ° на deg
            
            # Убираем суффиксы _typ, _nom
            if new_name.endswith('_typ'):
                new_name = new_name[:-4]
            if new_name.endswith('_nom'):
                new_name = new_name[:-4]
            
            # Убираем суффиксы типа _1, _2 от pandas для дублирующихся "Unnamed" столбцов
            # Это более общая очистка для "unnamed_X"
            if new_name.startswith("unnamed_") and new_name.split('_')[-1].isdigit():
                 # Мы оставим этот столбец пока с таким именем, переименуем его ниже более точно
                 pass # Пока не трогаем, разберемся ниже по контексту
            
            cleaned_column_names[original_col_name] = new_name
        
        df.rename(columns=cleaned_column_names, inplace=True)

        # Теперь более точное переименование столбцов, которые могли стать "unnamed_X"
        # или для которых нужно объединить информацию из многоуровневого заголовка
        
        # Для "A/D Converters 12-bit" и следующего за ним (бывший "Number of Channels typ")
        target_base_col_adc = 'a_d_converters_12_bit'
        columns_list = list(df.columns)
        
        try:
            idx_adc_base = columns_list.index(target_base_col_adc)
            # Следующий столбец должен быть "Number of Channels typ"
            if idx_adc_base + 1 < len(columns_list):
                col_for_channels_original_name_in_df = columns_list[idx_adc_base + 1]
                # Переименовываем его в любом случае, если он следует за target_base_col_adc
                df.rename(columns={col_for_channels_original_name_in_df: target_base_col_adc + '_number_of_channels'}, inplace=True)
                print(f"Столбец '{col_for_channels_original_name_in_df}' переименован в '{target_base_col_adc}_number_of_channels'.")
                # Столбец target_base_col_adc (бывший "A/D Converters 12-bit") переименуем в "a_d_converters_12_bit_converters"
                df.rename(columns={target_base_col_adc: target_base_col_adc + '_converters'}, inplace=True)
                print(f"Столбец '{target_base_col_adc}' переименован в '{target_base_col_adc}_converters'.")

        except ValueError:
            print(f"Предупреждение: Не удалось найти базовый столбец '{target_base_col_adc}' для переименования столбцов A/D конвертера в файле {filepath}.")
        except IndexError:
            print(f"Предупреждение: Недостаточно столбцов после '{target_base_col_adc}' для переименования каналов A/D в файле {filepath}.")


        products_data = df.to_dict(orient='records')
        return products_data

    except FileNotFoundError:
        print(f"Ошибка: Файл не найден по пути: {filepath}")
        return []
    except Exception as e:
        print(f"Ошибка при парсинге CSV файла {filepath}: {e}")
        return []

# --- Основное выполнение ---
if __name__ == "__main__":
    # Ищем все CSV файлы, начинающиеся с "ProductsList_L"
    csv_files = glob.glob("ProductsList_L*.csv")
    
    if not csv_files:
        print("Не найдены CSV файлы по шаблону 'ProductsList_L*.csv'")
    else:
        print(f"Найдены следующие CSV файлы для обработки: {csv_files}")

    all_products_data = []
    for csv_file_path in csv_files:
        print(f"\n--- Обработка файла: {csv_file_path} ---")
        product_data_from_file = parse_csv_product_list(csv_file_path)
        if product_data_from_file:
            print(f"Из файла '{csv_file_path}' извлечено записей: {len(product_data_from_file)}")
            all_products_data.extend(product_data_from_file)
        else:
            print(f"Не удалось извлечь данные из файла: {csv_file_path}")

    if all_products_data:
        print(f"\n--- Всего собрано записей о продуктах: {len(all_products_data)} ---")

        if len(all_products_data) > 0:
            print("\nДанные первых 2 продуктов (из общего списка):")
            pprint.pprint(all_products_data[:2])

            # Создаем Pandas DataFrame из общего списка словарей
            final_df = pd.DataFrame(all_products_data)
            
            # Проверим типы данных и попытаемся преобразовать строки в числа, где это возможно
            # Это важно для корректной записи в Parquet и для дальнейшего анализа
            for col in final_df.columns:
                # Попытка преобразовать в числовой тип, если это возможно
                # errors='ignore' оставит столбец как есть, если преобразование не удалось
                final_df[col] = pd.to_numeric(final_df[col], errors='ignore')

            parquet_output_path = "all_stm_products.parquet"
            try:
                final_df.to_parquet(parquet_output_path, engine='pyarrow', index=False)
                print(f"\nВсе данные успешно сохранены в Parquet файл: {parquet_output_path}")
            except Exception as e:
                print(f"Ошибка при сохранении в Parquet файл: {e}")
    else:
        print("\nНе удалось собрать данные ни из одного файла.")
