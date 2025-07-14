# PubMed Abstract Summarizer

このリポジトリは、PubMedの論文情報（タイトル、著者、アブストラクトおよびPMCID）を取得し、その内容をLLM（GPT-4o）を用いて自動要約するPythonスクリプトを提供します。

## 概要

### スクリプト一覧

#### 1. `script/pmid2summary.py`
指定したPubMed IDに基づき、NCBI Eutils APIを利用して論文情報を取得し、LLMで要約を生成します。

**取得情報:**
- 論文タイトル
- 著者情報
- アブストラクト
- PMCID
- 出版年

**要約チェーン:**
- **stuffチェーン**: 論文全体のテキストをLLMに渡し、単一の要約を生成します
- **refineチェーン**: 長文のテキストを分割し、初回チャンクで初期要約を生成した後、残りのチャンクに対して逐次的に要約を精錬（refine）し、最終的な要約を出力します

#### 2. `script/piptex2pmid.py`
CSVファイルからPMIDとPMCIDを抽出し、バッチ処理で複数の論文を一括要約するスクリプトです。

**機能:**
- CSVファイルから7-8桁のPMID（PubMed ID）を抽出
- PMCIDの有無を判定し、PMCIDが存在しないPMIDを別途記録
- PMIDとPMCIDの対応表を生成
- 抽出したPMIDに対して`pmid2summary.py`を自動実行（refineチェーンを使用）
- PMCIDが存在しないPMIDのリストを`result/PMID_without_PMCID.txt`に出力

### 最近の修正点

- 入力辞書のキーを **"context"** に統一するように変更しました。  
  これにより、RefineDocumentsChain や StuffDocumentsChain が内部で **"context"** と **"question"** の入力変数名を期待しているため、一貫して正しい形式で入力が渡されるようになりました。  
  - 例えば、`summarize_text` 関数では、`chain.invoke([{"context": text}])` の形でテキストが渡されます。
  - また、`refine_summarize_text` 関数では、各チャンクの Document の内容が **{"context": doc.page_content}** として渡され、RefineDocumentsChain が期待する変数名に合わせています.
  
- 出力先の変更:  
  以前は標準出力へ要約結果を表示していましたが、現在の修正では、`def main()` 内で出力がファイルへ書き出されるようになりました。  
  出力ファイルの名前は、実行時の引数に基づいて決定され、チェーンタイプが指定された場合は `chain_type` と PubMedID をアンダースコアで連結したもの（例: `refine_12345678.markdown`）、指定がない場合は PubMedID 単体（例: `12345678.markdown`）となっています.
これにより、PMID 33221939 や PMID 32598085 など、複数の文献に対して一貫して正しく要約テキストがパースされるようになりました。

## Docker と Poetry の利用

- **Dockerfile**:
  - スクリプトの実行環境をコンテナ化するための設定ファイルです。
- **docker-compose.yml**:
  - Dockerコンテナのセットアップや管理に利用されます。
- **Poetry**:
  - 依存関係およびパッケージ管理にはPoetryを使用します。プロジェクトルートにある `pyproject.toml` および `poetry.lock` ファイルを参照してください。

## 使用方法

### 環境セットアップ

1. 依存関係のインストール:
   ```bash
   poetry install
   ```

2. OpenAI APIキーの設定:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

### 単一論文の要約（pmid2summary.py）

- **デフォルト（stuffチェーンの場合）:**
  ```bash
  python script/pmid2summary.py <PubMedID>
  ```

- **refineチェーンを利用する場合:**
  ```bash
  python script/pmid2summary.py refine <PubMedID>
  ```

**出力ファイル:**
- チェーンタイプ指定時: `{chain_type}_{PMID}.md`（例: `refine_12345678.md`）
- デフォルト: `{PMID}.md`（例: `12345678.md`）

### バッチ処理（piptex2pmid.py）

CSVファイルから複数のPMIDを抽出して一括処理:

```bash
python script/piptex2pmid.py <CSVファイルパス>
```

**例:**
```bash
python script/piptex2pmid.py data/ReviewList_ipsc_def.csv
```

**処理フロー:**
1. CSVファイルからPMIDとPMCIDを抽出
2. PMIDとPMCIDの対応表を表示
3. PMCIDが存在しないPMIDを`result/PMID_without_PMCID.txt`に出力
4. 各PMIDに対して`pmid2summary.py refine`を自動実行

### Dockerでの実行

```bash
docker-compose up --build
```

## 出力形式

要約は以下の構造でMarkdown形式で出力されます：

- **基本情報**: PMID、出版年、タイトル、著者情報、PMCID
- **詳細要約**: 各段落を1000文字以上で詳細に要約
- **まとめ**: 対象細胞、分子名、制御機構、実験方法、データ解析方法、研究成果、課題・制約

## 依存関係

主要な依存パッケージ（`pyproject.toml`で管理）:
- `langchain`: LLMチェーンの構築
- `langchain-openai`: OpenAI GPT-4oとの連携
- `pandas`: データ処理
- `requests`: API通信
- `biopython`: 生物学データ処理

## 注意事項

- NCBI Eutils APIの利用制限に注意してください
- OpenAI APIキーが必要です
- LLMによる要約の出力は入力に依存し、内容が変動する場合があります
- 最新の修正により、チェーンに渡す入力は "context" キーで統一されています。これにより、StuffDocumentsChain および RefineDocumentsChain のバリデーションエラーが解消されています
- iPS細胞研究に特化したプロンプトが使用されています
