from django.contrib.staticfiles.testing import StaticLiveServerTestCase
# from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium import webdriver


class MySeleniumTests(StaticLiveServerTestCase):
    fixtures = ['user-data.json']

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # cls.selenium = WebDriver()

        # Firefox driver
        firefox_options = webdriver.FirefoxOptions()
        firefox_options.headless = True

        # Chrome driver
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--disable-gpu')
        # options.add_argument('--window-size=1280x1696')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--hide-scrollbars')
        chrome_options.add_argument('--ignore-certificate-errors')
        # options.disablegpu = True        

        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("--disable-extensions")

        # Experimental options
        '''
        options.add_experimental_option(
            'prefs',
            {
                "download.default_directory": self._download_path,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True
            },
        )
        '''

        # options.set_capability("browserVersion", "67")
        # options.set_capability("platformName", "Windows XP")

        cls.selenium = webdriver.Remote(
            # command_executor="http://localhost:4444/wd/hub",
            command_executor="http://potato.local:4444/wd/hub",
            # options=chrome_options,
            # desired_capabilities=DesiredCapabilities.CHROME
            options=firefox_options,
            desired_capabilities=DesiredCapabilities.FIREFOX
        )
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_login(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/login/'))
        username_input = self.selenium.find_element_by_name("username")
        username_input.send_keys('bob')
        password_input = self.selenium.find_element_by_name("password")
        password_input.send_keys('bob')
        self.selenium.find_element_by_xpath('//input[@value="Log in"]').click()
