# -*- coding: utf-8 -*-
"""Update available Scihub links

method 1: Crawling the website https://lovescihub.wordpress.com/
method 2: Brute force search
"""
import requests, os, sys, re, string, random
from bs4 import BeautifulSoup
from qspider import ThreadManager, Task
from termcolor import colored
from colorama import init
from scholar.configs import API_KEY

init()

LETTERS = list(string.ascii_lowercase)
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

PROXIES = {
    "http": "http://scraperapi:{}@proxy-server.scraperapi.com:8001".format(API_KEY),
    "https": "http://scraperapi:{}@proxy-server.scraperapi.com:8001".format(API_KEY),
}


def update_link(mod="c"):
    LINK_FILE = open(get_resource_path("link.txt"), "w", encoding="utf-8")
    print(STD_INFO + "Updating links ...")
    PATTERN = r">(htt[^:]+://sci-hub.[^</]+)<"
    if mod == "c":
        # method 1: crawl the website.
        # src_url = "https://sci-hub.top/"
        # src_url = "https://lovescihub.wordpress.com/"
        src_url = "http://tool.yovisun.com/scihub/"
        html = requests.get(src_url).text
        available_links = re.findall(PATTERN, html)
        for link in available_links:
            if link[-3:] != "fun":
                print(STD_INFO + "%s" % (link))
                LINK_FILE.write(link + "\n")
    elif mod == "b":
        # method 2: brute force search
        def get_url_list():
            url_list = []
            url_pre = "http://sci-hub."
            url_pre2 = "https://sci-hub."
            for first_letter in LETTERS:
                for last_letter in LETTERS:
                    url = url_pre + first_letter + last_letter
                    url2 = url_pre2 + first_letter + last_letter
                    url_list.extend([url, url2])
            return url_list

        class SearchTask(Task):
            def __init__(self, link):
                Task.__init__(self, link)
                self.link = link

            def run(self):
                try:
                    html = requests.get(self.link, timeout=3).content
                    soup = BeautifulSoup(html, "lxml")
                    title = soup.title.contents[0]
                    if title[:7] == "Sci-Hub":
                        msg = "\r" + STD_INFO + "Found %s" % (self.link)
                        print(msg.ljust(os.get_terminal_size().columns, " "))
                        LINK_FILE.write(self.link + "\n")
                except Exception as e:
                    # print("\r%spassing...".ljust(60) %(STD_INFO), end='')
                    return

        tm = ThreadManager(
            get_url_list(),
            SearchTask,
            has_result=False,
            num_workers=500,
            add_failed=True,
        )
        tm.run()
    LINK_FILE.close()


def get_resource_path(path):
    dir_path = os.path.dirname(__file__)
    dir_path = dir_path if dir_path else os.getcwd()
    return os.path.join(dir_path, path)


