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
    if digits in ["00", "51", "52", "62"]: 
        return f"L1{digits}"
    else: 
        return f"L1{digits}" 


def update_l1_eeprom_data_in_csv(csv_filepath):
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

    numeric_cols_for_filter = ['flash_size_kb_prog', 'total_eeprom_b_from_export', 'ram_size_kb']
    for col in numeric_cols_for_filter:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        else:
            df[col] = 0

    print("Обновление данных EEPROM для STM32L1...")
    l1_overall_mask = df['part_number'].str.startswith('STM32L1')
    
    if not df[l1_overall_mask].empty:
        print(f"Найдено {len(df[l1_overall_mask])} МК серии STM32L1 для обновления EEPROM.")
    else:
        print("МК серии STM32L1 не найдены. Обновление для L1 не будет произведено.")
        # Сохраняем, так как series_line мог быть обновлен глобальным скриптом ранее
        try:
            df.to_csv(csv_filepath, index=False, encoding='utf-8')
            print(f"Файл '{csv_filepath}' сохранен (МК L1 не найдены). Записей: {len(df)}.")
        except Exception as e:
            print(f"Ошибка при сохранении CSV файла '{csv_filepath}': {e}")
        return

    eeprom_l1_bank1_addr = "0x08080000"
    eeprom_l1_cat4_bank2_addr = "0x08081800"
    eeprom_l1_cat5_6_bank2_addr = "0x08082000"

    # --- Точная обработка STM32L100xx на основе Table 2 из RM0038 ---
    l100_cat1_rpn = ["STM32L100C6", "STM32L100R8", "STM32L100RB"]
    l100_cat2_rpn = ["STM32L100C6-A", "STM32L100R8-A", "STM32L100RB-A"]
    l100_cat3_rpn = ["STM32L100RC"]

    # Маски для конкретных RPNs STM32L100xx
    # Для создания маски ищем точное совпадение начала part_number с RPN
    l100_cat1_mask = df['part_number'].apply(lambda x: any(str(x).startswith(rpn) for rpn in l100_cat1_rpn)) & (df['series_line'] == "L100")
    l100_cat2_mask = df['part_number'].apply(lambda x: any(str(x).startswith(rpn) for rpn in l100_cat2_rpn)) & (df['series_line'] == "L100")
    l100_cat3_mask = df['part_number'].apply(lambda x: any(str(x).startswith(rpn) for rpn in l100_cat3_rpn)) & (df['series_line'] == "L100")

    # L100 Cat.1: 4KB EEPROM
    df.loc[l100_cat1_mask, 'category_from_doc'] = 'Cat.1 (L100)'
    df.loc[l100_cat1_mask, 'eeprom_bank1_start_addr'] = eeprom_l1_bank1_addr
    df.loc[l100_cat1_mask, 'eeprom_bank1_size_b'] = "4096"
    df.loc[l100_cat1_mask, 'eeprom_total_size_b_from_doc'] = "4096"
    df.loc[l100_cat1_mask, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""
    df.loc[l100_cat1_mask & (df['total_eeprom_b_from_export'] != 4096), 'notes'] = \
        df.loc[l100_cat1_mask & (df['total_eeprom_b_from_export'] != 4096), 'notes'].astype(str) + \
        "INFO: EEPROM size set to 4096B based on RM0038 Table 2 & 8 (Cat.1); "

    # L100 Cat.2: 4KB EEPROM
    df.loc[l100_cat2_mask, 'category_from_doc'] = 'Cat.2 (L100)'
    df.loc[l100_cat2_mask, 'eeprom_bank1_start_addr'] = eeprom_l1_bank1_addr
    df.loc[l100_cat2_mask, 'eeprom_bank1_size_b'] = "4096"
    df.loc[l100_cat2_mask, 'eeprom_total_size_b_from_doc'] = "4096"
    df.loc[l100_cat2_mask, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""
    df.loc[l100_cat2_mask & (df['total_eeprom_b_from_export'] != 4096), 'notes'] = \
        df.loc[l100_cat2_mask & (df['total_eeprom_b_from_export'] != 4096), 'notes'].astype(str) + \
        "INFO: EEPROM size set to 4096B based on RM0038 Table 2 & 8 (Cat.2); "
        
    # L100 Cat.3: 8KB EEPROM
    df.loc[l100_cat3_mask, 'category_from_doc'] = 'Cat.3 (L100)'
    df.loc[l100_cat3_mask, 'eeprom_bank1_start_addr'] = eeprom_l1_bank1_addr
    df.loc[l100_cat3_mask, 'eeprom_bank1_size_b'] = "8192"
    df.loc[l100_cat3_mask, 'eeprom_total_size_b_from_doc'] = "8192"
    df.loc[l100_cat3_mask, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""
    df.loc[l100_cat3_mask & (df['total_eeprom_b_from_export'] != 8192), 'notes'] = \
        df.loc[l100_cat3_mask & (df['total_eeprom_b_from_export'] != 8192), 'notes'].astype(str) + \
        "INFO: EEPROM size set to 8192B based on RM0038 Table 2 & 9 (Cat.3); "

    print(f"Данные для L100 (Cat.1, Cat.2, Cat.3) обновлены на основе точной классификации.")

    # Маска для всех STM32L100xx, чтобы исключить их из последующей общей обработки L1
    processed_l100_mask = l100_cat1_mask | l100_cat2_mask | l100_cat3_mask

    # --- Общая обработка остальных STM32L1 (L151, L152, L162) ---
    # Cat.1 & Cat.2 (для L15x, L16x): EEPROM 4096B (4KB), один банк
    cat1_2_mask_l1_others = l1_overall_mask & (~processed_l100_mask) & (df['total_eeprom_b_from_export'] == 4096)
    df.loc[cat1_2_mask_l1_others, 'category_from_doc'] = 'Cat.1/Cat.2 (L1)' 
    df.loc[cat1_2_mask_l1_others, 'eeprom_bank1_start_addr'] = eeprom_l1_bank1_addr
    df.loc[cat1_2_mask_l1_others, 'eeprom_bank1_size_b'] = "4096"
    df.loc[cat1_2_mask_l1_others, 'eeprom_total_size_b_from_doc'] = "4096"
    df.loc[cat1_2_mask_l1_others, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""

    # Cat.3 (для L15x, L16x): EEPROM 8192B (8KB), один банк
    cat3_mask_l1_others = l1_overall_mask & (~processed_l100_mask) & (df['total_eeprom_b_from_export'] == 8192)
    df.loc[cat3_mask_l1_others, 'category_from_doc'] = 'Cat.3 (L1)'
    df.loc[cat3_mask_l1_others, 'eeprom_bank1_start_addr'] = eeprom_l1_bank1_addr
    df.loc[cat3_mask_l1_others, 'eeprom_bank1_size_b'] = "8192"
    df.loc[cat3_mask_l1_others, 'eeprom_total_size_b_from_doc'] = "8192"
    df.loc[cat3_mask_l1_others, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""

    # Cat.4 (для L15x, L16x): EEPROM 12288B (12KB) total, 2 банка по 6KB
    cat4_mask_l1_others = l1_overall_mask & (~processed_l100_mask) & (df['total_eeprom_b_from_export'] == 12288)
    df.loc[cat4_mask_l1_others, 'category_from_doc'] = 'Cat.4 (L1)'
    df.loc[cat4_mask_l1_others, 'eeprom_bank1_start_addr'] = eeprom_l1_bank1_addr
    df.loc[cat4_mask_l1_others, 'eeprom_bank1_size_b'] = "6144"
    df.loc[cat4_mask_l1_others, 'eeprom_bank2_start_addr'] = eeprom_l1_cat4_bank2_addr
    df.loc[cat4_mask_l1_others, 'eeprom_bank2_size_b'] = "6144"
    df.loc[cat4_mask_l1_others, 'eeprom_total_size_b_from_doc'] = "12288"

    # Cat.5 & Cat.6 (для L15x, L16x): EEPROM 16384B (16KB) total, 2 банка по 8KB
    cat5_6_mask_l1_others = l1_overall_mask & (~processed_l100_mask) & (df['total_eeprom_b_from_export'] == 16384)
    df.loc[cat5_6_mask_l1_others, 'category_from_doc'] = 'Cat.5/Cat.6 (L1)'
    df.loc[cat5_6_mask_l1_others, 'eeprom_bank1_start_addr'] = eeprom_l1_bank1_addr
    df.loc[cat5_6_mask_l1_others, 'eeprom_bank1_size_b'] = "8192"
    df.loc[cat5_6_mask_l1_others, 'eeprom_bank2_start_addr'] = eeprom_l1_cat5_6_bank2_addr
    df.loc[cat5_6_mask_l1_others, 'eeprom_bank2_size_b'] = "8192"
    df.loc[cat5_6_mask_l1_others, 'eeprom_total_size_b_from_doc'] = "16384"
    
    print("Данные EEPROM для остальных STM32L1 (L15x, L16x) обновлены.")

    try:
        df.to_csv(csv_filepath, index=False, encoding='utf-8')
        print(f"Файл '{csv_filepath}' успешно обновлен. Записей: {len(df)}.")
    except Exception as e:
        print(f"Ошибка при сохранении обновленного CSV файла '{csv_filepath}': {e}")

if __name__ == "__main__":
    research_csv_file = "stm32_l0_l1_eeprom_research.csv"
    
    try:
        with open(research_csv_file, 'r', encoding='utf-8') as f:
            pass 
        # Вызываем функцию, которая теперь содержит всю логику обновления L1
        update_l1_eeprom_data_in_csv(research_csv_file) 
    except FileNotFoundError:
        print(f"Файл '{research_csv_file}' не найден.")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")
