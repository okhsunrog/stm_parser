import pandas as pd
import re

# Эта функция нужна для первоначальной коррекции/установки series_line,
# если она еще не была корректно установлена для L0x0.
# Если вы уверены, что series_line уже везде правильная, эту часть можно упростить.
def get_l0_series_line(part_number_str):
    pn = str(part_number_str)
    if not pn.startswith("STM32L0"): return "Unknown_L0_Prefix"
    match = re.match(r"STM32L0(\d{2})", pn)
    if not match: return "L0_Malformed_PN"
    digits = match.group(1)
    if digits == "10": return "L0x0"
    # Эта функция теперь вызывается только для L0x0, так что другие ветки L0 не нужны здесь,
    # но оставим их на случай, если вы захотите расширить скрипт позже.
    elif digits in ["11", "21", "31", "41", "51", "61", "71", "81"]: return "L0x1"
    elif digits in ["52", "62", "72", "82"]: return "L0x2"
    elif digits in ["53", "63", "73", "83"]: return "L0x3"
    else: return "L0_Unknown_Digits"

def get_l1_series_line(part_number_str): # Оставляем для полноты, если вдруг в CSV есть L1
    pn = str(part_number_str)
    if not pn.startswith("STM32L1"): return "Unknown_L1_Prefix"
    match = re.match(r"STM32L1(\d{2})", pn)
    if not match: return "L1_Malformed_PN"
    digits = match.group(1)
    if digits in ["00", "51", "52", "62"]: return f"L1{digits}"
    else: return f"L1{digits}"


