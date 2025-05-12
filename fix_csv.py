import pandas as pd
import re

def correct_series_line_l0(part_number_str):
    """
    Более точное извлечение series_line для STM32L0.
    """
    part_number = str(part_number_str)
    if not part_number.startswith("STM32L0"):
        return "Unknown" # Или вернуть исходное значение, если это не L0

    # STM32L010xx - это Value Line
    if re.match(r"STM32L010", part_number):
        return "L0x0 Value Line"
    
    # STM32L0x1 (базовая периферия)
    # STM32L011, L021 (AES), L031, L041 (AES), L051, L061 (AES)
    if re.match(r"STM32L0(11|21|31|41|51|61)", part_number):
        return "L0x1"
        
    # STM32L0x2 (USB)
    # STM32L052, L062 (AES), L072, L082 (AES)
    if re.match(r"STM32L0(52|62|72|82)", part_number):
        return "L0x2"

    # STM32L0x3 (USB + LCD)
    # STM32L053, L063 (AES), L073, L083 (AES)
    if re.match(r"STM32L0(53|63|73|83)", part_number):
        return "L0x3"
        
    # Если не подошло под специфичные, возвращаем общий L0 (маловероятно после фильтров)
    return "L0_Other"


def update_l0x1_eeprom_data(df):
    """
    Обновляет данные EEPROM для линейки L0x1 на основе исследования.
    """
    print("Обновление данных для L0x1...")
    
    # Базовые адреса для L0x1
    eeprom_bank1_addr = "0x08080000"
    eeprom_bank2_addr = "0x08080C00"

    # Обновляем series_line для всех L0
    l0_mask = df['part_number'].str.startswith('STM32L0')
    df.loc[l0_mask, 'series_line'] = df.loc[l0_mask, 'part_number'].apply(correct_series_line_l0)
    print("Поле 'series_line' для STM32L0 обновлено.")

    # Фильтруем только L0x1 для специфичных обновлений EEPROM
    l0x1_mask = df['series_line'] == "L0x1"
    
    if not df[l0x1_mask].empty:
        print(f"Найдено {len(df[l0x1_mask])} МК серии L0x1 для обновления EEPROM.")
    else:
        print("МК серии L0x1 не найдены для обновления EEPROM.")
        return df

    # L0x1 Category 1 (Flash 8KB/16KB, EEPROM 512B)
    # Part numbers: STM32L011xx, STM32L021xx
    cat1_mask_l0x1 = l0x1_mask & \
                     (df['flash_size_kb_prog'].isin([8, 16])) & \
                     (df['total_eeprom_b_from_export'] == 512)
    df.loc[cat1_mask_l0x1, 'category_from_doc'] = 'Category 1'
    df.loc[cat1_mask_l0x1, 'eeprom_bank1_start_addr'] = eeprom_bank1_addr
    df.loc[cat1_mask_l0x1, 'eeprom_bank1_size_b'] = 512
    df.loc[cat1_mask_l0x1, 'eeprom_total_size_b_from_doc'] = 512
    # Bank 2 не используется
    df.loc[cat1_mask_l0x1, 'eeprom_bank2_start_addr'] = "" 
    df.loc[cat1_mask_l0x1, 'eeprom_bank2_size_b'] = ""

    # L0x1 Category 2 (Flash 16KB/32KB, EEPROM 1024B)
    # Part numbers: STM32L031xx, STM32L041xx
    cat2_mask_l0x1 = l0x1_mask & \
                     (df['flash_size_kb_prog'].isin([16, 32])) & \
                     (df['total_eeprom_b_from_export'] == 1024)
    df.loc[cat2_mask_l0x1, 'category_from_doc'] = 'Category 2'
    df.loc[cat2_mask_l0x1, 'eeprom_bank1_start_addr'] = eeprom_bank1_addr
    df.loc[cat2_mask_l0x1, 'eeprom_bank1_size_b'] = 1024
    df.loc[cat2_mask_l0x1, 'eeprom_total_size_b_from_doc'] = 1024
    df.loc[cat2_mask_l0x1, 'eeprom_bank2_start_addr'] = ""
    df.loc[cat2_mask_l0x1, 'eeprom_bank2_size_b'] = ""

    # L0x1 Category 3 (Flash 32KB/64KB, EEPROM 2048B)
    # Part numbers: STM32L051xx, STM32L061xx (AES)
    cat3_mask_l0x1 = l0x1_mask & \
                     (df['flash_size_kb_prog'].isin([32, 64])) & \
                     (df['total_eeprom_b_from_export'] == 2048)
    df.loc[cat3_mask_l0x1, 'category_from_doc'] = 'Category 3'
    df.loc[cat3_mask_l0x1, 'eeprom_bank1_start_addr'] = eeprom_bank1_addr
    df.loc[cat3_mask_l0x1, 'eeprom_bank1_size_b'] = 2048
    df.loc[cat3_mask_l0x1, 'eeprom_total_size_b_from_doc'] = 2048
    df.loc[cat3_mask_l0x1, 'eeprom_bank2_start_addr'] = ""
    df.loc[cat3_mask_l0x1, 'eeprom_bank2_size_b'] = ""
    
    # L0x1 Category 5 (64KB Flash, EEPROM 3072B in Bank 2)
    # Part numbers: STM32L071xx (где Flash=64KB), STM32L081xx (где Flash=64KB)
    # Важно: total_eeprom_b_from_export для них должен быть 3072
    cat5_64k_mask_l0x1 = l0x1_mask & \
                         (df['flash_size_kb_prog'] == 64) & \
                         (df['total_eeprom_b_from_export'] == 3072) & \
                         (df['part_number'].str.contains(r'STM32L0[78]1', regex=True)) # Уточняем, что это L071/L081
    df.loc[cat5_64k_mask_l0x1, 'category_from_doc'] = 'Category 5 (64K Flash)'
    df.loc[cat5_64k_mask_l0x1, 'eeprom_bank1_start_addr'] = "" # Нет Bank1 EEPROM
    df.loc[cat5_64k_mask_l0x1, 'eeprom_bank1_size_b'] = ""
    df.loc[cat5_64k_mask_l0x1, 'eeprom_bank2_start_addr'] = eeprom_bank2_addr
    df.loc[cat5_64k_mask_l0x1, 'eeprom_bank2_size_b'] = 3072
    df.loc[cat5_64k_mask_l0x1, 'eeprom_total_size_b_from_doc'] = 3072

    # L0x1 Category 5 (128KB Flash / 192KB Flash, EEPROM 6144B total, 2 Banks of 3072B)
    # Part numbers: STM32L071xx, STM32L081xx (где Flash=128KB или 192KB)
    cat5_large_mask_l0x1 = l0x1_mask & \
                            (df['flash_size_kb_prog'].isin([128, 192])) & \
                            (df['total_eeprom_b_from_export'] == 6144) & \
                            (df['part_number'].str.contains(r'STM32L0[78]1', regex=True))
    df.loc[cat5_large_mask_l0x1, 'category_from_doc'] = 'Category 5 (' + df.loc[cat5_large_mask_l0x1, 'flash_size_kb_prog'].astype(str) + 'K Flash)'
    df.loc[cat5_large_mask_l0x1, 'eeprom_bank1_start_addr'] = eeprom_bank1_addr
    df.loc[cat5_large_mask_l0x1, 'eeprom_bank1_size_b'] = 3072
    df.loc[cat5_large_mask_l0x1, 'eeprom_bank2_start_addr'] = eeprom_bank2_addr
    df.loc[cat5_large_mask_l0x1, 'eeprom_bank2_size_b'] = 3072
    df.loc[cat5_large_mask_l0x1, 'eeprom_total_size_b_from_doc'] = 6144
    
    print("Данные для L0x1 обновлены.")
    return df

