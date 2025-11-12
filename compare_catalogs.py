import csv
import json
import argparse
import html
import os
import sys

PLACEHOLDER_COMMA = "<<<COMMA>>>"
PLACEHOLDER_NEWLINE = "<<<NEWLINE>>>"
PLACEHOLDER_SECTION = "<<<SECTION>>>"


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(filename, delimiter, special_field, key_field):
    with open(filename, "r", encoding="utf-8-sig") as f:
        content = f.read()

    lines = content.splitlines()
    if not lines:
        return {}

    header = lines[0]
    headers = header.split(delimiter)
    try:
        special_idx = headers.index(special_field)
    except ValueError:
        special_idx = -1

    def replace_special_fields(line):
        parts = []
        current = ""
        in_quotes = False
        quote_char = ''
        for ch in line:
            if ch in ('"', "'"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = ch
                elif quote_char == ch:
                    in_quotes = False
                current += ch
            elif ch == delimiter and not in_quotes:
                parts.append(current)
                current = ""
            else:
                current += ch
        parts.append(current)

        if 0 <= special_idx < len(parts):
            val = parts[special_idx]
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            val = val.replace(",", PLACEHOLDER_COMMA).replace("\n", PLACEHOLDER_NEWLINE).replace("\r",
                                                                                                 PLACEHOLDER_NEWLINE).replace(
                "§", PLACEHOLDER_SECTION)
            parts[special_idx] = val
        return delimiter.join(parts)

    processed_lines = [header] + [replace_special_fields(line) for line in lines[1:]]

    reader = csv.DictReader(processed_lines, delimiter=delimiter)
    data = {}
    for row in reader:
        if not row.get(key_field):
            continue
        if special_field in row and row[special_field]:
            row[special_field] = row[special_field].replace(PLACEHOLDER_COMMA, ",").replace(PLACEHOLDER_NEWLINE,
                                                                                            "\n").replace(
                PLACEHOLDER_SECTION, "§")
        data[row[key_field].strip()] = row
    return data


def parse_additional_attributes(attr_string, attr_separator):
    attributes = {}
    if not attr_string:
        return attributes

    pairs = attr_string.split(attr_separator)
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            key = key.strip()
            value = value.strip()
            value = html.unescape(value)
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            attributes[key] = value
        else:
            attributes[pair.strip()] = ''
    return attributes


def diff_additional_attributes(stg_val, prod_val, attr_separator, exclude_attrs):
    stg_attrs = parse_additional_attributes(stg_val, attr_separator)
    prod_attrs = parse_additional_attributes(prod_val, attr_separator)
    diffs = {}

    for key, stg_value in stg_attrs.items():
        if key in exclude_attrs:
            continue
        prod_value = prod_attrs.get(key, "")
        if prod_value != stg_value:
            diffs[key] = (stg_value, prod_value)

    for key, prod_value in prod_attrs.items():
        if key in exclude_attrs:
            continue
        if key not in stg_attrs:
            diffs[key] = ("", prod_value)

    return diffs


def compare_catalogs(staging, production, ignore_fields, special_field, attr_separator, exclude_additional_attributes,
                     key_field):
    diffs = []

    for sku, stg_row in staging.items():
        prod_row = production.get(sku)
        if not prod_row:
            diffs.append({
                key_field: sku,
                "type": "missing_in_production",
                "field": "",
                "staging_value": "",
                "production_value": ""
            })
            continue

        for field in stg_row.keys():
            if field in ignore_fields:
                continue

            stg_val = (stg_row[field] or "").strip()
            prod_val = (prod_row.get(field) or "").strip()

            if field == special_field:
                subdiffs = diff_additional_attributes(stg_val, prod_val, attr_separator, exclude_additional_attributes)
                for subkey, (stg_subval, prod_subval) in subdiffs.items():
                    diffs.append({
                        key_field: sku,
                        "type": "different_value (additional_attribute)",
                        "field": f"{special_field}:{subkey}",
                        "staging_value": stg_subval,
                        "production_value": prod_subval
                    })
                continue

            if stg_val != prod_val:
                diffs.append({
                    key_field: sku,
                    "type": "different_value",
                    "field": field,
                    "staging_value": stg_val,
                    "production_value": prod_val
                })

    for sku in production.keys():
        if sku not in staging:
            diffs.append({
                key_field: sku,
                "type": "extra_in_production",
                "field": "",
                "staging_value": "",
                "production_value": ""
            })

    return diffs


def write_report(diffs, html_fields, staging_data, output_file, key_field):
    if not diffs:
        print("✅ Nessuna differenza trovata tra i due cataloghi.")
        return

    fields = [key_field, "product_websites", "differences"]
    grouped = {}

    for diff in diffs:
        sku = diff[key_field]
        if sku not in grouped:
            grouped[sku] = {"diffs": [], "product_websites": ""}
        if diff["type"] == "missing_in_production":
            grouped[sku]["diffs"].append("missing_in_production")
        elif diff["type"] == "extra_in_production":
            grouped[sku]["diffs"].append("extra_in_production")
        else:
            field = diff["field"]
            stg_val = diff["staging_value"]
            prod_val = diff["production_value"]
            if any(field == html_field or field.startswith(f"{html_field}:") for html_field in html_fields):
                stg_val = html.escape(stg_val)
                prod_val = html.escape(prod_val)
            grouped[sku]["diffs"].append(f"{field} [{stg_val} → {prod_val}]")

    for sku in grouped:
        stg_row = staging_data.get(sku)
        grouped[sku]["product_websites"] = stg_row.get("product_websites", "") if stg_row else ""

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for sku, info in grouped.items():
            writer.writerow({
                key_field: sku,
                "product_websites": info["product_websites"],
                "differences": "; ".join(info["diffs"])
            })

    print(f"📄 Report generato: {output_file}")
    print(f"Totale differenze trovate: {len(diffs)}")


def main():
    parser = argparse.ArgumentParser(description="CSV Catalog Comparer")
    parser.add_argument("--config", default="config.json", help="Percorso del file di configurazione JSON")
    args = parser.parse_args()

    config = load_config(args.config)

    key_field = config.get("key_field", "sku")
    csv_delimiter = config.get("csv_delimiter", ",")
    attr_separator = config.get("attr_separator", "§")
    exclude_columns = set(config.get("exclude_columns", []))
    exclude_additional_attributes = set(config.get("exclude_additional_attributes", []))
    html_fields = config.get("html_fields", [])
    master_file = config.get("master_file")
    comparison_file = config.get("comparison_file")
    special_field = config.get("special_field", "additional_attributes")
    output_file = config.get("output_file", "output/diff_report.csv")

    staging = load_csv(master_file, csv_delimiter, special_field, key_field)
    production = load_csv(comparison_file, csv_delimiter, special_field, key_field)
    diffs = compare_catalogs(staging, production, exclude_columns, special_field, attr_separator,
                             exclude_additional_attributes, key_field)
    write_report(diffs, html_fields, staging, output_file, key_field)


if __name__ == "__main__":
    main()
