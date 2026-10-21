"""DOI metadata from CrossRef."""
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from lxml import etree

from neurovault.core.application.ports import PaperProperties

QUERY_URL = "http://doi.crossref.org/servlet/query"


class CrossRefLookup:
    def lookup(self, doi):
        xmlpath = (
            QUERY_URL
            + "?pid=k.j.gorgolewski@sms.ed.ac.uk&format=unixref&id="
            + urllib.parse.quote(doi)
        )
        doc = etree.fromstring(urllib.request.urlopen(xmlpath).read())
        if len(doc.getchildren()) == 0 or len(doc.findall(".//crossref/error")) > 0:
            raise LookupError("DOI %s was not found" % doi)
        journal_name = doc.findall(".//journal/journal_metadata/full_title")[0].text
        title = doc.findall(".//title")[0].text
        authors = [
            a.findall("given_name")[0].text + " " + a.findall("surname")[0].text
            for a in doc.findall(".//contributors/person_name")
        ]
        if len(authors) > 1:
            authors = ", ".join(authors[:-1]) + " and " + authors[-1]
        else:
            authors = authors[0]
        url = doc.findall(".//doi_data/resource")[0].text
        date_node = doc.findall(".//publication_date")[0]
        year = int(date_node.findall("year")[0].text)
        month = int(date_node.findall("month")[0].text) if date_node.findall("month") else 1
        day = int(date_node.findall("day")[0].text) if date_node.findall("day") else 1
        return PaperProperties(title, authors, url, date(year, month, day), journal_name)
