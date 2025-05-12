import pandas as pd
import re

def extract_series_line(part_number_str):
    """
    Извлекает основную серию и линейку из part_number.
    Пример: STM32L071RBT6 -> L0x1 (если STM32L071...), STM32L151CBU6 -> L151
    Это эвристика, возможно, потребует доработки.
    """
    part_number = str(part_number_str) # Убедимся, что это строка
    if part_number.startswith("STM32L0"):
        # Эвристика для L0: STM32L0<Digit1><Digit2>...
        # Digit1 (третья цифра после L0) обычно указывает на "категорию" или линейку
        # 1,2 -> x1 (STM32L01x, STM32L02x)
        # 3,4 -> x1 (STM32L03x, STM32L04x)
        # 5,6 -> x1, x2, x3 (STM32L05x, STM32L06x)
        # 7,8 -> x1, x2, x3 (STM32L07x, STM32L08x)
        # 0 -> x0 (STM32L010 Value line)
        
        # Более простой подход: берем L0 и следующую цифру, если она не 0, то это x<digit>
        # если 0, то L0x0.
        # Для STM32L0x1, STM32L0x2, STM32L0x3 - они часто группируются.
        # Для простоты пока можем сделать L0<первые две цифры после L0>
        match_l0 = re.search(r"STM32L0(\d{2})", part_number)
        if match_l0:
            sub_family_digits = match_l0.group(1)
            # Основываясь на вашем исследовании:
            if sub_family_digits in ["10"]: # STM32L010xx Value Line
                return "L0x0 Value Line"
            elif sub_family_digits in ["11", "21", "31", "41", "51", "61", "71", "81"]: # STM32L0x1
                return "L0x1"
            elif sub_family_digits in ["52", "62", "72", "82"]: # STM32L0x2 USB
                return "L0x2"
            elif sub_family_digits in ["53", "63", "73", "83"]: # STM32L0x3 USB/LCD
                return "L0x3"
            else: # Общий случай, если эвристика не покрыла
                return f"L0_{sub_family_digits}" # Например, L0_51, L0_71
        return "L0_Unknown"
        
    elif part_number.startswith("STM32L1"):
        # Для L1: STM32L1<Digit1><Digit2>...
        match_l1 = re.search(r"STM32L1(\d{2})", part_number)
        if match_l1:
            return f"L1{match_l1.group(1)}" # Например, L100, L151, L152, L162
        return "L1_Unknown"
    return "Unknown"


def create_eeprom_research_csv(parquet_filepath, output_csv_filepath):
    try:
        df = pd.read_parquet(parquet_filepath)
    except Exception as e:
        print(f"Ошибка чтения Parquet файла '{parquet_filepath}': {e}")
        return

    print(f"Прочитано {len(df)} записей из Parquet.")

    # Оставляем только те, где есть информация о EEPROM (data_e2prom_b > 0)
    # и это L0 или L1
    df_eeprom = df[
        (df['data_e2prom_b'].fillna(0) > 0) & 
        (df['part_number'].str.startswith('STM32L0') | df['part_number'].str.startswith('STM32L1'))
    ].copy() # Используем .copy() чтобы избежать SettingWithCopyWarning

    if df_eeprom.empty:
        print("Не найдено МК L0/L1 с информацией о EEPROM в Parquet файле.")
        return

    print(f"Найдено {len(df_eeprom)} МК L0/L1 с EEPROM для дальнейшего исследования.")

    # Создаем новый DataFrame с нужными столбцами
    research_df = pd.DataFrame()
    research_df['part_number'] = df_eeprom['part_number']
    
    # Применяем функцию для извлечения серии/линейки
    research_df['series_line'] = df_eeprom['part_number'].apply(extract_series_line)
    
    research_df['flash_size_kb_prog'] = df_eeprom['flash_size_kb_prog']
    research_df['ram_size_kb'] = df_eeprom['ram_size_kb']
    research_df['total_eeprom_b_from_export'] = df_eeprom['data_e2prom_b']

    # Добавляем пустые столбцы для ручного заполнения
    research_df['category_from_doc'] = ""
    research_df['eeprom_bank1_start_addr'] = ""
    research_df['eeprom_bank1_size_b'] = ""
    research_df['eeprom_bank2_start_addr'] = "" # Будет NA если нет второго банка
    research_df['eeprom_bank2_size_b'] = ""   # Будет NA если нет второго банка
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
    research_df = research_df[column_order]

    try:
        research_df.to_csv(output_csv_filepath, index=False, encoding='utf-8')
        print(f"Создан CSV файл для исследования EEPROM: {output_csv_filepath}")
    except Exception as e:
        print(f"Ошибка при сохранении CSV файла '{output_csv_filepath}': {e}")

if __name__ == "__main__":
    parquet_file = "all_stm_products.parquet"
    output_csv_for_research = "stm32_l0_l1_eeprom_research.csv"
    create_eeprom_research_csv(parquet_file, output_csv_for_research)
