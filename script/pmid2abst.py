#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PubMed IDに基づいてNCBI Eutils APIを使用し、論文情報（タイトル、著者情報、アブストラクト）を取得するスクリプト

使用方法:
    python pmid2abst.py <PubMedID>
"""

import sys
import requests
import xml.etree.ElementTree as ET
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
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
    
    # アブストラクト取得
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

def split_text(text):
    """
    指定したテキストを分割する（現在使用していません）
    """
    return text

def summarize_text(text):
    """
    指定した文章をLangChainとGPTを用いて要約する
    """
    prompt_template = "はじめにこの論文の対象とする細胞、実験方法、データの種類、データ解析方法、対象とする生物学的機構を箇条書きにして出力してください。その後この論文で言及されていることを5000文字でまとめて説明してください。説明の中にはこの研究分野で何ができるようになって、何が課題になっているかも含めてください。:\n\n{text}\n\n要約:"
    prompt = PromptTemplate(input_variables=["text"], template=prompt_template)
    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")
    # チャット形式のメッセージとして渡す
    messages = [{"role": "user", "content": prompt.format(text=text)}]
    result = llm.invoke(messages)
    # 結果を処理。返り値がリストの場合は、先頭のメッセージのcontentを返す
    if isinstance(result, list) and len(result) > 0:
        outputs = []
        for item in result:
            if hasattr(item, "content"):
                outputs.append(item.content)
            else:
                outputs.append(str(item))
        return "\n".join(outputs)
    elif isinstance(result, dict) and "content" in result:
        return result["content"]
    elif isinstance(result, str):
        return result
    else:
        return result

def main():
    if len(sys.argv) != 2:
        print("使い方: python pmid2abst.py <PubMedID>")
        sys.exit(1)

    pmid = sys.argv[1]
    info = get_article_info(pmid)
    if not info:
        print("文献情報が取得できませんでした。")
        sys.exit(1)

    # タイトルと著者情報を表示
    print("\n【タイトル】")
    print(info.get('title') if info.get('title') else "タイトルが見つかりませんでした。")
    print("\n【著者情報】")
    if info.get('authors'):
        print(", ".join(info.get('authors')))
    else:
        print("著者情報が見つかりませんでした。")
    print("\n【PMCID】")
    print(info.get('pmcid'))

    # 本文および要約を取得
    summary = None
    if info.get('pmcid') != "No_PMCID":
        full_text = get_full_text_by_pmcid(info.get('pmcid'))
        if full_text:
#            print("\n【全文】")
#            print(full_text)
            try:
                summary = summarize_text(full_text)
            except Exception as e:
                print(f"要約生成中にエラーが発生しました: {e}")
        else:
            print("\n【全文が取得できませんでした】")
    if not summary:
        # full_textが取得できなかった場合はアブストラクトで要約を試みる
        if info.get('abstract'):
            print("\n【アブストラクト本文】")
            print(info.get('abstract'))
            try:
                summary = summarize_text(info.get('abstract'))
            except Exception as e:
                print(f"要約生成中にエラーが発生しました: {e}")
        else:
            print("アブストラクト本文が見つかりませんでした。")
    if summary:
        print("\n ChatGPT Summary")
        print(summary.content)
        print("Abstract text")
        print(info.get('abstract'))
    else:
        print("要約が取得できませんでした。")

if __name__ == "__main__":
    main()
