#!/usr/bin/env python3
import os, csv, glob

def extract_last_row(csv_file):
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
        if len(rows) > 1:
            return rows[-1]
    return None

def main():
    log_dir = '/root/sim_storage/experiments'
    output_file = '/root/sim_storage/exp_results_final.csv'
    csv_files = glob.glob(os.path.join(log_dir, 'S*.csv'))
    final_rows = []
    header = None

    for f in csv_files:
        last = extract_last_row(f)
        if last:
            if header is None:
                header = last
            else:
                final_rows.append(last)
    
    with open(output_file, 'w', newline='') as out:
        writer = csv.writer(out)
        if header:
            writer.writerow(header)
        writer.writerows(final_rows)
    print(f"✅ Сохранено {len(final_rows)} финальных записей в {output_file}")

if __name__ == '__main__':
    main()
