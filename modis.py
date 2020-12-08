import scrapy

down_urls = [f'https://oceandata.sci.gsfc.nasa.gov/cgi/getfile/TERRA_MODIS.{i}1201_{i}1231.L3m.MO.SST.sst.4km.nc' for i in range(2001,2020) ]

LOGIN_OR_USE_EXISTED_COOKIE = False  # 是否即时登录

username = 'your-username'
password = 'your-password'

ie_cookies_path = r'C:\Users\dell\Desktop\cookies.txt'

def ie_cookies_to_cookies(ie_cookies_path): 
    with open(ie_cookies_path,'r') as f1:
        return [ {'name':(k:=i.strip().split('\t'))[-2],'value':k[-1],'domain':k[0],'path':k[2]} for i in f1.readlines()[1:] if i.strip() != '']


def authentication_failed(response):
    return False

class ModisSpider(scrapy.Spider):
    name = 'modis'
    down_urls = down_urls
    login_url  = 'https://urs.earthdata.nasa.gov/'
    custom_settings = {'DEFAULT_REQUEST_HEADERS':
                       {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}
                      }
    def start_requests(self):
        if LOGIN_OR_USE_EXISTED_COOKIE:
            yield scrapy.Request(self.login_url,callback=self.before_login)
        else:
            self.cookie_list = ie_cookies_to_cookies(ie_cookies_path)
            #breakpoint()
            for i in self.start_requests_():  # 不能用return self.start_requests_(),否则为空，原因未知。
                yield i 
    
    def before_login(self,response):
        return scrapy.FormRequest.from_response(
            response,
            formdata={'username': username, 'password': password},
            callback=self.after_login
        )
            
    def after_login(self, response):
        if authentication_failed(response):
            self.logger.error("Login failed")
            return
        else:
            from scrapy.http.cookies import CookieJar  # 来自：https://www.cnblogs.com/nuochengze/p/13376791.html
            cookie_jar = CookieJar()
            cookie_jar.extract_cookies(response, response.request)
            self.cookie_list = []
            for domain, kv in cookie_jar._cookies.items():
                for path, kv2 in kv.items():
                    for name, Cookie in kv2.items():
                        value = Cookie.value
                        self.cookie_list.append({'name':name,'value':value,'domain':domain,'path':path})
            return self.start_requests_()
            
    def start_requests_(self):   
        for req in  [scrapy.Request(url,
                               cookies=self.cookie_list,
                               meta={'cookiejar': i },
                               dont_filter = True)
                                    for i,url in enumerate(self.down_urls)]:
            yield req

    def parse(self, response):
        if response.headers.get('Content-Type').startswith(b'text/html'):
            yield scrapy.Request(
                                response.xpath('//*[@id="redir_link"]/@href')[0].get(),
                                meta={'cookiejar': response.meta['cookiejar']},
                                dont_filter = True)
        else:
            filename = response.url.split('/')[-1]
            with open(filename,'wb') as f:
                f.write(response.body)
