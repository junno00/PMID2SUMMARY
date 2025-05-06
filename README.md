# PubMed Abstract Summarizer

このリポジトリは、PubMedの論文情報（タイトル、著者、アブストラクトおよびPMCID）を取得し、その内容をLLM（GPT-4o）を用いて自動要約するPythonスクリプトを提供します。

## 概要

- **スクリプト**: `script/pmid2summary.py`  
  指定したPubMed IDに基づき、NCBI Eutils APIを利用して論文情報を取得します。取得情報として、論文タイトル、著者情報、アブストラクト、PMCIDが含まれます。  
  要約チェーンには2種類が利用可能です：
  - **stuffチェーン**: 論文全体のテキストをLLMに渡し、単一の要約を生成します。  
  - **refineチェーン**: 長文のテキストを分割し、初回チャンクで初期要約を生成した後、残りのチャンクに対して逐次的に要約を精錬（refine）し、最終的な要約を出力します。

### 最近の修正点

- プレーンなテキストとして文書を渡すのではなく、入力辞書のキーを **"context"** に統一するように変更しました。  
  これは、RefineDocumentsChain や StuffDocumentsChain が内部で **"context"** と **"question"** の入力変数名を期待しているためです。  
  - 例えば、`summarize_text` 関数では、`chain.invoke([{"context": text}])` の形でテキストが渡されます。
  - また、`refine_summarize_text` 関数では、各チャンクの Document の内容が **{"context": doc.page_content}** として渡され、RefineDocumentsChain が期待する変数名に合わせています。

これにより、PMID 33221939 や PMID 32598085 など、複数の文献に対して一貫して正しく要約テキストがパースされるようになりました。

## Docker と Poetry の利用

- **Dockerfile**:
  - スクリプトの実行環境をコンテナ化するための設定ファイルです。
- **docker-compose.yml**:
  - Dockerコンテナのセットアップや管理に利用されます。
- **Poetry**:
  - 依存関係およびパッケージ管理にはPoetryを使用します。プロジェクトルートにある `pyproject.toml` および `poetry.lock` ファイルを参照してください。

## 使用方法

1. 依存関係のインストール:
   ```
   poetry install
   ```
2. Dockerコンテナでの実行例:
   ```
   docker-compose up --build
   ```
3. コマンドラインからの実行:
   - **デフォルト（stuffチェーンの場合）:**
     ```
     python script/pmid2summary.py <PubMedID>
     ```
   - **refineチェーンを利用する場合:**
     ```
     python script/pmid2summary.py refine <PubMedID>
     ```

## 注意事項

- NCBI Eutils APIの利用制限に注意してください。
- LLMによる要約の出力は入力に依存し、内容が変動する場合があります。
- 最新の修正により、チェーンに渡す入力は "context" キーで統一されています。これにより、StuffDocumentsChain および RefineDocumentsChain のバリデーションエラーが解消されています。
