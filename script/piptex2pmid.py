#!/usr/bin/env python3
import csv
import re
import sys
import os
import pandas as pd
import subprocess

def extract_ids_from_csv(file_path):
    records_both = []
    records_only_pmid = []
    # PMID : 7～8桁の数字
    pattern_pmid = re.compile(r'\b\d{7,8}\b')
    # PMCID : "PMC"に続く数字（大文字・小文字問わず）
    pattern_pmcid = re.compile(r'\bPMC\d+\b', re.IGNORECASE)
    with open(file_path, encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        # ヘッダーがある場合は読み飛ばす（必要に応じてコメントアウトしてください）
        header = next(reader, None)
        for row in reader:
            # 各行の全セルを結合して1つの文字列にする
            row_text = " ".join(row)
            pmid_match = pattern_pmid.search(row_text)
            pmcid_match = pattern_pmcid.search(row_text)
            if pmid_match:
                if pmcid_match:
                    record = {
                        "PMID": pmid_match.group(),
                        "PMCID": pmcid_match.group()
                    }
                    records_both.append(record)
                else:
                    # PMIDはあるがPMCIDがない場合のレコード
                    records_only_pmid.append({"PMID": pmid_match.group()})
    return records_both, records_only_pmid

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("使い方: {} ファイルパス".format(sys.argv[0]))
        sys.exit(1)
    csv_file = sys.argv[1]
    records_both, records_only_pmid = extract_ids_from_csv(csv_file)
    
    if not records_both and not records_only_pmid:
        print("指定されたCSVファイルからは、該当するIDが見つかりませんでした。")
        sys.exit(1)
    
    if records_both:
        df = pd.DataFrame(records_both)
        print("\n抽出されたDataFrame（PMIDとPMCIDの対応）:")
        print(df.to_string(index=False))
    if records_only_pmid:
        df_only = pd.DataFrame(records_only_pmid)
        output_file = "result/PMID_without_PMCID.txt"
        # 出力先ディレクトリが存在しない場合は作成する
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        df_only.to_csv(output_file, index=False, header=True)
        print("\nPMCIDが存在しないPMIDのリストを以下のファイルに出力しました:")
        print(output_file)
    
    # 取得したPMIDリストを使って個別の処理を実行（PMCIDが存在するレコードのみを対象）
    pmid_list = [record["PMID"] for record in records_both]
    if pmid_list:
        print("\n抽出されたPMIDのリスト:")
        for pmid in pmid_list:
            print(pmid)
        for pmid in pmid_list:
            command = ["python3", "script/pmid2summary.py","refine", pmid]
            print("\npmid2summary.py を PMID {0} で実行します。コマンド:".format(pmid))
            print(" ".join(command))
            subprocess.run(command)
