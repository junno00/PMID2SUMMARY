# PubMed Abstract Summarizer

このリポジトリは、PubMedの論文情報（タイトル、著者、アブストラクトおよびPMCID）を取得し、その内容をLLM（GPT-4o）を用いて自動要約するPythonスクリプトを提供します。

## 概要

- **スクリプト**: `script/pmid2summary.py`  
  指定したPubMed IDに基づき、NCBI Eutils APIを利用して論文情報を取得します。
  - 論文のタイトル、著者情報、アブストラクト、そしてPMCIDを表示します。
  - PMCIDが取得される場合、論文全文も取得し、その内容をLLMによる要約プロセスに渡します。

- **要約チェーン**:  
  スクリプトは2つの要約チェーンをサポートします。
  - **stuffチェーン**: テキスト全体をLLMに渡し、一括して要約を生成します。
  - **refineチェーン**: 論文全文やアブストラクトを分割し、初期要約に対して追加情報を統合することで、より洗練された最終要約を出力します。

- **プロンプトの更新**:  
  プロンプトテンプレートの入力変数名を統一することで、Pydanticの検証エラー（extra_forbidden エラー）を回避し、LLMに正しい入力データを渡すように改善されています。

## Docker と Poetry の利用

- **Dockerfile**:
  - Dockerfileは、スクリプトの実行環境をコンテナ化するために用意されています。
  - 必要なPython環境や依存関係（例: `langchain`, `requests` など）がDockerfile内で設定されています。

- **docker-compose.yml**:
  - docker-compose.ymlは、コンテナのセットアップと管理をシンプルに行うための設定ファイルです。
  - このファイルを用いることで、Dockerコンテナの立ち上げ、停止、ログの確認などが容易に行えます。

- **Poetry**:
  - Poetryは依存関係管理およびパッケージ管理ツールであり、プロジェクトルートにある `pyproject.toml` と `poetry.lock` を用いて依存関係を管理します。
  - ローカル環境で作業する場合は、通常の `poetry install` コマンドを実行して依存関係をインストールしてください。
  - Docker環境内では、Dockerfile内で依存関係が効率的にセットアップされるため、仮想環境の作成を無効化する必要があります。まず、以下のコマンドで仮想環境を無効化し:
    ```
    poetry config virtualenvs.create false
    ```
    その後、依存関係をインストールします:
    ```
    poetry install
    ```

## 使用方法

1. 必要な依存関係をインストールしてください（例: `poetry install` を実行）。
2. Dockerコンテナとして実行する場合は、以下の手順を行ってください:
    1. 以下のコマンドを実行してDockerコンテナを起動します:
       ```
       docker-compose up --build
       ```
    2. コンテナ内で必要なPoetryライブラリをインストールするため、コンテナに入り次のコマンドを実行します:
       ```
       poetry install
       ```
3. コマンドラインからスクリプトを実行する場合:
    - **デフォルト（`stuff` チェーンの場合）:**
      ```
      python script/pmid2summary.py <PubMedID>
      ```
    - **refineチェーンを利用する場合:**
      ```
      python script/pmid2summary.py refine <PubMedID>
      ```

## 更新履歴

- **最新の更新**:
  - プロンプトテンプレートの入力変数名を `"text"` に統一し、extra_forbidden エラーを解消。
  - `stuff` と `refine` の各要約チェーンで一貫性のある入力命名規則を採用。
  - スクリプトの名前を最新のもの（`script/pmid2summary.py`）に変更。
  - Dockerfile、docker-compose.yml、および Poetry に関する利用方法を追記し、Dockerコンテナ起動後にPoetryで依存関係をインストールする手順を更新。

## 注意事項

- このスクリプトはNCBIのEutils APIを利用しています。大量のリクエストを送信する場合は、APIの利用制限に注意してください。
- LLMによる要約は、モデルの応答や設定（例: `temperature`）に依存するため、内容が変動する可能性があります。
