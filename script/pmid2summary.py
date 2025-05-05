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

def summarize_text(text):
    """
    テキストをそのままLLMに渡して、指定のプロンプト（reduce_prompt）で要約を生成する。
    テキスト分割やmapreduceの機能は使用しない。chain_typeは"stuff"を用いる。
    """
    document = Document(page_content=text)
    reduce_prompt = PromptTemplate(
        input_variables=["text"],
        template="""
以下のテキストの内容を要約してください。要約は以下の手順に従って作成してください。
1. 論文の各章ごとに5段程度に詳しく要約すること。
2. 実験方法、データの種類、データ解析方法、対象とする生物学的機構を箇条書きにすること。
3. 研究分野での進展と今後の課題も含めること。
入力:
{text}
要約:
"""
    )
    llm = ChatOpenAI(temperature=0, model_name="gpt-4o")
    chain = load_summarize_chain(llm, chain_type="stuff", prompt=reduce_prompt)
    result = chain.invoke([document])
    if isinstance(result, str):
        return result
    elif isinstance(result, dict):
        if "output_text" in result:
            return result["output_text"]
        elif "content" in result:
            content_val = result["content"]
            if isinstance(content_val, dict):
                if "output_text" in content_val:
                    return content_val["output_text"]
                else:
                    def search_output(obj):
                        if isinstance(obj, dict):
                            if "output_text" in obj:
                                return obj["output_text"]
                            for value in obj.values():
                                found = search_output(value)
                                if found is not None:
                                    return found
                        elif isinstance(obj, list):
                            for item in obj:
                                found = search_output(item)
                                if found is not None:
                                    return found
                        return None
                    found = search_output(content_val)
                    if found is not None:
                        return found
                    else:
                        return str(content_val)
            elif isinstance(content_val, str):
                return content_val
            else:
                return str(content_val)
        else:
            return str(result)
    else:
        return str(result)

def refine_summarize_text(text):
    """
    テキストを分割してLLMに渡し、refine chainを用いたプロンプトで要約を生成する。
    refine chainは、初期要約に対して追加情報を統合し、より洗練された要約を生成します。
    """
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n\n", "\n\n"]
    )
    documents = [Document(page_content=chunk) for chunk in splitter.split_text(text)]
    initial_prompt = PromptTemplate(
        input_variables=["text"],
        template="""
あなたは、iPS細胞を対象とした分子生物学と細胞生物学の研究者です。以下の入力する論文の内容を他分野の研究者が理解できるように詳細に要約してください。また、要約の手順は以下に従ってください。
1. 以下の条件に則って各段落ごとに詳細に説明をしてください。
- 各段落を1000文字以上で説明
- バックグラウンドとなる生物学的な制御機構の情報を含めて説明
2. 以下の項目について論文中からそのまま抜き出して列挙してください。
- 研究の目的
- 対象とする細胞
- 登場する分子名
- 登場する分子が行う生物学的な制御機構
- 実験方法
- データの種類
- データ解析方法
3. この論文で示しているこの研究で現時点で明らかとなったことを詳細に要約してください。
4. この論文で示している制約や今後明らかにしなくてはならない研究課題を詳細に要約してください
入力:
{text}
要約:

"""
    )
    refine_prompt = PromptTemplate(
        input_variables=["text", "existing_summary"],
        template="""
あなたは、iPS細胞を対象とした分子生物学と細胞生物学の研究者です。以下の入力する論文の内容を他分野の研究者が理解できるように、既存の要約を改善してください。要約を改善する際に以下の条件に従ってください。
1. 現在の要約の内容に不足している内容があったら追加で2000文字以上で説明してください。
   - バックグラウンドとなる生物学的な制御機構の情報を含めて説明
   - 研究の目的
   - 対象とする細胞
   - 登場する分子名
   - 登場する分子が行う生物学的な制御機構
   - 実験方法
   - データの種類
   - データ解析方法
2. 最終的な要約に以下の項目を論文中からそのまま抜き出して列挙してください。
   - 研究の目的
   - 対象とする細胞
   - 登場する分子名
   - 登場する分子が行う生物学的な制御機構
   - 実験方法
   - データの種類
   - データ解析方法
3. 最終的な要約には各段落ごとに詳細に1000文字以上で説明してください。
3. この論文で示している、現時点で明らかとなったことを詳細に要約してください。
4. この論文で示している制約や、今後明らかにしなくてはならない研究課題を詳細に要約してください

新しい内容:
{text}
現在の要約:
{existing_summary}
"""
    )
    llm = ChatOpenAI(temperature=0, model_name="gpt-4o")
    chain = load_summarize_chain(
        llm, 
        chain_type="refine", 
        question_prompt=initial_prompt, 
        refine_prompt=refine_prompt
    )
    result = chain.invoke(documents)
    if isinstance(result, str):
        return result
    elif isinstance(result, dict):
        if "output_text" in result:
            return result["output_text"]
        elif "content" in result:
            content_val = result["content"]
            if isinstance(content_val, dict):
                if "output_text" in content_val:
                    return content_val["output_text"]
                else:
                    def search_output(obj):
                        if isinstance(obj, dict):
                            if "output_text" in obj:
                                return obj["output_text"]
                            for value in obj.values():
                                found = search_output(value)
                                if found is not None:
                                    return found
                        elif isinstance(obj, list):
                            for item in obj:
                                found = search_output(item)
                                if found is not None:
                                    return found
                        return None
                    found = search_output(content_val)
                    if found is not None:
                        return found
                    else:
                        return str(content_val)
            elif isinstance(content_val, str):
                return content_val
            else:
                return str(content_val)
        else:
            return str(result)
    else:
        return str(result)

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
        print("ChatGPT Summary")
        print(summary)
        print("Abstract text")
        print(info.get('abstract'))
    else:
        print("要約が取得できませんでした。")

if __name__ == "__main__":
    main()
