# プロジェクト概要

このプロジェクトは、PubMedの論文情報の取得および要約生成を自動化するためのツール群を提供します。

## pmid2abst.py Script

このスクリプトは、PubMed IDに基づいてNCBI Eutils APIを利用し、論文情報（タイトル、著者情報、アブストラクト）を取得した後、ChatOpenAI (gpt-4o) を用いて論文の要約を生成します。

### 特徴

- **記事情報の取得**:  
  PubMed APIからXML形式で論文データを取得し、タイトル、著者、アブストラクト、及びPMCIDを抽出します。

- **要約生成の2種類のチェーン**:  
  要約生成において、以下の2つのチェーンが利用可能です。
  - **stuffチェーン** (デフォルト):  
    論文全体またはアブストラクトを1チャンクとしてLLMに渡し、要約を生成します。
  - **refineチェーン**:  
    論文のテキストを自動で分割し、各チャンクに対して初期要約とそれに基づく精査プロンプトを用いて、より洗練された最終要約を生成します。
    refineチェーンを使用する場合のみ、テキスト分割が実施されます。

### 使い方

コマンドラインから次の形式で実行します：

```
python pmid2abst.py [chain_type] <PubMedID>
```

- `chain_type`: `"stuff"` または `"refine"` を指定します。省略した場合はデフォルトで `"stuff"` が使用されます。
- `<PubMedID>`: 取得対象の論文のPubMed ID。

### 主要な関数

- **get_article_info(pmid)**:  
  指定したPubMed IDに基づき、論文のタイトル、著者、アブストラクト、PMCIDを取得します。

- **get_full_text_by_pmcid(pmcid)**:  
  PMCIDを利用して、論文の全文を取得します（PMCIDが存在する場合）。

- **summarize_text(text)**:  
  `stuff`チェーンを用いて、全文またはアブストラクトを単一のチャンクとしてLLMに渡し、要約を生成します。

- **refine_summarize_text(text)**:  
  `refine`チェーンを用いて、論文のテキストを自動分割し、各チャンクを対象にした初期要約と精査プロンプトから、より洗練された最終要約を生成します。

### 補足

- 要約生成には、LangChainの`load_summarize_chain`関数と、OpenAIのChatOpenAI (gpt-4o) が利用されています。
- refineチェーンの場合、テキスト分割には`RecursiveCharacterTextSplitter`が使用され、適切なチャンクに分割して処理を行います。

このスクリプトを利用することで、PubMedに登録されている論文の概要を迅速に把握し、文献レビューや研究情報整理の効率化が期待できます。
