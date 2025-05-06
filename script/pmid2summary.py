#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PubMed IDに基づいてNCBI Eutils APIを使用し、論文情報（タイトル、著者情報、アブストラクト）を取得するスクリプト

使用方法:
    python pmid2abst.py [chain_type] <PubMedID>
chain_typeは"stuff"または"refine"を指定してください。指定がなければ"stuff"がデフォルトになります。
"""

import sys
import requests
import xml.etree.ElementTree as ET
from langchain_openai import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# JsonOutputParse のインポートは不要なため削除

def get_article_info(pmid):
    """
    指定したPubMed IDから論文情報を取得する
    取得する情報:
      - タイトル
      - 著者情報 (姓 名)
      - アブストラクト
    """
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
    except Exception as e:
        print(f"APIリクエストエラー: {e}")
        return None

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as pe:
        print(f"XML解析エラー: {pe}")
        return None

    # タイトル取得
    title_elem = root.find(".//Article/ArticleTitle")
    title = title_elem.text.strip() if title_elem is not None and title_elem.text else None

    # 著者情報取得
    authors = []
    for author in root.findall(".//Article/AuthorList/Author"):
        last_name = author.find("LastName")
        fore_name = author.find("ForeName")
        if last_name is not None and fore_name is not None:
            authors.append(f"{last_name.text.strip()} {fore_name.text.strip()}")
        elif last_name is not None:
            authors.append(last_name.text.strip())
    
    # アブストラクト
    abstract_texts = []
    for abstract_section in root.findall(".//Abstract"):
        for abstract_text in abstract_section.findall("AbstractText"):
            if abstract_text.text:
                abstract_texts.append(abstract_text.text.strip())
    abstract = "\n\n".join(abstract_texts) if abstract_texts else None

    # PMCID取得
    pmcid_elem = root.find(".//ArticleIdList/ArticleId[@IdType='pmc']")
    pmcid = pmcid_elem.text.strip() if pmcid_elem is not None and pmcid_elem.text else "No_PMCID"

    return {"title": title, "authors": authors, "abstract": abstract, "pmcid": pmcid}

def get_full_text_by_pmcid(pmcid):
    """
    指定したPMCIDから論文の全文を取得する
    """
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pmc",
        "id": pmcid,
        "retmode": "xml"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
    except Exception as e:
        print(f"APIリクエストエラー (PMCID): {e}")
        return None
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as pe:
        print(f"XML解析エラー (PMCID): {pe}")
        return None
    body_elem = root.find(".//body")
    if body_elem is not None:
        full_text = "".join(body_elem.itertext()).strip()
        if full_text:
            return full_text
    return None

def parse_result(result):
    """
    再帰的に辞書やリストから適切な要約テキストを抽出する関数。
    複数のキー（"output_text", "text", "summary", "result", "content" など）を優先順位順にチェックする。
    """
    if isinstance(result, str):
        return result.strip()
    elif isinstance(result, dict):
        # 優先順位の高いキーをチェックする
        for key in ["output_text", "text", "summary", "result"]:
            if key in result and isinstance(result[key], str) and result[key].strip():
                return result[key].strip()
        # "content"キーがあれば再帰的に探索
        if "content" in result:
            parsed = parse_result(result["content"])
            if parsed:
                return parsed
        # それ以外の全キーを再帰的に探索
        for key, value in result.items():
            parsed = parse_result(value)
            if parsed:
                return parsed
        return ""
    elif isinstance(result, list):
        for item in result:
            parsed = parse_result(item)
            if parsed:
                return parsed
        return ""
    else:
        return str(result).strip()

def summarize_text(text):
    """
    テキストをLLMに渡し、reduceチェーンを用いて要約を生成します。
    """
    document = Document(page_content=text)
    reduce_prompt = PromptTemplate(
        input_variables=["context"],
        template="""
以下のテキストの内容を要約してください。要約は以下の手順に従って作成してください。
1. 論文の各章ごとに5段程度に詳しく要約すること。
2. 実験方法、データの種類、データ解析方法、対象とする生物学的機構を箇条書きにすること。
3. 研究分野での進展と今後の課題も含めること。
入力:
{context}
要約:
"""
    )
    llm = ChatOpenAI(temperature=0, model_name="gpt-4o")
    chain = load_summarize_chain(llm, chain_type="stuff",
                                 prompt=reduce_prompt,
                                 document_variable_name="context",)
    result = chain.invoke([document])
    return parse_result(result)

def refine_summarize_text(text):
    """
    テキストを分割してLLMに渡し、refineチェーンを用いて要約を生成します。
    refineチェーンは、初期要約に対して追加情報を統合し、より洗練された要約を生成します。
    """
    question = """