class SciHub(object):
    def __init__(self, doi, out=".", proxy=False):
        self.doi = doi
        self.out = out
        self.sess = requests.Session()
        if proxy:
            self.sess.proxies.update(PROXIES)
        self.sess.headers.update(random.choice(HEADERS))
        self.check_out_path()
        self.read_available_links()

    def check_out_path(self):
        if not os.path.isdir(self.out):
            os.mkdir(self.out)

    def read_available_links(self):
        with open(get_resource_path("link.txt"), "r") as f:
            self.scihub_url_list = [l[:-1] for l in f.readlines()]

    def update_link(self, mod="c"):
        update_link(mod)
        self.read_available_links()

    def use_scihub_url(self, index):
        self.scihub_url = self.scihub_url_list[index]
        print(STD_INFO + "Choose the available link %d: %s" % (index, self.scihub_url))
        if self.scihub_url[-3:] == "red":
            self.scihub_url = self.scihub_url.replace("red", "tw")

    def download(self, choose_scihub_url_index=-1):
        """Download the pdf of self.doi to the self.out path.

        params:
            choose_scihub_url_index: (int)
                -1: Auto-choose the scihub urls.
                >=0: index of scihub url in scihub url links.
        """

        # Auto choose scihub urls.
        if choose_scihub_url_index == -1:
            # Check valid scihub urls
            scihub_url_index = 0
            while True:
                if scihub_url_index >= len(self.scihub_url_list):
                    print(STD_WARNING + "All Scihub links are invalid.")
                    self.update_link(mod="c")
                    self.download()

                self.use_scihub_url(scihub_url_index)
                scihub_paper_url = "%s/%s" % (self.scihub_url, str(self.doi))
                res = self.sess.get(scihub_paper_url, stream=True, verify=False)
                if res.text in ["\n", ""] or res.status_code in [429, 404]:
                    print(
                        STD_ERROR
                        + "Current Scihub link is invalid, changing another link..."
                    )
                    scihub_url_index += 1
                else:
                    break
        else:
            self.use_scihub_url(choose_scihub_url_index)
            scihub_paper_url = "%s/%s" % (self.scihub_url, str(self.doi))
            res = self.sess.get(scihub_paper_url, stream=True, verify=False)
        if len(res.content.strip()) == 0:
            return None  # skip empty pages on Sci Hub
        if (
            self.is_captcha_page(res)
            or res.headers["Content-Type"] == "application/pdf"
        ):
            pdf = {"pdf_url": scihub_paper_url, "title": self.check_title(self.doi)}
            print(
                STD_INFO
                + colored("PDF url", attrs=["bold"])
                + " -> \n\t%s" % (pdf["pdf_url"])
            )
            print(
                STD_INFO
                + colored("Article title", attrs=["bold"])
                + " -> \n\t%s" % (pdf["title"])
            )
        else:
            pdf = self.find_pdf_in_html(res.text)

        title = self.download_pdf(pdf)
        return title

    def find_pdf_in_html(self, html):
        """Find pdf url and title in a scihub html
        params:
            html: (str) scihub html in string format.
        returns:
            (dict) {
                'pdf_url': (str) real url of the pdf.
                'title': (str) title of the article.
            }
        """
        pdf = {}
        soup = BeautifulSoup(html, "html.parser")

        pdf_url = soup.find("iframe", {"id": "pdf"}).attrs["src"].split("#")[0]
        pdf["pdf_url"] = (
            pdf_url.replace("https", "http") if "http" in pdf_url else "http:" + pdf_url
        )

        title = " ".join(self._trim(soup.title.text.split("|")[1]).split("/")).split(
            "."
        )[0]
        title = title if title else pdf["pdf_url"].split("/")[-1].split(".pdf")[0]
        pdf["title"] = self.check_title(title)
        print(
            STD_INFO
            + colored("PDF url", attrs=["bold"])
            + " -> \n\t%s" % (pdf["pdf_url"])
        )
        print(
            STD_INFO
            + colored("Article title", attrs=["bold"])
            + " -> \n\t%s" % (pdf["title"])
        )
        return pdf

    def check_title(self, title):
        """Check title to drop invalid characters.

        params:
            title: (str) original title.

        returns:
            (str) title that drops invalid chars.
        """
        rstr = r"[\/\\\:\*\?\"\<\>\|]"  # / \ : * ? " < > |
        new_title = re.sub(rstr, " ", title)[:200]
        return new_title

    def download_pdf(self, pdf):
        """Download the pdf by given a pdf dict.
        params:
            pdf: (dict) {
                'pdf_url': (str) real url of the pdf,
                'title': (str) title of the article
            }
        """
        print(STD_INFO + "Verifying...")
        res = self.sess.get(pdf["pdf_url"], stream=True, verify=False)
        while True:
            if self.is_captcha_page(res):
                print(STD_INFO + "Captcha is required.")
                res.close()
                return "Captcha"
            else:
                print(STD_INFO + "Verification success.")
                break

        retry_times = 0
        while "Content-Length" not in res.headers and retry_times < 10:
            print("\r" + STD_INFO + "Retrying...", end="")
            res.close()
            res = self.sess.get(pdf["pdf_url"], stream=True, verify=False)
            retry_times += 1
        tot_size = (
            int(res.headers["Content-Length"]) if "Content-Length" in res.headers else 0
        )
        if tot_size == 0:
            return None
        out_file_path = os.path.join(self.out, pdf["title"] + ".pdf")
        downl_size = 0
        with open(out_file_path, "wb") as f:
            for data in res.iter_content(chunk_size=1024, decode_unicode=False):
                f.write(data)
                downl_size += len(data)
                if tot_size != 0:
                    perc = int(downl_size / tot_size * 100)
                    perc_disp = colored("[%3d%%] " % (perc), "green")
                else:
                    perc_disp = colored(STD_INFO)
                print(
                    "\r{0}Progress: {1} / {2}".format(perc_disp, downl_size, tot_size),
                    end="",
                )
        print("\n" + STD_INFO + "Done.".ljust(50))
        title = " ".join(pdf["title"].replace("\n", "").split())
        return title + ".pdf"

    def is_captcha_page(self, res):
        """Check if the result page is a captcha page."""
        # return 'must-revalidate' in res.headers['Cache-Control']
        return res.headers["Content-Type"] == "text/html; charset=UTF-8"

    def _trim(self, s):
        """Drop spaces located in the head or the end of the given string."""
        if len(s) == 0:
            return s
        elif s[0] == " ":
            return self._trim(s[1:])
        elif s[-1] == " ":
            return self._trim(s[:-1])
        else:
            return s


# if __name__ == "__main__":
#     DOI = r"https://doi.org/10.1002/gch2.202000102"
#     pdf = SciHub(DOI, "paper", proxy=True).download(choose_scihub_url_index=-1)
