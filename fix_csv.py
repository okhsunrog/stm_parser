import pandas as pd
import re

def get_l0_series_line(part_number_str):
    """
    Определяет линейку STM32L0 (L0x0, L0x1, L0x2, L0x3) на основе part_number.
    """
    pn = str(part_number_str)
    if not pn.startswith("STM32L0"):
        return "Unknown_L0_Prefix" # Должно быть отфильтровано ранее

    # Извлекаем цифры после "STM32L0"
    match = re.match(r"STM32L0(\d{2})", pn)
    if not match:
        return "L0_Malformed_PN" # Не удалось извлечь цифры

    device_line_digits = match.group(1)

    if device_line_digits == "10":
        return "L0x0"  # Убрали " Value Line"
    elif device_line_digits in ["11", "21", "31", "41", "51", "61", "71", "81"]:
        # L0x1 включает STM32L0[1/2]1xxx (Cat 1), L0[3/4]1xxx (Cat 2), 
        # L0[5/6]1xxx (Cat 3), L0[7/8]1xxx (Cat 5)
        # Все они относятся к общей группе L0x1 по базовой периферии,
        # но могут иметь AES (21,41,61,81) или больше Flash/RAM/EEPROM (71,81)
        return "L0x1"
    elif device_line_digits in ["52", "62", "72", "82"]:
        # L0x2 (USB)
        return "L0x2"
    elif device_line_digits in ["53", "63", "73", "83"]:
        # L0x3 (USB + LCD)
        return "L0x3"
    else:
        print(f"Предупреждение: Неизвестная комбинация цифр для STM32L0: {device_line_digits} в {pn}")
        return "L0_Unknown_Digits"

def get_l1_series_line(part_number_str):
    """
    Определяет линейку STM32L1 (L100, L151, L152, L162) на основе part_number.
    """
    pn = str(part_number_str)
    if not pn.startswith("STM32L1"):
        return "Unknown_L1_Prefix"

    match = re.match(r"STM32L1(\d{2})", pn)
    if not match:
        return "L1_Malformed_PN"
    
    device_line_digits = match.group(1)
    
    if device_line_digits in ["00", "51", "52", "62"]: # L100, L151, L152, L162
        return f"L1{device_line_digits}"
    else:
        print(f"Предупреждение: Неизвестная комбинация цифр для STM32L1: {device_line_digits} в {pn}")
        return "L1_Unknown_Digits"