この論文の各段落を、日本語で1000文字以上に要約してください。

【出力ルール】
- 各段落には「段落1:」「段落2:」のように番号付きの見出しをつけてください。
- 論文に章構成（序論・方法・結果・考察など）がある場合は、それに従って章見出しを「第1章：〜」のように明示してください。
- 各段落の要約には、生物学的背景、使用された手法、目的、結果、議論、限界を含めてください。
- 内容を簡略化せず、学部生・大学院生レベルの読者が理解できる粒度で解説してください。
- 必要に応じて専門用語には簡単な補足説明を加えてください。
- 出力形式はMarkdownに準拠してください。

【まとめ】
文献全体の中で以下の情報を、文末に明確に要約してください：
- 対象とする細胞
- 登場する分子名
- 登場する分子が行う生物学的な制御機構
- 実験方法
- データの種類
- データ解析方法
- この研究で明らかになったこと（1000文字程度）
- この研究で示された研究分野の課題や制約（1000文字程度）

※ 出力が途中で終わらないよう、論文の最終段落までを必ず含めてください。
"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n\n", "\n\n"]
    )
    documents = [Document(page_content=chunk) for chunk in splitter.split_text(text)]

    initial_prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
あなたは、iPS細胞を対象とした分子生物学と細胞生物学の研究者です。
以下の文書内容をもとに、他分野の研究者でも理解できるように、下記の質問に従って詳細に要約してください。

【文書】
{context}

【質問】
{question}

要約:
"""
)
    refine_prompt = PromptTemplate(
        input_variables=["existing_answer", "context", "question"],
        template="""
あなたは、iPS細胞を対象とした分子生物学と細胞生物学の研究者です。
以下の既存要約に続く文書情報を反映して、要約をより正確かつ包括的に改善してください。

---

【既存の要約】
{existing_answer}

【追加文書】
{context}

【質問】
{question}

更新後の要約:
"""
    )
    llm = ChatOpenAI(temperature=0, model_name="gpt-4o")
    if not documents:
        return ""
    if len(documents) == 1:
        summary = load_summarize_chain(llm, chain_type="stuff", prompt=initial_prompt).invoke([documents[0]])
    else:
        refine_chain = load_summarize_chain(llm,
                                            chain_type="refine",
                                            question_prompt=initial_prompt,
                                            refine_prompt=refine_prompt,
                                            document_variable_name="context")
        summary = refine_chain.invoke({"input_documents": documents, "question": question})
    return parse_result(summary)

def main():
    if len(sys.argv) not in [2, 3]:
        print("使い方: python pmid2abst.py [chain_type] <PubMedID>")
        print("chain_typeは'stuff'または'refine'を指定してください。（指定がなければ'stuff'がデフォルトになります）")
        sys.exit(1)
    if len(sys.argv) == 3:
        chain_type = sys.argv[1]
        pmid = sys.argv[2]
    else:
        chain_type = "stuff"
        pmid = sys.argv[1]

    info = get_article_info(pmid)
    if not info:
        print("文献情報が取得できませんでした。")
        sys.exit(1)

    # タイトルと著者情報を表示
    print("【タイトル】")
    print(info.get('title') if info.get('title') else "タイトルが見つかりませんでした。")
    print("【著者情報】")
    if info.get('authors'):
        print(", ".join(info.get('authors')))
    else:
        print("著者情報が見つかりませんでした。")
    print("【PMCID】")
    print(info.get('pmcid'))

    # 本文および要約を取得
    summary = None
    if info.get('pmcid') != "No_PMCID":
        full_text = get_full_text_by_pmcid(info.get('pmcid'))
        if full_text:
            try:
                if chain_type.lower() == "refine":
                    summary = refine_summarize_text(full_text)
                else:
                    summary = summarize_text(full_text)
            except Exception as e:
                print(f"要約生成中にエラーが発生しました: {e}")
        else:
            print("\n【全文が取得できませんでした】")
    if not summary:
        if info.get('abstract'):
            print("【アブストラクト本文】")
            print(info.get('abstract'))
            try:
                if chain_type.lower() == "refine":
                    summary = refine_summarize_text(info.get('abstract'))
                else:
                    summary = summarize_text(info.get('abstract'))
            except Exception as e:
                print(f"要約生成中にエラーが発生しました: {e}")
        else:
            print("アブストラクト本文が見つかりませんでした。")
    if summary:
        print("# ChatGPT Summary")
        print(summary)
        print("Abstract text")
        print(info.get('abstract'))
    else:
        print("要約が取得できませんでした。")

if __name__ == "__main__":
    main()
