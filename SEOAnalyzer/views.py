from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from django.http import HttpResponse
from django.shortcuts import render,redirect,reverse
from django.views.decorators.cache import never_cache
from django.contrib import messages
#import modules
import favicon
import requests
import urllib.request
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import re
from collections import Counter
import kaleido
import plotly.express as px
import json
import pycountry
import builtwith
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from math import pi
from PIL import Image
from py_w3c.validators.html.validator import HTMLValidator
import ssl
import socket
import geocoder
import time
import csscompressor
from jsmin import jsmin
import json
from PIL import Image
#---MOZ API
import json
import hashlib
import hmac
import time
import urllib.parse
import requests
import base64
import validators
from .helpers import send_forget_password_mail
import uuid
from .models import Profile
#---chrome driver
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from django.http import FileResponse

from webdriver_manager.chrome import ChromeDriverManager
Report_variables={}

# Create your views here.
class Website_Audit(object):
    def __init__(self, url):
        self.url = url
        session_obj = requests.Session()
        self.response = session_obj.get(url, headers={"User-Agent": "Mozilla/5.0"},timeout=300).text
        self.soup = BeautifulSoup(self.response, 'html.parser')
        self.title_score = 0
        self.desc_score = 0
        self.heading_score = 0
        self.internal_links = 0
        self.external_links = 0
        self.avg_score = 0
        self.alt_count = 0
        self.title = ""
        self.desc = ""
        self.heading = None
        self.H = None
        self.comp_desc = ""
        self.comp_head = ""
        self.conversion = None
        self.dict_1 = None
        self.total_count = 0
        self.Img_score = 0
        self.robot_flag = False
        self.sitemap_flag = False
        self.b_links = 0
        self.icon_flag = None
        self.schema_flag = None
        self.ogp_flag = None
        self.fb_flag = False
        self.insta_flag = False
        self.twitter_flag = False
        self.linkedin_flag = False
        self.ip_flag = None
        self.ip=None
        self.s_count = 0
        self.server_loc_flag = None
        self.loc_name = None
        self.error_len = 0
        self.warn_len = 0
        self.analytics_flag = None
        self.tech_flag = False
        self.webserver = None
        self.doc_flag = False
        self.encod_flag = False
        self.Doctype = None
        self.Encoding = None
        self.keyword_lst = []
        self.speed = 0  # new added
        self.plugins = None
        self.css = None
        self.jss = None
        self.mob_score = 0
        self.amp = None
        self.render = None
        self.mobpreview = None
        self.name = None
        self.organization = None
        self.ssl = False
        self.dmca = None
        self.https = None
        self.data = {}
        self.expiry_date=None
        self.lst=[]

    def Score(self, max_val, length):
        if length > max_val:
            length = max_val - 10
        score = (length / max_val) * 100
        score = round(score)
        return score

    def remove_unicode_characters(self,input_string):
        encoded_bytes = input_string.encode("ascii", "ignore")
        decoded_string = encoded_bytes.decode("ascii")
        return decoded_string

    def get_title(self, min_length=30, max_length=60):
        title1 = self.soup.find('title')

        if title1 == []:
            return None
        else:
            try:
                title1 = self.soup.find('title').get_text()
                title = self.remove_unicode_characters(title1)
            except:
                title=''
            title_length = len(title)


            if title_length == 0:
                self.title="Title is not Found!"
            if title_length < min_length:
                self.title = "Title is too Short!"
            elif min_length <= title_length <= max_length:
                self.title = "Title is good!"
            else:
                self.title = "Title is too long!"
            self.data['title_verdict']=' | '+self.title
            self.title = title
            self.data['title'] = self.title
            title_score = self.Score(max_length, title_length)
            self.title_score = title_score
            return title

    def get_description(self, min_length=50, max_length=160):
        meta = self.soup.findAll("meta")
        description = ""
        for tag in meta:
            if 'name' in tag.attrs.keys() and tag.attrs['name'].strip().lower() in ['description']:
                if tag.attrs['content'] == "":
                    pass
                elif tag.attrs['content'] != "":
                    description = description + tag.attrs['content']
                    self.comp_desc = self.remove_unicode_characters(description)
                    self.data['description']=self.comp_desc
                else:
                    return None
        # Calculate Length
        desc_length = len(self.comp_desc)
        if desc_length == 0:
            self.desc = "Description not found!"
        elif desc_length <= min_length and desc_length != 0:
            self.desc = "Description is too Short"
        elif min_length <= desc_length <= max_length:
            self.desc = "Description is good"
        else:
            self.desc = "Description is too long"
        self.data['desc_verdict']=' | '+self.desc
        desc_score = self.Score(max_length, desc_length)
        self.desc_score = desc_score
        return

    def get_Heading(self, min_length=20, max_length=60):
        Heading = ""
        h1 = self.soup.findAll('h1')
        if h1 == []:
            # print("Website does'nt have H1 Heading!")
            h2 = self.soup.findAll('h2')
            if h2 == []:
                pass
                # print("Website does'nt have H2 Heading!")
            else:
                Heading = h2
        else:
            Heading = h1

        heading = ""
        for i in Heading:
            heading = heading + i.get_text(strip=True)
            if Heading == h1:
                self.H = "H1"
                self.comp_head = heading
                break
            else:
                self.H = "H2"
                self.comp_head = heading
                break

        com_heading=self.remove_unicode_characters(heading)
        heading_length = len(com_heading)
        if heading_length == 0 or heading_length== 1:
            self.heading = "Heading Tag is Empty"
            heading_length == 0
        elif heading_length < min_length:
            self.heading = "Heading is too Short"
        elif min_length <= heading_length <= max_length:
            self.heading = "Heading is good"
        else:
            self.heading = "Heading is too long"

        self.data['head_verdict'] = ' | ' + self.heading
        if len(com_heading) ==0 or len(com_heading) ==1:
            self.data['heading'] = ''
        else:
            self.data['heading'] = com_heading

        heading_score = self.Score(max_length, heading_length)
        self.heading_score = heading_score
        return

    def get_Google_preview(self):
        self.avg_score = (self.title_score + self.desc_score + self.heading_score) / 3
        self.avg_score = round(self.avg_score)
        min = 50
        max = 100
        if min <= self.avg_score <= max:
            google1 = "Google Preview is SEO Optimzed"
            # print("Google Preview is SEO Optimzed")
            self.data['google_verdict']=google1
            self.data['verdict']=True
            return 1
        else:
            google1 = "Google Preview is not Optimized"
            # print("Google Preview is not Optimized")
            self.data['google_verdict'] = google1
            return 0

    def Keyword_Density(self):
        # All content of webpage
        content1 = re.sub(r'[-\r\n,0123456789|!&()@#$%^*/{}+=:]', '', self.soup.get_text())
        content = self.remove_unicode_characters(content1)
        result1 = content.lower().split()

        # If website have keywords
        meta = self.soup.findAll("meta")
        keyword = ""
        result = ""
        for tag in meta:
            if 'name' in tag.attrs.keys() and tag.attrs['name'].strip().lower() in ['keyword']:
                keyword = keyword + tag.attrs['content']
            elif 'name' in tag.attrs.keys() and tag.attrs['name'].strip().lower() in ['keywords']:
                keyword = keyword + tag.attrs['content']
        if keyword == "":
            result = result1

        else:
            content1 = re.sub(r'[-\r\n,0123456789|.!&()@#$%^*/{}+=]', '', keyword)
            content=self.remove_unicode_characters(content1)
            res = content.lower().split(' ')
            result = []
            for i in res:
                a = i.split(',')
                result += a
            result += result1
        dict_c = dict()
        extra_words =  ['all','not','have', 'from', 'the', 'and','are','...','ours','for','will'
                       'our', 'your','how', 'where', 'why', 'what', 'with','only','may','can','you',
                       'more','any','does','its','new','minute']

        result = [i for i in result if len(i) > 2 and not any(j in i for j in ["..."])]
        for i in result:
            if i in dict_c or i in extra_words:
                pass
            else:
                dict_c[i.lower()] = result1.count(i.lower())
        k = Counter(dict_c)
        high = k.most_common(5)
        density_dict = {}
        if len(high) >= 5:
            if high[0][1] <= 1:
                self.data['density'] = "Website doesn't give access to crawl the keywords!"
                return
        else:
            self.data['density'] = "Website doesn't give access to crawl the keywords!"
            return
        self.keyword_lst.append(high[0][0])
        self.keyword_lst.append(high[1][0])
        for i in high:
            density = (i[1] / len(result1)) * 100
            density=round(density,2)
            density_dict[i[0]]="Count:"+str(i[1]),"Density:"+str(density)+"%"
        self.data['density_dict']=density_dict




        self.conversion = dict(high)
        self.lst = list(self.conversion)
        # print('con',self.conversion)

    def get_missing_alt(self):
        alt=""
        for image in self.soup.find_all('img'):
            # print(self.total_count)
            try:
                if image['alt'] == "":
                    alt+= str(self.alt_count+1)+")"+str(image)+"\n"
                    self.alt_count += 1
            #                     print(image)
            except:
                image in self.soup
                alt += str(self.alt_count + 1) + ")" + str(image) + "\n"
                self.alt_count += 1
        #                 print(image)
        self.data['alt_check']=self.alt_count
        self.data['alt_links']=alt
        # print("Missing Image ALT Attribute:", self.alt_count)
        #         Img_score=(self.alt_count/self.total_count)*100
        # #         Img_score =round(Img_score)
        #         self.Img_score= Img_score
        #         print(self.Img_score)
        return

    def get_links(self):
        external_links=""
        internal_links=""
        pageurl = self.url
        pageurl1 = pageurl.replace("www.", "")
        pageurl2 = pageurl.replace("https", "http")
        pageurl3 = pageurl2.replace("www.", "")
        pageurl4 = pageurl.replace("com/", "com")

        links = self.soup.findAll('a')
        if len(links) ==1:
            for i in links:
                href_link= i.get("href")
                if href_link == None:
                    self.internal_links="Not Allow to Scrap!"
                    self.external_links="Not Allow to Scrap!"
        for i in links:
            href_link = i.get("href")
            try:
                if href_link == "":
                    pass
                elif href_link.startswith(pageurl) or href_link.startswith(pageurl3) or href_link.startswith(
                        pageurl2) or href_link.startswith(pageurl1) or href_link.startswith(
                        "/") or href_link.startswith("#"):
                    # print("i",href_link)
                    self.internal_links += 1
                    internal_links+=f"{self.internal_links}){href_link}\n"

                elif href_link.startswith("http") is False or href_link.startswith(pageurl4):
                    # print("i",href_link)
                    self.internal_links += 1
                    internal_links += f"{self.internal_links}){href_link}\n"

                else:
                    # print("e",href_link)
                    self.external_links += 1
                    external_links += f"{self.external_links}){href_link}\n"

            except:
                pass
        self.data['Internal_links']=self.internal_links
        self.data['External_links']=self.external_links
        self.data['i_url']=internal_links
        self.data['e_url'] = external_links
        # print("Internal Links :", self.internal_links)
        # print("External_links :", self.external_links)
        return

    def get_Status(self):
        statuses = {200: "Website Available", 301: "Permanent Redirect", 302: "Temporary Redirect", 404: "Not Found",
                    500: "Internal Server Error", 503: "Service Unavailable", 403: "Forbidden"}
        try:
            web_response = requests.get(self.url)
            status=web_response.status_code, statuses[web_response.status_code]
            self.data['status']=status
        except:
            status="No Status Found!"
            self.data['status']=status
            # print("No Status")
        return

    def Score_Graph(self,name,tag,score):
        # data
        if name == 'Alt_Image':
            if score<=50:
                shape1='rgba(0,0,0,0)'
                shape2='red'
            else:
                shape1='red'
                shape2='rgba(0,0,0,0)'
        else:
            if score<=50:
                shape1='rgba(0,0,0,0)'
                shape2='red'
            else:
                shape1='green'
                shape2='rgba(0,0,0,0)'
        df = pd.DataFrame({'values' :[100-score,score]})

        # plotly
        fig = px.pie(df, values ='values', hole = 0.7,
                     color_discrete_sequence = [shape1,shape2],title=name+'Score',width=350,height=350)

        fig.data[0].textfont.color = 'white'
        # fig.show()
        fig.write_image(tag)
        return

        # Structured Analysis

    def check_robot_txt(self):
        if self.url.endswith('/'):
            path = self.url
        else:
            path = self.url + '/'
        session = requests.Session()
        req = session.get(path + "robots.txt", headers={"User-Agent": "Mozila/5.0"}).text
        format_robot = "User-agent: *"

        if req.startswith(format_robot) or format_robot in req:
            robot_verdict="Found! Website have robot.txt file."
            self.robot_flag = True
        else:
            robot_verdict = "Not Found! Website don't have robot.txt file."
        self.data['robot']=robot_verdict

    def get_sitemap(self):
        if self.url.endswith('/'):
            path = self.url
        else:
            path = self.url + '/'
        session = requests.Session()
        req = session.get(path + "sitemap.xml", headers={"User-Agent": "Mozila/5.0"}).text
        format_sitemap = "sitemap.xml"
        if format_sitemap in req:
            #         print(req)
            sitemap_verdict="Found! Website have sitemap."
            self.data['sitemap'] = sitemap_verdict
        else:
            req = session.get(path + "sitemaps/sitemap.xml", headers={"User-Agent": "Mozila/5.0"}).text
            if format_sitemap in req:
                sitemap_verdict = "Found! Website have sitemap."
                self.sitemap_flag = True
                self.data['sitemap'] = sitemap_verdict
            else:
                # print("Sitemap not found!")
                sitemap_verdict = "Not Found! Website don't have sitemap."
                self.data['sitemap'] = sitemap_verdict

    def get_broken_links(self):
        Broken_links = ""
        # Create a requests session to reuse the same TCP connection for multiple requests
        session = requests.Session()
        # Make a request to the URL
        response = session.get(self.url, headers={"User-Agent": "Mozila/5.0"})
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a")
        count=1
        for link in links:
            href = link.get("href")
            if href == None:
                pass
            elif href.startswith("http"):
                try:
                    # Make a request to the link using the same session object
                    statusCode = requests.get(href, headers={"User-Agent": "Mozila/5.0"}).status_code
                    if statusCode != 200:
                        self.b_links = self.b_links+1
                        Broken_links+=f"{count})Broken link: {href}\n"
                        count+=1
                except requests.exceptions.RequestException:
                    Broken_links+=f"{count})Error connecting to link: {href}\n"
                    count+=1
        self.data['b_links']=self.b_links
        self.data['b_url']=Broken_links
        return

    def get_schema(self):
        session_obj = requests.Session()
        response = session_obj.get(self.url, headers={"User-Agent": "Mozilla/5.0"}).text
        soup = BeautifulSoup(response, 'html.parser')
        tag = soup.findAll('script')
        content = ""
        for i in tag:
            content += str(i)
        content = content.split(' ')

        for i in content:
            if "schema.org" in i or 'yoast-schema-graph' in i:
                self.schema_flag = True
                schema_verdict="Found! Website have Schema.org."
                self.data['schema']=schema_verdict
                # print("Schema.org found!")
                return
            else:
                pass
        schema_verdict = "Not Found! Website don't have Schema.org."
        self.data['schema'] = schema_verdict
        # print("Not found!")
        return

    def get_Open_GP(self):
        self.ogp_flag = False
        session_obj = requests.Session()
        response = session_obj.get(self.url, headers={"User-Agent": "Mozilla/5.0"}).text
        soup = BeautifulSoup(response, 'html.parser')
        # og:title
        if soup.findAll("meta", property="og:title"):
            if soup.find("meta", property="og:title")["content"] != None:
                self.ogp_flag = True
        else:
            pass
        #         print(None)
        # og:locale
        if soup.findAll("meta", property="og:locale"):
            if soup.find("meta", property="og:locale")["content"] != None:
                self.ogp_flag = True
        else:
            pass

        # og:description
        if soup.findAll("meta", property="og:description"):
            if soup.find("meta", property="og:description")["content"] != None:
                self.ogp_flag = True
        else:
            pass

        # og:site_name
        if soup.findAll("meta", property="og:site_name"):
            if soup.find("meta", property="og:site_name")["content"] != None:
                self.ogp_flag = True
        else:
            pass

        # og:image
        if soup.findAll("meta", property="og:image"):
            if soup.find("meta", property="og:image")["content"] != None:
                self.ogp_flag = True
        else:
            pass
        # og:url
        if soup.findAll("meta", property="og:url"):
            if soup.find("meta", property="og:url")["content"] != None:
                self.ogp_flag = True
        else:
            pass

        if self.ogp_flag == True:
            open_gp="Found! Website support Open Graph Protocol."

            # print("Website support Open Graph Protocol!")
        else:
            open_gp = "Not Found! Website does'nt support Open Graph Protocol."
            # print("Website does'nt support Open Graph Protocol!")

        self.data['open_gp'] =open_gp

    def get_favicon(self):
        icons = favicon.get(self.url)
        try:
            icon = icons[0]
            icon = urllib.request.urlopen(icon[0])

            with open("test.jpg","wb") as f:
                f.write(icon.read())
                Favicon = "Found! Website have favicon icon."
                self.icon_flag = True
        except:
            Favicon = "Not Found! Website does'nt favicon icon."
            self.icon_flag = False
        self.data['Favicon']=Favicon
        return

    def Social(self):
        verdict_fb = ""
        verdict_insta = ""
        verdict_twit = ""
        verdict_link = ""

        facebook = 'facebook.com/'
        insta = 'instagram.com/'
        twitter = 'twitter.com/'
        linkedin = 'linkedin.com/'

        session_obj = requests.Session()
        response = session_obj.get(self.url, headers={"User-Agent": "Mozilla/5.0"}).text
        soup = BeautifulSoup(response, 'html.parser')
        content = soup.findAll('a')
        for i in content:
            href_link = i.get("href")
            if href_link==None:
                verdict_fb = "Not Allow to Scrap!"
                verdict_insta = "Not Allow to Scrap!"
                verdict_twit = "Not Allow to Scrap!"
                verdict_link = "Not Allow to Scrap!"
                break
        for i in content:
            href_link = i.get("href")
            # facebook
            if href_link == "" or href_link == None:
                pass
            elif facebook in href_link:
                verdict_fb = "Facebook found!"
                self.s_count = self.s_count + 25
                self.fb_flag = True
                break
            else:
                verdict_fb = "Facebook not found!"
        for i in content:
            href_link = i.get("href")
            # Insta
            if href_link == "" or href_link == None:
                pass
            elif insta in href_link:
                verdict_insta = "Instagram found!"
                self.s_count = self.s_count + 25
                self.insta_flag = True
                break
            else:
                verdict_insta = "Instagram not found!"
        for i in content:
            href_link = i.get("href")
            # Twitter
            if href_link == "" or href_link == None:
                pass
            elif twitter in href_link:
                verdict_twit = "Twitter found!"
                self.s_count = self.s_count + 25
                self.twitter_flag = True
                break
            else:
                verdict_twit = "Twitter not found!"
        for i in content:
            href_link = i.get("href")
            # Linkedin
            if href_link == "" or href_link == None:
                pass
            elif linkedin in href_link:
                verdict_link = "Linkedin found!"
                self.s_count = self.s_count + 25
                self.linkedin_flag = True
                break
            else:
                verdict_link = "Linkedin not found!"

        # print(verdict_fb)
        # print(verdict_insta)
        # print(verdict_twit)
        # print(verdict_link)
        # print(self.s_count)
        self.data['facebook']=verdict_fb
        self.data['insta']=verdict_insta
        self.data['twitter']=verdict_twit
        self.data['linkedin']=verdict_link
        self.data['social_verdict']="Score: "+str(self.s_count)+"%"

    def get_technology(self):
        dict={}
        try:
            technology = requests.get(self.url)
            self.webserver = technology.headers['Server']
            dict['Server']=self.webserver
            self.data['technology']=dict
            self.tech_flag = True
        except:
            dict['Server'] = self.webserver
            self.data['technology'] = dict
        return


    def Google_Analytics(self):
        a = self.soup.findAll("script", src=True)
        if a ==[]:
            self.data['analytics'] = "Not Found!"
            return
        analytics=""
        for i in a:
            if "UA-" in i["src"] and "google" in i["src"]:
                self.analytics_flag = True
                analytics="Google Analytics found!"
                self.data['analytics'] = analytics
                # print("Google Analytics Found")
                break
            else:
                analytics = "Google Analytics not found!"
                self.data['analytics'] = analytics
                # print("Website Does'nt have google analytics")


    def w3c_validation(self):
        try:
            vld = HTMLValidator(charset='utf-8')
            vld.validate(self.url)
            error = vld.errors
            warnings = vld.warnings
            self.error_len = len(error)
            self.warn_len = len(warnings)
            self.data['w3c']="Errors: "+str(self.error_len),"Warnings: "+str(self.warn_len)
        except:
            self.data['w3c']="None"
        # print("Errors:", self.error_len)
        # print("Warnings:", self.warn_len)

    def get_content(self):
        #Doctype and encoding
        response = requests.get(self.url)
        a=response.headers['Content-Type']
        a=a.split()
        try:
            self.Doctype=a[0]
            self.doc_flag =True
            # print("DocType:",self.Doctype)
        except:
            self.Doctype="Not Found!"
            # print("Doctype:",self.Doctype)
        try:
            self.Encoding=a[1]
            self.encod_flag =True
            # print("Encoding:",self.Encoding)
        except:
            self.Encoding="Not Found!"
            # print("Encoding:",self.Encoding)

        self.data['doctype']=self.Doctype
        self.data['encoding']=self.Encoding



    def get_server(self):
        if "https://" in self.url:
            url=self.url.replace("https://","")
        elif "http://" in self.url:
            url=self.url.replace("http://","")
        else:
            url=self.url
        try:
            ip_address = socket.gethostbyname(url)
            g = geocoder.ip(ip_address)
            server_location = g.country
            hostname = socket.getfqdn(url)
            if len(ip_address) != 0:
                self.ip=ip_address
                self.ip_flag=True
            else:
                self.ip="Not Found!"
            if len(server_location) != 0:
                self.loc_name=server_location
                self.server_loc_flag=True
            else:
                self.loc_name="Not Found!"
        except:
            self.ip = "Not Found!"
            self.loc_name = "Not Found!"
            hostname="Not Found!"
        self.data['s_ip'] = self.ip
        self.data['s_loc'] = self.loc_name
        self.data['hostname'] = hostname

    def SSL(self):
        if 'https://' in self.url:
            url = self.url.replace('https://', '')
        elif 'http://' in self.url:
            url = self.url.replace('http://', '')
        else:
            url = self.url

        try:
            context = ssl.create_default_context()
            sock = socket.create_connection((url, 443))
            ssock = context.wrap_socket(sock, server_hostname=url)
            cert = ssock.getpeercert()

            subject = dict(x[0] for x in cert['subject'])
            issuer = dict(x[0] for x in cert['issuer'])
            if 'commonName' in subject:
                self.ssl = True
                self.data['ssl_name']=subject['commonName']
                self.data['ssl_verdict']="Website have SSL certification!"
                self.name=subject['commonName']
            else:
                self.data['ssl_name']="Not Found!"
                self.data['ssl_verdict'] = "Website does'nt have SSL certification!"

            if 'commonName' in issuer:
                self.data['ssl_organ']=issuer['commonName']
                self.organization=issuer['commonName']
            else:
                self.data['ssl_organ']="Not Found!"

            if 'notAfter' in cert:
                self.data['ssl_expiry']=cert['notAfter']
                self.expiry_date=cert['notAfter']
            else:
                self.data['ssl_expiry']="Not Found!"

        except:
            self.data['ssl_name'] = "Not Found!"
            self.data['ssl_verdict'] = "Website does'nt have SSL certification!"
            self.data['ssl_organ'] = "Not Found!"
            self.data['ssl_expiry'] = "Not Found!"

    def Https_Redirection(self):
        if "www." in self.url:
            url=self.url.replace("www.","")
        try:
            response = requests.get(url, allow_redirects=False)
            if response.status_code == 301 or response.status_code == 302:
                if response.headers.get('Location').startswith('https://'):
                    self.data['http_redir'] = "The website is using HTTPS redirection"
                    self.https = True
                    return
                else:
                    pass
            else:
                pass
        except:
            self.data['http_redir'] = "The website is not using HTTPS redirection"
            return
        self.data['http_redir'] = "The website is not using HTTPS redirection"

    def DMCA(self):
        response = requests.get(self.url)
        content = response.text
        dmca_terms = ['DMCA', 'Digital Millennium Copyright Act']
        for term in dmca_terms:
            match = re.search(term, content, re.IGNORECASE)
            if match:
                self.data['dmca']="The website is protected by DMCA."
                self.dmca=True
                # print(f"The website is protected by DMCA.")
        self.data['dmca'] = "The website is not protected by DMCA."
        # print(f"The website is not protected by DMCA.")

    def measure_website_speed(self):
        start_time = time.time()
        session_obj = requests.Session()
        response = session_obj.get(self.url, headers={"User-Agent": "Mozilla/5.0"}).text
        end_time = time.time()
        self.speed = end_time - start_time
        self.speed=round(self.speed,2)
        self.data['website_speed']=self.speed
        if self.speed < 2.5:
            self.data['speed_verdit']="The website speed is good!"
        else:
            self.data['speed_verdit'] = "The website speed is not good!"


    def CSS_minification(self):
        try:
            session_obj = requests.Session()
            response = session_obj.get(self.url, headers={"User-Agent": "Mozilla/5.0"}).text
            css_code = response
            compressed_css = csscompressor.compress(css_code)
            if len(compressed_css) < len(css_code):
                self.data['css_minified'] = "CSS code for the website is not minified."
            else:
                self.data['css_minified'] = "CSS code for the website is minified."
                self.css = True
        except:
            self.data['css_minified'] = "CSS code for the website is given Error."

    def JSS_minification(self):
        try:
            response = requests.get(self.url)
            js_code = response.text
            compressed_js = jsmin(js_code)
            if len(compressed_js) < len(js_code):
                self.data['jss_minified'] = "JavaScript code for the website is not minified."
            else:
                self.data['jss_minified'] = "JavaScript code for the website is minified."
                self.jss = True

        except:
            self.data['jss_minified'] = "JavaScript code for the website is given Error."


    def Optmized_Plugins(self):
        from bs4 import BeautifulSoup

        response = requests.get(self.url)
        html_content = response.content

        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Search for optimized plugins
        optimized_plugins = soup.find_all('link', {'rel': 'preload'})

        # Print the optimized plugins
        if optimized_plugins:
            self.data['opt_plugins']="The website is using the  optimized plugins"
            self.plugins=True
        else:
            self.data['opt_plugins'] = "The website is not using the optimized plugins"

    def Mobile_speed(self):
        try:
            url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
            params = {
                'url': self.url,
                'strategy': 'mobile',
                'key': 'AIzaSyCpW9QRlTmh5nzQsN8tu3vJA1x1XQDvZW4'}

            response = requests.get(url, params=params)
            data = json.loads(response.text)

            score = data['lighthouseResult']['categories']['performance']['score']
            self.data["mobile_speed"]=score
            self.mob_score = score
        except:
            score = 0
            self.data["mobile_speed"] = score
            self.mob_score = score
        if score < 3 :
            self.data["mobile_score_verdict"]="The mobile speed score is good"
        else:
            self.data["mobile_score_verdict"] = "The mobile speed score is not good"
        self.mobile_speed=score


    def AMP(self):
        response = requests.get(self.url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Check if the website is using AMP
        if soup.find('html', {'amp': ''}):
            self.data["amp"]="The website is using AMP"
            self.amp=True
        else:
            self.data["amp"] = "The website is not using AMP"


    def Mobile_rendering(self):
        # set the user agent for mobile device
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'}

        response = requests.get(self.url, headers=headers)

        # check the response status code to determine if the website is working or not
        if response.status_code == 200:
            self.data["mobile_render"]="Mobile rendering is working."
            self.render=True
        else:
            self.data["mobile_render"] = "Mobile rendering is not working."

    def Mobile_preview(self):
        #check the mobile usability

        url = 'https://searchconsole.googleapis.com/v1/urlTestingTools/mobileFriendlyTest:run'
        params = {
            'url': self.url,
            'key': "AIzaSyBHQ0tzn7Ox6e4OOWYPfwuV66TcTyM316Q"
        }
        x = requests.post(url, params=params)
        data = json.loads(x.text)
        try:
            if data["mobileFriendliness"] == "NOT_MOBILE_FRIENDLY" or self.mobile_speed > 3:
                self.data["mobile_prev"]="The mobile preview is not optimized."
            else:
                self.data["mobile_prev"] = "The mobile preview is optimized."
                self.mobpreview=True
        except:
            self.data["mobile_prev"]="The page is unreachable!"

        return

    def Report(self,dict):
        #for mobile preview screenshot
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=375,812")
        chrome_options.add_argument("--log-level=3")
        mobile_emulation = {
            "deviceMetrics": {"width": 375, "height": 812, "pixelRatio": 3.0},
            "userAgent": "Mozilla/5.0 (Linux; Android 9; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Mobile Safari/537.36",
        }
        chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)

        driver = webdriver.Chrome(options=chrome_options)
        driver.get(dict['url'])
        driver.implicitly_wait(2)
        driver.save_screenshot("mobile_view.png")
        driver.quit()
        image = Image.open("mobile_view.png")
        resized_image = image.resize((375, 812), Image.ANTIALIAS)
        resized_image.save("mobile_view.png")

        import webbrowser
        import random
        from datetime import date
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Times', 'B', 25)

        # Header
        pdf.set_font('Courier', 'BU', 45)
        pdf.set_text_color(20, 100, 238)
        pdf.text(17, 115, "SMART WEB ANALYZER")
        pdf.set_font('Times', 'BU', 20)
        pdf.set_text_color(0, 0, 0)
        pdf.text(42, 145, "Summarized Recommendation Report")
        pdf.set_font('Times', 'B', 20)
        pdf.text(100, 160, " + ")
        pdf.set_font('Times', 'BU', 20)
        pdf.text(51, 175, "Detail Recommendation Report")
        pdf.set_font('Times', '', 15)
        pdf.text(167, 10, "Date:")
        pdf.text(180, 10, str(date.today()))
        pdf.text(5, 10, "Smart Web Analyzer")
        # Content
        pdf.set_font('Times', 'BU', 20)
        pdf.text(58, 210, "URL:")
        pdf.set_text_color(28, 134, 238)
        pdf.set_font('Times', 'U', 20)
        pdf.text(78, 210, dict['url'])
        pdf.image('Supported/icon.png', 70, 15)

        pdf.add_page()

        # Content Analysis Summmary
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', 'B', 26)
        pdf.text(30, 30, " Summarized Recommendation Report")
        pdf.set_font('Times', 'BU', 18)
        pdf.text(10, 54, "Content Analysis Recommendations:")
        pdf.ln(60)
        # Title Summary
        pdf.set_font('Times', '', 16)
        if dict['title_score'] < 30:
            # title_txt = '1) Must increase the length of title it should be between 30 to 60 words.'
            title_txt = '1) Length of title should be between 30 to 60 words.'
            pdf.text(20, 70, title_txt)
            pdf.ln(30)
        elif 30 <= dict['title_score'] < 60:
            # title_txt = '1) Perfect! No need to change title length.'
            title_txt = '1) Length of title should be between 30 to 60 words.'
            pdf.text(20, 70, title_txt)
            pdf.ln(30)
        else:
            # title_txt = '1) Must decrease the length of title it should be between 30 to 60 words.'
            title_txt = '1) Length of title should be between 30 to 60 words.'
            pdf.text(20, 70, title_txt)
            pdf.ln(30)

        # Description Summary
        pdf.set_font('Times', '', 16)
        pdf.ln(60)
        if dict['desc_score'] < 30:
            # title_txt = '2) Must increase the length of description it should be between 50 to 160 words.'
            title_txt = '2) Length of description should be between 50 to 160 words.'
            pdf.text(20, 80, title_txt)
            pdf.ln(30)
        elif dict['desc_score'] == 0:
            title_txt = '2) Description not found in meta tag!'
            pdf.text(20, 80, title_txt)
            pdf.ln(30)
        elif 50 <= dict['desc_score'] < 160:
            # title_txt = '2) Perfect! No need to change description length.'
            title_txt = '2) Length of description should be between 50 to 160 words.'
            pdf.text(20, 80, title_txt)
            pdf.ln(30)
        else:
            # title_txt = '2) Must decrease the length of description it should be between 50 to 160 words.'
            title_txt = '2) Length of description should be between 50 to 160 words.'
            pdf.text(20, 80, title_txt)
            pdf.ln(30)

        # Heading Summary
        pdf.set_text_color(0, 0, 0)
        pdf.ln(60)
        if dict['H'] == None:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 90, "3) Heading tags not found!")
            pdf.set_font('Times', '', 16)
            pdf.text(20, 100, "     a) Add H1 tag to ensure clarity for the reader!")
            pdf.text(20, 110, "     b) Add H2 tag to makes it easier for users to find what they are looking for!")
            pdf.text(20, 120, "     c) H1 and H2 headings help improve the readability of a page.")

        elif dict['H'] == "H1":
            if dict['heading_score'] == 0:
                pdf.set_font('Times', 'B', 16)
                pdf.text(20, 90, "3) H1 Heading tag not found!")
                pdf.set_font('Times', '', 16)
                pdf.text(20, 100, "     The H1 tag is important for both search engines and users to understand ")
                pdf.text(20, 110, "     the main topic or purpose of the page.Therefore, it is recommended to add ")
                pdf.text(20, 120, "     an H1 tag that accurately reflects the content of the page.")
            else:
                pdf.set_font('Times', 'B', 16)
                pdf.text(20, 90, "3) H1 Heading tag found!")
                pdf.set_font('Times', '', 16)
                pdf.text(20, 100, "     a) Make sure the h1 tag accurately reflects the content of the page.")
                pdf.text(20, 110, "     b) Optimize the H1 tag for search engines.")
                pdf.text(20, 120, "     c) Test page with different screen sizes to ensure that the h1 tag is visible.")

        elif dict['H'] == "H2":
            if dict['heading_score'] == 0:
                pdf.set_font('Times', 'B', 16)
                pdf.text(20, 90, "3) H1 tag and H2 not found!")
                pdf.set_font('Times', '', 16)
                pdf.text(20, 100, "     a) Add H1 tag to ensure clarity for the reader!")
                pdf.text(20, 110, "     b) Add H2 tag to makes it easier for users to find what they are looking for!")
                pdf.text(20, 120, "     c) H1 and H2 headings help structure and organize the content on a page.")
            else:
                pdf.set_font('Times', 'B', 16)
                pdf.text(20, 90, "3) H1 Heading tag not found!")
                pdf.text(20, 100,"    H2 Heading tag  found!")
                pdf.set_font('Times', '', 16)
                pdf.text(20, 110, "     a) Use your main keyword in the H2 heading.")
                pdf.text(20, 120, "     b) H2 heading should accurately define the content of section it introduce.")

        # Google preview summary
        pdf.text(20, 130, '4) A good Google search preview must have')
        pdf.set_font('Times', 'B', 16)
        pdf.text(20, 140, '    Max title length:')
        pdf.set_font('Times', '', 16)
        pdf.text(20, 150, '    Recommended length is from 30 to 52 characters, up to 580 pixels.')
        pdf.set_font('Times', 'B', 16)
        pdf.text(   20, 160, '    Max meta description length:')
        pdf.set_font('Times', '', 16)
        pdf.text(20, 170, '    Recommended length is from 120 to 158 characters, up to 920 pixels.')

        # Keyword Density Summary
        if len(dict['lst']) == 0 or len(dict['lst']) < 5:
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 16)
            pdf.text(20, 180, "5) Website don't allow to crawl Keywords")
            pdf.set_font('Times', '', 16)
            pdf.text(20, 190, "     For this I recommend you! Add main keywords in target keywords and")
            pdf.text(20, 200, "     add keywords in (title/desc/head) having higher count in your site!")
        else:
            title_txt = '5) I analyze the top 5 words that occur most in your website so they      must be in your website (Title, Description, Heading).'
            pdf.text(20, 180, title_txt[0:70])
            pdf.text(20, 190, title_txt[70:135])
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 200, '     Note: For more details check Detail Recommendation Report')

        # Imag Alt Check Summary
        pdf.set_font('Times', '', 16)
        if dict['alt_count'] == 0:
            pdf.text(20, 210, '6) Perfect! All Images in your website contain Alt attribute.')
            pdf.text(20, 220, '     a) Make sure that the alt text accurately describes the image.')
            pdf.text(20, 230, '     b) Use descriptive file names for your images.')
            pdf.text(20, 240, '     c) Use Relevant keyword in alt text can improve your SEO.')
        else:
            pdf.text(20, 210, '6) '+str(dict['alt_count'])+ ' Images must contain Alt attribute')
            pdf.text(20, 220, '     a) It provides alternative information for an image.')
            pdf.text(20, 230, '     b) It provide better User Experience')
            pdf.text(20, 240, '     c) Search engines use alt text to understand the content of images.')

        # links Summary
        pdf.set_font('Times', '', 16)
        if dict['external_links'] == 0 or dict['external_links'] <= 8:
            pdf.text(20, 250, '7) Add 1 or 2 external links for every 500 words content, It helps:')
            pdf.text(20, 260, '     a) To improves your credibility and SEO.')
            pdf.text(20, 270, '     b) To offers readers more value and create connections in a easy way.')
        else:
            pdf.text(20, 250, '6) Perfect! Website have a good number of external links its best practices are:')
            pdf.text(20, 260, '     a) Make the links relevant to offers readers more value.')
            pdf.text(20, 270, '     b) Link to reputable sources. Do not link to competing websites')

        pdf.text(180, 288, 'Page | 01')
        pdf.add_page()

        # Structure Analysis Summary
        pdf.set_font('Times', 'BU', 18)
        pdf.text(10, 20, "Structure Analysis Recommendations:")


        # Robot.txt
        if dict['robot_flag'] == True:
            pdf.set_font('Times', '', 16)
            pdf.text(20, 35, '1)  Perfect! your website have a robot.txt file.')
            pdf.text(20, 45, '      a) Tells search engine crawlers which URLs it can access on your site.')
            pdf.text(20, 55, '      b) Mainly used to avoid overloading your site with requests')

        else:
            pdf.set_font('Times', '', 16)
            pdf.text(20, 35, '1)  Your website have no Robot.txt file so:')
            pdf.text(20, 45, '      a) Bot can crawl your website and index pages as it normally would.')
            pdf.text(20, 55, '      b) Only needed if you want to have more control on what is being crawled.')

        # sitemap summary
        if dict['sitemap_flag'] == True:
            pdf.text(20, 65, '2)  Sitemaps should be no larger than 10MB and can contain a maximum of 50,000 URLs.')
            pdf.text(20, 75, '      a) If Bigger than 10MB, you must create multiple sitemap files.')

        else:
            pdf.text(20, 65, '2)  I recommend you to have a Sitemap file in your site! ')
            pdf.text(20, 75, '      a) It will enhance the ranking of your website in search engine results.')

        # broken link summary
        if dict['b_links'] == 0:
            pdf.text(20, 85, '3)  Perfect! Your site have no Broken Links.')
            pdf.text(20, 95, '      a) Our recommendation is to analyze your website every-month to better check')
            pdf.text(20, 105, '         for broken links as they have a huge impact on ranking')
        else:
            pdf.text(20, 85, '3)  Opps! Broken links found in your website.')
            pdf.text(20, 95, '      a) Too many Broken Links sends signals to Google that your site is outdated,')
            pdf.text(20, 105, '      b) Could harmful to rankings so maintain this problem ASAP!')

        # Favicon Summary
        if dict['icon_flag'] == True:
            pdf.text(20, 115, '4)  Icon found! Keep it simple and recognizable.')
        else:
            pdf.text(20, 115, '4)  Sorry! We dont have access to analyze your icon.')

        # opengraph Summary
        if dict['ogp_flag'] == True:
            pdf.text(20, 125,'5)  Perfect! Your site have Open Graph Protocol')
            pdf.text(20, 135,'      a) I recommend to optimize your shared content to provides a better UX.')
        else:
            pdf.text(20, 125, '5)  Open graph tags not found! It may not directly affect your SEO but:')
            pdf.text(20, 135, '      a) They can increase your traffic and social media discoverability.')

        # Technology Analysis Summary
        pdf.set_font('Times', 'BU', 18)
        pdf.text(10, 155, "Technology Analysis Recommendations:")


        # Webserver Summary

        if dict['tech_flag'] == True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 170, "1) I found your website Webserver! I recommend you:")
            pdf.set_font('Times', '', 16)
            pdf.text(20, 180, '     a) Configure the server properly.')
            pdf.text(20, 190, '     b) Optimize server performance.')
            pdf.text(20, 200, '     c) Monitor server activity / Backup regularly')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 170, "1) I can't access your website webserver.")
            pdf.set_font('Times', '', 16)
            pdf.text(20, 180, '      I recommend you to select the webserver on base of your Website traffic,')
            pdf.text(20, 190, '      Content management, Programming Language and Technologies used. Some ')
            pdf.text(20, 200, '      commonly used Webserver are (Apache, Nginx, Microsoft IIS, Lighttpd)')

        #Google Analytics Summary
        if dict['analytics_flag'] == True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 210, "2) Google Analytics installed, I would recommend the following:")
            pdf.set_font('Times', '', 16)
            pdf.text(20, 220, '     a) Analyze traffic sources and Monitor user behavior.')
            pdf.text(20, 230, '     b) Set up custom reports.')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 210, "2) First Install Google Analytics as it is important for several reasons:")
            pdf.set_font('Times', '', 16)
            pdf.text(20, 220,'       a) Track and optimize website performance.')
            pdf.text(20, 230,'       b) Measure marketing effectiveness.')

        #Doc type Summary
        if dict['doc_flag'] == True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 240, "3) Doctype tag found in your website!")
            pdf.set_font('Times', '', 16)
            pdf.text(20, 250, '     I recommend you to use the HTML5 doctype for your website.')
            pdf.text(20, 260,'      a) HTML5 is the latest version of HTML and it has several advantages.')
            pdf.text(20, 270,'      b) HTML5 includes a number of new features and elements')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 240, "1) I recommend you to attach a doctype html tag in your website!")
            pdf.set_font('Times', '', 16)
            pdf.text(20, 250, '      Without a doctype, web browsers may have to guess which version of HTML')
            pdf.text(20, 260, '      or XHTML the document is written in, which can lead to inconsistencies in')
            pdf.text(20, 270, '      rendering, and may cause certain elements or styles to display incorrectly.')

        pdf.text(180, 288, 'Page | 02')
        pdf.add_page()

        # Security Analysis Summary
        pdf.set_font('Times', 'BU', 18)
        pdf.text(10, 20, "Security Analysis Recommendations:")

        # DMCA Summary
        if dict['dmca'] == True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 35, '1) Website is protected by DMCA, I recommend you to:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 45, '      a) Display the DMCA badge prominently on your website.')
            pdf.text(20, 55, '      b) Regularly monitor your website for infringing content and promptly')
            pdf.text(20, 65, '          remove it when found (OR) Use Robust content management system ')
            pdf.text(20, 75, '          to quickly remove infringing content from your website.')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 35, '1) I recommend you to protect your Website by DMCA!')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 45, '      Without DMCA protection, website operators should be responsible for ')
            pdf.text(20, 55, '      violate activities of their users, even if they had no knowledge of such')
            pdf.text(20, 65, '      activities. This could lead to significant legal expenses, damages, and')
            pdf.text(20, 75, '      reputational harm for the website operator.')

        # HTTPS Redirection Summary
        if dict['https'] == True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 85, '2) Website is HTTP Redirected! I Recommend you to:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 95,  '      a) Obtain / Install an SSL/TLS certificate.')
            pdf.text(20, 105, '      b) Configure your web server to use HTTPS.')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 85, '2) I would recommend to consider implementing HTTP redirection!')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 95,  '       HTTP redirection is important as it ensures that users are automatically ')
            pdf.text(20, 105, '       directed to the correct version of a website, whether it is the HTTP version. ')

        pdf.set_font('Times', 'B', 16)
        pdf.text(20, 115, '3) Update your SSL Certificate: ')
        pdf.set_font('Times', '', 16)
        pdf.set_text_color(255, 0, 0)
        pdf.text(100, 115,str(dict['expiry_date']))
        # Social Analysis Summary
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', 'BU', 18)
        pdf.text(10, 130, "Social Analysis Recommendations:")

        # Facebook Summary
        if dict['fb_flag'] == True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 143, '1) Website have a facebook link! I Recommend you to:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 153, '      a) Make sure the link is prominent and works properly.')
            pdf.text(20, 163, '      c) Post regular updates on your Fb page to keep your followers engaged.')
            pdf.text(20, 173, '      d) Use Facebook advertising to promote your website.')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 143, '1) Website not have a facebook link! I recommend you to add one because:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 153, '      a) It can provide social proof that your website is legitimate and active.')
            pdf.text(20, 163, '      c) If you are running Facebook ads, having a Facebook link on your site can')
            pdf.text(20, 173, '          be important for tracking and measuring the success of your campaigns.')

        # Instagram Summary
        if dict['insta_flag'] == True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 183, '2) Website have a Instagram link! I Recommend you to:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 193, '      a) Optimize the link placement.')
            pdf.text(20, 203, '      b) Use a call-to-action (CTA).')
            pdf.text(20, 213, '      c) Keep your Instagram content fresh and engaging.')
            pdf.text(20, 223, '      d) Consider using Instagram advertising.')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 183, '2) Website not have a Instagram link! I recommend you to add one only if:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 193, '      Your target audience is active on Instagram and you want to increase your')
            pdf.text(20, 203, '      social media presence, then adding an Instagram link to your website could')
            pdf.text(20, 213, '      be beneficial. This allows visitors to easily find and follow your Instagram')
            pdf.text(20, 223, '      account, which can help increase engagement and brand awareness.')


        # Twitter Summary
        if dict['twitter_flag'] == True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 233, '3) Website have a Twitter link! I Recommend you to:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 243, '      a) Ensure that the Twitter link is prominently displayed on the website.')
            pdf.text(20, 253, '      b) Cross-promote your website on Twitter and use twitter cards.')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 233, '3) Twitter link not found adding it is not necessary, but it can be beneficial:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 243, '      a) It can help increase your social media presence and followers.')
            pdf.text(20, 253, '      b) Add only if your website content is relevant to your Twitter followers.')


        if dict['linkedin_flag'] == True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 263, '4) LinkedIn link Found! I Recommend you to:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 273, '      a) Check if the link is still valid and use descriptive anchor text.')
        else:
            pdf.set_font('Times', '', 16)
            pdf.text(20, 263, '4) LinkedIn link not found adding it to your site is not necessary, but if your site ')
            pdf.text(20, 273, '     is related to Second Life or virtual worlds in general, it could be useful.')

        pdf.text(180, 288, 'Page | 03')
        pdf.add_page()

        #Performance Analysis Recommendations
        pdf.set_font('Times', 'BU', 18)
        pdf.text(10, 20, "Performance Analysis Recommendations:")

        #website speed summary
        if dict['speed'] >= 2.5:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 35, '1) Some improvement can be made to improve website performance & speed!')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 45, '      a) Optimize images.')
            pdf.text(20, 55, '      b) Minimize HTTP requests.')
            pdf.text(20, 65, '      c) Use a content delivery network (CDN).')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 35, '1) Website is performing well! I recommend you to:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 45, '      a) Regularly monitor and optimize website performance.')
            pdf.text(20, 55, '      b) Minimize Plugins.')
            pdf.text(20, 65, '      c) Use a faster web host if you want your site to perform more well.')

        #CSS minification summary
        if dict['css']==True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 75, '2) CSS Files Minified! For more better performance, I recommend you:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 85, '      Combine multiple CSS files into a single file, which can reduce the')
            pdf.text(20, 95, '      number of HTTP requests needed to load the website.')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 75, '2) I recommend you to minify the CSS files, you can use various tools like:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 85, '      a) Online CSS minification tools (CSS Minifier or Online CSS Compressor).')
            pdf.text(20, 95, '      b) Manually minify CSS code using text editor (Sublime Text or Notepad++).')

        # JSS minification summary
        if dict['jss']==True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 105, '3) JS Files Minified! For more better performance I recommend you:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 115, '      a) Enable gzip compression.')
            pdf.text(20, 125, '      b) Combine multiple JavaScript files into single file.')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 105, '3)  Your website is not JS minified, I would recommend the following steps:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 115, '      a) Use tools such as (UglifyJS or Closure Compiler) to minify your JS code.')
            pdf.text(20, 125, '      b) Remove unnecessary characters, white spaces and comments, from the code.')


        #Mobile Usability Analysis Recommendations
        pdf.set_font('Times', 'BU', 18)
        pdf.text(10, 140, "Mobile Usability Analysis Recommendations:")

        #mobile speed summary
        if dict['mob_score'] >= 3:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 155, '1) Some improvement can be made to improve mobile speed score!')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 165, '      a) Reduce the number of images on a page.')
            pdf.text(20, 175, '      b) Minimize render-blocking resources.')
            pdf.text(20, 185, '      c) Reduce the number of plugins or third-party scripts used on the website.')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 155, '1) Mobile Speed score of your site is good! I recommend you to:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 165, '      a) Optimize your database queries.')
            pdf.text(20, 175, '      b) Reduce server response time.')
            pdf.text(20, 185, '      c) Regularly monitor website performance.')

        #AMP summary
        if dict['amp'] == True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 195, '1) Good! Your website is using AMP! I recommend you:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 205, '      a) Ensure that AMP has been implemented correctly on the website.')
            pdf.text(20, 215, '      b) Use of preconnect & prefetch further improve loading speed of AMP pages.')
            pdf.text(20, 225, '      c) Implement server-side rendering.')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 195, '2) Several things can be done to improve mobile-friendliness & performance:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 205, '      a) Minimize CSS and JavaScript files.')
            pdf.text(20, 215, '      b) Optimize images for the web by reducing their file size.')
            pdf.text(20, 225, '      c) Use a content delivery network (CDN)')

        #Mobile Rendering summary
        if dict['render'] == True:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 235, '3) Great! Mobile Rendering is working for website, I recommend you:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 245, '      a) Avoid using pop-ups.')
            pdf.text(20, 255, '      b) Improve readability.')
            pdf.text(20, 265, '      c) Test your website on multiple devices.')
        else:
            pdf.set_font('Times', 'B', 16)
            pdf.text(20, 235, '3) Mobile Rendering not working! some recommendations to improve it are:')
            pdf.set_font('Times', '', 16)
            pdf.text(20, 245, '      a) Prioritize content.')
            pdf.text(20, 255, '      b) Simplify navigation.')
            pdf.text(20, 265, '      c) Use responsive web design.')

        pdf.text(180, 288, 'Page | 04')
        pdf.add_page()

        # Detail Report

        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', 'B', 26)
        pdf.text(36, 15, " Detail Recommendation Report")
        pdf.set_font('Times', '', 18)
        pdf.text(0, 25, "--------------------------------------------------------------------------------------------------------")
        pdf.set_text_color(34, 139, 34)
        pdf.set_font('Times', '', 16)
        pdf.text(10, 30, "Green For Success: Great! Your website is performing good in specific analysis.")
        pdf.set_text_color(255, 0, 0)
        pdf.set_font('Times', '', 16)
        pdf.text(10, 40, "Red For Warning  : Must work in specific area of your website as it effect your SEO.")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', '', 18)
        pdf.text(0, 45, "--------------------------------------------------------------------------------------------------------")



        # Title Detail Recommendation
        # title=self.soup.find('title').get_text()
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 59, "TITLE:")
        pdf.set_font('Times', 'B', 18)
        #         print(self.title)
        pdf.text(37, 59, dict['title'][0:50] + '...')
        pdf.set_font('Times', '', 18)
        pdf.ln(60)
        if dict['title_score'] == 0:
            title_txt = 'The optimum page title length should be between 30 and 60 characters.'
            pdf.multi_cell(65, 10, title_txt)
            pdf.ln(30)
            self.Score_Graph('Title', 'title.jpg', dict['title_score'])
            pdf.image('title.jpg', 80, 62)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', 'B', 35)
            pdf.text(135, 114, '0%')
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(125, 134, 'Not Found!')
        elif dict['title_score'] < 30:
            title_txt = 'The optimum page title length should be between 30 and 60 characters.'
            pdf.multi_cell(65, 10, title_txt)
            pdf.ln(30)
            self.Score_Graph('Title', 'title.jpg', dict['title_score'])
            pdf.image('title.jpg', 80, 62)
        else:
            title_txt = 'You must always use modifiers like "best", "guide", "fast" and "checklist" along with the targeted keyword in the title of your page. It can help you rank for long tail versions of your target keyword.'
            pdf.multi_cell(68, 8, title_txt)
            self.Score_Graph('Title', 'title.jpg', dict['title_score'])
            pdf.image('title.jpg', 80, 62)


        # Description Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 156, "DESC:")
        pdf.set_font('Times', 'B', 18)
        #         print(self.desc)
        pdf.text(37, 156, dict['desc'])
        pdf.ln(30)
        pdf.set_font('Times', '', 18)
        if dict['desc_score'] == 0:
            title_txt = 'The meta description can impact a pages click-through rate (CTR) in Google SERPs, which can positively impact a pages ability to rank.'
            pdf.multi_cell(70, 10, title_txt)
            self.Score_Graph('Description', 'desc.jpg', self.desc_score)
            pdf.image('desc.jpg', 85, 158)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', 'B', 35)
            pdf.text(140, 210, '0%')
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(130, 230, 'Not Found!')
        elif dict['desc_score'] < 30:
            title_txt = 'The optimum meta description length should be between 50 and 160 characters.'
            pdf.multi_cell(75, 8, title_txt)
            self.Score_Graph('Description', 'desc.jpg', dict['desc_score'])
            pdf.image('desc.jpg', 85, 158)
        else:
            title_txt = 'The meta description can impact a pages click-through rate (CTR) in Google SERPs, which can positively impact a pages ability to rank.'
            pdf.multi_cell(70, 10, title_txt)
            self.Score_Graph('Description', 'desc.jpg', dict['desc_score'])
            pdf.image('desc.jpg', 85, 158)

        pdf.set_text_color(0, 0, 0)
        pdf.text(180, 288, 'Page | 05')
        pdf.add_page()

        # Heading Detail Recommendation
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', 'UB', 20)
        pdf.text(10, 15, "HEADING:")
        pdf.set_font('Times', 'B', 18)
        pdf.text(50, 15, dict['heading'])

        if dict['H'] == None:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 17)
            pdf.text(50, 30, "Warning!")
            pdf.text(78, 30, "H1 and H2 Heading tag is missing!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)

        elif dict['H'] == "H1":
            if dict['heading_score'] == 0:
                pdf.set_text_color(255, 0, 0)
                pdf.set_font('Times', 'B', 18)
                pdf.text(50, 30, "Warning!")
                pdf.text(78, 30, "H1 Tag is Empty!")
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Times', '', 18)
            else:
                pdf.set_text_color(34, 139, 34)
                pdf.set_font('Times', 'B', 18)
                pdf.text(50, 30, "Success!")
                pdf.text(78, 30, dict['H'] + ' Found')
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Times', '', 18)

        elif dict['H'] == "H2":
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(50, 30, "Warning!")
            pdf.text(78, 30, "H1 Heading is missing!")
            if dict['heading_score'] == 0:
                pdf.set_text_color(255, 0, 0)
                pdf.set_font('Times', 'B', 18)
                pdf.text(50, 40, "Warning!")
                pdf.text(78, 40, "H2 Tag is Empty!")
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Times', '', 18)
            else:
                pdf.set_text_color(34, 139, 34)
                pdf.set_font('Times', 'B', 18)
                pdf.text(50, 40, "Success!")
                pdf.text(78, 40, dict['H'] + ' Found')
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Times', '', 18)

        pdf.ln(32)
        if dict['H'] == None:
            pdf.text(10, 45, 'H1 tag should be used once or twice and H2 tag should be used twice and')
            pdf.text(10, 55, 'thrice per page as it provide semantic structure to a webpage.')
            pdf.text(10, 70, 'Add H1 and H2 as it helps')
            pdf.text(10, 80, 'search engines understand')
            pdf.text(10, 90, 'the content of the webpage')
            pdf.text(10, 100, 'and improve accessibility')
            pdf.text(10, 110, 'of the webpage and are good')
            pdf.text(10, 120, 'indicator of what the most')
            pdf.text(10, 130, 'important text on a page is')
            self.Score_Graph('Heading', 'head.jpg', self.heading_score)
            pdf.image('head.jpg', 90, 60)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', 'B', 35)
            pdf.text(140, 100, '0%')
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(130, 120, 'Not Found!')
        elif dict['H'] == "H1":
            if dict['heading_score'] == 0:
                title_txt = 'H1 tag should be used once or twice per page for better results and the H2 tag should be used twice or thrice.'
                pdf.multi_cell(70, 10, title_txt)
            elif dict['heading_score'] < 30:
                title_txt = 'The optimum meta heading length should be between 20 and 60 characters.'
                pdf.multi_cell(70, 8, title_txt)
            else:
                title_txt = 'The h1 tag should contain your targeted keywords, ones that closely relate to the page title, and are relevant to your content. The h2 tag is a subheading and should contain similar keywords to your h1 tag.'
                pdf.multi_cell(75, 10, title_txt)

            self.Score_Graph('Heading', 'head.jpg', dict['heading_score'])
            pdf.image('head.jpg', 90, 35)

        else:
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.ln(5)
            title_txt = 'H1 tag should be used once or twice per page for better results and the H2 tag should be used twice or thrice.'
            pdf.multi_cell(180, 8, title_txt)
            pdf.ln(10)
            if dict['heading_score'] < 30:
                title_txt = 'The optimum meta heading length should be between 20 and 60 characters.'
                pdf.multi_cell(70, 8, title_txt)
            else:
                title_txt = 'The h2 tag is a subheading and should contain similar keywords to your h1 tag.Relevant subheads should use an H2 tag. Use headers as they make sense, they may reinforce other ranking factors.'
                pdf.multi_cell(80, 10, title_txt)

            self.Score_Graph('Heading', 'head.jpg', dict['heading_score'])
            pdf.image('head.jpg', 90, 62)

        # Google Preview Detail Recommendation
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 162, "GOOGLE PREVIEW:")
        pdf.image('Supported/preview.jpeg', 1, 170)


        pdf.set_font('Times', '', 14)
        pdf.text(55, 232, dict['url'])
        title=dict['title']
        show_title = title.split(" ")
        if len(show_title) > 2:
            show_title = show_title[0] + ' ' + show_title[1]+ ' ' + show_title[2]
        elif len(show_title) > 1:
            show_title = show_title[0] + ' ' + show_title[1]
        else:
            show_title = show_title[0]
                # show_title=show_title+' '+title.split(' ', 1)[1]
        pdf.set_font('Times', '', 14)
        pdf.text(60, 187, show_title)
        pdf.set_text_color(26, 13, 171)
        pdf.set_font('Times', 'U', 16)
        pdf.text(55, 242, title)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', '', 14)
        if dict['comp_desc']==None:
            pass
        else:
            pdf.text(55, 250, dict['comp_desc'][0:67])
            pdf.text(55, 257, dict['comp_desc'][67:135])
            pdf.text(55, 264, dict['comp_desc'][135:200]+'...')

        pdf.text(180, 288, 'Page | 06')
        pdf.add_page()

        # Keyword Density Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 15, "KEYWORD DENSITY:")

        pdf.ln(15)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', '', 18)
        key_txt = "Keyword density is the percentage calculated based on the number of times a keyword occurs inside the content of webpage divided by the total word count. Keyword density / keyword frequency is still a pretty strong indicator to determine the main focus keywords and keyword phrases for a specific webpage."
        pdf.multi_cell(65, 10, key_txt)
        pdf.ln(10)

        if len(dict['lst']) == 0 or len(dict['lst']) < 5:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', '', 22)
            pdf.text(110, 100, "Website don't allow to")
            pdf.text(110, 110, "  crawl Keywords")
        else:
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(0, 180, "--------------------------------------------------------------------------------------------------------")
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', '', 15)
            pdf.text(5, 185, "Word Found in (Title, Desc & Head) : Yes |")
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', '', 15)
            pdf.text(105, 185, "| Word Not Found in (Title, Desc & Head) : No")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(0, 190, "--------------------------------------------------------------------------------------------------------")
            pdf.set_font('Times', 'B', 18)
            pdf.text(73, 198, "Title")
            pdf.text(110, 198, "Description")
            pdf.text(170, 198, "Heading")
            pdf.set_font('Times', 'B', 18)
            pdf.text(10, 198, "Words")
            pdf.set_font('Times', '', 18)
            pdf.text(10, 210, str(dict['lst'][0]))
            pdf.text(10, 225, str(dict['lst'][1]))
            pdf.text(10, 240, str(dict['lst'][2]))
            pdf.text(10, 255, str(dict['lst'][3]))
            pdf.text(10, 270, str(dict['lst'][4]))
            # self.lst0
            if len(dict['title']) > 1:
                dict['title']=dict['title'].lower()
            if len(dict['comp_desc']) >1:
                dict['comp_desc']=dict['comp_desc'].lower()
            if len(dict['comp_head']) >1:
                dict['comp_head']=dict['comp_head'].lower()

            if dict['lst'][0] in dict['title']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(75, 210, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(75, 210, "No")
            if dict['lst'][0] in dict['comp_desc']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(120, 210, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(120, 210, "No")

            if dict['lst'][0] in dict['comp_head']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(180, 210, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(180, 210, "No")

            # self.lst1
            if dict['lst'][1] in dict['title']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(75, 225, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(75, 225, "No")
            if dict['lst'][1] in dict['comp_desc']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(120, 225, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(120, 225, "No")

            if dict['lst'][1] in dict['comp_head']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(180, 225, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(180, 225, "No")

            # self.lst2
            if dict['lst'][2] in dict['title']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(75, 240, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(75, 240, "No")
            if dict['lst'][2] in dict['comp_desc']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(120, 240, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(120, 240, "No")

            if dict['lst'][2] in dict['comp_head']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(180, 240, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(180, 240, "No")

            # self.lst3
            if dict['lst'][3] in dict['title']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(75, 255, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(75, 255, "No")
            if dict['lst'][3] in dict['comp_desc']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(120, 255, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(120, 255, "No")

            if dict['lst'][3] in dict['comp_head']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(180, 255, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(180, 255, "No")

            # self.lst4
            if dict['lst'][4] in dict['title']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(75, 270, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(75, 270, "No")
            if dict['lst'][4] in dict['comp_desc']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(120, 270, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(120, 270, "No")

            if dict['lst'][4] in dict['comp_head']:
                pdf.set_text_color(34, 139, 34)
                pdf.text(180, 270, "Yes")
            else:
                pdf.set_text_color(255, 0, 0)
                pdf.text(180, 270, "No")

            courses = []
            for i in dict['conversion'].keys():
                if len(i) > 5:
                    courses.append(i[:5]+'...')
                else:
                    courses.append(i)
            values = list(dict['conversion'].values())
            fig = plt.figure(figsize=(3.7, 3.7))
            # creating the bar plot
            plt.bar(courses, values, color='#1C86EE', width=0.4)
            plt.xlabel("Keyword")
            plt.ylabel("Count")
            plt.savefig("graph.png")
            pdf.image('graph.png', 84, 25)

        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 07')
        pdf.add_page()

        # Internal & External link Detail Recommendation:
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 15, "LINKS:")
        pdf.set_font('times', '', 18)
        pdf.ln(15)
        key_txt = "External links boost the visibility on various Search Engine Results pages.External links you add can assist search engines in determining quality of your pages. High quality pages usually link to other quality pages. Thus, search engines will look your content favorably, helping you rank higher."
        key_txt = "External links boost the visibility on various Search Engine Results pages.External links you add can assist search engines in determining quality of your pages. High quality pages usually link to other quality pages. Thus, search engines will look your content favorably, helping you rank higher."
        pdf.multi_cell(65, 10, key_txt)
        pdf.ln(10)

        link_dict = {"Internal_link": dict['internal_links'], "External_link": dict['external_links']}
        x_axis = list(link_dict.keys())
        y_axis = list(link_dict.values())
        fig = plt.figure(figsize=(3.7, 3.7))
        # creating the bar plot
        plt.bar(x_axis, y_axis, color=['#1C86EE', 'green'], width=0.4)
        plt.xlabel("Links")
        plt.ylabel("Total_links found")
        plt.savefig("Links.png")
        pdf.image('Links.png', 85, 15)

        # Robot.txt Detail Recommendation
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 165, "ROBOT.txt:")
        pdf.set_font('times', '', 18)
        pdf.ln(10)

        if dict['robot_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(63, 175, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(92, 175, 'Robot.txt found')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(63, 175, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(92, 175, 'Robot.txt not found')
        pdf.ln(5)
        if dict['robot_flag'] == True:
            robot_text = "The robots.txt file, also known as the robots exclusion protocol or standard, is a text file that tells web robots (search engines) which pages on your site to crawl or not to crawl."
            pdf.multi_cell(180, 10, robot_text)

        else:
            robot_text = "It should be created and researched carefully in order to avoid a decrease in ranking or to speedup your profile during crawling."
            pdf.multi_cell(180, 10, robot_text)

        # Sitemap Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 220, "SITEMAP:")
        pdf.set_font('times', '', 18)
        pdf.ln(22)

        if dict['sitemap_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(63, 230, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(92, 230, 'Sitemap found')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(63, 230, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(92, 230, 'Sitemap not found')
        pdf.ln(12)
        if dict['sitemap_flag'] == True:
            pdf.text(10, 245,'In simple terms, an XML sitemap is a list of your websites URLs. It')
            pdf.text(10, 255,'acts as a roadmap to tell search engines what content is available and')
            pdf.text(10, 265,'how to reach it. A search engine will find all nine pages in a sitemap')
            pdf.text(10, 275,'with one visit to the XML sitemap file.')
        else:
            sitemap_text = "It is important to optimize the site map of the website so that the search engine can find it and gather information."
            pdf.multi_cell(180, 10, sitemap_text)

        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 08')
        pdf.add_page()

        #Btroken Links Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 15, "BROKEN LINKS:")
        pdf.set_font('times', '', 18)
        pdf.ln(15)
        link_txt = "Broken links are not only bad for user experience but can also be harmful to your sites loving relationship with Google, i.e., your SEO. Avoid linking out to broken content and avoid having pages on your site that are broken. "
        pdf.multi_cell(65, 10, link_txt)
        pdf.ln(10)
        fig, ax = plt.subplots(figsize=(4,4), subplot_kw={'projection': 'polar'})
        x = (dict['b_links'] * pi * 2) / 100
        left = (0 * pi * 2) / 360  # this is to control where the bar starts
        plt.xticks([])
        plt.yticks([])
        ax.spines.clear()
        ax.barh(1, x, left=left, height=1, color='#FF0000')
        plt.ylim(-3, 3)
        plt.text(0, -3, str(dict['b_links']) + "%", ha='center', va='center', fontsize=42)
        plt.savefig('b_links.png')

        pdf.image('b_links.png', 80, 10)

        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 155, "FAVICON:")
        pdf.set_font('times', '', 18)
        pdf.ln(30)
        #
        if dict['icon_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(63, 170, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.ln(2)
            pdf.text(92, 170, 'Icon found')
            try:
                image = Image.open('test.jpg')
                im = image.convert('RGB')
                im.save("test.jpg")

                pdf.image('test.jpg', 130, 158, 15, 15)
                pdf.ln(2)
            except:
                pdf.set_text_color(255, 0, 0)
                pdf.set_font('Times', 'B', 18)
                pdf.text(63, 180, "Warning!")
                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Times', '', 18)
                # pdf.image('test1.png', 110, 158, 15, 15)
                pdf.text(92, 180, 'Icon format have Error')

        elif dict['icon_flag'] == False:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(63, 170, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            # pdf.image('test1.png', 110, 158, 15, 15)
            pdf.text(92, 170, 'Icon not found')
        pdf.ln(2)
        pdf.set_font('times', '', 18)
        icon_txt = "A favicon is a visual representation of your website and business, so users will identify with your brand based on the favicon you use. SEO is all about branding and marketing and the more visible your website is, the more users are likely to click on your website and remember who you are."
        pdf.multi_cell(170, 12, icon_txt)
        pdf.ln(2)

        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 09')
        pdf.add_page()

        # Schema Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 15, "SCHEMA:")
        pdf.set_font('times', '', 18)
        pdf.ln(30)

        if dict['schema_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(63, 30, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(92, 30, 'Schema found')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(63, 30, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(92, 30, 'Schema not found')

        if dict['schema_flag'] == True:
            schema_text = " Schema markup is code (semantic vocabulary) that you place on your website to help the search engines return more informative results for users."
            pdf.multi_cell(180, 10, schema_text)

        else:
            schema_text = "The web we know is changing and the only way to remain visible on the new layer of the web is providing semantically described structured data. Schema.org is helping us."
            pdf.multi_cell(180, 10, schema_text)

        # OpenGraph Protocol Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 85, "OPEN GRAPH PROTOCOL:")
        pdf.set_font('times', '', 18)
        pdf.ln(38)

        if dict['ogp_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(48, 100, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(75, 100, ' Open Graph Protocol found')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(48, 100, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(75, 100, ' Open Graph Protocol not found')

        if dict['ogp_flag'] == True:
            ogp_text = "Open Graph is a protocol that allows developers to control what content is shown when their websites are linked on Facebook or another social media platform. If you lack these tags, then there is a good chance that an unrelated image will appear when your website isshared, or the description will be inaccurate."
            pdf.multi_cell(180, 10, ogp_text)

        else:
            ogp_text = "Open Graph Protocol has advantages for website owners: they can more precisely track who has visited the website and which elements have been viewed on an individual page."
            pdf.multi_cell(180, 10, ogp_text)

        # Facebook
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 175, "FACEBOOK:")
        pdf.set_font('times', '', 18)

        if dict['fb_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(10, 195, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(40, 195, 'Facebook found')
        elif dict['fb_flag'] == False:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(10, 195, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(40, 195, 'Facebook not found')
            pdf.text(10, 210,'One of the easiest way to')
            pdf.text(10, 220,'expand your reach and spread')
            pdf.text(10, 230,'information regarding your')
            pdf.text(10, 240,'organization is to share')
            pdf.text(10, 250,'website links on Facebook.')

        # Instagram
        pdf.set_font('Times', 'BU', 20)
        pdf.text(110, 175, "INSTAGRAM:")
        pdf.set_font('times', '', 18)
        pdf.ln(38)

        if dict['insta_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(110, 195, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(140, 195, 'Instagram found')
        elif dict['insta_flag'] == False:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(110, 195, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(140, 195, 'Instagram not found')
            pdf.text(110, 210,
                     'One of your main instagram goals is to drive traffic to your website. The best way to do this is by inserting links on your instagram.'[
                     0:36])
            pdf.text(110, 220,
                     'One of your main instagram goals is to drive traffic to your website. The best way to do this is by inserting links on your instagram.'[
                     36:73])
            pdf.text(110, 230,
                     'One of your main instagram goals is to drive traffic to your website. The best way to do this is by inserting links on your instagram.'[
                     74:109])
            pdf.text(110, 240,
                     'One of your main instagram goals is to drive traffic to your website. The best way to do this is by inserting links on your instagram and optimize'[
                     110:])
            pdf.text(110, 250, 'your content to increase visibility.')

        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 10')
        pdf.add_page()

        # Twitter Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 15, "TWITTER:")
        pdf.set_font('times', '', 18)
        pdf.ln(28)
        if dict['twitter_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(10, 30, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(40, 30, 'Twitter found')
        elif dict['twitter_flag'] == False:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(10, 30, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(40, 30, 'Twitter not found')
            pdf.multi_cell(80, 10,
                           'Posting a twitter backlink is for the traffic to your website. It improves your site SEO score and also increases your site authority.')

        # Lindedin
        pdf.set_font('Times', 'BU', 20)
        pdf.text(110, 15, "LINKEDIN:")
        pdf.set_font('times', '', 18)
        pdf.ln(38)

        if dict['linkedin_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(110, 30, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(140, 30, 'Linkedin found')
        elif dict['linkedin_flag'] == False:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(110, 30, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(140, 30, 'Linkedin not found')
            pdf.text(110, 44,
                     'Set up your Linkedin Page to improve your reputation & drive more traffic to your website and optimize your Linkedin presence as part of your social media optimization.'[
                     0:36])
            pdf.text(110, 54,
                     'Set up your Linkedin Page to improve your reputation & drive more traffic to your website and optimize your Linkedin presence as part of your social media optimization.'[
                     37:73])
            pdf.text(110, 64,
                     'Set up your Linkedin Page to improve your reputation & drive more traffic to your website and optimize your Linkedin presence as part of your social media optimization.'[
                     74:107])
            pdf.text(110, 74,
                     'Set up your Linkedin Page to improve your reputation & drive more traffic to your website and optimize your Linkedin presence as part of your social media optimization'[
                     108:141])
            pdf.text(110, 84,
                     'Set up your Linkedin Page to improve your reputation & drive more traffic to your website and optimize your Linkedin presence as part of your social media optimization efforts.'[
                     142:])
        fig, ax = plt.subplots(figsize=(2.5,2.5), subplot_kw={'projection': 'polar'})
        x = (dict['s_count'] * pi * 2) / 100
        left = (0 * pi * 2) / 360  # this is to control where the bar starts
        plt.xticks([])
        plt.yticks([])
        ax.spines.clear()
        ax.barh(1, x, left=left, height=1, color='#1874CD')
        plt.ylim(-3, 3)
        plt.text(0, -3, str(dict['s_count']) + "%", ha='center', va='center', fontsize=24)
        plt.savefig('social.png')
        pdf.image('social.png', 110, 98)


        pdf.set_font('Times', '', 20)
        pdf.text(10, 95, "-----------------------------------")
        pdf.text(10, 115,"-----------------------------------")
        pdf.set_font('Times', 'BU', 16)
        pdf.text(10,105 , "SOCIAL ANALYSIS SCORE")
        pdf.text(132, 105, "YOUR SCORE:")

        pdf.set_font('Times', '', 16)
        pdf.text(10, 125,"All 4 links found:")
        pdf.text(10, 135,"Any 3 links found:")
        pdf.text(10, 145,"Any 2 links found:")
        pdf.text(10, 155,"Only 1 link found:")
        pdf.text(10, 165,"Zero!! link found:")

        pdf.set_text_color(34, 139, 34)
        pdf.text(60, 125, "100%")
        pdf.text(60, 135, "75%")
        pdf.text(60, 145, "50%")
        pdf.set_text_color(255, 0, 0)
        pdf.text(60, 155, "25%")
        pdf.text(60, 165, "0%")

        #Technology Analysis

        #ServerIP Detail Recommendation
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 185, "SERVER IP:")
        pdf.set_font('times', '', 18)

        if dict['ip_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(63, 200, "IP Found!")
            pdf.set_text_color(0, 0, 0)
            pdf.text(93, 200, dict['ip'])
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(63, 200, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.text(93, 200, 'Server IP not found')

        pdf.ln(75)
        pdf.set_font('Times', '', 18)
        pdf.text(10, 215,
                 'According to the SEO experts Server IP have no impact on ranking.If your website is targeting a specific geographic region, hosting your website on a server located in that region could potentially improve your local SEO efforts.'[
                 0:72])
        pdf.text(10, 225,
                 'According to the SEO experts Server IP have no impact on ranking.If your website is targeting a specific geographic region, hosting your website on a server located in that region could potentially improve your local SEO efforts.'[
                 73:147])
        pdf.text(10, 235,
                 'According to the SEO experts Server IP have no impact on ranking.If your website is targeting a specific geographic region, hosting your website on a server located in that region could potentially improve your local SEO efforts.'[
                 148:220])
        pdf.text(10, 245,
                 'According to the SEO experts Server IP have no impact on ranking.If your website is targeting a specific geographic region, hosting your website on a server located in that region could potentially improve your local SEO efforts.'[
                 221:])
        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 11')
        pdf.add_page()

        # Server location Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 15, "SERVER LOCATION:")
        pdf.set_font('times', '', 18)
        pdf.ln(26)

        if dict['server_loc_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(43, 30, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(73, 30, "Server Location Found!")
            pdf.text(135, 30, "(" + dict['loc_name'] + ")")
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(43, 30, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(73, 30, 'Server Location not found')

        pdf.multi_cell(180, 10,
                       'Although the server location is not much important in SEO, but if you are targeting a specific audience in a country, then the location must be near the region.')

        # Technology Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 80, "TECHNOLOGY:")
        pdf.set_font('times', '', 18)
        pdf.ln(43)
        if dict['tech_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 17)
            pdf.text(30, 95, "Webserver Found!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 17)
            pdf.text(92, 95, dict['webserver'])

        elif dict['tech_flag'] == False:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 17)
            pdf.text(30, 95, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(92, 95, 'Webserver not found')

        pdf.multi_cell(180, 10,
                       'The technology used on the website is one of the most important factors in SEO. Since the new technologies are getting improved day by day, it is better for the websites to use tech like Ext JS, Angular,React,Jquery etc.')

        # w3c Validation Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 160, "W3C VALIDATION:")
        pdf.set_font('times', '', 18)
        pdf.ln(26)
        key_txt = "Validating your website is important because there are code errors that can cause serious styling issues from a web design perspective.Errors in your code can affect your site's performance and make a big impact on your site's SEO."
        pdf.multi_cell(72, 10, key_txt)
        pdf.ln(26)

        link_dict = {"Error": dict['error_len'], "Warning": dict['warn_len']}
        x_axis = list(link_dict.keys())
        y_axis = list(link_dict.values())
        fig = plt.figure(figsize=(3, 3))
        # creating the bar plot

        plt.bar(x_axis, y_axis, color=['red', '#1C86EE'], width=0.4)
        plt.xlabel("")
        plt.ylabel("")
        plt.savefig("w3c.png")
        pdf.image('w3c.png', 90, 160)

        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 12')
        pdf.add_page()

        # Google Analytics
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 15, "GOOGLE ANALYTICS:")
        pdf.set_font('times', '', 18)
        pdf.ln(30)

        if dict['analytics_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(57, 30, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(82, 30, 'Google Analytics found')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(49, 30, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(82, 30, 'Google Analytics not found')

        if dict['analytics_flag'] == True:
            ana_text = "SEO analytics refers to the process of collecting, tracking, and analyzing your marketing data with the core aim of growing your websites organic traffic. The website must have a search engine analytics such as Google analytics."
            pdf.multi_cell(180, 10, ana_text)

        else:
            ana_text = "You do really need to have some form of analytics on your website. Without analytics, you can not draw conclusions about how people are using your site. Without data, you can not make the improvements that are going to grow your business or brand."
            pdf.multi_cell(180, 10, ana_text)

        # Content Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 90, "CONTENT:")
        pdf.set_font('times', '', 18)
        pdf.ln(38)

        # Doctype Detail Recommendation
        if dict['doc_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(10, 105, "DocType Found!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(60, 105,dict['Doctype'][0:9])
        elif dict['doc_flag'] == False:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(10, 105, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(50, 105, 'DocType not found')
        pdf.multi_cell(80, 10,
                       'A document type declaration, defines which version of (X)HTML your webpage is using.It lets the browser know how the document should be interpreted ')

        #Encoding Detail Recommendation
        if dict['encod_flag'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(110, 105, "Encoding Found!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(160, 105, dict['Encoding'])
        elif dict['encod_flag'] == False:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(110, 105, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(145, 105, 'Encoding not found')
        text = 'The encoding type refers to the character encoding, which is the method of converting a sequence of bytes into a sequence of characters. The website should have content that is rightly encoded.'
        pdf.text(110, 125, text[0:32])
        pdf.text(110, 135, text[32:65])
        pdf.text(110, 145, text[65:97])
        pdf.text(110, 155, text[97:125])
        pdf.text(110, 165, text[125:161])
        pdf.text(110, 175, text[161:])

        # PERFORMANCE ANALYSIS

        # Optimized plugins Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 195, "OPTIMIZED PLUGINS:")
        pdf.set_font('times', '', 18)

        if dict['plugins'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(35, 210, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(63, 210, 'Website is using optimized plugins.')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(35, 210, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(63, 210, 'Website is not using any optimized plugins.')

        pdf.ln(40)
        if dict['plugins'] == True:
            plug_text = "Congratulations, your website is using optimized plugins which can lead to increased traffic, improved search engine rankings, and higher conversion rates."
            pdf.multi_cell(180, 10, plug_text)
        else:
            plug_text = "Website is not using any optimized plugins so it may cause performance issues and security vulnerabilities. Optimized plugins can greatly enhance their websites performance and make it more competitive in their industry."
            pdf.multi_cell(180, 10, plug_text)

        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 13')
        pdf.add_page()

        # Website speed Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 15, "WEBSITE SPEED:")
        pdf.set_font('times', '', 18)
        pdf.ln(28)
        title_txt = 'A good website should aim to load as quickly as possible, ideally within 3 seconds or less.'
        pdf.text(10, 30, title_txt[0:75])
        pdf.text(10, 40, title_txt[75:])

        pdf.ln(32)
        if dict['speed'] >= 2.5:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(55, 53, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(82, 53, 'Wesbite speed score is not good')
            pdf.ln(7)
            title_txt = 'Research has shown that users tend to lose interest and abandon websites that take longer than 3 seconds to load.'
            pdf.multi_cell(70, 10, title_txt)
            pdf.ln(40)

            fig, ax = plt.subplots(figsize=(2, 2), subplot_kw={'projection': 'polar'})
            x = (dict['speed'] * pi * 2) / 100
            left = (0 * pi * 2) / 360  # this is to control where the bar starts
            plt.xticks([])
            plt.yticks([])
            ax.spines.clear()
            ax.barh(1, x, left=left, height=1, color='#FFFFFF')
            plt.ylim(-3, 3)
            plt.text(0, -3, str(dict['speed']), ha='center', va='center', fontsize=42)
            plt.savefig('webspeed.png')
            # self.Score_Graph('webspeed_Image', 'webspeed.jpg', dict['speed'])
            pdf.set_text_color(0, 0, 0)
            pdf.image('webspeed.png', 120, 55)
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(142, 110, "SECONDS")

        else:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(50, 53, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(78, 53, "Website speed score is good")
            pdf.ln(5)
            title_txt = 'Your website is optimized for speed and it should provide a fast and seamless user experience.'
            pdf.multi_cell(70, 10, title_txt)

            pdf.ln(35)
            fig, ax = plt.subplots(figsize=(2, 2), subplot_kw={'projection': 'polar'})
            x = (dict['speed'] * pi * 2) / 100
            left = (0 * pi * 2) / 360  # this is to control where the bar starts
            plt.xticks([])
            plt.yticks([])
            ax.spines.clear()
            ax.barh(1, x, left=left, height=1, color='#FFFFFF')
            plt.ylim(-3, 3)
            plt.text(0, -3, str(dict['speed']), ha='center', va='center', fontsize=42)
            plt.savefig('webspeed.png')
            # self.Score_Graph('webspeed_Image', 'webspeed.jpg', dict['speed'])
            pdf.set_text_color(0, 0, 0)
            pdf.image('webspeed.png', 120, 55)
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(142, 110, "SECONDS")


            # css minified Detail Recommendation
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 160, "CSS MINIFICATION:")
        pdf.set_font('times', '', 18)

        if dict['css'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(45, 175, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(78, 175, 'CSS code for the website is minified')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(45, 175, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(78, 175, 'CSS code for the website is not minified')

        if dict['css'] == True:
            pdf.ln(35)
            css_text = "Congratulations, your website minified CSS code is helping to provide a faster and smoother experience to your users."
            pdf.multi_cell(195, 10, css_text)
        else:
            pdf.ln(35)
            css_text = "Non-minified CSS code may increase file size, slow down website loading speed and performance. We recommend minifying your websites CSS code to improve its loading speed and overall performance for better user experience."
            pdf.multi_cell(195, 10, css_text)

        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 14')
        pdf.add_page()

        # jss minified Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 15, "JSS MINIFICATION:")
        pdf.set_font('times', '', 18)
        if dict['jss'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(45, 30, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(78, 30, 'JSS code for the website is minified')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(45, 30, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(78, 30, 'JSS code for the website is not minified')

        if dict['jss'] == True:
            pdf.ln(25)
            jss_text = "Minifying JavaScript code means removing unnecessary characters from the code to make it smaller and faster to load.It provides a smoother user experience for your customers."
            pdf.multi_cell(180, 10, jss_text)
        else:
            pdf.ln(25)
            jss_text = "The js code includes unnecessary characters such as whitespace and comments, which can make it larger and slower to load. This may result in slower website performance and longer load times for your customers."
            pdf.multi_cell(180, 10, jss_text)

            # Mobile speed Detail Recommendation
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 90, "MOBILE SPEED:")
        pdf.set_font('times', '', 18)
        pdf.ln(26)
        link_txt = "Its important to note that the score can vary depending on the websites content, functionality, and design. A website that has a lot of high-quality images or complex functionality may have a slightly lower score, but still be considered fast enough for users."
        pdf.multi_cell(65, 10, link_txt)
        pdf.ln(50)
        fig, ax = plt.subplots(figsize=(3, 3), subplot_kw={'projection': 'polar'})
        x = (dict['mob_score'] * pi * 2) / 100
        left = (0 * pi * 2) / 360  # this is to control where the bar starts
        plt.xticks([])
        plt.yticks([])
        ax.spines.clear()
        ax.barh(1, x, left=left, height=1, color='#FFFFFF')
        plt.ylim(-3, 3)
        plt.text(0, -3, str(dict['mob_score']), ha='center', va='center', fontsize=42)
        plt.savefig('mob_speed.png')
        # self.Score_Graph('mob_speed_Image', 'mob_speed.jpg', dict['mob_score'])
        pdf.image('mob_speed.png', 91, 90)
        pdf.set_text_color(34, 139, 34)
        if dict['mob_score'] < 3:
            pdf.set_font('Times', 'B', 18)
            pdf.text(131, 160, "SECONDS")
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(131, 160, "SECONDS")

        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 15')
        pdf.add_page()

        # AMP
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 15, "AMP:")
        pdf.set_font('times', '', 18)

        if dict['amp'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(50, 25, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(80, 25, 'Website using AMP')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(50, 25, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(80, 25, 'Website not using AMP')

        if dict['amp'] == True:
            pdf.ln(20)
            amp_text = "Website is optimized for fast page load times, improved mobile SEO, and a better mobile user experience."
            pdf.multi_cell(195, 10, amp_text)

        else:
            pdf.ln(20)
            amp_text = "AMP can improve their websites mobile user experience and search engine rankings, resulting in increased traffic and engagement."
            pdf.multi_cell(195, 10, amp_text)

            # Mobile Rendering
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 65, "MOBILE RENDERING:")
        pdf.set_font('times', '', 18)

        if dict['render'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(32, 80, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(65, 80, 'Mobile rendering is working for wesbite')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(32, 80, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(65, 80, 'Mobile rendering is not working for wesbite')

        if dict['render'] == True:
            pdf.ln(37)
            render_text = "Mobile Rendering is the process where Googlebot retrieves your pages,runs your code, and assesses your content to understand the layout or structure of your site.The mobile version of the website must be stable and well functional."
            pdf.multi_cell(195, 10, render_text)

        else:
            pdf.ln(37)
            render_text = "Having a website that is optimized for mobile devices is crucial for SEO as it improves user experience, increases engagement, and can positively impact the website's search engine rankings. Not having mobile rendering available for a website can negatively impact its performance and visibility in search results."
            pdf.multi_cell(195, 10, render_text)

            #         #Image Alt Check
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 155, "IMAGE ALT CHECK:")
        pdf.ln(30)
        pdf.set_font('Times', '', 18)
        if dict['alt_count'] == 0:
            alt_txt = "Alt attributes enable screen readers to read the information about on-page images for the benefit of a person with complete lack of sight, visually impaired, or who is otherwise unable to view the images on the page.."
            pdf.multi_cell(85, 8, alt_txt)
        else:
            alt_txt = "All image tags should have attribute ALT."
            pdf.multi_cell(68, 20, alt_txt)
        fig, ax = plt.subplots(figsize=(3, 3), subplot_kw={'projection': 'polar'})
        x = (dict['alt_count']* pi * 2) / 100
        left = (0 * pi * 2) / 360  # this is to control where the bar starts
        plt.xticks([])
        plt.yticks([])
        ax.spines.clear()
        ax.barh(1, x, left=left, height=1, color='#FF0000')
        plt.ylim(-3, 3)
        plt.text(0, -3, str(dict['alt_count']) + "%", ha='center', va='center', fontsize=25)
        plt.savefig('img.jpg')
        pdf.image('img.jpg', 97, 130)
        pdf.set_text_color(255, 0, 0)
        pdf.set_font('Times', 'B', 16)
        pdf.text(112, 234, 'No of Images without Alt Attribute')

        # Mobile preview Detail Recommendation
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', 'BU', 18)
        pdf.text(10,250, "MOBILE PREVIEW")
        pdf.set_font('Times', '', 16)
        if dict['mobpreview'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(45, 265, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(73, 265, 'Mobile preview is optimized')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(45, 265, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(73, 265, 'Mobile preview is not optimized')


        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 16')
        pdf.add_page()

        # Mobile preview Image
        pdf.image('mobile_view.png', 42, 5)
        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 17')
        pdf.add_page()

        # Security
        # SSL
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 15, "SSL:")
        pdf.set_font('times', '', 18)
        pdf.ln(50)
        if dict['ssl'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 16)
            pdf.text(15, 30, "SSL Name Found!")
            pdf.text(15, 40, "SSL Organization Found!")
            pdf.text(15, 50, "SSL Expiry Found!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 16)
            pdf.text(95, 30, str(dict['name']))
            pdf.text(95, 40, str(dict['organization']))
            pdf.text(95, 50, str(dict['expiry_date']))

        elif dict['ssl'] == False:
            pdf.set_font('Times', 'B', 16)
            pdf.set_text_color(255, 0, 0)
            pdf.text(15, 30, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.text(95, 30, 'SSL Name not found')
            pdf.set_text_color(255, 0, 0)
            pdf.text(15, 40, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.text(95, 40, 'SSL Oragnaization not found')
            pdf.set_text_color(255, 0, 0)
            pdf.text(15, 50, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.text(95, 50, 'SSL Expiry not found')
            pdf.set_text_color(0, 0, 0)

        pdf.set_font('Times', '', 18)
        pdf.multi_cell(180, 10,'It improves website security and user trust, both of which can lead to higher search engine rankings and increased traffic to the website.')

        # DMCA
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 100, "DMCA:")
        pdf.set_font('times', '', 18)

        if dict['dmca'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(45, 110, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(73, 110, 'Website is protected by DMCA')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(45, 110, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(73, 110, 'Website is not protected by DMCA')

        if dict['dmca'] == True:
            pdf.ln(40)
            dmca_text = "Regularly review and update their DMCA policy to ensure it is effective in protecting their users intellectual property."
            pdf.multi_cell(195, 10, dmca_text)

        else:
            pdf.ln(40)
            dmca_text = "Implementing DMCA on their website to protect the intellectual property of their users and comply with legal requirements for addressing claims of copyright infringement."
            pdf.multi_cell(195, 10, dmca_text)

        # HTTP Redirection
        pdf.set_font('Times', 'BU', 20)
        pdf.text(10, 165, "HTTPS REDIRECTION:")
        pdf.set_font('times', '', 18)

        if dict['https'] == True:
            pdf.set_text_color(34, 139, 34)
            pdf.set_font('Times', 'B', 18)
            pdf.text(42, 180, "Success!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(70, 180, 'Website is using HTTPS redirection')
        else:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font('Times', 'B', 18)
            pdf.text(42, 180, "Warning!")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Times', '', 18)
            pdf.text(70, 180, 'Website is not using HTTPS redirection')

        if dict['https'] == True:
            pdf.ln(40)
            https_text = "HTTPS redirection ensures website security and is a positive ranking signal for search engines."
            pdf.multi_cell(195, 10, https_text)

        else:
            pdf.ln(40)
            https_text = "HTTPS will add privacy and security to a website and SEO goals through verification of the website that it is the right one on the server, preventing tampering by third parties, making the website more secure for visitors, and encrypting all communication like URLs, which in turn protects things like credit card."
            pdf.multi_cell(195, 10, https_text)

        pdf.set_font('Times', '', 16)
        pdf.text(180, 288, 'Page | 18')
        pdf_name = 'Report_' + str(random.randint(10, 99))
        pdf.output(pdf_name + '.pdf')
        pdf_file = (pdf_name + '.pdf')
        webbrowser.open(pdf_file)
        return





    def get_data(self):
        global Report_variables
        self.data['url']=self.url
        self.get_title()
        self.get_description()
        self.get_Heading()
        self.get_Google_preview()
        self.Keyword_Density()
        self.get_missing_alt()
        self.get_Status()
        self.get_links()
        self.check_robot_txt()
        self.get_sitemap()
        self.get_broken_links()
        self.get_schema()
        self.get_Open_GP()
        self.get_favicon()
        self.Social()
        self.get_technology()
        self.Google_Analytics()
        self.w3c_validation()
        self.get_content()
        self.get_server()
        self.SSL()
        self.Https_Redirection()
        self.DMCA()
        self.measure_website_speed()
        self.CSS_minification()
        self.JSS_minification()
        self.Optmized_Plugins()
        self.Mobile_speed()
        self.AMP()
        self.Mobile_rendering()
        self.Mobile_preview()


        Report_variables['url']=self.url
        Report_variables['title']=self.title
        Report_variables['title_score']=self.title_score
        Report_variables['desc_score']=self.desc_score
        Report_variables['H']=self.H
        Report_variables['heading_score']=self.heading_score
        Report_variables['alt_count']=self.alt_count
        Report_variables['external_links']=self.external_links
        Report_variables['robot_flag']=self.robot_flag
        Report_variables['sitemap_flag']=self.sitemap_flag
        Report_variables['b_links']=self.b_links
        Report_variables['icon_flag']=self.icon_flag
        Report_variables['ogp_flag']=self.ogp_flag
        Report_variables['tech_flag']=self.tech_flag
        Report_variables['analytics_flag']=self.analytics_flag
        Report_variables['doc_flag']=self.doc_flag
        Report_variables['Doctype'] = self.Doctype
        Report_variables['Encoding'] = self.Encoding
        Report_variables['dmca']=self.dmca
        Report_variables['https']=self.https
        Report_variables['fb_flag']=self.fb_flag
        Report_variables['insta_flag']=self.insta_flag
        Report_variables['twitter_flag']=self.twitter_flag
        Report_variables['linkedin_flag']=self.linkedin_flag
        Report_variables['speed']=self.speed
        Report_variables['css']=self.css
        Report_variables['jss']=self.jss
        Report_variables['mob_score']=self.mob_score
        Report_variables['amp']=self.amp
        Report_variables['render']=self.render
        Report_variables['desc']=self.desc
        Report_variables['heading']=self.heading
        Report_variables['comp_desc']=self.comp_desc
        Report_variables['lst']=self.lst
        Report_variables['comp_head']=self.comp_head
        Report_variables['conversion']=self.conversion
        Report_variables['internal_links']=self.internal_links
        Report_variables['schema_flag']=self.schema_flag
        Report_variables['s_count']=self.s_count
        Report_variables['ip_flag']=self.ip_flag
        Report_variables['ip']=self.ip
        Report_variables['server_loc_flag']=self.server_loc_flag
        Report_variables['loc_name']=self.loc_name
        Report_variables['webserver']=self.webserver
        Report_variables['error_len']=self.error_len
        Report_variables['warn_len']=self.warn_len
        Report_variables['encod_flag']=self.encod_flag
        Report_variables['plugins']=self.plugins
        Report_variables['mobpreview']=self.mobpreview
        Report_variables['ssl']=self.ssl
        Report_variables['name']=self.name
        Report_variables['organization']=self.organization
        Report_variables['expiry_date']=self.expiry_date



        return self.data





def upload(request,url):
    upload.get_url=str(url)
    if url == "":
        return
    obj=Website_Audit(str(url))
    return obj


def Report(request):
    try:
        obj = Website_Audit(Report_variables['url'])
        obj.Report(Report_variables)
        messages.success(request, 'Report generated successfully!')
        home_url = reverse('Home')
        return redirect(home_url)
    except Exception as e:
        messages.error(request, 'An error occurred: {}'.format(str(e)))
        return render(request, 'home.html')

def index(request):
    # data=upload(request)
    # data['message']="URL entered"
    return render(request, 'index.html')

def show(request):
    url = request.POST["fname"]
    if not url or not validators.url(url):
        return render(request, 'index.html')
    #clean url
    if 'com/' in url and 'pk/' in url:
        pass
    else:
        if ".com/" in url:
            url=url.replace(".com/",".com")
        elif ".pk/" in url:
            url=url.replace(".pk/",".pk")
        elif ".edu/" in url:
            url=url.replace(".edu/",".edu")
        elif ".uk/" in url:
            url=url.replace(".uk/",".uk")
        else:
            pass

    try:
        data = upload(request, url)
        data = data.get_data()
        return render(request, 'home.html', data)
    except requests.exceptions.Timeout as e:
        # Handle timeout error
        messages.error(request, 'Connection timed out!Website is taking Too much time.')
        return render(request, 'index.html')
    except requests.exceptions.RequestException as e:
        # Handle connection error
        messages.error(request, 'Check your internet connection! OR May be Network Error.')
        return render(request, 'index.html')
    except Exception as e:
        # Handle other types of exceptions
        messages.error(request, 'An error occurred: {}'.format(str(e)))
        return render(request, 'index.html')



def backlink(request):
    try:
        if request.method == "GET":
            return render(request, 'backlink.html')
        url = request.POST["fname"]
        if not url or not validators.url(url):
            return render(request, 'backlink.html')

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a')
        backlinks = []
        for link in links:
            href = link.get('href')
            if href and 'example.com' not in href and 'http' in href:
                backlinks.append(href)

        data = {
            'backlinks': len(backlinks),
            'urls': enumerate(backlinks, start=1),
            'url': url,
        }
        return render(request, 'backlink.html', data)

    except requests.exceptions.Timeout as e:
        # Handle timeout error
        messages.error(request, 'Connection timed out!Website is taking Too much time.')
        return render(request, 'backlink.html')
    except requests.exceptions.RequestException as e:
        # Handle connection error
        messages.error(request, 'Check your internet connection! OR May be Network Error.')
        return render(request, 'backlink.html')



def DomainAuthority(request):
    try:
        if request.method == "GET":
            return render(request, 'DomainAuthority.html')
        url = request.POST["fname"]
        if not url or not validators.url(url):
            return render(request, 'DomainAuthority.html')
        data={}
        access_id = 'mozscape-14743efc78'
        secret_key = 'd437141078506f5aa883e3ffef9ad549'
        obj_url = urllib.parse.urlparse(url).hostname
        expires = str(int(time.time()) + 300)
        sign_in_str = access_id + "\n" + expires
        binary_signature = hmac.new(secret_key.encode('utf-8'), sign_in_str.encode('utf-8'), hashlib.sha1).digest()
        safe_signature = urllib.parse.quote(base64.b64encode(binary_signature).decode('utf-8'))
        cols = '103079231488'
        flags = '103079215108'
        req_url = f"http://lsapi.seomoz.com/linkscape/url-metrics/{obj_url}?Cols={cols}&AccessID={access_id}&Expires={expires}&Signature={safe_signature}"
        response = requests.get(req_url)
        res_obj = json.loads(response.content.decode('utf-8'))
        domain_score=round(res_obj['pda'], 2)
        data["url"]=url
        data["da"]=domain_score

        return render(request, 'DomainAuthority.html',data)

    except requests.exceptions.Timeout as e:
        # Handle timeout error
        messages.error(request, 'Connection timed out!Website is taking Too much time.')
        return render(request, 'DomainAuthority.html')
    except requests.exceptions.RequestException as e:
        # Handle connection error
        messages.error(request, 'Check your internet connection! OR May be Network Error.')
        return render(request, 'DomainAuthority.html')


def pageAuthority(request):
    try:
        if request.method=="GET":
            return render(request, 'pageAuthority.html')
        url = request.POST["fname"]
        if not url or not validators.url(url):
            return render(request, 'pageAuthority.html')
        data = {}
        access_id = 'mozscape-14743efc78'
        secret_key = 'd437141078506f5aa883e3ffef9ad549'
        obj_url = urllib.parse.urlparse(url).hostname
        expires = str(int(time.time()) + 300)
        sign_in_str = access_id + "\n" + expires
        binary_signature = hmac.new(secret_key.encode('utf-8'), sign_in_str.encode('utf-8'), hashlib.sha1).digest()
        safe_signature = urllib.parse.quote(base64.b64encode(binary_signature).decode('utf-8'))
        cols = '103079231488'
        flags = '103079215108'
        req_url = f"http://lsapi.seomoz.com/linkscape/url-metrics/{obj_url}?Cols={cols}&AccessID={access_id}&Expires={expires}&Signature={safe_signature}"
        response = requests.get(req_url)
        res_obj = json.loads(response.content.decode('utf-8'))
        page_score = round(res_obj['upa'], 2)
        data["pa"] = page_score
        data["url"]=url
        return render(request, 'pageAuthority.html',data)
    except requests.exceptions.Timeout as e:
        # Handle timeout error
        messages.error(request, 'Connection timed out!Website is taking Too much time.')
        return render(request, 'pageAuthority.html')
    except requests.exceptions.RequestException as e:
        # Handle connection error
        messages.error(request, 'Check your internet connection! OR May be Network Error.')
        return render(request, 'pageAuthority.html')



def mobiletest(request):
    try:
        if request.method == "GET":
            return render(request, 'mobiletest.html')
        url1 = request.POST["fname"]
        if not url1 or not validators.url(url1):
            return render(request, 'mobiletest.html')
        data1={}
        content=""
        test=True
        test1=False
        try:
            url = 'https://searchconsole.googleapis.com/v1/urlTestingTools/mobileFriendlyTest:run'
            params = {
                'url': url1,
                'key': "AIzaSyBHQ0tzn7Ox6e4OOWYPfwuV66TcTyM316Q"
            }
            x = requests.post(url, params=params)
            data = json.loads(x.text)
            result=data["mobileFriendliness"]
            data1["result"]=result
            if data["mobileFriendliness"] == "NOT_MOBILE_FRIENDLY":
                test=False
                test1=True
                for iteration in range(len(data["mobileFriendlyIssues"])):
                    content+="The page has problems with " + str(data["mobileFriendlyIssues"][iteration]["rule"])+"\n"

            issues = data.get("resourceIssues", 0)
            if issues != 0:
                for iteration in range(len(data["resourceIssues"])):
                    content+="Problems with the blocked resources " + str(data["resourceIssues"][iteration]["blockedResource"]["url"])+"\n"

        except:
            x = requests.post(url, params=params)
            content="Problem with " + str(params["url"]) + ". " + str(x)[len(str(x)) - 5:len(str(x)) - 2] + " Response Code."
        data1["content"]=content
        data1["url"]=url1
        data1["test"]=test
        data1["test1"] = test1
        return render(request, 'mobiletest.html',data1)
    except requests.exceptions.Timeout as e:
        # Handle timeout error
        messages.error(request, 'Connection timed out!Website is taking Too much time.')
        return render(request, 'mobiletest.html')
    except requests.exceptions.RequestException as e:
        # Handle connection error
        messages.error(request, 'Check your internet connection! OR May be Network Error.')
        return render(request, 'mobiletest.html')


def robot(request):
    try:
        if request.method=="GET":
            return render(request, 'robot.html')
        url = request.POST["fname"]
        if not url or not validators.url(url):
            return render(request, 'robot.html')

        content = "#robots.txt generated by Smart Web Analyzer\n"
        content += f"User-agent: *\n"
        content += "Disallow: \n"
        content += "Disallow: /cgi-bin/\n"
        content += "#Restricted Directory\n"
        content += "Sitemap: {}/sitemap.xml".format(url)

        data={}
        data['content']=content
        data["url"]=url
        return render(request, 'robot.html', data)
    except requests.exceptions.Timeout as e:
        # Handle timeout error
        messages.error(request, 'Connection timed out!Website is taking Too much time.')
        return render(request, 'robot.html')
    except requests.exceptions.RequestException as e:
        # Handle connection error
        messages.error(request, 'Check your internet connection! OR May be Network Error.')
        return render(request, 'robot.html')

def keyPosition(request):
    from googlesearch import search
    try:
        if request.method == 'GET':
            return render(request, 'keyPosition.html')

        data = {}
        url = request.POST.get("url")
        keyword = request.POST.get("keyword")

        data['url'] = url
        data['keyword'] = keyword

        if not url or not keyword or not validators.url(url):
            data.clear()
            return render(request, 'keyPosition.html', data)


        def check_url(url):
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://" + url
            if not re.search(r'www\.', url):
                url = url.replace("://", "://www.")
            if not url.endswith('/'):
                url += '/'

            return url

        url1=check_url(url)

        data["url"] = url1
        data["keyword"]= keyword


        def find_link_position(keyword, link):
            search_results = list(search(keyword, num_results=10))
            for position, url in enumerate(search_results, 1):
                if url == link:
                    return position

            return -1  # Return -1 if the link is not found in the top 10 search results.

        position = find_link_position(keyword, url1)
        if position != -1:
            data['rank']=f"The link '{url1}' is found at position {position} in the results."
        else:
            data['rank']=f"The link '{url1}' is not found in the top 10 search results."

        return render(request, 'keyPosition.html',data)
    except requests.exceptions.Timeout as e:
        # Handle timeout error
        messages.error(request, 'Connection timed out!Website is taking Too much time.')
        return render(request, 'keyPosition.html')
    except requests.exceptions.RequestException as e:
        # Handle connection error
        messages.error(request, 'Check your internet connection! OR May be Network Error.')
        return render(request, 'keyPosition.html')

def keysuggestion(request):
    try:
        if request.method=="GET":
            return render(request, 'keysuggestion.html')
        data={}
        keyword = request.POST.get("fname", "").strip()
        word_regex = re.compile(r'^[A-Za-z]+$')

        if keyword == '' or not word_regex.match(keyword):
            data.clear()
            return render(request, 'keysuggestion.html', data)
        url = f"http://suggestqueries.google.com/complete/search?output=firefox&q={keyword}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(url, headers=headers)
        suggestions = response.json()[1]
        keywords = ""
        for i in suggestions:
            keywords += i + "\n"
        data["keywords"]=keywords
        data["keyword"]=keyword
        return render(request, 'keysuggestion.html',data)
    except requests.exceptions.Timeout as e:
        # Handle timeout error
        messages.error(request, 'Connection timed out!Website is taking Too much time.')
        return render(request, 'keysuggestion.html')
    except requests.exceptions.RequestException as e:
        # Handle connection error
        messages.error(request, 'Check your internet connection! OR May be Network Error.')
        return render(request, 'keysuggestion.html')

def loginuser (request):

    if request.method=='POST':
        username = request.POST.get('username')
        pass1 = request.POST.get('pass')
        user=authenticate(request,username=username,password=pass1)
        if username == '' or pass1 == '':
            messages.error(request, 'Please fill to Proceed!')
            return redirect('login')
        if user is not None:
            login(request,user)
            return redirect('Home')
        else:
            messages.error(request, 'Invalid Credentials!')
            return redirect('login')
    return render(request, 'fyplogin.html')
def register(request):

    def is_valid_email(email):
        regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(regex, email))

    dict={}
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('FirstName')
        last_name = request.POST.get('LastName')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        dict['username'] = username
        dict['firstname'] = first_name
        dict['lastname'] = last_name
        dict['email'] = email

        if not all([username, email, first_name, last_name, password1, password2]):
            messages.error(request, 'Please fill in all the fields!')
            return render(request, 'register.html',dict)

        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'register.html',dict)

        if not is_valid_email(email):
            messages.error(request, 'Please enter a valid email address!')
            return render(request, 'register.html',dict)

        if User.objects.filter(email=email).exists():
            messages.error(request, 'This email is already registered!')
            del dict['email']
            return render(request, 'register.html',dict)

        try:
            user = User.objects.create_user(username, email, password1, first_name=first_name, last_name=last_name)
            profile = Profile.objects.create(user=user)
            return redirect('login')
        except:
            messages.error(request, 'This User already exist!')
            return render(request, 'register.html')

    return render(request, 'register.html')

@never_cache
def logoutuser(request):
    logout(request)
    response = redirect('login')
    # Disable caching of the page to prevent the user from navigating back to it
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response

def ChangePassword(request, token):
    context = {}

    try:
        profile_obj = Profile.objects.filter(forget_password_token=token).first()
        context = {'user_id': profile_obj.user.id}

        if request.method == 'POST':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('reconfirm_password')
            user_id = request.POST.get('user_id')

            if user_id is None:
                messages.success(request, 'No user id found.')
                return redirect(f'/change-password/{token}/')

            if new_password != confirm_password:
                messages.success(request, 'Both should be equal.')
                return redirect(f'/change-password/{token}/')

            user_obj = User.objects.get(id=user_id)
            user_obj.set_password(new_password)
            user_obj.save()
            return redirect('login')


    except Exception as e:
        print(e)
    return render(request, 'change-password.html', context)


def ForgetPassword(request):
    try:
        if request.method == 'POST':
            email = request.POST.get('email')
            if email == '':
                messages.error(request, 'Please Enter Email to Forget.')
                return redirect('forget_password')
            if not User.objects.filter(email=email):
                messages.error(request, 'No user found with this email.')
                return redirect('forget_password')

            user_obj = User.objects.get(email=email)
            token = str(uuid.uuid4())
            profile_obj = Profile.objects.get(user=user_obj)
            profile_obj.forget_password_token = token
            profile_obj.save()
            send_forget_password_mail(user_obj.email, token)
            messages.success(request, 'An email is sent.')
            return redirect('forget_password')

    except Exception as e:
        messages.error(request, e)
    return render(request, 'forget-password.html')