def correct_and_update_series_line(csv_filepath):
    """
    Читает CSV, корректирует столбец 'series_line' и сохраняет изменения.
    Также обновляет данные для L0x1, как в предыдущем скрипте.
    """
    try:
        # Читаем все как строки, чтобы сохранить форматирование и пустые ячейки
        df = pd.read_csv(csv_filepath, dtype=str) 
        df.fillna("", inplace=True) 
    except FileNotFoundError:
        print(f"Ошибка: Файл '{csv_filepath}' не найден.")
        return
    except Exception as e:
        print(f"Ошибка при чтении CSV файла '{csv_filepath}': {e}")
        return
    
    print(f"Прочитано {len(df)} записей из '{csv_filepath}'.")

    if 'part_number' not in df.columns:
        print("Ошибка: В CSV отсутствует столбец 'part_number'.")
        return
    if 'series_line' not in df.columns:
        print("Информация: В CSV отсутствует столбец 'series_line'. Он будет создан.")
        df['series_line'] = ""


    # Коррекция 'series_line'
    print("Коррекция столбца 'series_line'...")
    for index, row in df.iterrows():
        pn = str(row['part_number'])
        corrected_series = ""
        if pn.startswith("STM32L0"):
            corrected_series = get_l0_series_line(pn)
        elif pn.startswith("STM32L1"):
            corrected_series = get_l1_series_line(pn)
        else:
            corrected_series = row['series_line'] # Оставляем как есть, если не L0/L1

        if row['series_line'] != corrected_series:
            # print(f"  Изменение для {pn}: '{row['series_line']}' -> '{corrected_series}'")
            df.loc[index, 'series_line'] = corrected_series
            
    print("Столбец 'series_line' обновлен.")
    
    # --- Начало блока обновления данных для L0x1 (как в предыдущем скрипте) ---
    # Преобразуем числовые столбцы, необходимые для фильтров, во float/int
    # ошибки 'coerce' превратят нечисловые значения в NaN, затем fillna(0)
    numeric_cols_for_filter = ['flash_size_kb_prog', 'total_eeprom_b_from_export', 'ram_size_kb']
    for col in numeric_cols_for_filter:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    print("Обновление EEPROM данных для L0x1...")
    eeprom_bank1_addr = "0x08080000"
    eeprom_bank2_addr = "0x08080C00"
    l0x1_mask = df['series_line'] == "L0x1"

    # L0x1 Category 1
    cat1_mask = l0x1_mask & (df['flash_size_kb_prog'].isin([8, 16])) & (df['total_eeprom_b_from_export'] == 512)
    df.loc[cat1_mask, 'category_from_doc'] = 'Category 1'
    df.loc[cat1_mask, 'eeprom_bank1_start_addr'] = eeprom_bank1_addr
    df.loc[cat1_mask, 'eeprom_bank1_size_b'] = "512"
    df.loc[cat1_mask, 'eeprom_total_size_b_from_doc'] = "512"
    df.loc[cat1_mask, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""

    # L0x1 Category 2
    cat2_mask = l0x1_mask & (df['flash_size_kb_prog'].isin([16, 32])) & (df['total_eeprom_b_from_export'] == 1024)
    df.loc[cat2_mask, 'category_from_doc'] = 'Category 2'
    df.loc[cat2_mask, 'eeprom_bank1_start_addr'] = eeprom_bank1_addr
    df.loc[cat2_mask, 'eeprom_bank1_size_b'] = "1024"
    df.loc[cat2_mask, 'eeprom_total_size_b_from_doc'] = "1024"
    df.loc[cat2_mask, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""

    # L0x1 Category 3
    cat3_mask = l0x1_mask & (df['flash_size_kb_prog'].isin([32, 64])) & (df['total_eeprom_b_from_export'] == 2048)
    df.loc[cat3_mask, 'category_from_doc'] = 'Category 3'
    df.loc[cat3_mask, 'eeprom_bank1_start_addr'] = eeprom_bank1_addr
    df.loc[cat3_mask, 'eeprom_bank1_size_b'] = "2048"
    df.loc[cat3_mask, 'eeprom_total_size_b_from_doc'] = "2048"
    df.loc[cat3_mask, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""
    
    # L0x1 Category 5 (64KB Flash, EEPROM 3072B in Bank 2 only)
    cat5_64k_mask = l0x1_mask & (df['flash_size_kb_prog'] == 64) & (df['total_eeprom_b_from_export'] == 3072)
    df.loc[cat5_64k_mask, 'category_from_doc'] = 'Category 5 (64K Flash)'
    df.loc[cat5_64k_mask, ['eeprom_bank1_start_addr', 'eeprom_bank1_size_b']] = ""
    df.loc[cat5_64k_mask, 'eeprom_bank2_start_addr'] = eeprom_bank2_addr
    df.loc[cat5_64k_mask, 'eeprom_bank2_size_b'] = "3072"
    df.loc[cat5_64k_mask, 'eeprom_total_size_b_from_doc'] = "3072"

    # L0x1 Category 5 (128KB Flash / 192KB Flash, EEPROM 6144B total, 2 Banks of 3072B)
    cat5_large_mask = l0x1_mask & (df['flash_size_kb_prog'].isin([128, 192])) & (df['total_eeprom_b_from_export'] == 6144)
    # Динамическое формирование 'category_from_doc' для этих случаев
    df.loc[cat5_large_mask, 'category_from_doc'] = 'Category 5 (' + df.loc[cat5_large_mask, 'flash_size_kb_prog'].astype(int).astype(str) + 'K Flash)'
    df.loc[cat5_large_mask, 'eeprom_bank1_start_addr'] = eeprom_bank1_addr
    df.loc[cat5_large_mask, 'eeprom_bank1_size_b'] = "3072"
    df.loc[cat5_large_mask, 'eeprom_bank2_start_addr'] = eeprom_bank2_addr
    df.loc[cat5_large_mask, 'eeprom_bank2_size_b'] = "3072"
    df.loc[cat5_large_mask, 'eeprom_total_size_b_from_doc'] = "6144"
    
    print("Данные EEPROM для L0x1 обновлены.")
    # --- Конец блока обновления данных для L0x1 ---

    # Возвращаем числовые столбцы к строковому типу, чтобы сохранить "" вместо NaN и избежать ".0"
    # Это важно, так как мы читали все как dtype=str
    for col in df.columns:
        if col not in ['part_number', 'series_line', 'category_from_doc', 
                       'eeprom_bank1_start_addr', 'eeprom_bank2_start_addr', 
                       'eeprom_erase_value', 'notes', 
                       'rust_regex_map_key', 'rust_mem_entry']: # Столбцы, которые точно строки или могут быть HEX
            # Для остальных, если они были числами, но теперь могут быть объектами из-за пустых строк,
            # pandas.to_csv должен справиться с ними нормально.
            # Если хотим явно контролировать, чтобы числа не имели ".0",
            # можно преобразовать в Int64 (который поддерживает NA) и потом в строку, но это усложнит.
            # Проще всего оставить как есть после fillna("") и read_csv(dtype=str)
            pass


    try:
        df.to_csv(csv_filepath, index=False, encoding='utf-8')
        print(f"Файл '{csv_filepath}' успешно обновлен. Записей: {len(df)}.")
    except Exception as e:
        print(f"Ошибка при сохранении обновленного CSV файла '{csv_filepath}': {e}")

if __name__ == "__main__":
    research_csv_file = "stm32_l0_l1_eeprom_research.csv"
    try:
        # Проверяем, что файл существует
        with open(research_csv_file, 'r') as f:
            pass
        correct_and_update_series_line(research_csv_file)
    except FileNotFoundError:
        print(f"Файл '{research_csv_file}' не найден. Пожалуйста, сначала создайте его.")
