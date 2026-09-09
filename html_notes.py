"""Extract HTML notes as inert text. Never execute scripts or load URLs."""
from html.parser import HTMLParser
from pathlib import Path

class NotesParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.skip=[]
    def handle_starttag(self, tag, attrs):
        if self.skip:
            if tag in ('script','style','head','nav','iframe','object'): self.skip.append(tag)
            return
        if tag in ('script','style','head','nav','iframe','object'):
            self.skip.append(tag)
        elif tag in ('p','div','section','h1','h2','h3','h4','li','tr','br','pre'):
            self.parts.append('\n')
    def handle_endtag(self,tag):
        if self.skip:
            if tag == self.skip[-1]: self.skip.pop()
        elif tag in ('p','div','section','li','tr','h1','h2','h3'):
            self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip: self.parts.append(data+' ')

def extract_html_notes(path):
    parser=NotesParser()
    parser.feed(Path(path).read_text(encoding='utf-8-sig'))
    text='\n'.join(' '.join(line.split()) for line in ''.join(parser.parts).splitlines() if line.strip())
    if not text.strip(): raise ValueError('No readable text in this HTML file.')
    return text

def odia_requested(language, question=''):
    import re
    return bool(re.search(r'odia|oriya|ଓଡ଼ିଆ|ଓଡିଆ', language, re.I) or
                re.search(r'(?:in|into|me|mein)\s+(?:odia|oriya)|(?:odia|oriya)\s+(?:me|mein)|ଓଡ଼ିଆରେ',question,re.I))

def has_odia_prose(text):
    odia=sum('\u0b00'<=c<='\u0b7f' for c in text)
    hindi=sum('\u0900'<=c<='\u097f' for c in text)
    return odia>=15 and odia>hindi*3
