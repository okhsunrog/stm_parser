import pandas as pd
import re

def extract_series_line(part_number_str):
    """
    Извлекает основную серию и линейку из part_number.
    """
    part_number = str(part_number_str)
    
    if part_number.startswith("STM32L0"):
        match_l0 = re.match(r"STM32L0(\d{2})", part_number)
        if not match_l0:
            return "L0_Malformed_PN"
        device_line_digits = match_l0.group(1)
        if device_line_digits == "10":
            return "L0x0"
        elif device_line_digits in ["11", "21", "31", "41", "51", "61", "71", "81"]:
            return "L0x1"
        elif device_line_digits in ["52", "62", "72", "82"]:
            return "L0x2"
        elif device_line_digits in ["53", "63", "73", "83"]:
            return "L0x3"
        else:
            return "L0_Unknown_Digits"
            
    elif part_number.startswith("STM32L1"):
        match_l1 = re.match(r"STM32L1(\d{2})", part_number)
        if not match_l1:
            return "L1_Malformed_PN"
        device_line_digits = match_l1.group(1)
        # L100, L151, L152, L162
        if device_line_digits in ["00", "51", "52", "62"]: 
            return f"L1{device_line_digits}"
        else:
            # Для L1 могут быть и другие, например, STM32L151xD (Cat 4), STM32L151xE (Cat 5)
            # Пока оставляем так, но эту логику можно будет уточнить при необходимости
            # для более детальной классификации L1.
            # Сейчас главное - отделить L1 от L0.
            return f"L1{device_line_digits}" # Возвращаем L1XX
    return "Unknown_Series"


def create_eeprom_research_csv(parquet_filepath, output_csv_filepath):
    try:
        df = pd.read_parquet(parquet_filepath)
    except Exception as e:
        print(f"Ошибка чтения Parquet файла '{parquet_filepath}': {e}")
        return

    print(f"Прочитано {len(df)} записей из Parquet файла '{parquet_filepath}'.")

    # Фильтруем только L0 и L1 серии и те, у кого есть EEPROM
    # (столбец data_e2prom_b из вашего парсинга pandas)
    # Убедимся, что data_e2prom_b числовой для фильтрации
    df['data_e2prom_b'] = pd.to_numeric(df['data_e2prom_b'], errors='coerce').fillna(0)

    df_filtered = df[
        (df['part_number'].str.startswith('STM32L0') | df['part_number'].str.startswith('STM32L1')) &
        (df['data_e2prom_b'] > 0)
    ].copy()

    if df_filtered.empty:
        print("Не найдено МК L0/L1 с информацией о EEPROM (>0 байт) в Parquet файле.")
        return

    print(f"Найдено {len(df_filtered)} МК L0/L1 с EEPROM для создания исследовательского CSV.")

    # Создаем новый DataFrame с нужными столбцами
    research_df = pd.DataFrame()
    research_df['part_number'] = df_filtered['part_number']
    
    research_df['series_line'] = df_filtered['part_number'].apply(extract_series_line)
    
    # Копируем существующие полезные поля
    # Убедимся, что эти столбцы существуют в вашем df_filtered
    cols_to_copy = ['flash_size_kb_prog', 'ram_size_kb', 'data_e2prom_b']
    for col in cols_to_copy:
        if col in df_filtered.columns:
            research_df[col.replace('data_e2prom_b', 'total_eeprom_b_from_export')] = df_filtered[col]
        else:
            print(f"Предупреждение: столбец '{col}' не найден в Parquet, будет пропущен.")
            research_df[col.replace('data_e2prom_b', 'total_eeprom_b_from_export')] = ""


    # Добавляем пустые столбцы для ручного заполнения
    research_df['category_from_doc'] = ""
    research_df['eeprom_bank1_start_addr'] = ""
    research_df['eeprom_bank1_size_b'] = ""
    research_df['eeprom_bank2_start_addr'] = "" 
    research_df['eeprom_bank2_size_b'] = ""   
    research_df['eeprom_total_size_b_from_doc'] = ""
    research_df['eeprom_write_size_b'] = ""
    research_df['eeprom_erase_value'] = ""
    research_df['notes'] = ""
    research_df['rust_regex_map_key'] = ""
    research_df['rust_mem_entry'] = ""
    
    # Переупорядочиваем столбцы для удобства
    column_order = [
        'part_number', 'series_line', 'category_from_doc', 
        'flash_size_kb_prog', 'ram_size_kb', 
        'total_eeprom_b_from_export', 'eeprom_total_size_b_from_doc',
        'eeprom_bank1_start_addr', 'eeprom_bank1_size_b',
        'eeprom_bank2_start_addr', 'eeprom_bank2_size_b',
        'eeprom_write_size_b', 'eeprom_erase_value',
        'notes', 'rust_regex_map_key', 'rust_mem_entry'
    ]
    # Убедимся, что все столбцы из column_order присутствуют в research_df перед переупорядочиванием
    final_columns = [col for col in column_order if col in research_df.columns]
    research_df = research_df[final_columns]


    try:
        research_df.to_csv(output_csv_filepath, index=False, encoding='utf-8')
        print(f"Создан/перезаписан CSV файл для исследования EEPROM: {output_csv_filepath}")
        print(f"В файл записано {len(research_df)} строк.")
    except Exception as e:
        print(f"Ошибка при сохранении CSV файла '{output_csv_filepath}': {e}")

if __name__ == "__main__":
    parquet_file = "all_stm_products.parquet" # Убедитесь, что этот файл обновлен
    output_csv_for_research = "stm32_l0_l1_eeprom_research.csv" # Этот файл будет перезаписан
    create_eeprom_research_csv(parquet_file, output_csv_for_research)
