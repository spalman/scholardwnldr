import random
import re
from os import path
import argparse
import numpy as np
import pandas as pd
import requests
import tqdm.notebook as tq
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from termcolor import colored
from colorama import init
from scihub import *
from scholar.configs import DUMP_FREQ
import logging

init()
LOG_FILENAME = "crawler_logs.log"


def setup_logger(log_path):
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logger = logging.getLogger(__name__)

    logger.setLevel("INFO")
    # Use FileHandler() to log to a file
    # Add the log message handler to the logger
    log_file = path.join(log_path, LOG_FILENAME)
    file_handler = logging.FileHandler(log_file)
    rotation_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=100000, backupCount=2
    )
    logger.addHandler(rotation_handler)
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


STD_INFO = colored("[INFO] ", "green")
STD_ERROR = colored("[ERROR] ", "red")
STD_WARNING = colored("[WARNING] ", "yellow")
STD_INPUT = colored("[INPUT] ", "blue")


HEADERS = [
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36"
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9"
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1"
    },
]


def find_doi(content, url):
    """Search DOI from a page

    Parameters
    ----------
    content :
        request response content
    url : str
        Page URL

    Returns
    -------
    str
        Returns DOI if found, "Not found" otherwise.
    """
    soup = BeautifulSoup(content, "lxml")
    a = soup.find("a", {"href": re.compile(r"doi.org", flags=re.IGNORECASE)})

    if a:
        return a["href"]

    a = soup.body.find_all(
        text=re.compile(
            r"10.\d{4,9}\/[-._;()\/:A-Z0-9]+", flags=re.IGNORECASE + re.MULTILINE
        )
    )

    if a:
        if len(a[0]) < 100:
            return re.sub(r"^.*?10", "10", a[0], flags=re.DOTALL).strip()

        return re.sub(r"^.*?10", "10", a[1], flags=re.DOTALL).strip()

    logger.info("%s \t doi not found", url)
    return "Not found"


def get_doi(csv_file):
    """Crawl links and search for DOI.
    Edit file by adding found DOI for each link.

    Parameters
    ----------
    csv_file : str
        csv file with link column
    """
    df = pd.read_csv(csv_file)
    df = df.drop_duplicates(subset=["link"], keep="first")
    df = df.drop(df[df.title == "title"].index)
    df_size = len(df)
    excel_file = path.splitext(csv_file)[0] + ".xlsx"
    if "doi" not in df.columns:
        df["doi"] = ""
    if df.doi.dtype != "object":
        df["doi"] = df["doi"].astype("object")
    last_dump = datetime.now()
    try:
        for index, row in tq.tqdm(df.iterrows()):

            # dump
            if datetime.now() > last_dump + timedelta(minutes=DUMP_FREQ):
                df.to_csv(csv_file, index=False)
                df.to_excel(excel_file)
                last_dump = datetime.now()
                logger.info("Changes saved {} {}".format(csv_file, excel_file))
                logger.info(
                    "Links crawled: {}/{} {:.2f}%".format(
                        index, df_size, (index + 1) / df_size * 100
                    )
                )

            url = row["link"]

            if len(str(row["doi"])) > 5:
                continue
            if url.endswith("pdf") or "download" in url:
                continue  # do not search doi on direct pdf links
            try:
                response = requests.get(url, headers=random.choice(HEADERS), timeout=10)
                item = find_doi(response.content, url)
            except:
                logger.info("%s \t failed to access url.", url)
                item = ""
            df.at[index, "doi"] = item

    finally:
        df.to_csv(csv_file, index=False)
        df.to_excel(excel_file)


def download_pdfs(csv_file, out_path="papers"):
    """Downloading pdfs from SciHub by DOI.
    Edit file by adding filename for each DOI.

    Parameters
    ----------
    csv_file : str
        csv file with 'doi' column
    out_path : str, optional
        path to pdfs, by default "papers"
    """
    df = pd.read_csv(csv_file)
    df = df.drop(df[df.title == "title"].index)
    if "filename" not in df.columns:
        df["filename"] = ""
    if df.filename.dtype != "object":
        df["filename"] = df["filename"].astype("object")
    update_link("c")
    links = get_resource_path("link.txt")
    links = open(links, "r").readlines()
    url_index = 0
    out = out_path
    last_dump = datetime.now()
    df_size = len(df)
    excel_file = path.splitext(csv_file)[0] + ".xlsx"
    try:
        for index, row in tq.tqdm(df.iterrows()):
            if datetime.now() > last_dump + timedelta(minutes=DUMP_FREQ):
                df.to_csv(csv_file, index=False)
                df.to_excel(excel_file)
                last_dump = datetime.now()
                logger.info("Changes saved {} {}".format(csv_file, excel_file))
                logger.info(
                    "DOIs crawled: {}/{} {:.2f}".format(
                        index, df_size, (index + 1) / df_size * 100
                    )
                )
            success = False
            DOI = row["doi"]
            if len(str(row["filename"])) > 5:
                continue
            if row["link"].endswith("pdf") or "download" in row["link"]:
                pdf_obj = {"pdf_url": row["link"], "title": row["title"]}
                try:
                    pdf = SciHub(DOI, out).download_pdf(pdf_obj)
                    df.at[index, "filename"] = pdf + ".pdf"
                except:
                    logger.info(
                        "Falied to download pdf directly from \t{}".format(row["link"])
                    )
            if DOI == "Not found":
                continue
            if not DOI:
                continue

            url_index = 0
            while url_index < len(links) - 1 and not success:
                try:
                    pdf = SciHub(DOI, out).download(choose_scihub_url_index=url_index)
                    if not pdf:
                        pdf = "Not found at Sci-Hub"
                        logger.info("{} not found at Sci-Hub".format(DOI))
                        success = True
                    elif pdf == "Captcha":
                        raise ValueError("Captcha required")
                    success = True
                    df.at[index, "filename"] = pdf
                except Exception as e1:
                    try:
                        logger.debug("%s", str(e1))

                        print(STD_INFO + "Retrying with proxy")
                        pdf = SciHub(DOI, out, proxy=True).download(
                            choose_scihub_url_index=url_index
                        )
                        df.at[index, "filename"] = pdf + ".pdf"
                        success = True
                    except Exception as e2:
                        logger.debug("%s", str(e2))
                        url_index += 1
                        logger.info(
                            "Falied to download \t{} from \t{}".format(
                                DOI, links[url_index]
                            )
                        )
            if not success:
                logger.info(
                    "DOI: {} \t failed to download on any sci-hub mirror".format(DOI)
                )
    except Exception as e:
        logger.debug("%s", e)
    finally:
        df.to_csv(csv_file, index=False)
        df.to_excel(excel_file)


def main(args):
    """Command line tool to crawl links to find DOI and download pdfs via DOI from Scihub."""

    if args.search_doi:
        logger.info("Crawling links...")
        get_doi(args.file)
    if args.download_pdf:
        logger.info("Downloading pdfs...")
        download_pdfs(args.file, args.out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Command line tool to crawl links to find DOI and download pdfs via DOI from Scihub."
    )
    parser.add_argument("-f", "--file", help="cvs file with link")
    parser.add_argument("-o", "--out", help="path to pdfs")
    parser.add_argument("-d", "--search_doi", action="store_true")
    parser.add_argument("-p", "--download_pdf", action="store_true")
    args = parser.parse_args()
    logger = setup_logger(path.split(args.file)[0])

    main(args)

