from flair.data import Sentence
from flair.models import SequenceTagger
from sys import argv
from urllib.parse import urlparse
import json, os, sys, re, time
import nltk, phonenumbers
#from html.parser import HTMLParser
from difflib import SequenceMatcher
from names_dataset import NameDataset
from random import randint

#isHTML=False
emails=[]
names=dict()

toanon=dict()
our_suffixes=['usc.edu', 'isi.edu']
our_orgs=['usc', 'university of southern california', 'information sciences institute', 'institute for creative technologies', 'usc/isi', 'usc-isi', 'usc isi', 'isi', 'ict']

def is_number(text):
    for i in range(0, len(text)):
        if not text[i].isdigit():
            return False
    return True

def find_overlap(name, toadd):
    global emails, names
    overlap = 0
    name = strip(name)
        
    for e in emails:
        eparts = e.split('@')
        euid = eparts[0].lower()
        match = SequenceMatcher(None, euid, name.lower()).find_longest_match(0, len(euid), 0, len(name))
        if toadd:
            if match.size == len(name) and (match.a  == 0 or match.a + match.size == len(euid)) and match.size > 3:
                names[name.title()] = 1
                # Find out which part of euid is left and add that to anonymization set too
                if match.a == 0 and match.size < len(euid):
                    # Likely last name
                    names[euid[match.size:].title()] = 2
                if match.a > 0:
                    # Likely first name
                    names[euid[0:match.a].title()] = 1
        else:
            if (match.a == 0 or match.a + match.size == len(euid)) and match.b == 0 and match.size > 0:
                for n in names:
                    if euid == n.lower() + euid[match.a:match.a + match.size] or euid == euid[match.a: match.a + match.size] + n.lower():
                        names[name.title()] = 1
                        if match.a == 0 and match.size < len(euid):
                            # Likely last name
                            names[euid[match.size:].title()] = 2
                        if match.a > 0:
                            # Likely first name
                            names[euid[0:match.a].title()] = 1
                        break


def find_urls(content):
    #url_extract_pattern = "https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)"
    p_list = re.split('[\<\>\(\)\s]', content)
    for p in p_list:
        a = urlparse(p)
        if a.netloc == "urldefense.com":
            i = a.path.find("http")
            b = urlparse(a.path[i:])
            toanon[p] = "url"
            anonymized[p] = b.scheme+"://"+b.netloc
        elif a.scheme == 'http' or a.scheme == 'https':
            toanon[p] = "url"
            anonymized[p] = a.scheme+"://"+a.netloc
    
