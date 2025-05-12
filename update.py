import pandas as pd
import re

# Функции get_l0_series_line и get_l1_series_line остаются такими же
def get_l0_series_line(part_number_str):
    pn = str(part_number_str)
    if not pn.startswith("STM32L0"): return "Unknown_L0_Prefix"
    match = re.match(r"STM32L0(\d{2})", pn)
    if not match: return "L0_Malformed_PN"
    digits = match.group(1)
    if digits == "10": return "L0x0"
    elif digits in ["11", "21", "31", "41", "51", "61", "71", "81"]: return "L0x1"
    elif digits in ["52", "62", "72", "82"]: return "L0x2"
    elif digits in ["53", "63", "73", "83"]: return "L0x3"
    else: return "L0_Unknown_Digits"

def get_l1_series_line(part_number_str):
    pn = str(part_number_str)
    if not pn.startswith("STM32L1"): return "Unknown_L1_Prefix"
    match = re.match(r"STM32L1(\d{2})", pn)
    if not match: return "L1_Malformed_PN"
    digits = match.group(1)
    if digits in ["00", "51", "52", "62"]: return f"L1{digits}"
    else: return f"L1{digits}"

def update_l0x2_data_in_csv(csv_filepath):
    """
    Читает CSV и обновляет данные EEPROM ТОЛЬКО для линейки L0x2.
    Предполагается, что series_line уже корректно заполнена.
    """
    try:
        df = pd.read_csv(csv_filepath, dtype=str)
        df.fillna("", inplace=True)
    except FileNotFoundError:
        print(f"Ошибка: Файл '{csv_filepath}' не найден.")
        return
    except Exception as e:
        print(f"Ошибка при чтении CSV файла '{csv_filepath}': {e}")
        return
    
    print(f"Прочитано {len(df)} записей из '{csv_filepath}'.")

    # Преобразуем числовые столбцы для фильтров
    numeric_cols_for_filter = ['flash_size_kb_prog', 'total_eeprom_b_from_export']
    for col in numeric_cols_for_filter:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            print(f"Предупреждение: столбец '{col}' отсутствует для преобразования в число.")
            # Если столбец отсутствует, создадим его с нулями, чтобы фильтры не падали
            df[col] = 0


    print("Обновление данных EEPROM для L0x2...")
    l0x2_mask = df['series_line'] == "L0x2"
    eeprom_base_addr = "0x08080000"
    eeprom_bank2_addr_cat5 = "0x08080C00"
    
    if not df[l0x2_mask].empty:
        print(f"Найдено {len(df[l0x2_mask])} МК серии L0x2 для обновления EEPROM.")
    else:
        print("МК серии L0x2 не найдены. Обновление для L0x2 не будет произведено.")
        # Файл все равно нужно сохранить, если series_line могла быть обновлена ранее
        # Но в этом скрипте мы series_line не трогаем, только читаем
        return # Выходим, если нет L0x2 строк

    # L0x2 Category 3 (STM32L052x, STM32L062x)
    # Flash 32KB/64KB, EEPROM 2048B (2KB)
    cat3_mask_l0x2 = l0x2_mask & \
                     (df['flash_size_kb_prog'].isin([32, 64])) & \
                     (df['total_eeprom_b_from_export'] == 2048)
    df.loc[cat3_mask_l0x2, 'category_from_doc'] = 'Category 3 (L0x2)'
    df.loc[cat3_mask_l0x2, 'eeprom_bank1_start_addr'] = eeprom_base_addr
    df.loc[cat3_mask_l0x2, 'eeprom_bank1_size_b'] = "2048"
    df.loc[cat3_mask_l0x2, 'eeprom_total_size_b_from_doc'] = "2048"
    df.loc[cat3_mask_l0x2, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""

    # L0x2 Category 5 (STM32L072x, STM32L082x)
    # --- Flash 64KB, EEPROM 3072B (3KB) in Bank 2 only ---
    cat5_64k_mask_l0x2 = l0x2_mask & \
                         (df['flash_size_kb_prog'] == 64) & \
                         (df['total_eeprom_b_from_export'] == 3072)
    df.loc[cat5_64k_mask_l0x2, 'category_from_doc'] = 'Category 5 (L0x2 64K Flash)'
    df.loc[cat5_64k_mask_l0x2, ['eeprom_bank1_start_addr', 'eeprom_bank1_size_b']] = ""
    df.loc[cat5_64k_mask_l0x2, 'eeprom_bank2_start_addr'] = eeprom_bank2_addr_cat5
    df.loc[cat5_64k_mask_l0x2, 'eeprom_bank2_size_b'] = "3072"
    df.loc[cat5_64k_mask_l0x2, 'eeprom_total_size_b_from_doc'] = "3072"

    # --- Flash 128KB/192KB, EEPROM 6144B (6KB) total, 2 Banks of 3072B ---
    cat5_large_mask_l0x2 = l0x2_mask & \
                           (df['flash_size_kb_prog'].isin([128, 192])) & \
                           (df['total_eeprom_b_from_export'] == 6144)
    df.loc[cat5_large_mask_l0x2, 'category_from_doc'] = 'Category 5 (L0x2 ' + df.loc[cat5_large_mask_l0x2, 'flash_size_kb_prog'].astype(int).astype(str) + 'K Flash)'
    df.loc[cat5_large_mask_l0x2, 'eeprom_bank1_start_addr'] = eeprom_base_addr
    df.loc[cat5_large_mask_l0x2, 'eeprom_bank1_size_b'] = "3072"
    df.loc[cat5_large_mask_l0x2, 'eeprom_bank2_start_addr'] = eeprom_bank2_addr_cat5
    df.loc[cat5_large_mask_l0x2, 'eeprom_bank2_size_b'] = "3072"
    df.loc[cat5_large_mask_l0x2, 'eeprom_total_size_b_from_doc'] = "6144"
    
    print("Данные EEPROM для L0x2 обновлены.")

    try:
        df.to_csv(csv_filepath, index=False, encoding='utf-8')
        print(f"Файл '{csv_filepath}' успешно обновлен. Записей: {len(df)}.")
    except Exception as e:
        print(f"Ошибка при сохранении обновленного CSV файла '{csv_filepath}': {e}")

if __name__ == "__main__":
    research_csv_file = "stm32_l0_l1_eeprom_research.csv"
    
    try:
        # Проверка существования файла
        with open(research_csv_file, 'r', encoding='utf-8') as f:
            pass 
        update_l0x2_data_in_csv(research_csv_file)
    except FileNotFoundError:
        print(f"Файл '{research_csv_file}' не найден. Пожалуйста, сначала создайте его и убедитесь, что 'series_line' корректно заполнено.")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")