def update_l0x0_data_in_csv(csv_filepath):
    """
    Читает CSV, корректирует 'series_line' (если нужно) и обновляет 
    данные EEPROM ТОЛЬКО для линейки L0x0.
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
        print("Информация: В CSV отсутствует столбец 'series_line'. Он будет создан и заполнен.")
        df['series_line'] = ""
    
    # 1. Коррекция/установка series_line для всех записей (на всякий случай)
    # Это гарантирует, что L0x0 будут правильно идентифицированы.
    print("Проверка и обновление 'series_line' для всех записей...")
    for index, row in df.iterrows():
        pn = str(row['part_number'])
        current_series_line = str(row['series_line'])
        corrected_series = current_series_line # По умолчанию не меняем

        if pn.startswith("STM32L0"):
            corrected_series = get_l0_series_line(pn)
        elif pn.startswith("STM32L1"): # На случай, если в файле есть L1
            corrected_series = get_l1_series_line(pn)
        
        if current_series_line != corrected_series:
            df.loc[index, 'series_line'] = corrected_series
    print("'series_line' проверен и обновлен где необходимо.")

    # 2. Преобразование числовых столбцов, необходимых для фильтров L0x0, во float/int
    # ошибки 'coerce' превратят нечисловые значения в NaN, затем fillna(0)
    # Делаем это перед фильтрацией по l0x0_mask
    numeric_cols_for_filter = ['flash_size_kb_prog', 'total_eeprom_b_from_export']
    for col in numeric_cols_for_filter:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            print(f"Предупреждение: столбец '{col}' отсутствует и не будет преобразован в число.")


    # 3. Обновление данных ТОЛЬКО для L0x0
    print("Обновление данных EEPROM для L0x0...")
    l0x0_mask = df['series_line'] == "L0x0"
    eeprom_base_addr_l0x0 = "0x08080000"
    
    if not df[l0x0_mask].empty:
        print(f"Найдено {len(df[l0x0_mask])} МК серии L0x0 для обновления EEPROM.")
    else:
        print("МК серии L0x0 не найдены. Обновление для L0x0 не будет произведено.")
        # Сохраняем файл даже если L0x0 не найдены, так как series_line мог быть обновлен
        try:
            df.to_csv(csv_filepath, index=False, encoding='utf-8')
            print(f"Файл '{csv_filepath}' сохранен (обновления L0x0 не требовались, но series_line мог измениться). Записей: {len(df)}.")
        except Exception as e:
            print(f"Ошибка при сохранении CSV файла '{csv_filepath}': {e}")
        return # Выходим, так как дальше нечего делать для L0x0
        

    # L0x0 Category 1 (Flash 8KB/16KB, EEPROM 128B)
    # Соответствует STM32L010x3 и STM32L010x4 из вашей таблицы плотности
    cat1_mask_l0x0 = l0x0_mask & (df['flash_size_kb_prog'].isin([8, 16])) & (df['total_eeprom_b_from_export'] == 128)
    df.loc[cat1_mask_l0x0, 'category_from_doc'] = 'Category 1 (L0x0)'
    df.loc[cat1_mask_l0x0, 'eeprom_bank1_start_addr'] = eeprom_base_addr_l0x0
    df.loc[cat1_mask_l0x0, 'eeprom_bank1_size_b'] = "128"
    df.loc[cat1_mask_l0x0, 'eeprom_total_size_b_from_doc'] = "128"
    df.loc[cat1_mask_l0x0, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""

    # L0x0 Category 2 (Flash 32KB, EEPROM 256B)
    # Соответствует STM32L010x6
    cat2_mask_l0x0 = l0x0_mask & (df['flash_size_kb_prog'] == 32) & (df['total_eeprom_b_from_export'] == 256)
    df.loc[cat2_mask_l0x0, 'category_from_doc'] = 'Category 2 (L0x0)'
    df.loc[cat2_mask_l0x0, 'eeprom_bank1_start_addr'] = eeprom_base_addr_l0x0
    df.loc[cat2_mask_l0x0, 'eeprom_bank1_size_b'] = "256"
    df.loc[cat2_mask_l0x0, 'eeprom_total_size_b_from_doc'] = "256"
    df.loc[cat2_mask_l0x0, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""

    # L0x0 Category 3 (Flash 64KB, EEPROM 256B)
    # Соответствует STM32L010x8
    cat3_mask_l0x0 = l0x0_mask & (df['flash_size_kb_prog'] == 64) & (df['total_eeprom_b_from_export'] == 256)
    df.loc[cat3_mask_l0x0, 'category_from_doc'] = 'Category 3 (L0x0)'
    df.loc[cat3_mask_l0x0, 'eeprom_bank1_start_addr'] = eeprom_base_addr_l0x0
    df.loc[cat3_mask_l0x0, 'eeprom_bank1_size_b'] = "256"
    df.loc[cat3_mask_l0x0, 'eeprom_total_size_b_from_doc'] = "256"
    df.loc[cat3_mask_l0x0, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""

    # L0x0 Category 5 (Flash 128KB, EEPROM 512B)
    # Соответствует STM32L010xB
    cat5_mask_l0x0 = l0x0_mask & (df['flash_size_kb_prog'] == 128) & (df['total_eeprom_b_from_export'] == 512)
    df.loc[cat5_mask_l0x0, 'category_from_doc'] = 'Category 5 (L0x0)'
    df.loc[cat5_mask_l0x0, 'eeprom_bank1_start_addr'] = eeprom_base_addr_l0x0
    df.loc[cat5_mask_l0x0, 'eeprom_bank1_size_b'] = "512"
    df.loc[cat5_mask_l0x0, 'eeprom_total_size_b_from_doc'] = "512"
    df.loc[cat5_mask_l0x0, ['eeprom_bank2_start_addr', 'eeprom_bank2_size_b']] = ""
    
    print("Данные EEPROM для L0x0 обновлены.")

    # Важно: после числовых операций для фильтрации, если вы хотите сохранить
    # эти столбцы как строки (чтобы пустые значения были "", а не 0.0 или NaN при чтении),
    # убедитесь, что они остаются строками или преобразуются обратно перед сохранением,
    # если это не обрабатывается `dtype=str` при чтении и `fillna("")`.
    # В данном случае, `read_csv(dtype=str)` и `fillna("")` должны это покрыть.
    # Присвоение строковых значений ("128", "256", "512") также помогает.

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
            pass # Просто проверяем, что файл открывается
        update_l0x0_data_in_csv(research_csv_file)
    except FileNotFoundError:
        print(f"Файл '{research_csv_file}' не найден. Пожалуйста, сначала создайте его.")
    except Exception as e:
        print(f"Произошла непредвиденная ошибка: {e}")