def find_addresses(content):
    global toanon, anonymized
    streets=['street', 'st', 'ave', 'avenue', 'blvd', 'boulevard', 'court', 'ct', 'road', 'rd', 'highway', 'hwy', 'lane', 'ln', 'way',
             'drive', 'dr', 'terrace', 'ter', 'place', 'pl', 'plaza']
    longstates=['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware', 'District of Columbia', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming']
    shortstates=['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']    
            
    # Split into new lines first
    loc = ""
    s_list = content.split('\n')
    for s in s_list:
        a_list = nltk.tokenize.sent_tokenize(s)
        for a in a_list:
            p_list = re.split('[\s\,\.\!\?]', a)
            for i in range(0, len(p_list)):
                for j in range (0,3):
                    if j == 0:
                        candidate = p_list[i]
                    elif j == 1:
                        if i < len(p_list) - 1:
                            candidate = p_list[i] + ' ' + p_list[i+1]
                        else:
                            continue
                    else:
                        if i < len(p_list) - 2:
                            candidate = p_list[i] + ' ' + p_list[i+1] + ' ' + p_list[i+2]
                        else:
                            continue

                    if candidate in toanon and toanon[candidate] == "LOC":
                        # Figure out if it is street, city, state, zip
                        words = candidate.split(' ')
                        aloc = []
                        prev = ""
                        foundstate = ""
                        for w in words:
                            if is_number(w):
                                if not foundstate:
                                    w = randint(1, 10000)
                                    aloc.append(str(w))
                                else:
                                    aloc.append("11111")
                                foundstate = False
                            elif w.lower() in streets:
                                # Remove last item from aloc and add anon street name
                                aloc.pop()
                                aloc.append("Anon")
                                aloc.append(w)
                                foundstate = False
                            elif w not in longstates and w not in shortstates:
                                if not foundstate:
                                    aloc.append("AnonCity")
                                else:
                                    aloc.append("11111")
                                    foundstate = False
                            elif w in longstates:
                                aloc.append("AnonState")
                                foundstate = True
                            else:
                                aloc.append("AN")
                                foundstate = True
                            prev = w                        
                        anonymized[candidate] = ' '.join(aloc)

                        
def check_names(content):
    # Split into new lines first
    s_list = content.split('\n')
    for s in s_list:
        a_list = nltk.tokenize.sent_tokenize(s)
        for a in a_list:
            p_list = a.split(' ')
            for p in p_list:
                ov = find_overlap(p, True)

        
def tag_sentence(content):
    greetings=['hi', 'hello', 'good', 'morning', 'evening', 'day', 'afternoon', 'dear', 'respected', 'mr', 'mrs', 'miss', 'dr', 'prof', 'doctor', 'professor', 'greetings']
    # Split into new lines first
    s_list = content.split('\n')
    for s in s_list:
        a_list = nltk.tokenize.sent_tokenize(s)
        for a in a_list:
            # make a sentence
            sentence = Sentence(a)            
            
            # run NER over sentence
            tagger.predict(sentence)
            
            # print the sentence with all annotations
            #print(sentence)
            
            
            # iterate over entities and print each
            for entity in sentence.get_spans('ner'):
                # print entity text, start_position and end_position
                text=entity.text
                value=entity.get_label("ner").value
                
                if value=="PER":
                    # Check if there is something extra
                    words = text.split(' ')
                    if len(words) >= 2:
                        for w in words:
                            w = strip(w)
                            if w.lower() in greetings:
                                words.remove(w)
                            else:
                                toanon[w.title()] = value
                                    
                elif value=="ORG" or value=="LOC":
                    w = strip(text)
                    # Do not anon America
                    if text.title() != "America":
                        toanon[w] = value

def strip(word):
    if len(word) > 0 and not word[-1].isalpha():
        return word[0:len(word)-1]
    return word

    
def check_email(content):
    # Split into new lines first
    s_list = content.split('\n')
    p_list = []
    for s in s_list:
        a_list = s.split(" ")
        for a in a_list:
            if re.search("(^\w+@\w+\.(\w+.)?\w+$)", a):
                p_list.append(a)
    return p_list


def check_phone(content):
    # Split into new lines first
    s_list = content.split('\n')
    p_list = []
    for s in s_list:
        a_list = re.split('[\s\,\.\!\?\<\:]', s)
        for i in range(0, len(a_list)):
            for j in range (0,3):
                if j == 0:
                    candidate = a_list[i]
                elif j == 1:
                    if i < len(a_list) - 1:
                        candidate = a_list[i] + ' ' + a_list[i+1]
                    else:
                        continue
                else:
                    if i < len(a_list) - 2:
                        candidate = a_list[i] + ' ' + a_list[i+1] + ' ' + a_list[i+2]
                    else:
                        continue
                if len(candidate) > 0 and not candidate[-1].isdigit():
                    candidate=candidate[0:len(candidate)-2]

                valid=False
                
                try:
                    valid=phonenumbers.is_valid_number(phonenumbers.parse(candidate, "US"))
                except:
                    pass

                isFormatted = True
                if valid:
                    # Check if this string has any alphabetic chars
                    # or any other characters that are not in the right place
                    isND=False
                    for k in range(0, len(candidate)):
                        if not candidate[k].isdigit():
                            isND = True
                            isFormatted = False
                            break
                    if isND:
                        if re.search("(^\(\d\d\d\)\s?\d\d\d[\-\.]?\s?\d\d\d\d$)", candidate):
                            isFormatted = True
                        if re.search("(^\d\d\d[\-\.]\s?\d\d\d[\-\.]?\s?\d\d\d\d$)", candidate):
                            isFormatted = True
                            
                    if isFormatted:
                        p_list.append(candidate)

    return p_list

def parse(data):
    global toanon, emails
    # Check if there are phone numbers in the data
    p_list=check_phone(data)
    for p in p_list:
        toanon[p]="phone"
        
    a_list=check_email(data)
    for a in a_list:
        toanon[a]="email"
        
    if len(emails) == 0:
        tag_sentence(data)
    else:        
        check_names(data)
        
                
#class MyHTMLParser(HTMLParser):
    
#    def handle_starttag(self, tag, attrs):
#        global isHTML
#        if tag=='html':
#            isHTML=True

#    def handle_endtag(self, tag):
#        global isHTML
#        if tag=='html':
#            isHTML=False

#    def handle_data(self, data):
#        global toanon, emails
        # Check if there are phone numbers in the data
#        p_list=check_phone(data)
#        for p in p_list:
#            toanon[p]="phone"
#        a_list=check_email(data)
#        for a in a_list:
#            toanon[a]="email"

#        if len(emails) == 0:
#            tag_sentence(data)
#        else:        
#            check_names(data)
        
def get_random_phone():
    phone = "("
    for i in range(0,10):
        phone += str(randint(0,9))
        if i == 2:
            phone += ") "
        if i == 5:
            phone += "-"
    return phone

def get_random_name (last):
    global first_names, last_names
    if last:
        n=randint(0,500)
        return last_names[n]
    else:
        n=randint(0,1000)
        return first_names[n]


def anonymize_email(text):
    global anonymized, toanon
    for e in toanon:
        if toanon[e] == "email":
            if e in anonymized:
                text = text.replace(e, anonymized[e])
    return text

def anonymize_url(text):
    global anonymized, toanon
    for e in toanon:
        if toanon[e] == "url":
            if e in anonymized:
                text = text.replace(e, anonymized[e])
    return text


def anonymize_location(text):
    global anonymized, toanon
    for e in toanon:
        if toanon[e] == "LOC":
            if e in anonymized:
                text = text.replace(e, anonymized[e])                
            # Do second pass to remove zip codes
            newtext = ""
            n_list = text.split('\n')
            for n in n_list:
                p_list = n.split(' ')
                a_list = []
                prev = ""
                for p in p_list:
                    if prev == "AN":
                        continue
                    else:
                        prev = p
                        a_list.append(p)
                newtext += ' '.join(a_list)
                newtext += '\n'
            text = newtext
    return text


def same_digits(a,b):
    an = ""
    for e in re.split('\D', a):
        an += e
    bn = ""
    for e in re.split('\D', b):
        bn += e
    if an == bn:
        return True
    return False
        
def anonymize_phone(text):
    global anonymized, toanon
    for e in toanon:
        if toanon[e] == "phone":
            if e in anonymized:
                text = text.replace(e, anonymized[e])
    return text

def anonymize(text):
    global anonymized
    
    text=anonymize_phone(text)
    text=anonymize_url(text)
    text=anonymize_email(text)
    text=anonymize_location(text)
    newtext=""
    a_list = nltk.tokenize.sent_tokenize(text)
    for a in a_list:
        newsen = ""
        s_list = re.split('([\W\_])', a)
        for b in s_list:                
            if b in anonymized:
                newsen += anonymized[b] 
            elif b.title() in anonymized:
                newsen += anonymized[b.title()]
            else:
                newsen += b
        newtext += newsen + '\n'
    return newtext
    
#parser = MyHTMLParser()
nd=NameDataset()
d1=nd.get_top_names(n=500, country_alpha2="US")
first_names = d1['US']['M'] + d1['US']['F']
d1=nd.get_top_names(n=500, country_alpha2="US", use_first_names=False)
last_names = d1['US']

#nltk.download('punkt')
tagger = SequenceTagger.load('ner')
anonymized=dict()
text = ""

dir_path = argv[1]
out_path = argv[2]
if not os.path.exists(out_path):
    os.mkdir(out_path)
for path in os.listdir(dir_path):
    # check if current path is a file
    if os.path.isfile(os.path.join(dir_path, path)):
        print("MESSAGE ", path)
        text = ""
        header = []
        f = open(os.path.join(dir_path, path))
        data = json.load(f)
        for elem in data["body"]:
            if elem["content_header"]["content-type"][0].find("text/plain") > -1:                
                parse(elem["content"])
                text += elem["content"]
        for elem in data["header"]["from"], data["header"]["to"], data["header"]["subject"]:
            if isinstance(elem, list):
                for e in elem:
                    parse(e)
                    header.append(e)
            else:
                parse(elem)
                header.append(elem)
            

        emails=[]
        lastname=dict()
        names.clear()
        for a in toanon:
            if toanon[a] == "email":
                emails.append(a)

        # Second pass to detect missing names
        parse(text)

        for a in toanon:
            #print("To anon ", a, " type ", toanon[a])
            if toanon[a] == "PER":
                names[a] = 1

        # Now hunt for last names
        s_list = text.split('\n')
        for s in s_list:
            a_list = nltk.tokenize.sent_tokenize(s)
            for a in a_list:
                p_list = a.split(' ')
                
                # Find missing names
                for p in p_list:
                    if p.title() not in names and (p.title() not in toanon and p not in toanon):
                        find_overlap(p, False)

                # Second pass to find missing last names
                prev = None
                for p in p_list:
                    p = strip(p)
                    if p.title() in names and prev is not None:
                        # This is a last name
                        names[p.title()] = 2
                        lastname[prev] = p.title()
                    if p.title() in names and prev is None:
                        prev = p.title()

        anonymized.clear()
        
        for n in names:
            if len(n.strip()) == 0:
                continue
            if n.title() not in anonymized:
                if names[n.title()] == 1:
                    an = get_random_name(False)
                    anonymized[n.title()] = an
                else:
                    an = get_random_name(True)
                    anonymized[n.title()] = an
                    
        for e in emails:
            eparts = e.split('@')
            euid = eparts[0].lower()
            esuf = eparts[1]
            aeuid = ""
            for name in names:
                match = SequenceMatcher(None, euid, name.lower()).find_longest_match(0, len(euid), 0, len(name))                
                if match.size > 0 and match.a == 0 and names[name] == 1:
                    #print("Found overlap between ", euid, " and first name ", name.title())
                    aeuid = anonymized[name.title()]
                    found = False
                    if name.title() in lastname:
                        #print("Found in lastname ", lastname[name.title()])
                        aeuid += anonymized[lastname[name.title()]]
                    else:    
                        for lname in names:
                            if names[lname] == 2:
                                for i in range (1,len(lname)):  
                                    seg = lname[:i+1].lower()
                                    #print ("Trying segment ", seg)
                                    if name.lower() + seg == euid:                                  
                                        aeuid += anonymized[lname.title()]
                                        found = True
                                        break
                            if found:
                                break
                if aeuid == "":
                    aeuid = (get_random_name(False) + get_random_name(True))
                anonymized[euid] = aeuid.lower()
                for suf in our_suffixes:
                    if esuf.endswith(suf):
                        anonymized[e] = anonymized[euid] + "@anon.org"
                        break
                break
            
            if euid not in anonymized:
                for suf in our_suffixes:
                    if esuf.endswith(suf):
                        aeuid = (get_random_name(False) + get_random_name(True))
                        anonymized[euid] = aeuid.lower()
                        anonymized[e] = anonymized[euid] + "@anon.org"
                        break
                        
            for a in toanon:
                if toanon[a] == "ORG" and a.lower() in our_orgs:
                    anonymized[a] = "OrgAnon"
                if toanon[a] == "phone":
                    # Check for duplicates
                    for b in toanon:
                        if toanon[b] == "phone":
                            if same_digits(a,b) and b in anonymized:
                                anonymized[a] = anonymized[b]
                    if a not in anonymized:
                        anonymized[a] = get_random_phone()
                        
        # Hunt for addresses
        find_addresses(text)

        # Hunt for URLs
        find_urls(text)


        for a in anonymized:
            print("Will anon ", a, " as ", anonymized[a])
            
        text=anonymize(text)

        f = open(out_path + "/" + path, "w")
        f.write("From:" + anonymize(header[0]))
        f.write("To:" + anonymize(header[1]))
        f.write("Subject:" + anonymize(header[2]))
            
        f.write(text)
        f.close()
        text = ""        
        toanon.clear()
        emails=[]
        names.clear()