def modify_research_csv(csv_filepath):
    try:
        df = pd.read_csv(csv_filepath, dtype=str) # Читаем все как строки, чтобы сохранить форматирование пустых ячеек
        df.fillna("", inplace=True) # Заменяем NaN, которые могли появиться при чтении, на пустые строки
    except FileNotFoundError:
        print(f"Ошибка: Файл '{csv_filepath}' не найден.")
        return
    except Exception as e:
        print(f"Ошибка при чтении CSV файла '{csv_filepath}': {e}")
        return
    
    original_row_count = len(df)
    print(f"Прочитано {original_row_count} записей из '{csv_filepath}'.")

    # Преобразуем числовые столбцы для расчетов, но сохраним их как строки при записи, если они были строками
    # Или можно просто работать с ними как с числами и pandas сам выберет тип при записи
    numeric_cols_for_filter = ['flash_size_kb_prog', 'total_eeprom_b_from_export']
    for col in numeric_cols_for_filter:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0) # fillna(0) чтобы избежать проблем с NaN в условиях

    # Обновление данных для L0x1
    df = update_l0x1_eeprom_data(df.copy()) # Передаем копию, чтобы избежать SettingWithCopyWarning

    # Приводим обратно к строкам те столбцы, которые должны быть строками или могут быть пустыми,
    # чтобы избежать '.0' для целых чисел при сохранении, если они были прочитаны как float из-за NaN
    cols_to_ensure_object_or_int_string = [
        'flash_size_kb_prog', 'ram_size_kb', 'total_eeprom_b_from_export',
        'eeprom_bank1_size_b', 'eeprom_bank2_size_b', 'eeprom_total_size_b_from_doc',
        'eeprom_write_size_b'
    ]
    for col in cols_to_ensure_object_or_int_string:
        if col in df.columns:
            # Если столбец числовой и не содержит NaN после операций, преобразуем в int, потом в str
            # Если есть NaN или нечисловые, оставляем как object (pandas сам разберется)
            # Это немного сложно, так как мы хотим сохранить пустые строки как пустые, а числа как числа без .0
            # Самый простой путь - оставить как есть и позволить to_csv решить, или вручную форматировать
            pass # Pandas to_csv обычно неплохо справляется. Если нужно точнее, можно здесь добавить логику.


    try:
        df.to_csv(csv_filepath, index=False, encoding='utf-8')
        print(f"Файл '{csv_filepath}' успешно обновлен. Записей: {len(df)}.")
    except Exception as e:
        print(f"Ошибка при сохранении обновленного CSV файла '{csv_filepath}': {e}")

if __name__ == "__main__":
    research_csv_file = "stm32_l0_l1_eeprom_research.csv"
    
    # Перед модификацией, убедимся, что файл существует. 
    # Если нет, его нужно сначала создать скриптом из предыдущего ответа.
    try:
        # Пробное чтение, чтобы убедиться, что файл существует
        pd.read_csv(research_csv_file, nrows=1) 
        modify_research_csv(research_csv_file)
    except FileNotFoundError:
        print(f"Файл '{research_csv_file}' не найден. Пожалуйста, сначала создайте его с помощью предыдущего скрипта.")
